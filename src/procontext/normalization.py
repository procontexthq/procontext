"""Shared normalization helpers for resolver indexing and lookup."""

from __future__ import annotations

import re

_PYPI_CANONICAL_SEPARATORS_RE = re.compile(r"[-_.]+")
_PYTHON_EXTRAS_RE = re.compile(r"\[[^\]]*\]")
_PYTHON_VERSION_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*"
    r"(?P<operator>===|==|~=|!=|<=|>=|<|>)\s*.+$"
)
_SCOPED_NPM_VERSION_RE = re.compile(
    r"^(?P<name>@[^/\s]+/[^@\s]+)@(?P<version>[~^]?\d[0-9A-Za-z.+-]*)$"
)
_UNSCOPED_NPM_VERSION_RE = re.compile(r"^(?P<name>[^@\s/]+)@(?P<version>[~^]?\d[0-9A-Za-z.+-]*)$")


def canonicalize_pypi_name(name: str) -> str:
    """Canonicalize a PyPI project name using PEP 503 rules."""
    return _PYPI_CANONICAL_SEPARATORS_RE.sub("-", name.strip()).lower()


def normalize_package_key(name: str) -> str:
    """Normalize an exact package key without changing package semantics."""
    return name.strip().lower()


def normalize_text_key(text: str) -> str:
    """Normalize free-form text keys for exact name, ID, and alias lookup."""
    return " ".join(text.strip().lower().split())


def strip_safe_query(raw: str) -> str:
    """Strip only dependency syntax that is safe to discard for lookup."""
    query = raw.strip()
    if not query or is_source_spec_query(query):
        return query

    npm_match = _SCOPED_NPM_VERSION_RE.fullmatch(query)
    if npm_match is not None:
        return npm_match.group("name")

    npm_match = _UNSCOPED_NPM_VERSION_RE.fullmatch(query)
    if npm_match is not None:
        return npm_match.group("name")

    python_match = _PYTHON_VERSION_RE.fullmatch(query)
    if python_match is not None:
        return python_match.group("name")

    stripped_extras = _PYTHON_EXTRAS_RE.sub("", query)
    return stripped_extras.strip()


def normalize_fuzzy_term(raw: str) -> str:
    """Normalize a term for fuzzy matching symmetrically across index and query."""
    return normalize_text_key(strip_safe_query(raw))


def is_source_spec_query(raw: str) -> bool:
    """Return true when a query is a source spec we intentionally do not resolve."""
    return " @ " in raw or "://" in raw or raw.startswith(("git+", "github:"))
