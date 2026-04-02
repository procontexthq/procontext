"""HTTP documentation fetcher with SSRF-safe redirect handling."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urljoin

import httpx
import structlog

from procontext.config import FetcherSettings
from procontext.errors import ErrorCode, ProContextError
from procontext.fetch.models import FetchedContent
from procontext.fetch.processors import HtmlProcessorPipeline, build_html_processor_pipeline
from procontext.fetch.security import is_url_allowed

if TYPE_CHECKING:
    from httpx import Response

log = structlog.get_logger()


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
        max_redirects: int = 3,
    ) -> str:
        """Fetch a URL with per-hop SSRF validation."""
        current_url = url

        try:
            for hop in range(max_redirects + 1):
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
                    current_url = urljoin(current_url, response.headers["location"])
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

        raise ProContextError(
            code=ErrorCode.TOO_MANY_REDIRECTS,
            message="Redirect loop",
            suggestion="",
            recoverable=False,
        )


def _build_fetched_content(
    *,
    response: Response,
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
