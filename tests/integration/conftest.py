"""Integration test fixtures.

Provides a fully wired AppState using the shared sample_entries and indexes
fixtures from tests/conftest.py. HTTP and cache components are added in
Phase 2 — for now only registry-related fields are populated.
"""

from __future__ import annotations

import pytest
from procontext.config import Settings
from procontext.registry import RegistryIndexes
from procontext.state import AppState


@pytest.fixture()
def app_state(indexes: RegistryIndexes) -> AppState:
    """AppState wired for Phase 1 integration tests."""
    return AppState(
        settings=Settings(),
        indexes=indexes,
        registry_version="test",
    )
