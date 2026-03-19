"""Local registry loading and in-memory index construction."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

import structlog

from procontext.models.registry import ExactTextHit, RegistryEntry, RegistryIndexes, TextMatchType
from procontext.normalization import (
    canonicalize_pypi_name,
    normalize_fuzzy_term,
    normalize_package_key,
    normalize_text_key,
)

if TYPE_CHECKING:
    from pathlib import Path

log = structlog.get_logger()


def load_registry(
    local_registry_path: Path | None = None,
    local_state_path: Path | None = None,
) -> tuple[list[RegistryEntry], str] | None:
    """Load registry entries from the local registry pair."""
    return _load_local_registry_pair(local_registry_path, local_state_path)


def _load_local_registry_pair(
    local_registry_path: Path | None,
    local_state_path: Path | None,
) -> tuple[list[RegistryEntry], str] | None:
    """Load the local registry pair if both files are present and valid."""
    if local_registry_path is None or local_state_path is None:
        return None

    if not local_registry_path.is_file() or not local_state_path.is_file():
        log.debug(
            "registry_local_pair_missing",
            reason="missing_files",
            path_registry=str(local_registry_path),
            path_state=str(local_state_path),
        )
        return None

    try:
        registry_bytes = local_registry_path.read_bytes()
        raw_entries = json.loads(registry_bytes.decode("utf-8"))
        entries = [RegistryEntry(**entry) for entry in raw_entries]

        state_data = json.loads(local_state_path.read_text(encoding="utf-8"))
        version = state_data["version"]
        expected_checksum = state_data["checksum"]
        if not isinstance(version, str) or not version:
            raise ValueError("registry-state.json 'version' must be a non-empty string")
        if not isinstance(expected_checksum, str) or not expected_checksum.startswith("sha256:"):
            raise ValueError("registry-state.json 'checksum' must be 'sha256:<hex>'")

        actual_checksum = _sha256_prefixed(registry_bytes)
        if actual_checksum != expected_checksum:
            log.warning(
                "registry_local_pair_invalid",
                reason="checksum_mismatch",
                path_registry=str(local_registry_path),
                path_state=str(local_state_path),
            )
            return None

        return entries, version
    except Exception:
        log.warning(
            "registry_local_pair_invalid",
            reason="invalid_content",
            path_registry=str(local_registry_path),
            path_state=str(local_state_path),
            exc_info=True,
        )
        return None


def build_indexes(entries: list[RegistryEntry]) -> RegistryIndexes:
    """Build in-memory indexes from a list of registry entries."""
    by_package_exact_seen: dict[str, dict[str, None]] = {}
    by_package_pypi_canonical_seen: dict[str, dict[str, None]] = {}
    by_id: dict[str, RegistryEntry] = {}
    by_text_exact_seen: dict[str, dict[str, ExactTextHit]] = {}
    fuzzy_corpus_seen: dict[tuple[str, str], None] = {}

    for entry in entries:
        by_id[entry.id] = entry
        _add_text_hit(by_text_exact_seen, entry.id, entry.id, "library_id")
        _add_fuzzy_term(fuzzy_corpus_seen, entry.id, entry.id)
        _add_fuzzy_term(fuzzy_corpus_seen, entry.name, entry.id)

        for pkg_entry in entry.packages:
            for name in pkg_entry.package_names:
                exact_key = normalize_package_key(name)
                _add_keyed_library(by_package_exact_seen, exact_key, entry.id)
                _add_fuzzy_term(fuzzy_corpus_seen, name, entry.id)

                if pkg_entry.ecosystem == "pypi":
                    canonical_key = canonicalize_pypi_name(name)
                    _add_keyed_library(by_package_pypi_canonical_seen, canonical_key, entry.id)
                    _add_fuzzy_term(fuzzy_corpus_seen, canonical_key, entry.id)

        for alias in entry.aliases:
            _add_text_hit(by_text_exact_seen, alias, entry.id, "alias")
            _add_fuzzy_term(fuzzy_corpus_seen, alias, entry.id)

        _add_text_hit(by_text_exact_seen, entry.name, entry.id, "name")

    return RegistryIndexes(
        by_package_exact=_freeze_keyed_library_index(by_package_exact_seen),
        by_package_pypi_canonical=_freeze_keyed_library_index(by_package_pypi_canonical_seen),
        by_id=by_id,
        by_text_exact=_freeze_text_index(by_text_exact_seen),
        fuzzy_corpus=list(fuzzy_corpus_seen.keys()),
    )


def _sha256_prefixed(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _add_keyed_library(index: dict[str, dict[str, None]], key: str, library_id: str) -> None:
    index.setdefault(key, {})[library_id] = None


def _add_text_hit(
    index: dict[str, dict[str, ExactTextHit]],
    raw_key: str,
    library_id: str,
    match_type: TextMatchType,
) -> None:
    key = normalize_text_key(raw_key)
    hits_for_key = index.setdefault(key, {})
    existing = hits_for_key.get(library_id)
    if existing is None or _text_match_priority(match_type) < _text_match_priority(
        existing.match_type
    ):
        hits_for_key[library_id] = ExactTextHit(library_id=library_id, match_type=match_type)


def _add_fuzzy_term(
    fuzzy_corpus_seen: dict[tuple[str, str], None],
    raw_term: str,
    library_id: str,
) -> None:
    term = normalize_fuzzy_term(raw_term)
    if not term:
        return
    fuzzy_corpus_seen[(term, library_id)] = None


def _freeze_keyed_library_index(index: dict[str, dict[str, None]]) -> dict[str, list[str]]:
    return {key: list(library_ids.keys()) for key, library_ids in index.items()}


def _freeze_text_index(
    index: dict[str, dict[str, ExactTextHit]],
) -> dict[str, list[ExactTextHit]]:
    return {
        key: sorted(hits.values(), key=lambda hit: _text_match_priority(hit.match_type))
        for key, hits in index.items()
    }


def _text_match_priority(match_type: TextMatchType) -> int:
    if match_type == "library_id":
        return 0
    if match_type == "name":
        return 1
    return 2
