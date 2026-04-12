"""Tool handler for read_page.

Validates input, delegates fetching to the shared helper, applies outline
compaction, and applies line windowing to build the output dict.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from procontext.errors import ErrorCode, ProContextError
from procontext.models.tools import ReadPageInput, ReadPageOutput
from procontext.outline import (
    build_compaction_note,
    compact_outline,
    format_outline,
    parse_outline_entries,
    strip_empty_fences,
)
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
    include_outline: bool = True,
) -> dict:
    """Handle a read_page tool call."""
    log = structlog.get_logger().bind(tool="read_page", url=url)
    log.info("handler_called")

    try:
        validated = ReadPageInput(
            url=url,
            offset=offset,
            limit=limit,
            before=before,
            include_outline=include_outline,
        )
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
    compacted_outline = (
        _compact_page_outline(
            result.outline,
            max_entries=state.settings.outline.max_entries,
            max_chars=state.settings.outline.read_page_max_chars,
        )
        if validated.include_outline
        else None
    )

    return _build_output(
        url=result.url,
        content=result.content,
        outline=compacted_outline,
        offset=validated.offset,
        limit=validated.limit,
        before=validated.before,
        content_hash=result.content_hash,
    )


def _compact_page_outline(raw_outline: str, *, max_entries: int = 50, max_chars: int = 4000) -> str:
    """Parse, strip empty fences, and compact an outline for read_page output."""
    entries = parse_outline_entries(raw_outline)
    entries = strip_empty_fences(entries)
    total_entries = len(entries)

    if total_entries <= max_entries and len(format_outline(entries)) <= max_chars:
        return format_outline(entries)

    compacted = compact_outline(entries, max_entries=max_entries, max_chars=max_chars)
    if compacted is None:
        return (
            f"[Outline too large ({total_entries} entries). Use read_outline for paginated access.]"
        )

    note = build_compaction_note(compacted, total_entries)
    return note + "\n" + format_outline(compacted)


def _build_output(
    *,
    url: str,
    content: str,
    outline: str | None,
    offset: int,
    limit: int,
    before: int,
    content_hash: str,
) -> dict:
    """Apply line windowing and build the output dict."""
    all_lines = content.splitlines()
    total_lines = len(all_lines)

    start = max(1, offset - before)
    end = min(total_lines, offset + limit - 1)

    windowed = all_lines[start - 1 : end]
    windowed_content = "\n".join(windowed)

    has_more = end < total_lines
    next_offset = end + 1 if has_more else None

    output = ReadPageOutput(
        url=url,
        outline=outline,
        total_lines=total_lines,
        offset=start,
        limit=limit,
        content=windowed_content,
        has_more=has_more,
        next_offset=next_offset,
        content_hash=content_hash,
    )
    return output.model_dump(mode="json")
