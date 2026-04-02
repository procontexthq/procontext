"""Unit tests for fetched-content processing."""

from __future__ import annotations

from dataclasses import replace

import pytest

from procontext.fetch.models import FetchedContent
from procontext.fetch.processors import (
    HtmlProcessorPipeline,
    build_html_processor,
)


class _PrefixProcessor:
    name = "prefix"

    def applies_to(self, payload: FetchedContent) -> bool:
        return True

    async def transform(self, payload: FetchedContent) -> FetchedContent:
        return replace(payload, text_content="prefix:" + payload.text_content)


class _SuffixProcessor:
    name = "suffix"

    def applies_to(self, payload: FetchedContent) -> bool:
        return True

    async def transform(self, payload: FetchedContent) -> FetchedContent:
        return replace(payload, text_content=payload.text_content + ":suffix")


class _NeverProcessor:
    name = "never"

    def applies_to(self, payload: FetchedContent) -> bool:
        return False

    async def transform(self, payload: FetchedContent) -> FetchedContent:
        return replace(payload, text_content="should-not-run")


async def test_html_processor_pipeline_runs_processors_in_order() -> None:
    pipeline = HtmlProcessorPipeline([_PrefixProcessor(), _SuffixProcessor()])
    payload = FetchedContent(
        original_url="https://example.com/page",
        final_url="https://example.com/page",
        body=b"body",
        text_content="content",
        content_type="text/html",
        charset="utf-8",
    )

    result = await pipeline.process(payload)

    assert result.text_content == "prefix:content:suffix"


async def test_html_processor_pipeline_skips_non_applicable_processors() -> None:
    pipeline = HtmlProcessorPipeline([_NeverProcessor(), _SuffixProcessor()])
    payload = FetchedContent(
        original_url="https://example.com/page",
        final_url="https://example.com/page",
        body=b"body",
        text_content="content",
        content_type="text/html",
        charset="utf-8",
    )

    result = await pipeline.process(payload)

    assert result.text_content == "content:suffix"


def test_build_html_processor_instantiates_markitdown() -> None:
    processor = build_html_processor("markitdown")
    assert processor.name == "markitdown"


def test_build_html_processor_unknown_name_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported HTML processor"):
        build_html_processor("unknown")
