"""Library resolution algorithm.

Pure business logic — receives RegistryIndexes, returns LibraryMatch results.
No knowledge of AppState, MCP, or I/O.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from rapidfuzz import fuzz, process

from procontext.models.registry import LibraryMatch
from procontext.normalization import (
    is_unsupported_resolve_query,
    normalize_fuzzy_term,
    normalize_package_key,
    normalize_text_key,
)

if TYPE_CHECKING:
    from procontext.models.registry import RegistryEntry, RegistryIndexes

MatchType = Literal["package_name", "library_id", "name", "alias", "fuzzy"]


def resolve_library(
    query: str,
    indexes: RegistryIndexes,
    *,
    fuzzy_score_cutoff: int = 70,
    fuzzy_max_results: int = 5,
) -> list[LibraryMatch]:
    """Resolve a plain-name query using exact lookups before fuzzy search."""
    package_query = normalize_package_key(query)
    if not package_query or is_unsupported_resolve_query(query):
        return []

    package_matches = _resolve_package_matches(package_query, indexes)
    text_matches = _resolve_text_matches(query, indexes)
    exact_matches = _merge_exact_matches(package_matches, text_matches)
    if exact_matches:
        return exact_matches

    fuzzy_query = normalize_fuzzy_term(query)
    if not fuzzy_query:
        return []

    return _fuzzy_search(
        fuzzy_query,
        indexes.fuzzy_corpus,
        indexes.by_id,
        limit=fuzzy_max_results,
        score_cutoff=fuzzy_score_cutoff,
    )


def _match_from_entry(
    entry: RegistryEntry,
    *,
    matched_via: Literal["package_name", "library_id", "name", "alias", "fuzzy"],
    relevance: float,
) -> LibraryMatch:
    """Build a LibraryMatch from a RegistryEntry."""
    return LibraryMatch(
        library_id=entry.id,
        name=entry.name,
        description=entry.description,
        index_url=entry.llms_txt_url,
        full_docs_url=entry.llms_full_txt_url,
        packages=entry.packages,
        matched_via=matched_via,
        relevance=relevance,
    )


def _resolve_package_matches(
    package_query: str,
    indexes: RegistryIndexes,
) -> list[LibraryMatch]:
    return _matches_from_library_ids(
        indexes.by_package_exact.get(package_query, []),
        indexes,
        matched_via="package_name",
    )


def _resolve_text_matches(
    raw_query: str,
    indexes: RegistryIndexes,
) -> list[LibraryMatch]:
    text_key = normalize_text_key(raw_query)
    hits = indexes.by_text_exact.get(text_key, [])
    return [
        _match_from_entry(
            indexes.by_id[hit.library_id],
            matched_via=hit.match_type,
            relevance=1.0,
        )
        for hit in hits
    ]


def _matches_from_library_ids(
    library_ids: list[str],
    indexes: RegistryIndexes,
    *,
    matched_via: Literal["package_name"],
) -> list[LibraryMatch]:
    return [
        _match_from_entry(indexes.by_id[library_id], matched_via=matched_via, relevance=1.0)
        for library_id in library_ids
    ]


def _merge_exact_matches(
    package_matches: list[LibraryMatch],
    text_matches: list[LibraryMatch],
) -> list[LibraryMatch]:
    merged: dict[str, LibraryMatch] = {}
    ordered_ids: list[str] = []

    for match in package_matches + text_matches:
        existing = merged.get(match.library_id)
        if existing is None:
            merged[match.library_id] = match
            ordered_ids.append(match.library_id)
            continue

        if _exact_match_priority(match.matched_via) < _exact_match_priority(existing.matched_via):
            merged[match.library_id] = match

    return [merged[library_id] for library_id in ordered_ids]


def _exact_match_priority(match_type: MatchType) -> int:
    if match_type == "package_name":
        return 0
    if match_type == "library_id":
        return 1
    if match_type == "name":
        return 2
    if match_type == "alias":
        return 3
    return 4


def _fuzzy_search(
    query: str,
    corpus: list[tuple[str, str]],
    by_id: dict[str, RegistryEntry],
    limit: int = 5,
    score_cutoff: int = 70,
) -> list[LibraryMatch]:
    """Fuzzy match against the corpus using Levenshtein distance.

    Deduplicates by library_id (one result per library) and applies the
    result limit after deduplication.
    Returns matches sorted by relevance descending.
    """
    if not corpus or limit < 1:
        return []

    terms = [term for term, _ in corpus]
    results = process.extract(
        query,
        terms,
        scorer=fuzz.ratio,
        limit=len(terms),
        score_cutoff=score_cutoff,
    )

    seen: set[str] = set()
    matches: list[LibraryMatch] = []

    for _term, score, idx in results:
        _, library_id = corpus[idx]
        if library_id in seen:
            continue
        seen.add(library_id)
        entry = by_id[library_id]
        matches.append(
            _match_from_entry(
                entry,
                matched_via="fuzzy",
                relevance=round(score / 100, 2),
            )
        )
        if len(matches) == limit:
            break

    return sorted(matches, key=lambda m: m.relevance, reverse=True)
