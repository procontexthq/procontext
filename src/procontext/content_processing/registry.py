"""Built-in HTML processor registry."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .pipeline import HtmlProcessorPipeline

if TYPE_CHECKING:
    from .base import HtmlProcessor

SUPPORTED_HTML_PROCESSORS = frozenset({"markitdown"})


def is_supported_html_processor(name: str) -> bool:
    """Return True when a built-in HTML processor name is supported."""
    return name in SUPPORTED_HTML_PROCESSORS


def build_html_processor(name: str) -> HtmlProcessor:
    """Instantiate a built-in HTML processor by name."""
    if name == "markitdown":
        from .markitdown_processor import MarkItDownHtmlProcessor

        return MarkItDownHtmlProcessor()
    raise ValueError(f"Unsupported HTML processor: {name}")


def build_html_processor_pipeline(names: list[str]) -> HtmlProcessorPipeline:
    """Build a processor pipeline from configured processor names."""
    return HtmlProcessorPipeline([build_html_processor(name) for name in names])
