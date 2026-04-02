"""Pure helpers for building search_page outline context.

This module handles range trimming, ancestor rollup, and stage-aware reduction
for oversized search_page outline responses.
"""

from __future__ import annotations

from dataclasses import dataclass

from procontext.outline import (
    OutlineEntry,
    compact_outline,
    format_outline,
    iter_outline_reduction_stages,
    trim_outline_to_range,
)


@dataclass(frozen=True)
class SearchOutlineSelection:
    """Selected outline entries for search_page plus compaction metadata."""

    entries: list[OutlineEntry]
    compacted: bool


def select_search_outline_entries(
    entries: list[OutlineEntry],
    first_line: int | None,
    last_line: int | None,
    *,
    max_entries: int,
    max_chars: int,
) -> SearchOutlineSelection | None:
    """Build the search_page outline for the current match span.

    Small full outlines are returned unchanged. For no-match cases, this falls
    back to normal compaction. For oversized match ranges, ancestor rollup is
    computed separately for each reduction stage so filtered headings are never
    reintroduced.
    """
    if len(entries) <= max_entries and len(format_outline(entries)) <= max_chars:
        return SearchOutlineSelection(entries=entries, compacted=False)

    if first_line is None or last_line is None:
        compacted = compact_outline(entries, max_entries=max_entries, max_chars=max_chars)
        if compacted is None:
            return None
        return SearchOutlineSelection(entries=compacted, compacted=True)

    for stage, stage_entries in iter_outline_reduction_stages(entries):
        candidate = build_match_range_with_rollup(stage_entries, first_line, last_line)
        if len(candidate) <= max_entries and len(format_outline(candidate)) <= max_chars:
            return SearchOutlineSelection(entries=candidate, compacted=stage != "none")

    return None


def build_match_range_with_rollup(
    entries: list[OutlineEntry],
    first_line: int,
    last_line: int,
    *,
    root_floor_depth: int = 2,
) -> list[OutlineEntry]:
    """Return trimmed match-range entries preceded by rolled-up ancestor context."""
    trimmed = trim_outline_to_range(entries, first_line, last_line)
    ancestors = build_ancestor_rollup(
        entries,
        first_line,
        root_floor_depth=root_floor_depth,
    )
    return merge_outline_entries(ancestors, trimmed)


def build_ancestor_rollup(
    entries: list[OutlineEntry],
    first_match_line: int,
    *,
    root_floor_depth: int = 2,
) -> list[OutlineEntry]:
    """Build the active heading chain immediately before *first_match_line*.

    Uses the current surviving entries only. The returned chain starts at the
    nearest surviving H2 when present, otherwise the nearest surviving H1, and
    otherwise the full available local chain.
    """
    stack: list[OutlineEntry] = []

    for entry in entries:
        if entry.line_number >= first_match_line:
            break
        if entry.depth is None:
            continue

        while stack and stack[-1].depth is not None and stack[-1].depth >= entry.depth:
            stack.pop()
        stack.append(entry)

    if not stack:
        return []

    root_index = _rollup_root_index(stack, root_floor_depth=root_floor_depth)
    return stack[root_index:]


def merge_outline_entries(
    ancestors: list[OutlineEntry],
    trimmed: list[OutlineEntry],
) -> list[OutlineEntry]:
    """Merge two outline entry lists in document order, deduplicated by line number."""
    merged: dict[int, OutlineEntry] = {}
    for entry in ancestors + trimmed:
        merged.setdefault(entry.line_number, entry)
    return sorted(merged.values(), key=lambda entry: entry.line_number)


def _rollup_root_index(stack: list[OutlineEntry], *, root_floor_depth: int) -> int:
    h2_index = next((i for i, entry in enumerate(stack) if entry.depth == root_floor_depth), None)
    if h2_index is not None:
        return h2_index

    h1_index = next((i for i, entry in enumerate(stack) if entry.depth == 1), None)
    if h1_index is not None:
        return h1_index

    return 0
