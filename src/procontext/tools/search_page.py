"""Tool handler for search_page.

Validates input, fetches page content via the shared helper, compiles the
search matcher, runs the line scan, and returns matches with pagination.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import structlog

from procontext.errors import ErrorCode, ProContextError
from procontext.models.tools import SearchPageInput, SearchPageOutput
from procontext.outline import (
    build_compaction_note,
    compact_outline,
    format_outline,
    parse_outline_entries,
    strip_empty_fences,
    trim_outline_to_range,
)
from procontext.page import fetch_or_cached_page
from procontext.search import LineMatch, SearchResult, build_matcher, search_lines

if TYPE_CHECKING:
    from procontext.state import AppState


async def handle(
    url: str,
    query: str,
    state: AppState,
    *,
    target: str = "content",
    mode: str = "literal",
    case_mode: str = "smart",
    whole_word: bool = False,
    offset: int = 1,
    max_results: int = 20,
) -> dict:
    """Handle a search_page tool call."""
    log = structlog.get_logger().bind(tool="search_page", url=url, query=query)
    log.info("handler_called")

    # Validate input
    try:
        validated = SearchPageInput(
            url=url,
            query=query,
            target=target,  # type: ignore[arg-type]
            mode=mode,  # type: ignore[arg-type]
            case_mode=case_mode,  # type: ignore[arg-type]
            whole_word=whole_word,
            offset=offset,
            max_results=max_results,
        )
    except ValueError as exc:
        raise ProContextError(
            code=ErrorCode.INVALID_INPUT,
            message=str(exc),
            suggestion=(
                "Check url, query, target, mode, case_mode, offset, and max_results values."
            ),
            recoverable=False,
        ) from exc

    # Fetch (or retrieve from cache) the page content
    result = await fetch_or_cached_page(validated.url, state)

    # Compile the search pattern
    try:
        matcher = build_matcher(
            validated.query,
            mode=validated.mode,
            case_mode=validated.case_mode,
            whole_word=validated.whole_word,
        )
    except re.error as exc:
        raise ProContextError(
            code=ErrorCode.INVALID_INPUT,
            message=f"Invalid regex pattern: {exc}",
            suggestion="Check your regex syntax or use mode='literal' for plain text search.",
            recoverable=False,
        ) from exc

    total_lines = len(result.content.splitlines())
    outline: str | None
    if validated.target == "outline":
        search_result = _search_outline_lines(
            result.outline,
            matcher,
            offset=validated.offset,
            max_results=validated.max_results,
        )
        raw_matches = search_result.matches
        matches_str = "\n".join(f"{m.line_number}:{m.content}" for m in raw_matches)
        outline = None
    else:
        # Run the search against page content
        search_result = search_lines(
            result.content,
            matcher,
            offset=validated.offset,
            max_results=validated.max_results,
        )

        # Format matches as "line_number:content" string
        raw_matches = search_result.matches
        matches_str = "\n".join(f"{m.line_number}:{m.content}" for m in raw_matches)

        # Build compacted outline trimmed to match range
        first_line = raw_matches[0].line_number if raw_matches else None
        last_line = raw_matches[-1].line_number if raw_matches else None
        outline = _compact_search_outline(
            result.outline,
            first_line,
            last_line,
            max_entries=state.settings.outline.max_entries,
            max_chars=state.settings.outline.max_chars,
        )

    output = SearchPageOutput(
        url=result.url,
        query=validated.query,
        outline=outline,
        matches=matches_str,
        total_lines=total_lines,
        has_more=search_result.has_more,
        next_offset=search_result.next_offset,
        content_hash=result.content_hash,
        cached=result.cached,
        cached_at=result.cached_at,
        stale=result.stale,
    )
    return output.model_dump(mode="json")


def _search_outline_lines(
    raw_outline: str,
    matcher: re.Pattern[str],
    *,
    offset: int,
    max_results: int,
):
    """Search raw outline lines, ignoring the numeric prefix for matching."""
    matches: list[LineMatch] = []
    lines = [line for line in raw_outline.splitlines() if line]

    for idx, raw_line in enumerate(lines):
        colon_idx = raw_line.find(":")
        if colon_idx == -1:
            continue

        line_number = int(raw_line[:colon_idx])
        text = raw_line[colon_idx + 1 :]
        if line_number < offset:
            continue

        if matcher.search(text):
            matches.append(LineMatch(line_number=line_number, content=text))
            if len(matches) == max_results:
                has_more = any(
                    _outline_line_matches(later_line, matcher=matcher, offset=line_number + 1)
                    for later_line in lines[idx + 1 :]
                )
                return SearchResult(
                    matches=matches,
                    has_more=has_more,
                    next_offset=line_number + 1 if has_more else None,
                )

    return SearchResult(matches=matches, has_more=False, next_offset=None)


def _outline_line_matches(raw_line: str, *, matcher: re.Pattern[str], offset: int) -> bool:
    colon_idx = raw_line.find(":")
    if colon_idx == -1:
        return False

    line_number = int(raw_line[:colon_idx])
    if line_number < offset:
        return False

    return matcher.search(raw_line[colon_idx + 1 :]) is not None


def _compact_search_outline(
    raw_outline: str,
    first_line: int | None,
    last_line: int | None,
    *,
    max_entries: int = 50,
    max_chars: int = 4000,
) -> str:
    """Trim and compact only oversized outlines for search_page output."""
    entries = parse_outline_entries(raw_outline)
    entries = strip_empty_fences(entries)
    total_entries = len(entries)

    # Small outlines fit inline already — preserve the full structure instead of
    # trimming to the match span, which can drop useful parent headings.
    if total_entries <= max_entries and len(format_outline(entries)) <= max_chars:
        return format_outline(entries)

    # No match range — compact without trimming to a span.
    if first_line is None or last_line is None:
        compacted = compact_outline(entries, max_entries=max_entries, max_chars=max_chars)
        if compacted is None:
            return (
                f"[Outline too large ({total_entries} entries)."
                " Use read_outline for paginated access.]"
            )
        note = build_compaction_note(compacted, total_entries)
        return note + "\n" + format_outline(compacted)

    # Trim to match range
    trimmed = trim_outline_to_range(entries, first_line, last_line)

    if len(trimmed) <= max_entries and len(format_outline(trimmed)) <= max_chars:
        return format_outline(trimmed)

    compacted = compact_outline(trimmed, max_entries=max_entries, max_chars=max_chars)
    if compacted is None:
        return (
            f"[Outline too large ({total_entries} entries). Use read_outline for paginated access.]"
        )

    note = build_compaction_note(compacted, total_entries, match_range=(first_line, last_line))
    return note + "\n" + format_outline(compacted)
