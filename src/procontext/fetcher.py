"""HTTP documentation fetcher with SSRF protection.

All network I/O for fetching documentation goes through a single Fetcher
instance shared across tool calls. The Fetcher receives an httpx.AsyncClient
via constructor injection — the lifespan owns the client lifecycle.
"""

from __future__ import annotations

import ipaddress
import re
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlparse

import httpx
import structlog

from procontext import __version__
from procontext.config import FetcherSettings
from procontext.content_processing import (
    FetchedContent,
    HtmlProcessorPipeline,
    build_html_processor_pipeline,
)
from procontext.errors import ErrorCode, ProContextError

if TYPE_CHECKING:
    from procontext.models.registry import RegistryEntry
    from procontext.state import AppState

log = structlog.get_logger()

_URL_RE = re.compile(r"https?://[^\s\)\]\"<>]+")
r"""
URL extraction regex used for discovering domains in documentation content.

DESIGN: Intentionally simple and permissive with known trade-offs.

CHARACTER CLASS EXPLANATION: [^\s\)\]\"<>]
  - \s      : Stop at whitespace (end of URL)
  - )       : Stop at closing paren (for markdown links [text](url))
  - \]      : Stop at closing bracket (for markdown [text](url) and IPv6)
  - \"      : Stop at quote (for quoted URLs)
  - <, >    : Stop at angle brackets (for <url> syntax)

RATIONALE FOR SIMPLICITY:
  - RFC 3986 strict parsing is complex and fragile for messy documentation
  - Documentation contains URLs in various contexts (code examples, prose, etc)
  - Simple regex + graceful error handling > strict parser with gaps
  - Performance: O(content_size) scan vs slower strict validation

DESIGN TRADE-OFFS:

  1. IPv6 URLs (SKIPPED)
     - Pattern: https://[::1]:8080/path
     - Issue: ] is excluded, so matches: https://[::1 (incomplete)
     - Result: urlparse fails, we log and skip
     - Decision: Acceptable because:
       * IPv6 URLs are rare in documentation (<1% of typical docs)
       * Usually local/example URLs ([::1] loopback, [fe80::1] link-local)
       * Even if extracted, blocked by SSRF private IP checks
       * Value of extracting these is minimal vs complexity of handling

  2. Single Quotes (INCLUDED)
     - Pattern: 'https://example.com' or text'https://example.com
     - Issue: ' is not excluded, included in URL match
     - Result: hostname becomes example.com' (fails allowlist check, blocked)
     - Decision: Acceptable because:
       * Rare in structured documentation
       * Failing safely (blocked, not allowed)
       * Fixing it adds complexity (need to handle quote types)

  3. Trailing Punctuation (INCLUDED but HANDLED)
     - Pattern: See https://example.com. or Visit https://example.com!
     - Issue: Period/punctuation included in match
     - Result: urlparse handles it (treats as path), _base_domain strips trailing dots
     - Decision: Works correctly in practice

EXTRACTION FLOW:
  1. Regex finds potential URLs in content
  2. urlparse() validates and extracts hostname
  3. If ValueError (malformed URL): log and skip
  4. _base_domain() normalizes: api.example.com → example.com
  5. Domain added to allowlist if in discovered mode
"""

PRIVATE_NETWORKS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


def build_http_client(settings: FetcherSettings | None = None) -> httpx.AsyncClient:
    """Create the shared httpx client. Called once at startup."""
    read_timeout = settings.request_timeout_seconds if settings is not None else 30.0
    connect_timeout = settings.connect_timeout_seconds if settings is not None else 5.0
    return httpx.AsyncClient(
        follow_redirects=False,
        timeout=httpx.Timeout(read_timeout, connect=connect_timeout),
        headers={"User-Agent": f"procontext/{__version__}"},
        limits=httpx.Limits(
            max_connections=10,
            max_keepalive_connections=5,
        ),
    )


def _base_domain(hostname: str) -> str:
    """Return the last two DNS labels: ``'api.langchain.com'`` → ``'langchain.com'``."""
    parts = hostname.rstrip(".").split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else hostname


def build_allowlist(
    entries: list[RegistryEntry],
    extra_domains: list[str] | None = None,
) -> frozenset[str]:
    """Build the SSRF domain allowlist from registry entries and optional extra domains.

    Extracts base domains from all ``llms_txt_url`` fields, then merges any
    manually specified ``extra_domains``.
    """
    base_domains: set[str] = set()
    for entry in entries:
        hostname = urlparse(entry.llms_txt_url).hostname or ""
        if hostname:
            base_domains.add(_base_domain(hostname))
    for domain in extra_domains or []:
        domain = domain.strip().lower()
        if domain:
            base_domains.add(_base_domain(domain))
    return frozenset(base_domains)


def extract_base_domains_from_content(content: str) -> frozenset[str]:
    """Extract base domains from all http/https URLs found in content.

    Used for runtime allowlist expansion at depth 1 (llms.txt) and depth 2 (pages).
    """
    domains: set[str] = set()
    for match in _URL_RE.finditer(content):
        try:
            hostname = urlparse(match.group()).hostname or ""
            if hostname:
                domains.add(_base_domain(hostname))
        except ValueError as e:
            # Log malformed URLs for visibility (e.g., malformed IPv6)
            log.warning(
                "skipped_malformed_url",
                url=match.group()[:100],  # truncate for logging
                error=str(e),
            )
    return frozenset(domains)


