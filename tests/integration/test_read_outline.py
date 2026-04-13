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
        }

    @respx.mock
    async def test_limit_counts_outline_entries(self, app_state: AppState) -> None:
        """limit=2 returns exactly 2 outline entries, not a 2-line page window."""
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        result = await read_outline_handle(SAMPLE_URL, 1, 2, app_state)

        # 2 entries: line 1 (# Streaming) and line 3 (## Overview)
        assert result["outline"] == "1:# Streaming\n3:## Overview"
        assert result["has_more"] is True
        # next_offset points to the next entry's line number (7), not 4
        assert result["next_offset"] == 7

    @respx.mock
    async def test_pagination_chains_via_next_offset(self, app_state: AppState) -> None:
        """Paginating with next_offset chains correctly across calls."""
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        first = await read_outline_handle(SAMPLE_URL, 1, 2, app_state)
        assert first["outline"] == "1:# Streaming\n3:## Overview"
        assert first["next_offset"] == 7

        second = await read_outline_handle(SAMPLE_URL, first["next_offset"], 2, app_state)
        assert second["outline"] == "7:## Streaming with Chat Models\n11:### Using .stream()"
        assert second["next_offset"] == 15

        third = await read_outline_handle(SAMPLE_URL, second["next_offset"], 2, app_state)
        assert third["outline"] == "15:### Using .astream()\n19:## Streaming with Chains"
        assert third["has_more"] is False
        assert third["next_offset"] is None

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
        assert result["total_entries"] > 0
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
    async def test_before_counts_outline_entries(self, app_state: AppState) -> None:
        """before=2 includes 2 outline entries before offset, not 2 page lines."""
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        # offset=11 lands on "### Using .stream()" (4th entry)
        # before=2 should include 2 entries before it: ## Overview (line 3)
        # and ## Streaming with Chat Models (line 7)
        # limit=1 takes 1 forward entry: ### Using .stream() (line 11)
        result = await read_outline_handle(SAMPLE_URL, 11, 1, app_state, before=2)

        assert result["outline"] == (
            "3:## Overview\n7:## Streaming with Chat Models\n11:### Using .stream()"
        )
        assert result["next_offset"] == 15

    @respx.mock
    async def test_before_clamps_at_start(self, app_state: AppState) -> None:
        """before larger than available entries clamps to all earlier entries."""
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        # offset=3 is "## Overview" (2nd entry), before=10 but only 1 entry before it
        result = await read_outline_handle(SAMPLE_URL, 3, 1, app_state, before=10)

        assert result["outline"] == "1:# Streaming\n3:## Overview"
        assert result["next_offset"] == 7

    @respx.mock
    async def test_before_near_eof_keeps_next_offset_null(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        # offset=19 is last entry, limit=5 but only 1 entry available
        result = await read_outline_handle(SAMPLE_URL, 19, 5, app_state, before=2)

        # before=2 includes ### Using .stream() (line 11) and ### Using .astream() (line 15)
        assert result["outline"] == (
            "11:### Using .stream()\n15:### Using .astream()\n19:## Streaming with Chains"
        )
        assert result["has_more"] is False
        assert result["next_offset"] is None

    @respx.mock
    async def test_sparse_entries_no_empty_pages(self, app_state: AppState) -> None:
        """Sparse outlines never produce empty results when entries exist ahead."""
        respx.get(SETEXT_URL).mock(return_value=httpx.Response(200, text=SETEXT_PAGE))

        # SETEXT entries: 1:# Main Title, 4:## Section Title, 9:## Tail
        first = await read_outline_handle(SETEXT_URL, 1, 1, app_state)
        assert first["outline"] == "1:# Main Title"
        assert first["has_more"] is True
        # next_offset jumps to the next entry (line 4), not line 2
        assert first["next_offset"] == 4

        second = await read_outline_handle(SETEXT_URL, first["next_offset"], 1, app_state)
        assert second["outline"] == "4:## Section Title"
        assert second["has_more"] is True
        assert second["next_offset"] == 9

        third = await read_outline_handle(SETEXT_URL, second["next_offset"], 1, app_state)
        assert third["outline"] == "9:## Tail"
        assert third["has_more"] is False
        assert third["next_offset"] is None

    @respx.mock
    async def test_offset_between_entries_starts_at_next_entry(self, app_state: AppState) -> None:
        """Offset on a non-entry line finds the next entry at or after it."""
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        # offset=5 is between ## Overview (3) and ## Streaming with Chat Models (7)
        result = await read_outline_handle(SAMPLE_URL, 5, 2, app_state)

        assert result["outline"] == ("7:## Streaming with Chat Models\n11:### Using .stream()")
        assert result["next_offset"] == 15

    @respx.mock
    async def test_default_limit_is_500(self, app_state: AppState) -> None:
        """Default limit returns all entries for small outlines."""
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        # Call without explicit limit — default should be 500
        result = await read_outline_handle(SAMPLE_URL, 1, 500, app_state)

        assert result["total_entries"] == 6
        assert result["has_more"] is False
