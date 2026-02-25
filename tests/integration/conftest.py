"""Integration test fixtures.

Provides a fully wired AppState with in-memory SQLite, mocked HTTP client,
and all Phase 2 components. Registry-related fixtures come from
tests/conftest.py (sample_entries, indexes).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import aiosqlite
import httpx
import pytest

from procontext.cache import Cache
from procontext.config import Settings
from procontext.fetcher import Fetcher, build_allowlist
from procontext.state import AppState

if TYPE_CHECKING:
    from procontext.models.registry import RegistryEntry
    from procontext.registry import RegistryIndexes


@pytest.fixture()
async def app_state(indexes: RegistryIndexes, sample_entries: list[RegistryEntry]) -> AppState:
    """Full AppState wired for Phase 2 integration tests."""
    async with aiosqlite.connect(":memory:") as db:
        cache = Cache(db)
        await cache.init_db()

        async with httpx.AsyncClient() as client:
            fetcher = Fetcher(client)
            allowlist = build_allowlist(sample_entries)

            state = AppState(
                settings=Settings(),
                indexes=indexes,
                registry_version="test",
                http_client=client,
                cache=cache,
                fetcher=fetcher,
                allowlist=allowlist,
            )
            yield state