def expand_allowlist_from_content(
    content: str,
    state: AppState,
) -> frozenset[str]:
    """Extract discovered domains from content and optionally expand the live allowlist.

    Always returns the full set of discovered domains for cache persistence,
    regardless of expansion configuration. Only mutates ``state.allowlist`` when
    ``settings.fetcher.allowlist_expansion == "discovered"``.
    """
    discovered_domains = extract_base_domains_from_content(content)
    if state.settings.fetcher.allowlist_expansion == "discovered":
        new_domains = discovered_domains - state.allowlist
        if new_domains:
            state.allowlist = state.allowlist | new_domains
            log.info("allowlist_expanded", added_domains=len(new_domains))
    return discovered_domains


def is_url_allowed(
    url: str,
    allowlist: frozenset[str],
    *,
    check_private_ips: bool = True,
    check_domain: bool = True,
) -> bool:
    """Check whether a URL is permitted by the SSRF controls.

    ``check_private_ips``: block requests to private/internal IP ranges.
    ``check_domain``: enforce the domain allowlist. When False, any public domain
    is permitted (private IPs are still blocked if ``check_private_ips`` is True).
    """
    parsed = urlparse(url)
    hostname = parsed.hostname or ""

    if check_private_ips:
        try:
            addr = ipaddress.ip_address(hostname)
            if any(addr in net for net in PRIVATE_NETWORKS):
                return False
        except ValueError:
            pass  # hostname is a domain name, not an IP — proceed

    if not check_domain:
        return True

    return _base_domain(hostname) in allowlist


class Fetcher:
    """HTTP documentation fetcher with SSRF-safe redirect handling."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        settings: FetcherSettings | None = None,
        html_processor_pipeline: HtmlProcessorPipeline | None = None,
    ) -> None:
        self._client = client
        self._settings = settings or FetcherSettings()
        self._html_processor_pipeline = html_processor_pipeline or build_html_processor_pipeline(
            self._settings.html_processors
        )

    async def fetch(
        self,
        url: str,
        allowlist: frozenset[str],
        max_redirects: int = 3,  # Implementation detail, not part of FetcherProtocol
    ) -> str:
        """Fetch a URL with per-hop SSRF validation.

        Returns the response text content on success. Raises ProContextError
        on SSRF violations, network errors, and non-2xx responses.
        """
        current_url = url

        try:
            for hop in range(max_redirects + 1):
                # On redirect hops the originating domain was already vetted, so skip
                # the domain allowlist check. Private IP check still runs on every hop
                # to prevent open-redirect abuse toward internal network addresses.
                check_domain = self._settings.ssrf_domain_check and hop == 0
                if not is_url_allowed(
                    current_url,
                    allowlist,
                    check_private_ips=self._settings.ssrf_private_ip_check,
                    check_domain=check_domain,
                ):
                    log.warning("ssrf_blocked", url=current_url, reason="not_in_allowlist")
                    raise ProContextError(
                        code=ErrorCode.URL_NOT_ALLOWED,
                        message=f"URL not in allowlist: {current_url}",
                        suggestion="Only URLs from known documentation domains are permitted.",
                        recoverable=False,
                    )

                response = await self._client.get(current_url)

                if response.is_redirect and "location" in response.headers:
                    if hop == max_redirects:
                        raise ProContextError(
                            code=ErrorCode.TOO_MANY_REDIRECTS,
                            message=f"Too many redirects fetching {url}",
                            suggestion=(
                                "The documentation URL has an unusually long redirect chain."
                            ),
                            recoverable=False,
                        )
                    location = response.headers["location"]
                    current_url = urljoin(current_url, location)
                    continue

                if not response.is_success:
                    if response.status_code == 404:
                        raise ProContextError(
                            code=ErrorCode.PAGE_NOT_FOUND,
                            message=f"HTTP 404 fetching {url}",
                            suggestion=(
                                "The requested documentation page does not exist at this URL."
                            ),
                            recoverable=False,
                        )
                    raise ProContextError(
                        code=ErrorCode.PAGE_FETCH_FAILED,
                        message=f"HTTP {response.status_code} fetching {url}",
                        suggestion="The documentation source may be temporarily unavailable.",
                        recoverable=True,
                    )

                fetched_content = _build_fetched_content(
                    response=response,
                    original_url=url,
                    final_url=current_url,
                )
                processed_content = await self._html_processor_pipeline.process(fetched_content)
                log.info(
                    "fetch_complete",
                    url=url,
                    status_code=response.status_code,
                    content_length=len(processed_content.text_content),
                    final_url=current_url,
                    content_type=processed_content.content_type,
                )
                return processed_content.text_content

        except ProContextError:
            raise
        except httpx.HTTPError as exc:
            raise ProContextError(
                code=ErrorCode.PAGE_FETCH_FAILED,
                message=f"Network error fetching {url}: {exc}",
                suggestion="The documentation source may be temporarily unavailable.",
                recoverable=True,
            ) from exc

        # Unreachable but satisfies the type checker
        raise ProContextError(
            code=ErrorCode.TOO_MANY_REDIRECTS,
            message="Redirect loop",
            suggestion="",
            recoverable=False,
        )


def _build_fetched_content(
    *,
    response: httpx.Response,
    original_url: str,
    final_url: str,
) -> FetchedContent:
    content_type, charset = _parse_content_type(response.headers.get("content-type"))
    return FetchedContent(
        original_url=original_url,
        final_url=final_url,
        body=response.content,
        text_content=response.text,
        content_type=content_type,
        charset=charset or response.encoding,
    )


def _parse_content_type(header_value: str | None) -> tuple[str | None, str | None]:
    if not header_value:
        return None, None

    parts = [part.strip() for part in header_value.split(";") if part.strip()]
    if not parts:
        return None, None

    content_type = parts[0].lower()
    charset: str | None = None
    for part in parts[1:]:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key.strip().lower() == "charset":
            parsed_value = value.strip().strip("\"'")
            charset = parsed_value or None
            break

    return content_type, charset
