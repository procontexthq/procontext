"""Integration tests for the read_page tool handler."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import anyio
import httpx
import pytest
import respx

from procontext.config import FetcherSettings, Settings
from procontext.errors import ErrorCode, ProContextError
from procontext.fetch.service import Fetcher
from procontext.tools.read_page import handle as read_page_handle
from tests.integration.tool_test_support import (
    SAMPLE_PAGE,
    SAMPLE_URL,
    SETEXT_PAGE,
    SETEXT_URL,
    expire_cached_page,
    update_cached_page_content,
)

if TYPE_CHECKING:
    from procontext.state import AppState


class TestReadPageHandler:
    """Full handler pipeline tests for read_page."""

    @respx.mock
    async def test_cache_miss_fetches_and_returns(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        result = await read_page_handle(SAMPLE_URL, 1, 500, app_state)

        assert result["url"] == SAMPLE_URL
        assert result["cached"] is False
        assert result["cached_at"] is None
        assert result["stale"] is False
        assert result["total_lines"] == 21
        assert "# Streaming" in result["outline"]
        assert "## Overview" in result["outline"]
        assert "# Streaming" in result["content"]

    @respx.mock
    async def test_extensionless_url_is_fetched_as_is(self, app_state: AppState) -> None:
        url = "https://python.langchain.com/docs/concepts/streaming"
        respx.get(url).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        result = await read_page_handle(url, 1, 500, app_state)

        assert result["url"] == url
        assert result["cached"] is False
        assert respx.calls.call_count == 1
        assert str(respx.calls[0].request.url) == url

    @respx.mock
    async def test_html_pages_are_cached_as_markdown(self, app_state: AppState) -> None:
        url = "https://python.langchain.com/docs/concepts/html-page"
        html = "<html><body><h1>Title</h1><p>Hello <strong>world</strong>.</p></body></html>"
        respx.get(url).mock(
            return_value=httpx.Response(
                200,
                text=html,
                headers={"content-type": "text/html; charset=utf-8"},
            )
        )

        result = await read_page_handle(url, 1, 500, app_state)

        assert result["cached"] is False
        assert result["content"] == "# Title\n\nHello **world**."
        assert "1:# Title" in result["outline"]

    @respx.mock
    async def test_html_pages_return_raw_html_when_processors_disabled(
        self, app_state: AppState
    ) -> None:
        url = "https://python.langchain.com/docs/concepts/html-page-raw"
        html = "<html><body><h1>Title</h1><p>Hello <strong>world</strong>.</p></body></html>"
        respx.get(url).mock(
            return_value=httpx.Response(
                200,
                text=html,
                headers={"content-type": "text/html; charset=utf-8"},
            )
        )

        assert app_state.http_client is not None
        app_state.settings = Settings(fetcher=FetcherSettings(html_processors=[]))
        app_state.fetcher = Fetcher(app_state.http_client, app_state.settings.fetcher)

        result = await read_page_handle(url, 1, 500, app_state)

        assert result["cached"] is False
        assert result["content"] == html

    @respx.mock
    async def test_cache_hit_returns_cached(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        await read_page_handle(SAMPLE_URL, 1, 500, app_state)

        result = await read_page_handle(SAMPLE_URL, 1, 500, app_state)
        assert result["cached"] is True
        assert result["cached_at"] is not None
        assert result["stale"] is False
        assert respx.calls.call_count == 1

    @respx.mock
    async def test_equivalent_host_case_and_default_port_share_cache(
        self, app_state: AppState
    ) -> None:
        variant_url = "HTTPS://PYTHON.LANGCHAIN.COM:443/docs/concepts/streaming.md"
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        first = await read_page_handle(variant_url, 1, 500, app_state)
        second = await read_page_handle(SAMPLE_URL, 1, 500, app_state)

        assert first["url"] == SAMPLE_URL
        assert first["cached"] is False
        assert second["url"] == SAMPLE_URL
        assert second["cached"] is True
        assert respx.calls.call_count == 1

    @respx.mock
    async def test_trailing_slash_url_uses_distinct_cache_entry(self, app_state: AppState) -> None:
        without_slash = "https://python.langchain.com/docs/concepts?view=raw"
        with_slash = "https://python.langchain.com/docs/concepts/?view=raw"
        respx.get(without_slash).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))
        respx.get(with_slash).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        first = await read_page_handle(without_slash, 1, 500, app_state)
        second = await read_page_handle(with_slash, 1, 500, app_state)
        third = await read_page_handle(without_slash, 1, 500, app_state)
        fourth = await read_page_handle(with_slash, 1, 500, app_state)

        assert first["url"] == without_slash
        assert first["cached"] is False
        assert second["url"] == with_slash
        assert second["cached"] is False
        assert third["cached"] is True
        assert fourth["cached"] is True
        assert respx.calls.call_count == 2

    @respx.mock
    async def test_stale_cache_serves_stale_immediately(
        self,
        app_state: AppState,
    ) -> None:
        """Expired cache returns stale content immediately and spawns background refresh."""
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        await read_page_handle(SAMPLE_URL, 1, 500, app_state)
        await expire_cached_page(app_state)

        result = await read_page_handle(SAMPLE_URL, 1, 500, app_state)
        assert result["cached"] is True
        assert result["stale"] is True
        assert "# Streaming" in result["content"]

    @respx.mock
    async def test_stale_background_refresh_updates_cache(
        self,
        app_state: AppState,
    ) -> None:
        """Background refresh updates the cache so the next call gets fresh content."""
        updated_page = "# Updated\n\nNew content."
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        await read_page_handle(SAMPLE_URL, 1, 500, app_state)
        await expire_cached_page(app_state)

        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=updated_page))

        result = await read_page_handle(SAMPLE_URL, 1, 500, app_state)
        assert result["stale"] is True

        with anyio.fail_after(5):
            while True:
                result2 = await read_page_handle(SAMPLE_URL, 1, 500, app_state)
                if result2["cached"] is True and result2["stale"] is False:
                    assert "# Updated" in result2["content"]
                    break
                await anyio.sleep(0)

    @respx.mock
    async def test_content_hash_present_and_stable(self, app_state: AppState) -> None:
        """content_hash is a 12-char hex string, consistent across calls."""
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        result1 = await read_page_handle(SAMPLE_URL, 1, 500, app_state)
        assert len(result1["content_hash"]) == 12
        assert all(char in "0123456789abcdef" for char in result1["content_hash"])

        result2 = await read_page_handle(SAMPLE_URL, 1, 500, app_state)
        assert result1["content_hash"] == result2["content_hash"]

    @respx.mock
    async def test_content_hash_changes_when_content_changes(self, app_state: AppState) -> None:
        """content_hash differs when the underlying page content changes."""
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        result1 = await read_page_handle(SAMPLE_URL, 1, 500, app_state)
        await update_cached_page_content(app_state, "# Different content\n\nChanged.")

        result2 = await read_page_handle(SAMPLE_URL, 1, 500, app_state)
        assert result1["content_hash"] != result2["content_hash"]

    @respx.mock
    async def test_stale_no_duplicate_background_tasks(
        self,
        app_state: AppState,
    ) -> None:
        """Repeated stale reads return cached stale data while refresh happens in the background."""
        updated_page = "# Updated once\n\nNew content."
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        await read_page_handle(SAMPLE_URL, 1, 500, app_state)
        await expire_cached_page(app_state)

        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=updated_page))

        first_stale = await read_page_handle(SAMPLE_URL, 1, 500, app_state)
        second_stale = await read_page_handle(SAMPLE_URL, 1, 500, app_state)

        assert first_stale["stale"] is True
        assert second_stale["stale"] is True
        assert respx.calls.call_count == 2

        with anyio.fail_after(5):
            while True:
                refreshed = await read_page_handle(SAMPLE_URL, 1, 500, app_state)
                if refreshed["stale"] is False:
                    assert "# Updated once" in refreshed["content"]
                    break
                await anyio.sleep(0)

    @respx.mock
    async def test_stale_respects_last_checked_cooldown(self, app_state: AppState) -> None:
        """Recently-checked stale entries don't trigger background refresh."""
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        await read_page_handle(SAMPLE_URL, 1, 500, app_state)
        await expire_cached_page(app_state, last_checked_at=datetime.now(UTC).isoformat())

        result = await read_page_handle(SAMPLE_URL, 1, 500, app_state)
        assert result["stale"] is True
        assert respx.calls.call_count == 1

    @respx.mock
    async def test_windowing_offset_and_limit(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        result = await read_page_handle(SAMPLE_URL, 3, 3, app_state)
        lines = result["content"].split("\n")
        assert len(lines) == 3
        assert lines[0] == "## Overview"
        assert result["offset"] == 3
        assert result["limit"] == 3

    @respx.mock
    async def test_before_includes_backward_context_without_reducing_limit(
        self, app_state: AppState
    ) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        result = await read_page_handle(SAMPLE_URL, 7, 3, app_state, before=2)

        assert result["offset"] == 5
        assert result["limit"] == 3
        assert result["content"].split("\n") == [
            "LangChain supports streaming.",
            "",
            "## Streaming with Chat Models",
            "",
            "Details here.",
        ]
        assert result["next_offset"] == 10

    @respx.mock
    async def test_before_clamps_window_start_at_top_of_file(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        result = await read_page_handle(SAMPLE_URL, 2, 2, app_state, before=10)

        assert result["offset"] == 1
        assert result["content"].split("\n") == ["# Streaming", "", "## Overview"]
        assert result["next_offset"] == 4

    @respx.mock
    async def test_before_near_eof_keeps_next_offset_null(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        result = await read_page_handle(SAMPLE_URL, 20, 5, app_state, before=2)

        assert result["offset"] == 18
        assert result["has_more"] is False
        assert result["next_offset"] is None
        assert result["content"].split("\n") == [
            "",
            "## Streaming with Chains",
            "",
            "Chain streaming details.",
        ]

    @respx.mock
    async def test_has_more_true_when_content_remains(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        result = await read_page_handle(SAMPLE_URL, 1, 5, app_state)
        assert result["has_more"] is True
        assert result["next_offset"] == 6

    @respx.mock
    async def test_has_more_false_when_window_covers_all(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        result = await read_page_handle(SAMPLE_URL, 1, 500, app_state)
        assert result["has_more"] is False
        assert result["next_offset"] is None

    @respx.mock
    async def test_has_more_false_at_exact_boundary(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        total_lines = len(SAMPLE_PAGE.splitlines())
        result = await read_page_handle(SAMPLE_URL, 1, total_lines, app_state)
        assert result["has_more"] is False
        assert result["next_offset"] is None

    @respx.mock
    async def test_outline_always_full_page(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        result = await read_page_handle(SAMPLE_URL, 1, 2, app_state)
        assert "## Streaming with Chains" in result["outline"]

    @respx.mock
    async def test_total_lines_correct(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        result = await read_page_handle(SAMPLE_URL, 1, 500, app_state)
        assert result["total_lines"] == len(SAMPLE_PAGE.splitlines())

    @respx.mock
    async def test_url_not_in_allowlist_raises(self, app_state: AppState) -> None:
        evil_url = "https://evil.example.com/docs.md"
        respx.get(evil_url).mock(return_value=httpx.Response(200, text="# Evil"))

        with pytest.raises(ProContextError) as exc_info:
            await read_page_handle(evil_url, 1, 500, app_state)
        assert exc_info.value.code == ErrorCode.URL_NOT_ALLOWED
        assert exc_info.value.recoverable is False

    @respx.mock
    async def test_404_raises_page_not_found(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(404))

        with pytest.raises(ProContextError) as exc_info:
            await read_page_handle(SAMPLE_URL, 1, 500, app_state)
        assert exc_info.value.code == ErrorCode.PAGE_NOT_FOUND
        assert exc_info.value.recoverable is False

    @respx.mock
    async def test_network_error_raises_fetch_failed(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(503))

        with pytest.raises(ProContextError) as exc_info:
            await read_page_handle(SAMPLE_URL, 1, 500, app_state)
        assert exc_info.value.code == ErrorCode.PAGE_FETCH_FAILED
        assert exc_info.value.recoverable is True

    @respx.mock
    async def test_too_many_redirects_raises_redirect_error(self, app_state: AppState) -> None:
        redirect1 = "https://python.langchain.com/docs/concepts/r1.md"
        redirect2 = "https://python.langchain.com/docs/concepts/r2.md"
        redirect3 = "https://python.langchain.com/docs/concepts/r3.md"
        redirect4 = "https://python.langchain.com/docs/concepts/r4.md"
        respx.get(SAMPLE_URL).mock(
            return_value=httpx.Response(301, headers={"location": redirect1})
        )
        respx.get(redirect1).mock(return_value=httpx.Response(301, headers={"location": redirect2}))
        respx.get(redirect2).mock(return_value=httpx.Response(301, headers={"location": redirect3}))
        respx.get(redirect3).mock(return_value=httpx.Response(301, headers={"location": redirect4}))
        respx.get(redirect4).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        with pytest.raises(ProContextError) as exc_info:
            await read_page_handle(SAMPLE_URL, 1, 500, app_state)
        assert exc_info.value.code == ErrorCode.TOO_MANY_REDIRECTS
        assert exc_info.value.recoverable is False

    async def test_invalid_url_scheme_raises(self, app_state: AppState) -> None:
        with pytest.raises(ProContextError) as exc_info:
            await read_page_handle("ftp://example.com/docs.md", 1, 500, app_state)
        assert exc_info.value.code == ErrorCode.INVALID_INPUT
        assert exc_info.value.recoverable is False

    async def test_url_too_long_raises(self, app_state: AppState) -> None:
        long_url = "https://example.com/" + "a" * 2040
        with pytest.raises(ProContextError) as exc_info:
            await read_page_handle(long_url, 1, 500, app_state)
        assert exc_info.value.code == ErrorCode.INVALID_INPUT

    @respx.mock
    async def test_output_contains_all_required_fields(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        result = await read_page_handle(SAMPLE_URL, 1, 500, app_state)
        assert set(result.keys()) == {
            "url",
            "outline",
            "total_lines",
            "offset",
            "limit",
            "content",
            "has_more",
            "next_offset",
            "content_hash",
            "cached",
            "cached_at",
            "stale",
        }

    @respx.mock
    async def test_offset_beyond_content_returns_empty(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        result = await read_page_handle(SAMPLE_URL, 9999, 100, app_state)
        assert result["content"] == ""
        assert result["total_lines"] == 21
        assert result["outline"] != ""

    @respx.mock
    async def test_include_outline_false_returns_null_outline(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        result = await read_page_handle(SAMPLE_URL, 1, 500, app_state, include_outline=False)
        assert result["outline"] is None
        assert result["content"] != ""

    @respx.mock
    async def test_include_outline_default_returns_outline(self, app_state: AppState) -> None:
        respx.get(SAMPLE_URL).mock(return_value=httpx.Response(200, text=SAMPLE_PAGE))

        result = await read_page_handle(SAMPLE_URL, 1, 500, app_state)
        assert result["outline"] != ""
        assert "# Streaming" in result["outline"]

    @respx.mock
    async def test_setext_headings_are_normalized_in_outline(self, app_state: AppState) -> None:
        respx.get(SETEXT_URL).mock(return_value=httpx.Response(200, text=SETEXT_PAGE))

        result = await read_page_handle(SETEXT_URL, 1, 500, app_state)

        assert "1:# Main Title" in result["outline"]
        assert "4:## Section Title" in result["outline"]
        assert "## Tail" in result["outline"]
