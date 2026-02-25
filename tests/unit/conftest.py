"""Unit-specific fixtures (no I/O beyond in-memory SQLite)."""

from __future__ import annotations

import aiosqlite
import pytest

from procontext.cache import Cache


@pytest.fixture()
async def cache():
    """In-memory SQLite cache for unit tests."""
    async with aiosqlite.connect(":memory:") as db:
        c = Cache(db)
        await c.init_db()
        yield c
