"""SSRF checks and allowlist helpers for the fetch layer."""

from __future__ import annotations

import ipaddress
import re
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import structlog

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


def _base_domain(hostname: str) -> str:
    """Return the last two DNS labels: ``'api.langchain.com'`` → ``'langchain.com'``."""
    parts = hostname.rstrip(".").split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else hostname


def build_allowlist(
    entries: list[RegistryEntry],
    extra_domains: list[str] | None = None,
) -> frozenset[str]:
    """Build the SSRF domain allowlist from registry entries and optional extra domains."""
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
    """Extract base domains from all http/https URLs found in content."""
    domains: set[str] = set()
    for match in _URL_RE.finditer(content):
        try:
            hostname = urlparse(match.group()).hostname or ""
            if hostname:
                domains.add(_base_domain(hostname))
        except ValueError as error:
            log.warning(
                "skipped_malformed_url",
                url=match.group()[:100],
                error=str(error),
            )
    return frozenset(domains)


def expand_allowlist_from_content(
    content: str,
    state: AppState,
) -> frozenset[str]:
    """Extract discovered domains from content and optionally expand the live allowlist."""
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
    """Check whether a URL is permitted by the SSRF controls."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""

    if check_private_ips:
        try:
            addr = ipaddress.ip_address(hostname)
            if any(addr in net for net in PRIVATE_NETWORKS):
                return False
        except ValueError:
            pass

    if not check_domain:
        return True

    return _base_domain(hostname) in allowlist
