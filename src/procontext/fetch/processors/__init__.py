"""Fetch-time processor pipeline for fetched documentation content."""

from procontext.fetch.models import FetchedContent

from .base import HtmlProcessor
from .builtins import (
    SUPPORTED_HTML_PROCESSORS,
    build_html_processor,
    build_html_processor_pipeline,
    is_supported_html_processor,
)
from .pipeline import HtmlProcessorPipeline

__all__ = [
    "FetchedContent",
    "HtmlProcessor",
    "HtmlProcessorPipeline",
    "SUPPORTED_HTML_PROCESSORS",
    "build_html_processor",
    "build_html_processor_pipeline",
    "is_supported_html_processor",
]
