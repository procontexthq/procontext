"""Unit tests for page.service internals that are not part of the public API.

These tests cover background refresh orchestration directly so the integration
tests can stay focused on externally visible behavior.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from procontext.config import Settings
from procontext.models.cache import PageCacheEntry
from procontext.models.registry import RegistryIndexes
from procontext.page.service import _maybe_spawn_refresh
from procontext.state import AppState


def _make_state() -> AppState:
    return AppState(
        settings=Settings(),
        indexes=RegistryIndexes(),
        registry_version="test",
    )


def _cache_entry(*, last_checked_at: datetime | None = None) -> PageCacheEntry:
    now = datetime.now(UTC)
    return PageCacheEntry(
        url="https://example.com/docs/page.md",
        url_hash="hash",
        content="# Title",
        outline="1:# Title",
        fetched_at=now,
        expires_at=now,
        last_checked_at=last_checked_at,
        stale=True,
    )


class TestMaybeSpawnRefresh:
    def test_adds_url_to_refreshing_and_schedules_task(self) -> None:
        state = _make_state()
        created_tasks: list[object] = []

        def fake_create_task(coro: object) -> MagicMock:
            created_tasks.append(coro)
            close = getattr(coro, "close", None)
            if callable(close):
                close()
            return MagicMock()

        with patch("procontext.page.service.asyncio.create_task", side_effect=fake_create_task):
            _maybe_spawn_refresh(
                url="https://example.com/docs/page.md",
                url_hash="hash",
                state=state,
                cached_entry=_cache_entry(),
            )

        assert state._refreshing == {"hash"}
        assert len(created_tasks) == 1

    def test_skips_when_refresh_already_in_flight(self) -> None:
        state = _make_state()
        state._refreshing.add("hash")

        with patch("procontext.page.service.asyncio.create_task") as mock_create_task:
            _maybe_spawn_refresh(
                url="https://example.com/docs/page.md",
                url_hash="hash",
                state=state,
                cached_entry=_cache_entry(),
            )

        mock_create_task.assert_not_called()
        assert state._refreshing == {"hash"}

    def test_skips_when_last_checked_is_within_cooldown(self) -> None:
        state = _make_state()

        with patch("procontext.page.service.asyncio.create_task") as mock_create_task:
            _maybe_spawn_refresh(
                url="https://example.com/docs/page.md",
                url_hash="hash",
                state=state,
                cached_entry=_cache_entry(last_checked_at=datetime.now(UTC)),
            )

        mock_create_task.assert_not_called()
        assert state._refreshing == set()
