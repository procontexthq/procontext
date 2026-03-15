"""Tests for registry/update.py — remote update and setup download logic."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from pathlib import Path

import httpx

from procontext.config import Settings
from procontext.fetcher import build_allowlist
from procontext.registry import check_for_registry_update, fetch_registry_for_setup
from procontext.state import AppState

_METADATA_URL = "https://registry.example/registry_metadata.json"


def _sha256_prefixed(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _build_settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=str(tmp_path),
        cache={"db_path": str(tmp_path / "cache.db")},
        registry={"metadata_url": _METADATA_URL},
    )


def _build_state(
    *,
    client: httpx.AsyncClient,
    tmp_path: Path,
    indexes,
    sample_entries,
    registry_version: str = "unknown",
) -> AppState:
    return AppState(
        settings=_build_settings(tmp_path),
        indexes=indexes,
        registry_version=registry_version,
        registry_path=tmp_path / "registry" / "known-libraries.json",
        registry_state_path=tmp_path / "registry" / "registry-state.json",
        http_client=client,
        allowlist=build_allowlist(sample_entries),
    )


# ---------------------------------------------------------------------------
# check_for_registry_update
# ---------------------------------------------------------------------------


async def test_check_for_registry_update_success_updates_state(
    tmp_path: Path,
    indexes,
    sample_entries,
) -> None:
    updated_entries = [
        {
            "id": "newlib",
            "name": "NewLib",
            "llms_txt_url": "https://docs.newlib.dev/llms.txt",
        }
    ]
    registry_bytes = json.dumps(updated_entries).encode("utf-8")
    checksum = _sha256_prefixed(registry_bytes)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("registry_metadata.json"):
            return httpx.Response(
                200,
                json={
                    "version": "2026-02-26",
                    "download_url": "https://registry.example/known-libraries.json",
                    "checksum": checksum,
                },
            )
        if request.url.path.endswith("known-libraries.json"):
            return httpx.Response(200, content=registry_bytes)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        state = _build_state(
            client=client,
            tmp_path=tmp_path,
            indexes=indexes,
            sample_entries=sample_entries,
            registry_version="2026-02-20",
        )
        outcome = await check_for_registry_update(state)

    assert outcome == "success"
    assert state.registry_version == "2026-02-26"
    assert "newlib" in state.indexes.by_id
    assert state.registry_path is not None and state.registry_path.is_file()
    assert state.registry_state_path is not None and state.registry_state_path.is_file()


async def test_check_for_registry_update_transient_on_metadata_5xx(
    tmp_path: Path,
    indexes,
    sample_entries,
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        state = _build_state(
            client=client,
            tmp_path=tmp_path,
            indexes=indexes,
            sample_entries=sample_entries,
        )
        outcome = await check_for_registry_update(state)

    assert outcome == "transient_failure"
    assert state.registry_version == "unknown"


async def test_check_for_registry_update_semantic_on_checksum_mismatch(
    tmp_path: Path,
    indexes,
    sample_entries,
) -> None:
    updated_entries = [
        {
            "id": "newlib",
            "name": "NewLib",
            "llms_txt_url": "https://docs.newlib.dev/llms.txt",
        }
    ]
    registry_bytes = json.dumps(updated_entries).encode("utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("registry_metadata.json"):
            return httpx.Response(
                200,
                json={
                    "version": "2026-02-26",
                    "download_url": "https://registry.example/known-libraries.json",
                    "checksum": "sha256:deadbeef",
                },
            )
        if request.url.path.endswith("known-libraries.json"):
            return httpx.Response(200, content=registry_bytes)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        state = _build_state(
            client=client,
            tmp_path=tmp_path,
            indexes=indexes,
            sample_entries=sample_entries,
            registry_version="2026-02-20",
        )
        outcome = await check_for_registry_update(state)

    assert outcome == "semantic_failure"
    assert state.registry_version == "2026-02-20"


async def test_check_for_registry_update_up_to_date_writes_last_checked_at(
    tmp_path: Path,
    indexes,
    sample_entries,
) -> None:
    """When remote version equals current, returns 'success' and updates last_checked_at."""
    current_version = "2026-02-20"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "version": current_version,
                "download_url": "https://registry.example/known-libraries.json",
                "checksum": "sha256:abc123",
            },
        )

    # Write a state file for write_last_checked_at to update
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    old_checked = "2026-01-01T00:00:00Z"
    (registry_dir / "registry-state.json").write_text(
        json.dumps(
            {
                "version": current_version,
                "checksum": "sha256:abc123",
                "last_checked_at": old_checked,
            }
        ),
        encoding="utf-8",
    )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        state = _build_state(
            client=client,
            tmp_path=tmp_path,
            indexes=indexes,
            sample_entries=sample_entries,
            registry_version=current_version,
        )
        outcome = await check_for_registry_update(state)

    assert outcome == "success"
    assert state.registry_version == current_version  # unchanged

    state_data = json.loads((registry_dir / "registry-state.json").read_text(encoding="utf-8"))
    assert state_data["last_checked_at"] != old_checked  # timestamp was refreshed


async def test_check_for_registry_update_semantic_on_metadata_4xx(
    tmp_path: Path,
    indexes,
    sample_entries,
) -> None:
    """A 4xx response on the metadata URL maps to semantic_failure (not transient)."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        state = _build_state(
            client=client,
            tmp_path=tmp_path,
            indexes=indexes,
            sample_entries=sample_entries,
        )
        outcome = await check_for_registry_update(state)

    assert outcome == "semantic_failure"
    assert state.registry_version == "unknown"  # unchanged


