"""HTML content processing pipeline for fetched documentation pages."""

from .base import HtmlProcessor
from .payload import FetchedContent
from .pipeline import HtmlProcessorPipeline
from .registry import (
    SUPPORTED_HTML_PROCESSORS,
    build_html_processor,
    build_html_processor_pipeline,
    is_supported_html_processor,
)

__all__ = [
    "FetchedContent",
    "HtmlProcessor",
    "HtmlProcessorPipeline",
    "SUPPORTED_HTML_PROCESSORS",
    "build_html_processor",
    "build_html_processor_pipeline",
    "is_supported_html_processor",
]
