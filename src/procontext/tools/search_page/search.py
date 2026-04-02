"""In-memory line search for documentation pages.

Pure functions — no I/O, no AppState, no cache. Content is passed in as a
string, split into lines, and scanned with ``re.search()``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class LineMatch:
    """A single matching line."""

    line_number: int
    content: str


@dataclass(frozen=True)
class SearchResult:
    """Paginated search result."""

    matches: list[LineMatch]
    has_more: bool
    next_offset: int | None


def build_matcher(
    query: str,
    *,
    mode: Literal["literal", "regex"] = "literal",
    case_mode: Literal["smart", "insensitive", "sensitive"] = "smart",
    whole_word: bool = False,
) -> re.Pattern[str]:
    """Compile a search query into a ``re.Pattern``."""
    pattern = re.escape(query) if mode == "literal" else query

    if whole_word:
        pattern = rf"\b{pattern}\b"

    flags = re.NOFLAG
    if case_mode == "insensitive" or (case_mode == "smart" and query == query.lower()):
        flags = re.IGNORECASE

    return re.compile(pattern, flags)


def search_lines(
    content: str,
    matcher: re.Pattern[str],
    *,
    offset: int = 1,
    max_results: int = 20,
) -> SearchResult:
    """Scan *content* line-by-line and return matching lines."""
    lines = content.splitlines()
    matches: list[LineMatch] = []

    for idx, line in enumerate(lines, start=1):
        if idx < offset:
            continue
        if matcher.search(line):
            matches.append(LineMatch(line_number=idx, content=line))
            if len(matches) == max_results:
                for remaining_idx in range(idx + 1, len(lines) + 1):
                    if matcher.search(lines[remaining_idx - 1]):
                        return SearchResult(
                            matches=matches,
                            has_more=True,
                            next_offset=idx + 1,
                        )
                return SearchResult(
                    matches=matches,
                    has_more=False,
                    next_offset=None,
                )

    return SearchResult(
        matches=matches,
        has_more=False,
        next_offset=None,
    )
