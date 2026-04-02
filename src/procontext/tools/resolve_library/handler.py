"""Tool handler for resolve_library.

Receives AppState, delegates to the resolver module, and returns
a structured dict. No MCP or FastMCP imports — server.py handles
the MCP wiring.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from procontext.errors import ErrorCode, ProContextError
from procontext.models.tools import ResolveHint, ResolveLibraryInput, ResolveLibraryOutput
from procontext.normalization import is_unsupported_resolve_query
from procontext.tools.resolve_library.resolver import resolve_library

if TYPE_CHECKING:
    from procontext.models.registry import LibraryMatch
    from procontext.state import AppState


async def handle(
    query: str,
    state: AppState,
    *,
    language: str | None = None,
) -> dict:
    """Handle a resolve_library tool call."""
    log = structlog.get_logger().bind(tool="resolve_library", query=query)
    log.info("handler_called")

    try:
        validated = ResolveLibraryInput(query=query, language=language)
    except ValueError as exc:
        raise ProContextError(
            code=ErrorCode.INVALID_INPUT,
            message=str(exc),
            suggestion=(
                "Provide a library name, package name, or alias between 3 and 500 characters."
            ),
            recoverable=False,
        ) from exc

    matches = resolve_library(
        validated.query,
        state.indexes,
        fuzzy_score_cutoff=state.settings.resolver.fuzzy_score_cutoff,
        fuzzy_max_results=state.settings.resolver.fuzzy_max_results,
    )

    if validated.language:
        matches = _sort_by_language(matches, validated.language)

    log.info("resolve_complete", match_count=len(matches))

    output = ResolveLibraryOutput(matches=matches, hint=_resolve_hint(validated.query, matches))
    return output.model_dump(mode="json")


def _sort_by_language(matches: list[LibraryMatch], language: str) -> list[LibraryMatch]:
    """Sort matches and their package entries by language preference."""
    sorted_matches: list[LibraryMatch] = []
    for match in matches:
        has_lang = [package for package in match.packages if language in package.languages]
        no_lang = [package for package in match.packages if language not in package.languages]
        sorted_matches.append(match.model_copy(update={"packages": has_lang + no_lang}))

    def _has_language(match: LibraryMatch) -> bool:
        return any(language in package.languages for package in match.packages)

    return sorted(sorted_matches, key=lambda match: not _has_language(match))


def _resolve_hint(query: str, matches: list[LibraryMatch]) -> ResolveHint | None:
    if is_unsupported_resolve_query(query):
        return ResolveHint(
            code="UNSUPPORTED_QUERY_SYNTAX",
            message=(
                "Provide only the published package name, library ID, display name, "
                "or alias without version specifiers, extras, tags, or source URLs."
            ),
        )

    if matches and all(match.matched_via == "fuzzy" for match in matches):
        return ResolveHint(
            code="FUZZY_FALLBACK_USED",
            message="No exact match was found. Verify the fuzzy match before continuing.",
        )

    return None
