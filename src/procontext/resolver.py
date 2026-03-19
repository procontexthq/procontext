"""Library resolution algorithm.

Pure business logic — receives RegistryIndexes, returns LibraryMatch results.
No knowledge of AppState, MCP, or I/O.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from rapidfuzz import fuzz, process

from procontext.models.registry import LibraryMatch
from procontext.normalization import (
    canonicalize_pypi_name,
    is_source_spec_query,
    normalize_fuzzy_term,
    normalize_package_key,
    normalize_text_key,
    strip_safe_query,
)

if TYPE_CHECKING:
    from procontext.models.registry import RegistryEntry, RegistryIndexes

QueryKind = Literal[
    "definitely_python",
    "definitely_npm",
    "maybe_python",
    "generic",
    "github_like",
]


def resolve_library(
    query: str,
    indexes: RegistryIndexes,
    *,
    fuzzy_score_cutoff: int = 70,
    fuzzy_max_results: int = 5,
) -> list[LibraryMatch]:
    """Resolve a query to matching libraries using exact tiers before fuzzy search."""
    stripped_query = strip_safe_query(query)
    if not stripped_query:
        return []

    query_kind = _classify_query(query, stripped_query)
    if query_kind == "github_like":
        return []

    package_matches = _resolve_package_matches(stripped_query, query_kind, indexes)
    if package_matches:
        return package_matches

    text_matches = _resolve_text_matches(stripped_query, indexes)
    if text_matches:
        return text_matches

    fuzzy_query = normalize_fuzzy_term(query)
    if not fuzzy_query:
        return []

    matches = _fuzzy_search(
        fuzzy_query,
        indexes.fuzzy_corpus,
        indexes.by_id,
        limit=fuzzy_max_results,
        score_cutoff=fuzzy_score_cutoff,
    )
    if matches:
        return matches

    return []


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
        packages=entry.packages,
        matched_via=matched_via,
        relevance=relevance,
    )


def _classify_query(raw_query: str, stripped_query: str) -> QueryKind:
    trimmed_query = raw_query.strip()
    if is_source_spec_query(trimmed_query):
        return "github_like"
    if _is_definitely_python_query(trimmed_query):
        return "definitely_python"
    if _is_definitely_npm_query(trimmed_query, stripped_query):
        return "definitely_npm"
    if _is_maybe_python_query(stripped_query):
        return "maybe_python"
    return "generic"


def _is_definitely_python_query(query: str) -> bool:
    if "@" in query or "/" in query:
        return False
    return "[" in query or any(
        operator in query for operator in ("==", "~=", "!=", "<=", ">=", "<", ">")
    )


def _is_definitely_npm_query(raw_query: str, stripped_query: str) -> bool:
    if stripped_query.startswith("@") and "/" in stripped_query:
        return True
    return raw_query != stripped_query and "@" in raw_query


def _is_maybe_python_query(query: str) -> bool:
    if not query or query.startswith("@") or "/" in query:
        return False
    return canonicalize_pypi_name(query) != normalize_package_key(query)


def _resolve_package_matches(
    stripped_query: str,
    query_kind: QueryKind,
    indexes: RegistryIndexes,
) -> list[LibraryMatch]:
    exact_key = normalize_package_key(stripped_query)
    canonical_key = canonicalize_pypi_name(stripped_query)

    if query_kind == "definitely_python":
        return _matches_from_library_ids(
            indexes.by_package_pypi_canonical.get(canonical_key, []),
            indexes,
            matched_via="package_name",
        )
    if query_kind == "definitely_npm":
        return _matches_from_library_ids(
            indexes.by_package_exact.get(exact_key, []),
            indexes,
            matched_via="package_name",
        )
    if query_kind == "maybe_python":
        exact_matches = _matches_from_library_ids(
            indexes.by_package_exact.get(exact_key, []),
            indexes,
            matched_via="package_name",
        )
        if exact_matches:
            return exact_matches
        return _matches_from_library_ids(
            indexes.by_package_pypi_canonical.get(canonical_key, []),
            indexes,
            matched_via="package_name",
        )
    return _matches_from_library_ids(
        indexes.by_package_exact.get(exact_key, []),
        indexes,
        matched_via="package_name",
    )


def _resolve_text_matches(
    stripped_query: str,
    indexes: RegistryIndexes,
) -> list[LibraryMatch]:
    text_key = normalize_text_key(stripped_query)
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


def _fuzzy_search(
    query: str,
    corpus: list[tuple[str, str]],
    by_id: dict[str, RegistryEntry],
    limit: int = 5,
    score_cutoff: int = 70,
) -> list[LibraryMatch]:
    """Fuzzy match against the corpus using Levenshtein distance.

    Deduplicates by library_id (one result per library).
    Returns matches sorted by relevance descending.
    """
    terms = [term for term, _ in corpus]
    results = process.extract(
        query,
        terms,
        scorer=fuzz.ratio,
        limit=limit,
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

    return sorted(matches, key=lambda m: m.relevance, reverse=True)
