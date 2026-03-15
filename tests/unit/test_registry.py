"""Tests for registry/local.py and registry/storage.py — loading, persistence, and state checks."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import patch

from procontext.registry import load_registry, save_registry_to_disk
from procontext.registry.storage import (
    _fsync_directory,
    registry_check_is_due,
    write_last_checked_at,
)

if TYPE_CHECKING:
    from pathlib import Path


def _sha256_prefixed(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# load_registry
# ---------------------------------------------------------------------------


def test_load_registry_uses_valid_local_pair(tmp_path: Path) -> None:
    payload = [
        {
            "id": "localonly",
            "name": "LocalOnly",
            "llms_txt_url": "https://docs.localonly.dev/llms.txt",
        }
    ]
    registry_bytes = json.dumps(payload).encode("utf-8")
    checksum = _sha256_prefixed(registry_bytes)

    registry_path = tmp_path / "known-libraries.json"
    state_path = tmp_path / "registry-state.json"
    registry_path.write_bytes(registry_bytes)
    state_path.write_text(
        json.dumps(
            {
                "version": "2026-02-25",
                "checksum": checksum,
                "updated_at": "2026-02-25T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    entries, version = load_registry(registry_path, state_path)

    assert version == "2026-02-25"
    assert [entry.id for entry in entries] == ["localonly"]


def test_load_registry_returns_none_on_checksum_mismatch(tmp_path: Path) -> None:
    payload = [
        {
            "id": "localonly",
            "name": "LocalOnly",
            "llms_txt_url": "https://docs.localonly.dev/llms.txt",
        }
    ]

    registry_path = tmp_path / "known-libraries.json"
    state_path = tmp_path / "registry-state.json"
    registry_path.write_text(json.dumps(payload), encoding="utf-8")
    state_path.write_text(
        json.dumps(
            {
                "version": "2026-02-25",
                "checksum": "sha256:deadbeef",
                "updated_at": "2026-02-25T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    assert load_registry(registry_path, state_path) is None


def test_load_registry_returns_none_when_both_paths_none() -> None:
    assert load_registry(None, None) is None


def test_load_registry_returns_none_when_files_missing(tmp_path: Path) -> None:
    assert load_registry(tmp_path / "missing.json", tmp_path / "also-missing.json") is None


def test_load_registry_returns_none_on_invalid_version_type(tmp_path: Path) -> None:
    """A non-string version (e.g. integer) in registry-state.json → None."""
    payload = [{"id": "lib", "name": "Lib", "llms_txt_url": "https://docs.lib.dev/llms.txt"}]
    registry_bytes = json.dumps(payload).encode("utf-8")
    checksum = _sha256_prefixed(registry_bytes)

    registry_path = tmp_path / "known-libraries.json"
    state_path = tmp_path / "registry-state.json"
    registry_path.write_bytes(registry_bytes)
    state_path.write_text(
        json.dumps({"version": 123, "checksum": checksum}),
        encoding="utf-8",
    )

    assert load_registry(registry_path, state_path) is None


def test_load_registry_returns_none_on_invalid_checksum_format(tmp_path: Path) -> None:
    """A checksum that does not start with 'sha256:' → None."""
    payload = [{"id": "lib", "name": "Lib", "llms_txt_url": "https://docs.lib.dev/llms.txt"}]
    registry_bytes = json.dumps(payload).encode("utf-8")

    registry_path = tmp_path / "known-libraries.json"
    state_path = tmp_path / "registry-state.json"
    registry_path.write_bytes(registry_bytes)
    state_path.write_text(
        json.dumps({"version": "1.0", "checksum": "not-sha256-prefixed"}),
        encoding="utf-8",
    )

    assert load_registry(registry_path, state_path) is None


def test_load_registry_returns_none_on_corrupt_json(tmp_path: Path) -> None:
    """A registry file that is not valid JSON → None."""
    registry_path = tmp_path / "known-libraries.json"
    state_path = tmp_path / "registry-state.json"
    registry_path.write_bytes(b"not valid json {{{")
    state_path.write_text(
        json.dumps({"version": "1.0", "checksum": "sha256:abc"}),
        encoding="utf-8",
    )

    assert load_registry(registry_path, state_path) is None


def test_build_indexes_duplicate_ids_last_entry_wins(tmp_path: Path) -> None:
    """Duplicate library IDs in the registry silently overwrite — last entry wins.

    This documents current behaviour. A future hardening pass could log a warning
    or raise on duplicates, but today the second entry replaces the first in by_id.
    """
    from procontext.models.registry import RegistryEntry
    from procontext.registry import build_indexes

    entry_a = RegistryEntry(
        id="duplicate",
        name="First",
        llms_txt_url="https://first.example.com/llms.txt",
    )
    entry_b = RegistryEntry(
        id="duplicate",
        name="Second",
        llms_txt_url="https://second.example.com/llms.txt",
    )
    indexes = build_indexes([entry_a, entry_b])
    assert indexes.by_id["duplicate"].name == "Second"


# ---------------------------------------------------------------------------
# save_registry_to_disk
# ---------------------------------------------------------------------------


def test_save_registry_to_disk_writes_registry_pair(tmp_path: Path) -> None:
    payload = [
        {
            "id": "persistedlib",
            "name": "PersistedLib",
            "llms_txt_url": "https://docs.persisted.dev/llms.txt",
        }
    ]
    registry_bytes = json.dumps(payload).encode("utf-8")
    checksum = _sha256_prefixed(registry_bytes)

    registry_path = tmp_path / "registry" / "known-libraries.json"
    state_path = tmp_path / "registry" / "registry-state.json"

    save_registry_to_disk(
        registry_bytes=registry_bytes,
        version="2026-02-26",
        checksum=checksum,
        registry_path=registry_path,
        state_path=state_path,
    )

    assert registry_path.read_bytes() == registry_bytes
    state_data = json.loads(state_path.read_text(encoding="utf-8"))
    assert state_data["version"] == "2026-02-26"
    assert state_data["checksum"] == checksum
    assert "updated_at" in state_data
    assert "last_checked_at" in state_data


# ---------------------------------------------------------------------------
# registry_check_is_due
# ---------------------------------------------------------------------------


class TestRegistryCheckIsDue:
    def test_no_state_file_returns_true(self, tmp_path: Path) -> None:
        assert registry_check_is_due(tmp_path / "missing.json", 24) is True

    def test_no_last_checked_at_field_returns_true(self, tmp_path: Path) -> None:
        state_file = tmp_path / "state.json"
        state_file.write_text(
            json.dumps({"version": "1", "checksum": "sha256:abc"}), encoding="utf-8"
        )
        assert registry_check_is_due(state_file, 24) is True

    def test_recent_check_returns_false(self, tmp_path: Path) -> None:
        state_file = tmp_path / "state.json"
        state_file.write_text(
            json.dumps(
                {
                    "version": "1",
                    "checksum": "sha256:abc",
                    "last_checked_at": datetime.now(UTC).isoformat(),
                }
            ),
            encoding="utf-8",
        )
        assert registry_check_is_due(state_file, 24) is False

    def test_stale_check_returns_true(self, tmp_path: Path) -> None:
        stale = (datetime.now(UTC) - timedelta(hours=25)).isoformat()
        state_file = tmp_path / "state.json"
        state_file.write_text(
            json.dumps({"version": "1", "checksum": "sha256:abc", "last_checked_at": stale}),
            encoding="utf-8",
        )
        assert registry_check_is_due(state_file, 24) is True

    def test_corrupt_state_file_returns_true(self, tmp_path: Path) -> None:
        state_file = tmp_path / "state.json"
        state_file.write_bytes(b"not valid json")
        assert registry_check_is_due(state_file, 24) is True


# ---------------------------------------------------------------------------
# write_last_checked_at
# ---------------------------------------------------------------------------


class TestWriteLastCheckedAt:
    def test_updates_last_checked_at_and_preserves_other_fields(self, tmp_path: Path) -> None:
        """Updates last_checked_at in-place without touching other state fields."""
        state_path = tmp_path / "registry-state.json"
        original = {
            "version": "2026-02-20",
            "checksum": "sha256:abc",
            "updated_at": "2026-01-01T00:00:00Z",
            "last_checked_at": "2026-01-01T00:00:00Z",
        }
        state_path.write_text(json.dumps(original), encoding="utf-8")

        before = datetime.now(UTC)
        write_last_checked_at(state_path)
        after = datetime.now(UTC)

        state_data = json.loads(state_path.read_text(encoding="utf-8"))
        assert state_data["version"] == "2026-02-20"
        assert state_data["checksum"] == "sha256:abc"
        assert state_data["updated_at"] == "2026-01-01T00:00:00Z"
        last_checked = datetime.fromisoformat(state_data["last_checked_at"])
        assert before <= last_checked <= after

    def test_nonexistent_file_does_not_raise(self, tmp_path: Path) -> None:
        """A missing state file is silently ignored (non-fatal)."""
        write_last_checked_at(tmp_path / "nonexistent.json")


# ---------------------------------------------------------------------------
# _fsync_directory platform guard
# ---------------------------------------------------------------------------


class TestFsyncDirectoryWindowsGuard:
    """Verify _fsync_directory is a no-op on Windows."""

    def test_noop_on_win32(self, tmp_path: Path) -> None:
        with patch("procontext.registry.storage.sys") as mock_sys:
            mock_sys.platform = "win32"
            # Should return without calling os.open or os.fsync
            _fsync_directory(tmp_path)

    def test_executes_on_non_windows(self, tmp_path: Path) -> None:
        with patch("procontext.registry.storage.sys") as mock_sys:
            mock_sys.platform = "linux"
            # On a real filesystem (macOS/Linux CI), this should succeed
            _fsync_directory(tmp_path)

    def test_save_registry_to_disk_succeeds_on_win32(self, tmp_path: Path) -> None:
        payload = [{"id": "test", "name": "Test", "llms_txt_url": "https://example.com/llms.txt"}]
        registry_bytes = json.dumps(payload).encode("utf-8")
        checksum = _sha256_prefixed(registry_bytes)

        registry_path = tmp_path / "registry" / "known-libraries.json"
        state_path = tmp_path / "registry" / "registry-state.json"

        with patch("procontext.registry.storage.sys") as mock_sys:
            mock_sys.platform = "win32"
            save_registry_to_disk(
                registry_bytes=registry_bytes,
                version="2026-02-26",
                checksum=checksum,
                registry_path=registry_path,
                state_path=state_path,
            )

        assert registry_path.read_bytes() == registry_bytes
