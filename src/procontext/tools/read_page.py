"""Tool handler for read_page.

Validates input, delegates fetching to the shared helper, and applies
line windowing to build the output dict.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import structlog

from procontext.errors import ErrorCode, ProContextError
from procontext.models.tools import ReadPageInput, ReadPageOutput
from procontext.tools._shared import fetch_or_cached_page

if TYPE_CHECKING:
    from datetime import datetime

    from procontext.state import AppState


async def handle(
    url: str,
    offset: int,
    limit: int,
    state: AppState,
    view: Literal["outline", "full"] = "full",
) -> dict:
    """Handle a read_page tool call."""
    log = structlog.get_logger().bind(tool="read_page", url=url)
    log.info("handler_called")

    # Validate input
    try:
        validated = ReadPageInput(url=url, offset=offset, limit=limit, view=view)
    except ValueError as exc:
        raise ProContextError(
            code=ErrorCode.INVALID_INPUT,
            message=str(exc),
            suggestion="Provide a valid URL (http/https, max 2048 chars), offset >= 1, limit >= 1.",
            recoverable=False,
        ) from exc

    result = await fetch_or_cached_page(validated.url, state)

    return _build_output(
        url=result.url,
        content=result.content,
        outline=result.outline,
        offset=validated.offset,
        limit=validated.limit,
        view=validated.view,
        cached=result.cached,
        cached_at=result.cached_at,
        stale=result.stale,
    )


def _build_output(
    *,
    url: str,
    content: str,
    outline: str,
    offset: int,
    limit: int,
    view: Literal["outline", "full"],
    cached: bool,
    cached_at: datetime | None,
    stale: bool,
) -> dict:
    """Apply line windowing and build the output dict."""
    all_lines = content.splitlines()
    total_lines = len(all_lines)

    # Window: offset is 1-based. Skipped for outline-only view.
    windowed_content: str | None
    if view == "full":
        windowed = all_lines[offset - 1 : offset - 1 + limit]
        windowed_content = "\n".join(windowed)
    else:
        windowed_content = None

    end = offset - 1 + limit
    has_more = end < total_lines
    next_offset = end + 1 if has_more else None

    output = ReadPageOutput(
        url=url,
        outline=outline,
        total_lines=total_lines,
        offset=offset,
        limit=limit,
        content=windowed_content,
        has_more=has_more,
        next_offset=next_offset,
        cached=cached,
        cached_at=cached_at,
        stale=stale,
    )
    result = output.model_dump(mode="json")
    # content is intentionally absent in view="outline" responses
    if result["content"] is None:
        del result["content"]
    return result
