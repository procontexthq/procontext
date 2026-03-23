"""Registry persistence and state-file helpers."""

from __future__ import annotations

import json
import os
import sys
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import structlog

from procontext.models.registry import RegistryState

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

log = structlog.get_logger()


def save_registry_to_disk(
    *,
    registry_bytes: bytes,
    version: str,
    checksum: str,
    registry_path: Path,
    state_path: Path,
    additional_info_download_url: str | None = None,
    additional_info_checksum: str | None = None,
    write_bytes_fsync_fn: Callable[[Path, bytes], None] | None = None,
    fsync_directory_fn: Callable[[Path], None] | None = None,
) -> None:
    """Persist the local registry pair with atomic replace semantics."""
    write_bytes_fsync = write_bytes_fsync_fn or _write_bytes_fsync
    fsync_directory = fsync_directory_fn or _fsync_directory

    registry_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
    state_bytes = _state_bytes(
        RegistryState(
            version=version,
            checksum=checksum,
            updated_at=now,
            last_checked_at=now,
            additional_info_download_url=additional_info_download_url,
            additional_info_checksum=additional_info_checksum,
        )
    )

    registry_tmp = registry_path.with_suffix(registry_path.suffix + ".tmp")
    state_tmp = state_path.with_suffix(state_path.suffix + ".tmp")

    try:
        write_bytes_fsync(registry_tmp, registry_bytes)
        write_bytes_fsync(state_tmp, state_bytes)

        os.replace(registry_tmp, registry_path)
        os.replace(state_tmp, state_path)
        fsync_directory(registry_path.parent)
    finally:
        for tmp_path in (registry_tmp, state_tmp):
            with suppress(OSError):
                tmp_path.unlink(missing_ok=True)


def save_additional_info_to_disk(
    *,
    additional_info_bytes: bytes,
    additional_info_path: Path,
    write_bytes_fsync_fn: Callable[[Path, bytes], None] | None = None,
    fsync_directory_fn: Callable[[Path], None] | None = None,
) -> None:
    """Persist additional-info.json with atomic replace semantics."""
    write_bytes_fsync = write_bytes_fsync_fn or _write_bytes_fsync
    fsync_directory = fsync_directory_fn or _fsync_directory

    additional_info_path.parent.mkdir(parents=True, exist_ok=True)
    additional_info_tmp = additional_info_path.with_suffix(additional_info_path.suffix + ".tmp")
    try:
        write_bytes_fsync(additional_info_tmp, additional_info_bytes)
        os.replace(additional_info_tmp, additional_info_path)
        fsync_directory(additional_info_path.parent)
    finally:
        with suppress(OSError):
            additional_info_tmp.unlink(missing_ok=True)


def write_registry_state(
    state_path: Path,
    *,
    state: RegistryState,
    write_bytes_fsync_fn: Callable[[Path, bytes], None] | None = None,
) -> None:
    """Persist registry-state.json without rewriting known-libraries.json."""
    write_bytes_fsync = write_bytes_fsync_fn or _write_bytes_fsync
    state_bytes = _state_bytes(state)
    state_tmp = state_path.with_suffix(state_path.suffix + ".tmp")
    try:
        write_bytes_fsync(state_tmp, state_bytes)
        os.replace(state_tmp, state_path)
    finally:
        with suppress(OSError):
            state_tmp.unlink(missing_ok=True)


def registry_check_is_due(state_path: Path | None, poll_interval_hours: float) -> bool:
    """Return True if poll_interval_hours have elapsed since the last metadata check."""
    if state_path is None:
        return True
    try:
        state_data = json.loads(state_path.read_text(encoding="utf-8"))
        last_checked_raw = state_data.get("last_checked_at")
        if last_checked_raw is None:
            return True
        last_checked = datetime.fromisoformat(last_checked_raw)
        return datetime.now(tz=UTC) - last_checked >= timedelta(hours=poll_interval_hours)
    except (OSError, json.JSONDecodeError, ValueError, KeyError):
        log.debug("registry_check_is_due_parse_failed", path=str(state_path), exc_info=True)
        return True


def write_last_checked_at(
    state_path: Path,
    *,
    write_bytes_fsync_fn: Callable[[Path, bytes], None] | None = None,
) -> None:
    """Update last_checked_at in registry-state.json without touching other fields."""
    try:
        state = RegistryState.model_validate_json(state_path.read_text(encoding="utf-8"))
        state.last_checked_at = datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
        write_registry_state(
            state_path,
            state=state,
            write_bytes_fsync_fn=write_bytes_fsync_fn,
        )
    except Exception:
        log.debug("registry_state_last_checked_at_update_failed", exc_info=True)


def _state_bytes(state: RegistryState) -> bytes:
    return json.dumps(state.model_dump(exclude_none=True)).encode("utf-8")


def _write_bytes_fsync(path: Path, data: bytes) -> None:
    with path.open("wb") as file_obj:
        file_obj.write(data)
        file_obj.flush()
        os.fsync(file_obj.fileno())


def _fsync_directory(path: Path) -> None:
    if sys.platform == "win32":
        return
    directory_fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