# ---------------------------------------------------------------------------
# fetch_registry_for_setup
# ---------------------------------------------------------------------------


class TestFetchRegistryForSetup:
    """Tests for fetch_registry_for_setup.

    fetch_registry_for_setup always passes current_version=None to
    _download_registry_if_newer, so a remote version string can never equal
    None — the download always runs. The defensive `result == "success"` branch
    in the function body is therefore unreachable in normal operation and is not
    tested here.
    """

    async def test_success_downloads_and_persists(self, tmp_path: Path) -> None:
        """Happy path: valid metadata + registry → files written, returns True."""
        entries = [
            {
                "id": "setuplib",
                "name": "SetupLib",
                "llms_txt_url": "https://docs.setuplib.dev/llms.txt",
            }
        ]
        registry_bytes = json.dumps(entries).encode("utf-8")
        checksum = _sha256_prefixed(registry_bytes)

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("registry_metadata.json"):
                return httpx.Response(
                    200,
                    json={
                        "version": "2026-03-01",
                        "download_url": "https://registry.example/known-libraries.json",
                        "checksum": checksum,
                    },
                )
            if request.url.path.endswith("known-libraries.json"):
                return httpx.Response(200, content=registry_bytes)
            return httpx.Response(404)

        settings = _build_settings(tmp_path)
        with patch(
            "procontext.registry.build_http_client",
            return_value=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        ):
            result = await fetch_registry_for_setup(settings)

        registry_path = tmp_path / "registry" / "known-libraries.json"
        state_path = tmp_path / "registry" / "registry-state.json"
        assert result is True
        assert registry_path.read_bytes() == registry_bytes
        state_data = json.loads(state_path.read_text(encoding="utf-8"))
        assert state_data["version"] == "2026-03-01"
        assert state_data["checksum"] == checksum

    async def test_transient_failure_returns_false(self, tmp_path: Path) -> None:
        """503 on metadata fetch → transient failure → returns False, no files written."""

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(503)

        settings = _build_settings(tmp_path)
        with patch(
            "procontext.registry.build_http_client",
            return_value=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        ):
            result = await fetch_registry_for_setup(settings)

        assert result is False
        assert not (tmp_path / "registry" / "known-libraries.json").exists()
        assert not (tmp_path / "registry" / "registry-state.json").exists()

    async def test_checksum_mismatch_returns_false(self, tmp_path: Path) -> None:
        """Metadata checksum doesn't match registry body → returns False, no files written."""
        entries = [{"id": "lib", "name": "Lib", "llms_txt_url": "https://docs.lib.dev/llms.txt"}]
        registry_bytes = json.dumps(entries).encode("utf-8")

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("registry_metadata.json"):
                return httpx.Response(
                    200,
                    json={
                        "version": "2026-03-01",
                        "download_url": "https://registry.example/known-libraries.json",
                        "checksum": "sha256:deadbeef",  # does not match body
                    },
                )
            if request.url.path.endswith("known-libraries.json"):
                return httpx.Response(200, content=registry_bytes)
            return httpx.Response(404)

        settings = _build_settings(tmp_path)
        with patch(
            "procontext.registry.build_http_client",
            return_value=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        ):
            result = await fetch_registry_for_setup(settings)

        assert result is False
        assert not (tmp_path / "registry" / "known-libraries.json").exists()
        assert not (tmp_path / "registry" / "registry-state.json").exists()

    async def test_persist_failure_returns_false(self, tmp_path: Path) -> None:
        """Download succeeds but save_registry_to_disk raises → returns False."""
        entries = [{"id": "lib", "name": "Lib", "llms_txt_url": "https://docs.lib.dev/llms.txt"}]
        registry_bytes = json.dumps(entries).encode("utf-8")
        checksum = _sha256_prefixed(registry_bytes)

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("registry_metadata.json"):
                return httpx.Response(
                    200,
                    json={
                        "version": "2026-03-01",
                        "download_url": "https://registry.example/known-libraries.json",
                        "checksum": checksum,
                    },
                )
            if request.url.path.endswith("known-libraries.json"):
                return httpx.Response(200, content=registry_bytes)
            return httpx.Response(404)

        settings = _build_settings(tmp_path)
        with (
            patch(
                "procontext.registry.build_http_client",
                return_value=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
            ),
            patch(
                "procontext.registry.save_registry_to_disk",
                side_effect=OSError("disk full"),
            ),
        ):
            result = await fetch_registry_for_setup(settings)

        assert result is False
