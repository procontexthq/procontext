"""Tool handler for read_outline.

Validates input, delegates fetching to the shared helper, strips empty fences,
filters outline entries by entry count from offset, and returns the formatted result.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from procontext.errors import ErrorCode, ProContextError
from procontext.models.tools import ReadOutlineInput, ReadOutlineOutput
from procontext.outline import format_outline, parse_outline_entries, strip_empty_fences
from procontext.page import fetch_or_cached_page

if TYPE_CHECKING:
    from procontext.state import AppState


async def handle(
    url: str,
    offset: int,
    limit: int,
    state: AppState,
    *,
    before: int = 0,
) -> dict:
    """Handle a read_outline tool call."""
    log = structlog.get_logger().bind(tool="read_outline", url=url)
    log.info("handler_called")

    try:
        validated = ReadOutlineInput(url=url, offset=offset, limit=limit, before=before)
    except ValueError as exc:
        raise ProContextError(
            code=ErrorCode.INVALID_INPUT,
            message=str(exc),
            suggestion=(
                "Provide a valid URL (http/https, max 2048 chars), "
                "offset >= 1, limit >= 1, before >= 0."
            ),
            recoverable=False,
        ) from exc

    result = await fetch_or_cached_page(validated.url, state)

    entries = parse_outline_entries(result.outline)
    entries = strip_empty_fences(entries)
    total_entries = len(entries)

    forward = [e for e in entries if e.line_number >= validated.offset]
    limited = forward[: validated.limit]

    backward = [e for e in entries if e.line_number < validated.offset]
    before_entries = backward[-validated.before :] if validated.before > 0 else []

    page = before_entries + limited

    has_more = len(forward) > validated.limit
    next_offset = forward[validated.limit].line_number if has_more else None

    output = ReadOutlineOutput(
        url=result.url,
        outline=format_outline(page),
        total_entries=total_entries,
        has_more=has_more,
        next_offset=next_offset,
        content_hash=result.content_hash,
    )
    return output.model_dump(mode="json")
