"""Shared fetch-layer models."""

from __future__ import annotations

from dataclasses import dataclass, replace
from urllib.parse import urlparse


@dataclass(frozen=True)
class FetchedContent:
    """Normalized fetched content passed through the processor pipeline."""

    original_url: str
    final_url: str
    body: bytes
    text_content: str
    content_type: str | None = None
    charset: str | None = None

    def with_text_content(self, text_content: str) -> FetchedContent:
        """Return a copy with updated text content."""
        return replace(self, text_content=text_content)

    def is_html(self) -> bool:
        """Return True when the fetched payload should be treated as HTML."""
        if self.content_type in {"text/html", "application/xhtml+xml"}:
            return True
        if self.content_type is not None:
            return False
        path = urlparse(self.final_url).path.lower()
        return path.endswith((".html", ".htm"))
