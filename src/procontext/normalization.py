"""Shared normalization helpers for resolver indexing and lookup."""

from __future__ import annotations

import re

_PYTHON_EXTRAS_ONLY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\[[^\]]+\]$")
_PYTHON_VERSION_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*(?:\[[^\]]*\])?\s*(?:===|==|~=|!=|<=|>=|<|>)\s*.+$"
)
_SCOPED_NPM_MODIFIER_RE = re.compile(r"^@[^/\s]+/[^@\s]+@.+$")
_UNSCOPED_NPM_MODIFIER_RE = re.compile(r"^[^@\s/]+@.+$")


def normalize_package_key(name: str) -> str:
    """Normalize an exact package key without changing package semantics."""
    return name.strip().lower()


def normalize_text_key(text: str) -> str:
    """Normalize free-form text keys for exact name, ID, alias, and fuzzy lookup."""
    return " ".join(text.strip().lower().split())


def normalize_fuzzy_term(raw: str) -> str:
    """Normalize a term for fuzzy matching symmetrically across index and query."""
    return normalize_text_key(raw)


def is_source_spec_query(raw: str) -> bool:
    """Return true when a query is a source spec we intentionally do not resolve."""
    query = raw.strip()
    return " @ " in query or "://" in query or query.startswith(("git+", "github:"))


def has_dependency_modifier_syntax(raw: str) -> bool:
    """Return true when a query contains dependency modifiers instead of a plain name."""
    query = raw.strip()
    if not query or is_source_spec_query(query):
        return False

    return (
        _PYTHON_EXTRAS_ONLY_RE.fullmatch(query) is not None
        or _PYTHON_VERSION_RE.fullmatch(query) is not None
        or _SCOPED_NPM_MODIFIER_RE.fullmatch(query) is not None
        or _UNSCOPED_NPM_MODIFIER_RE.fullmatch(query) is not None
    )


def is_unsupported_resolve_query(raw: str) -> bool:
    """Return true when resolve_library should reject the query with a hint."""
    query = raw.strip()
    if not query:
        return False
    return is_source_spec_query(query) or has_dependency_modifier_syntax(query)
