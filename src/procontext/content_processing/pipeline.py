"""Processor pipeline for fetched HTML content."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .base import HtmlProcessor
    from .payload import FetchedContent

log = structlog.get_logger()


class HtmlProcessorPipeline:
    """Run configured HTML processors in order."""

    def __init__(self, processors: Sequence[HtmlProcessor]) -> None:
        self._processors = tuple(processors)

    async def process(self, payload: FetchedContent) -> FetchedContent:
        """Process a fetched payload through all configured processors."""
        current = payload
        for processor in self._processors:
            if not processor.applies_to(current):
                continue
            try:
                current = await processor.transform(current)
            except Exception:
                log.warning(
                    "html_processor_failed",
                    processor=processor.name,
                    url=current.final_url,
                    exc_info=True,
                )
        return current
