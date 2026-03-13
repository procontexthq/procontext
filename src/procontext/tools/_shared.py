"""Shared fetch logic for page-based tools (read_page, search_page).

Encapsulates the full cache-check → fetch → cache-write flow. Tool handlers
call ``fetch_or_cached_page`` and then apply their own output formatting on
the result.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from os.path import splitext
from typing import TYPE_CHECKING
from urllib.parse import urlparse, urlunparse

import structlog

from procontext.errors import ErrorCode, ProContextError
from procontext.fetcher import expand_allowlist_from_content, is_url_allowed
from procontext.parser import parse_outline

if TYPE_CHECKING:
    from datetime import datetime

    from procontext.state import AppState

log = structlog.get_logger()


@dataclass(frozen=True)
class FetchResult:
    """Immutable result from ``fetch_or_cached_page``."""

    url: str
    content: str
    outline: str
    cached: bool
    cached_at: datetime | None
    stale: bool


async def fetch_or_cached_page(url: str, state: AppState) -> FetchResult:
    """Cache-check → network fetch → cache-write for a single page URL.

    Handles SSRF validation, cache lookup, .md probing, outline parsing,
    allowlist expansion, and cache write. When a cached entry has expired,
    a synchronous re-fetch is attempted; on failure the stale content is
    returned as a fallback.

    Raises:
        RuntimeError: if cache or fetcher are not initialised.
        ProContextError: for SSRF violations and network fetch failures.
    """
    if state.cache is None or state.fetcher is None:
        raise RuntimeError("Cache and fetcher must be initialized")

    # SSRF check — must happen before cache lookup so that pages from
    # domains removed from the allowlist are not served from cache.
    if not is_url_allowed(
        url,
        state.allowlist,
        check_private_ips=state.settings.fetcher.ssrf_private_ip_check,
        check_domain=state.settings.fetcher.ssrf_domain_check,
    ):
        log.warning("ssrf_blocked", url=url, reason="not_in_allowlist")
        raise ProContextError(
            code=ErrorCode.URL_NOT_ALLOWED,
            message=f"URL not in allowlist: {url}",
            suggestion="Only URLs from known documentation domains are permitted.",
            recoverable=False,
        )

    url_hash = hashlib.sha256(url.encode()).hexdigest()

    # Cache check
    cached_entry = await state.cache.get_page(url_hash)

    if cached_entry is not None and not cached_entry.stale:
        log.info("cache_hit", stale=False, url=url)
        return FetchResult(
            url=cached_entry.url,
            content=cached_entry.content,
            outline=cached_entry.outline,
            cached=True,
            cached_at=cached_entry.fetched_at,
            stale=False,
        )

    if cached_entry is not None and cached_entry.stale:
        log.info("cache_stale_refetching", url=url)
        try:
            return await _fetch_and_cache(url, url_hash, state)
        except Exception:
            log.warning("stale_refetch_failed_serving_cached", url=url, exc_info=True)
            return FetchResult(
                url=cached_entry.url,
                content=cached_entry.content,
                outline=cached_entry.outline,
                cached=True,
                cached_at=cached_entry.fetched_at,
                stale=True,
            )

    # Cache miss — fetch from network.
    return await _fetch_and_cache(url, url_hash, state)


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


async def _fetch_and_cache(url: str, url_hash: str, state: AppState) -> FetchResult:
    """Fetch a page from the network, cache it, and return a FetchResult."""
    assert state.cache is not None

    content = await _fetch_with_md_probe(url, state)
    outline = parse_outline(content)

    log.info("fetch_complete", url=url, content_length=len(content))

    discovered_domains = expand_allowlist_from_content(content, state)

    await state.cache.set_page(
        url=url,
        url_hash=url_hash,
        content=content,
        outline=outline,
        ttl_hours=state.settings.cache.ttl_hours,
        discovered_domains=discovered_domains,
    )

    return FetchResult(
        url=url,
        content=content,
        outline=outline,
        cached=False,
        cached_at=None,
        stale=False,
    )


async def _fetch_with_md_probe(url: str, state: AppState) -> str:
    """Fetch page content, trying .md variant first when applicable."""
    assert state.fetcher is not None
    if _should_probe_md(url):
        md_url = _with_md_extension(url)
        try:
            log.info("cache_miss_fetching", url=md_url)
            return await state.fetcher.fetch(md_url, state.allowlist)
        except Exception:
            log.info("md_probe_failed_falling_back", md_url=md_url, fallback_url=url)

    log.info("cache_miss_fetching", url=url)
    return await state.fetcher.fetch(url, state.allowlist)


def _with_md_extension(url: str) -> str:
    """Return the URL with .md appended to the path component.

    Appends before any query string or fragment so the server receives the
    correct path, e.g. ``/docs/page#section`` → ``/docs/page.md#section``.
    """
    parsed = urlparse(url)
    return urlunparse(parsed._replace(path=parsed.path + ".md"))


def _should_probe_md(url: str) -> bool:
    """Return True if the URL is a candidate for .md probing.

    Probing is skipped when:
    - The URL already has a real alphabetic file extension (.md, .txt, .html, …)
    - The path ends with a trailing slash or has no path (appending .md would
      corrupt the URL, e.g. ``/docs/.md``)
    - The URL has a query string — static file servers that serve raw markdown
      don't use query parameters, so the probe would always 404

    Version segments like ``v1.2`` are NOT treated as extensions because the
    part after the dot is numeric, not alphabetic.
    """
    parsed = urlparse(url)
    if parsed.query:
        return False
    last_segment = parsed.path.rsplit("/", 1)[-1]
    if not last_segment:
        return False
    _, ext = splitext(last_segment)
    return not (bool(ext) and ext[1:].isalpha())
