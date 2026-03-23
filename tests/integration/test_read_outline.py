"""Integration tests for the read_outline tool handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest
import respx

from procontext.errors import ErrorCode, ProContextError
from procontext.tools.read_outline import handle as read_outline_handle
from procontext.tools.read_page import handle as read_page_handle
from tests.integration.tool_test_support import SAMPLE_PAGE, SAMPLE_URL, SETEXT_PAGE, SETEXT_URL

if TYPE_CHECKING:
    from procontext.state import AppState


class TestReadOutlineHandler:
    """Full handler pipeline tests for read_outline."""

    @respx.mock
    async def test_basic_outline(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        result = await read_outline_handle(SAMPLE_URL, 1, 200, app_state)

        assert result["url"] == SAMPLE_URL
        assert result["total_entries"] > 0
        assert "# Streaming" in result["outline"]
        assert result["cached"] is False

    @respx.mock
    async def test_output_contains_all_fields(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        result = await read_outline_handle(SAMPLE_URL, 1, 200, app_state)
        assert set(result.keys()) == {
            "url",
            "outline",
            "total_entries",
            "has_more",
            "next_offset",
            "content_hash",
            "cached",
            "cached_at",
            "stale",
        }

    @respx.mock
    async def test_pagination(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        result = await read_outline_handle(SAMPLE_URL, 1, 2, app_state)
        assert result["outline"] == "1:# Streaming"
        assert result["has_more"] is True
        assert result["next_offset"] == 3

        result2 = await read_outline_handle(SAMPLE_URL, result["next_offset"], 2, app_state)
        assert result2["cached"] is True
        assert result2["outline"] == "3:## Overview"

    @respx.mock
    async def test_offset_beyond_total_lines(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        result = await read_outline_handle(SAMPLE_URL, 9999, 200, app_state)
        assert result["outline"] == ""
        assert result["has_more"] is False
        assert result["next_offset"] is None
        assert result["total_entries"] > 0

    @respx.mock
    async def test_cache_shared_with_read_page(self, app_state: AppState) -> None:
        """read_page populates cache, read_outline uses it."""
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        await read_page_handle(SAMPLE_URL, 1, 500, app_state)
        assert respx.calls.call_count == 1

        result = await read_outline_handle(SAMPLE_URL, 1, 200, app_state)
        assert result["cached"] is True
        assert respx.calls.call_count == 1

    async def test_url_not_allowed_raises(self, app_state: AppState) -> None:
        evil_url = "https://evil.example.com/docs.md"
        with pytest.raises(ProContextError) as exc_info:
            await read_outline_handle(evil_url, 1, 200, app_state)
        assert exc_info.value.code == ErrorCode.URL_NOT_ALLOWED

    async def test_negative_before_raises_invalid_input(self, app_state: AppState) -> None:
        with pytest.raises(ProContextError) as exc_info:
            await read_outline_handle(SAMPLE_URL, 1, 200, app_state, before=-1)
        assert exc_info.value.code == ErrorCode.INVALID_INPUT

    @respx.mock
    async def test_large_limit_accepted(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))
        result = await read_outline_handle(SAMPLE_URL, 1, 5000, app_state)
        assert result["url"] == SAMPLE_URL

    @respx.mock
    async def test_before_includes_earlier_outline_entries(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        result = await read_outline_handle(SAMPLE_URL, 11, 1, app_state, before=8)

        assert result["outline"] == (
            "3:## Overview\n7:## Streaming with Chat Models\n11:### Using .stream()"
        )
        assert result["next_offset"] == 12

    @respx.mock
    async def test_before_clamps_at_top_of_file(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        result = await read_outline_handle(SAMPLE_URL, 3, 1, app_state, before=10)

        assert result["outline"] == "1:# Streaming\n3:## Overview"
        assert result["next_offset"] == 4

    @respx.mock
    async def test_before_near_eof_keeps_next_offset_null(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        result = await read_outline_handle(SAMPLE_URL, 19, 5, app_state, before=2)

        assert result["outline"] == "19:## Streaming with Chains"
        assert result["has_more"] is False
        assert result["next_offset"] is None

    @respx.mock
    async def test_sparse_pagination_uses_page_line_continuation(self, app_state: AppState) -> None:
        respx.get(SETEXT_URL).mock(return_value=httpx.Response(200, text=SETEXT_PAGE))

        first = await read_outline_handle(SETEXT_URL, 1, 1, app_state)
        second = await read_outline_handle(SETEXT_URL, first["next_offset"], 1, app_state)
        third = await read_outline_handle(SETEXT_URL, second["next_offset"], 1, app_state)
        fourth = await read_outline_handle(SETEXT_URL, third["next_offset"], 1, app_state)

        assert first["outline"] == "1:# Main Title"
        assert first["has_more"] is True
        assert first["next_offset"] == 2
        assert second["outline"] == ""
        assert second["has_more"] is True
        assert second["next_offset"] == 3
        assert third["outline"] == ""
        assert third["has_more"] is True
        assert third["next_offset"] == 4
        assert fourth["outline"] == "4:## Section Title"
