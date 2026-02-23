"""Library registry: loading, index building, and background update check.

Full implementation in Phase 1. This stub defines RegistryIndexes so that
AppState can reference it in type annotations from Phase 0 onward.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pro_context.models.registry import RegistryEntry


@dataclass
class RegistryIndexes:
    """In-memory indexes built from known-libraries.json at startup.

    Three dicts rebuilt in a single pass (<100ms for 1,000 entries).
    """

    # package name (lowercase) → library ID  e.g. "langchain-openai" → "langchain"
    by_package: dict[str, str] = field(default_factory=dict)

    # library ID → full registry entry
    by_id: dict[str, RegistryEntry] = field(default_factory=dict)

    # flat list of (term, library_id) pairs for fuzzy matching
    # populated from all IDs + package names + aliases (lowercased)
    fuzzy_corpus: list[tuple[str, str]] = field(default_factory=list)


# load_registry(), build_indexes(), check_for_registry_update() — Phase 1
