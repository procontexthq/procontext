"""HTTP client construction for the fetch layer."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from procontext import __version__

if TYPE_CHECKING:
    from procontext.config import FetcherSettings


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
