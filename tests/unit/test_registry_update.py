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
from procontext.fetch.security import build_allowlist
from procontext.registry import build_indexes, check_for_registry_update, fetch_registry_for_setup
from procontext.registry.storage import save_registry_to_disk, write_registry_state
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
        registry_additional_info_path=tmp_path / "registry" / "additional-info.json",
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
                "checksum": "sha256:" + ("c" * 64),
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
                "checksum": "sha256:" + ("c" * 64),
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


async def test_check_for_registry_update_refreshes_additional_info_without_version_change(
    tmp_path: Path,
    indexes,
    sample_entries,
) -> None:
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    current_version = "2026-02-20"
    sidecar_bytes = b'{"useful_md_probe_base_urls":["https://docs.example.com"]}'
    sidecar_checksum = _sha256_prefixed(sidecar_bytes)
    (registry_dir / "registry-state.json").write_text(
        json.dumps(
            {
                "version": current_version,
                "checksum": "sha256:" + ("a" * 64),
                "last_checked_at": "2026-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("registry_metadata.json"):
            return httpx.Response(
                200,
                json={
                    "version": current_version,
                    "download_url": "https://registry.example/known-libraries.json",
                    "checksum": "sha256:" + ("a" * 64),
                    "additional_info_download_url": "https://registry.example/additional-info.json",
                    "additional_info_checksum": sidecar_checksum,
                },
            )
        if request.url.path.endswith("additional-info.json"):
            return httpx.Response(200, content=sidecar_bytes)
        return httpx.Response(404)

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
    assert (
        state.registry_additional_info_download_url
        == "https://registry.example/additional-info.json"
    )
    assert state.registry_additional_info_checksum == sidecar_checksum
    assert (registry_dir / "additional-info.json").read_bytes() == sidecar_bytes


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

    async def test_setup_downloads_additional_info_when_advertised(self, tmp_path: Path) -> None:
        entries = [
            {
                "id": "setuplib",
                "name": "SetupLib",
                "llms_txt_url": "https://docs.setuplib.dev/llms.txt",
            }
        ]
        registry_bytes = json.dumps(entries).encode("utf-8")
        registry_checksum = _sha256_prefixed(registry_bytes)
        additional_info_bytes = b'{"useful_md_probe_base_urls":["https://docs.setuplib.dev"]}'
        additional_info_checksum = _sha256_prefixed(additional_info_bytes)

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("registry_metadata.json"):
                return httpx.Response(
                    200,
                    json={
                        "version": "2026-03-01",
                        "download_url": "https://registry.example/known-libraries.json",
                        "checksum": registry_checksum,
                        "additional_info_download_url": "https://registry.example/additional-info.json",
                        "additional_info_checksum": additional_info_checksum,
                    },
                )
            if request.url.path.endswith("known-libraries.json"):
                return httpx.Response(200, content=registry_bytes)
            if request.url.path.endswith("additional-info.json"):
                return httpx.Response(200, content=additional_info_bytes)
            return httpx.Response(404)

        settings = _build_settings(tmp_path)
        with patch(
            "procontext.registry.build_http_client",
            return_value=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        ):
            result = await fetch_registry_for_setup(settings)

        assert result is True
        state_data = json.loads(
            (tmp_path / "registry" / "registry-state.json").read_text(encoding="utf-8")
        )
        assert (
            state_data["additional_info_download_url"]
            == "https://registry.example/additional-info.json"
        )
        assert state_data["additional_info_checksum"] == additional_info_checksum
        assert (
            tmp_path / "registry" / "additional-info.json"
        ).read_bytes() == additional_info_bytes

    async def test_setup_succeeds_when_additional_info_download_fails(self, tmp_path: Path) -> None:
        entries = [
            {
                "id": "setuplib",
                "name": "SetupLib",
                "llms_txt_url": "https://docs.setuplib.dev/llms.txt",
            }
        ]
        registry_bytes = json.dumps(entries).encode("utf-8")
        registry_checksum = _sha256_prefixed(registry_bytes)

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("registry_metadata.json"):
                return httpx.Response(
                    200,
                    json={
                        "version": "2026-03-01",
                        "download_url": "https://registry.example/known-libraries.json",
                        "checksum": registry_checksum,
                        "additional_info_download_url": "https://registry.example/additional-info.json",
                        "additional_info_checksum": "sha256:" + ("b" * 64),
                    },
                )
            if request.url.path.endswith("known-libraries.json"):
                return httpx.Response(200, content=registry_bytes)
            if request.url.path.endswith("additional-info.json"):
                return httpx.Response(503)
            return httpx.Response(404)

        settings = _build_settings(tmp_path)
        with patch(
            "procontext.registry.build_http_client",
            return_value=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        ):
            result = await fetch_registry_for_setup(settings)

        assert result is True
        assert (tmp_path / "registry" / "known-libraries.json").exists()
        assert not (tmp_path / "registry" / "additional-info.json").exists()

    async def test_setup_ignores_invalid_optional_additional_info_metadata(
        self, tmp_path: Path
    ) -> None:
        entries = [
            {
                "id": "setuplib",
                "name": "SetupLib",
                "llms_txt_url": "https://docs.setuplib.dev/llms.txt",
            }
        ]
        registry_bytes = json.dumps(entries).encode("utf-8")
        registry_checksum = _sha256_prefixed(registry_bytes)

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("registry_metadata.json"):
                return httpx.Response(
                    200,
                    json={
                        "version": "2026-03-01",
                        "download_url": "https://registry.example/known-libraries.json",
                        "checksum": registry_checksum,
                        "additional_info_download_url": "https://registry.example/additional-info.json",
                        "additional_info_checksum": "sha256:short",
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

        assert result is True
        state_data = json.loads(
            (tmp_path / "registry" / "registry-state.json").read_text(encoding="utf-8")
        )
        assert "additional_info_download_url" not in state_data
        assert "additional_info_checksum" not in state_data

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

    async def test_setup_additional_info_persist_failure_still_succeeds(
        self, tmp_path: Path
    ) -> None:
        """Additional-info persist failure during setup is non-fatal — returns True."""
        entries = [
            {
                "id": "setuplib",
                "name": "SetupLib",
                "llms_txt_url": "https://docs.setuplib.dev/llms.txt",
            }
        ]
        registry_bytes = json.dumps(entries).encode("utf-8")
        registry_checksum = _sha256_prefixed(registry_bytes)
        additional_info_bytes = b'{"useful_md_probe_base_urls":["https://docs.setuplib.dev"]}'
        additional_info_checksum = _sha256_prefixed(additional_info_bytes)

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("registry_metadata.json"):
                return httpx.Response(
                    200,
                    json={
                        "version": "2026-03-01",
                        "download_url": "https://registry.example/known-libraries.json",
                        "checksum": registry_checksum,
                        "additional_info_download_url": "https://registry.example/additional-info.json",
                        "additional_info_checksum": additional_info_checksum,
                    },
                )
            if request.url.path.endswith("known-libraries.json"):
                return httpx.Response(200, content=registry_bytes)
            if request.url.path.endswith("additional-info.json"):
                return httpx.Response(200, content=additional_info_bytes)
            return httpx.Response(404)

        settings = _build_settings(tmp_path)
        with (
            patch(
                "procontext.registry.build_http_client",
                return_value=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
            ),
            patch(
                "procontext.registry.save_additional_info_to_disk",
                side_effect=OSError("disk full"),
            ),
        ):
            result = await fetch_registry_for_setup(settings)

        # Registry itself should still be persisted
        assert result is True
        assert (tmp_path / "registry" / "known-libraries.json").exists()

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


# ---------------------------------------------------------------------------
# fetch_registry_additional_info_for_setup
# ---------------------------------------------------------------------------


class TestFetchRegistryAdditionalInfoForSetup:
    """Tests for fetch_registry_additional_info_for_setup."""

    async def test_returns_false_when_no_state_file(self, tmp_path: Path) -> None:
        """Missing registry-state.json → returns False."""
        settings = _build_settings(tmp_path)
        with patch(
            "procontext.registry.build_http_client",
            return_value=httpx.AsyncClient(
                transport=httpx.MockTransport(lambda _: httpx.Response(404))
            ),
        ):
            from procontext.registry import fetch_registry_additional_info_for_setup

            result = await fetch_registry_additional_info_for_setup(settings)
        assert result is False

    async def test_returns_true_when_not_advertised(self, tmp_path: Path) -> None:
        """State file exists but no additional-info metadata → True."""
        registry_dir = tmp_path / "registry"
        registry_dir.mkdir(parents=True, exist_ok=True)
        (registry_dir / "registry-state.json").write_text(
            json.dumps(
                {
                    "version": "2026-03-01",
                    "checksum": "sha256:" + ("a" * 64),
                }
            ),
            encoding="utf-8",
        )

        settings = _build_settings(tmp_path)
        with patch(
            "procontext.registry.build_http_client",
            return_value=httpx.AsyncClient(
                transport=httpx.MockTransport(lambda _: httpx.Response(404))
            ),
        ):
            from procontext.registry import fetch_registry_additional_info_for_setup

            result = await fetch_registry_additional_info_for_setup(settings)
        assert result is True

    async def test_downloads_and_persists(self, tmp_path: Path) -> None:
        """Happy path: advertised + valid download → persists, returns True."""
        registry_dir = tmp_path / "registry"
        registry_dir.mkdir(parents=True, exist_ok=True)
        ai_bytes = b'{"useful_md_probe_base_urls":["https://docs.example.com"]}'
        ai_checksum = _sha256_prefixed(ai_bytes)

        (registry_dir / "registry-state.json").write_text(
            json.dumps(
                {
                    "version": "2026-03-01",
                    "checksum": "sha256:" + ("a" * 64),
                    "additional_info_download_url": (
                        "https://registry.example/additional-info.json"
                    ),
                    "additional_info_checksum": ai_checksum,
                }
            ),
            encoding="utf-8",
        )

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("additional-info.json"):
                return httpx.Response(200, content=ai_bytes)
            return httpx.Response(404)

        settings = _build_settings(tmp_path)
        with patch(
            "procontext.registry.build_http_client",
            return_value=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        ):
            from procontext.registry import fetch_registry_additional_info_for_setup

            result = await fetch_registry_additional_info_for_setup(settings)

        assert result is True
        assert (registry_dir / "additional-info.json").read_bytes() == ai_bytes

    async def test_returns_false_on_download_failure(self, tmp_path: Path) -> None:
        """Advertised but download fails → returns False."""
        registry_dir = tmp_path / "registry"
        registry_dir.mkdir(parents=True, exist_ok=True)
        (registry_dir / "registry-state.json").write_text(
            json.dumps(
                {
                    "version": "2026-03-01",
                    "checksum": "sha256:" + ("a" * 64),
                    "additional_info_download_url": (
                        "https://registry.example/additional-info.json"
                    ),
                    "additional_info_checksum": "sha256:" + ("b" * 64),
                }
            ),
            encoding="utf-8",
        )

        settings = _build_settings(tmp_path)
        with patch(
            "procontext.registry.build_http_client",
            return_value=httpx.AsyncClient(
                transport=httpx.MockTransport(lambda _: httpx.Response(503))
            ),
        ):
            from procontext.registry import fetch_registry_additional_info_for_setup

            result = await fetch_registry_additional_info_for_setup(settings)
        assert result is False

    async def test_returns_false_when_incomplete_metadata(self, tmp_path: Path) -> None:
        """State has download_url but no checksum → incomplete → False."""
        registry_dir = tmp_path / "registry"
        registry_dir.mkdir(parents=True, exist_ok=True)
        (registry_dir / "registry-state.json").write_text(
            json.dumps(
                {
                    "version": "2026-03-01",
                    "checksum": "sha256:" + ("a" * 64),
                    "additional_info_download_url": (
                        "https://registry.example/additional-info.json"
                    ),
                }
            ),
            encoding="utf-8",
        )

        settings = _build_settings(tmp_path)
        with patch(
            "procontext.registry.build_http_client",
            return_value=httpx.AsyncClient(
                transport=httpx.MockTransport(lambda _: httpx.Response(404))
            ),
        ):
            from procontext.registry import fetch_registry_additional_info_for_setup

            result = await fetch_registry_additional_info_for_setup(settings)
        assert result is False

    async def test_returns_false_on_persist_failure(self, tmp_path: Path) -> None:
        """Download succeeds but persist raises → returns False."""
        registry_dir = tmp_path / "registry"
        registry_dir.mkdir(parents=True, exist_ok=True)
        ai_bytes = b'{"useful_md_probe_base_urls":["https://docs.example.com"]}'
        ai_checksum = _sha256_prefixed(ai_bytes)

        (registry_dir / "registry-state.json").write_text(
            json.dumps(
                {
                    "version": "2026-03-01",
                    "checksum": "sha256:" + ("a" * 64),
                    "additional_info_download_url": (
                        "https://registry.example/additional-info.json"
                    ),
                    "additional_info_checksum": ai_checksum,
                }
            ),
            encoding="utf-8",
        )

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("additional-info.json"):
                return httpx.Response(200, content=ai_bytes)
            return httpx.Response(404)

        settings = _build_settings(tmp_path)
        with (
            patch(
                "procontext.registry.build_http_client",
                return_value=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
            ),
            patch(
                "procontext.registry.save_additional_info_to_disk",
                side_effect=OSError("disk full"),
            ),
        ):
            from procontext.registry import fetch_registry_additional_info_for_setup

            result = await fetch_registry_additional_info_for_setup(settings)
        assert result is False


# ---------------------------------------------------------------------------
# check_for_registry_update — additional branch coverage
# ---------------------------------------------------------------------------


async def test_check_for_registry_update_no_http_client(
    tmp_path: Path, indexes, sample_entries
) -> None:
    """Returns semantic_failure when http_client is None."""
    state = AppState(
        settings=_build_settings(tmp_path),
        indexes=indexes,
        registry_version="2026-02-20",
        http_client=None,
        allowlist=build_allowlist(sample_entries),
    )
    outcome = await check_for_registry_update(state)
    assert outcome == "semantic_failure"


async def test_check_for_registry_update_network_error(
    tmp_path: Path, indexes, sample_entries
) -> None:
    """Network error on metadata fetch → transient_failure."""
    transport = httpx.MockTransport(lambda _: (_ for _ in ()).throw(httpx.ConnectError("refused")))
    async with httpx.AsyncClient(transport=transport) as client:
        state = _build_state(
            client=client,
            tmp_path=tmp_path,
            indexes=indexes,
            sample_entries=sample_entries,
        )
        outcome = await check_for_registry_update(state)
    assert outcome == "transient_failure"


async def test_check_for_registry_update_ai_download_failure_is_non_fatal(
    tmp_path: Path, indexes, sample_entries
) -> None:
    """additional-info download failure is non-fatal and preserves update success."""
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    ver = "2026-02-20"
    (registry_dir / "registry-state.json").write_text(
        json.dumps(
            {
                "version": ver,
                "checksum": "sha256:" + ("a" * 64),
                "last_checked_at": "2026-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("registry_metadata.json"):
            return httpx.Response(
                200,
                json={
                    "version": ver,
                    "download_url": "https://r.example/libs.json",
                    "checksum": "sha256:" + ("a" * 64),
                    "additional_info_download_url": "https://r.example/ai.json",
                    "additional_info_checksum": "sha256:" + ("d" * 64),
                },
            )
        if request.url.path.endswith("ai.json"):
            return httpx.Response(503)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        state = _build_state(
            client=client,
            tmp_path=tmp_path,
            indexes=indexes,
            sample_entries=sample_entries,
            registry_version=ver,
        )
        outcome = await check_for_registry_update(state)

    assert outcome == "success"
    assert state.registry_additional_info_download_url == "https://r.example/ai.json"
    assert state.registry_additional_info_checksum == "sha256:" + ("d" * 64)


async def test_check_for_registry_update_ai_removed_clears_state(
    tmp_path: Path, indexes, sample_entries
) -> None:
    """Metadata no longer advertises additional-info → state cleared."""
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    ver = "2026-02-20"
    (registry_dir / "registry-state.json").write_text(
        json.dumps(
            {
                "version": ver,
                "checksum": "sha256:" + ("a" * 64),
                "last_checked_at": "2026-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("registry_metadata.json"):
            return httpx.Response(
                200,
                json={
                    "version": ver,
                    "download_url": "https://r.example/libs.json",
                    "checksum": "sha256:" + ("a" * 64),
                },
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        state = _build_state(
            client=client,
            tmp_path=tmp_path,
            indexes=indexes,
            sample_entries=sample_entries,
            registry_version=ver,
        )
        state.registry_additional_info_download_url = "https://old.example.com/ai.json"
        state.registry_additional_info_checksum = "sha256:" + ("b" * 64)
        outcome = await check_for_registry_update(state)

    assert outcome == "success"
    assert state.registry_additional_info_download_url is None
    assert state.registry_additional_info_checksum is None


async def test_check_for_registry_update_persist_failure_non_fatal(
    tmp_path: Path, indexes, sample_entries
) -> None:
    """Registry persist failure is non-fatal."""
    entries = [{"id": "n", "name": "N", "llms_txt_url": "https://n.dev/llms.txt"}]
    reg_bytes = json.dumps(entries).encode()
    checksum = _sha256_prefixed(reg_bytes)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("registry_metadata.json"):
            return httpx.Response(
                200,
                json={
                    "version": "2026-02-26",
                    "download_url": "https://r.example/libs.json",
                    "checksum": checksum,
                },
            )
        if request.url.path.endswith("libs.json"):
            return httpx.Response(200, content=reg_bytes)
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
        from procontext.registry import update as registry_update

        def _raise(**_kw: object) -> None:
            raise OSError("disk full")

        outcome = await registry_update.check_for_registry_update(
            state,
            build_indexes_fn=build_indexes,
            build_allowlist_fn=build_allowlist,
            save_registry_to_disk_fn=_raise,
            save_additional_info_to_disk_fn=lambda **_kw: None,
            write_registry_state_fn=lambda *_a, **_kw: None,
            write_last_checked_at_fn=lambda _p: None,
        )

    assert outcome == "success"
    assert state.registry_version == "2026-02-26"


async def test_check_for_registry_update_ai_persist_failure_non_fatal(
    tmp_path: Path, indexes, sample_entries
) -> None:
    """Additional-info persist failure is non-fatal."""
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    ver = "2026-02-20"
    sb = b'{"useful_md_probe_base_urls":["https://docs.example.com"]}'
    sc = _sha256_prefixed(sb)
    (registry_dir / "registry-state.json").write_text(
        json.dumps(
            {
                "version": ver,
                "checksum": "sha256:" + ("a" * 64),
                "last_checked_at": "2026-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("registry_metadata.json"):
            return httpx.Response(
                200,
                json={
                    "version": ver,
                    "download_url": "https://r.example/libs.json",
                    "checksum": "sha256:" + ("a" * 64),
                    "additional_info_download_url": "https://r.example/ai.json",
                    "additional_info_checksum": sc,
                },
            )
        if request.url.path.endswith("ai.json"):
            return httpx.Response(200, content=sb)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        state = _build_state(
            client=client,
            tmp_path=tmp_path,
            indexes=indexes,
            sample_entries=sample_entries,
            registry_version=ver,
        )
        from procontext.registry import update as registry_update

        def _raise(**_kw: object) -> None:
            raise OSError("disk full")

        outcome = await registry_update.check_for_registry_update(
            state,
            build_indexes_fn=build_indexes,
            build_allowlist_fn=build_allowlist,
            save_registry_to_disk_fn=save_registry_to_disk,
            save_additional_info_to_disk_fn=_raise,
            write_registry_state_fn=write_registry_state,
            write_last_checked_at_fn=lambda _p: None,
        )

    assert outcome == "success"
    assert state.registry_additional_info_download_url == "https://r.example/ai.json"
    assert state.registry_additional_info_checksum == sc


async def test_check_for_registry_update_invalid_metadata_version(
    tmp_path: Path, indexes, sample_entries
) -> None:
    """Invalid metadata (empty version) → semantic_failure."""
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            json={
                "version": "",
                "download_url": "https://r.example/l.json",
                "checksum": "sha256:" + ("a" * 64),
            },
        )
    )
    async with httpx.AsyncClient(transport=transport) as client:
        state = _build_state(
            client=client,
            tmp_path=tmp_path,
            indexes=indexes,
            sample_entries=sample_entries,
        )
        outcome = await check_for_registry_update(state)
    assert outcome == "semantic_failure"


async def test_check_for_registry_update_invalid_registry_schema(
    tmp_path: Path, indexes, sample_entries
) -> None:
    """Registry body with invalid schema → semantic_failure."""
    body = b'[{"not_valid": true}]'
    checksum = _sha256_prefixed(body)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("registry_metadata.json"):
            return httpx.Response(
                200,
                json={
                    "version": "2026-03-01",
                    "download_url": "https://r.example/libs.json",
                    "checksum": checksum,
                },
            )
        if request.url.path.endswith("libs.json"):
            return httpx.Response(200, content=body)
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


async def test_check_for_registry_update_registry_download_5xx(
    tmp_path: Path, indexes, sample_entries
) -> None:
    """Registry download 5xx → transient_failure."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("registry_metadata.json"):
            return httpx.Response(
                200,
                json={
                    "version": "2026-03-01",
                    "download_url": "https://r.example/libs.json",
                    "checksum": "sha256:" + ("a" * 64),
                },
            )
        return httpx.Response(502)

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
    assert outcome == "transient_failure"


async def test_check_for_registry_update_no_paths_skips_persist(
    tmp_path: Path, indexes, sample_entries
) -> None:
    """When registry paths are None, persist is skipped but state updates."""
    entries = [{"id": "n", "name": "N", "llms_txt_url": "https://n.dev/llms.txt"}]
    reg_bytes = json.dumps(entries).encode()
    checksum = _sha256_prefixed(reg_bytes)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("registry_metadata.json"):
            return httpx.Response(
                200,
                json={
                    "version": "2026-03-01",
                    "download_url": "https://r.example/libs.json",
                    "checksum": checksum,
                },
            )
        if request.url.path.endswith("libs.json"):
            return httpx.Response(200, content=reg_bytes)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        state = AppState(
            settings=_build_settings(tmp_path),
            indexes=indexes,
            registry_version="2026-02-20",
            registry_path=None,
            registry_state_path=None,
            http_client=client,
            allowlist=build_allowlist(sample_entries),
        )
        from procontext.registry import update as registry_update

        outcome = await registry_update.check_for_registry_update(
            state,
            build_indexes_fn=build_indexes,
            build_allowlist_fn=build_allowlist,
            save_registry_to_disk_fn=save_registry_to_disk,
            save_additional_info_to_disk_fn=lambda **_kw: None,
            write_registry_state_fn=lambda *_a, **_kw: None,
            write_last_checked_at_fn=lambda _p: None,
        )

    assert outcome == "success"
    assert state.registry_version == "2026-03-01"


async def test_check_for_registry_update_only_ai_changed(
    tmp_path: Path, indexes, sample_entries
) -> None:
    """When only additional-info changed, registry is not re-downloaded."""
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    ver = "2026-02-20"
    sb = b'{"useful_md_probe_base_urls":["https://docs.new.com"]}'
    sc = _sha256_prefixed(sb)
    (registry_dir / "registry-state.json").write_text(
        json.dumps(
            {
                "version": ver,
                "checksum": "sha256:" + ("a" * 64),
                "last_checked_at": "2026-01-01T00:00:00Z",
                "additional_info_download_url": "https://r.example/old.json",
                "additional_info_checksum": "sha256:" + ("b" * 64),
            }
        ),
        encoding="utf-8",
    )
    reg_downloaded = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal reg_downloaded
        if request.url.path.endswith("registry_metadata.json"):
            return httpx.Response(
                200,
                json={
                    "version": ver,
                    "download_url": "https://r.example/libs.json",
                    "checksum": "sha256:" + ("a" * 64),
                    "additional_info_download_url": "https://r.example/ai.json",
                    "additional_info_checksum": sc,
                },
            )
        if request.url.path.endswith("libs.json"):
            reg_downloaded = True
            return httpx.Response(200, content=b"[]")
        if request.url.path.endswith("ai.json"):
            return httpx.Response(200, content=sb)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        state = _build_state(
            client=client,
            tmp_path=tmp_path,
            indexes=indexes,
            sample_entries=sample_entries,
            registry_version=ver,
        )
        state.registry_additional_info_download_url = "https://r.example/old.json"
        state.registry_additional_info_checksum = "sha256:" + ("b" * 64)
        outcome = await check_for_registry_update(state)

    assert outcome == "success"
    assert not reg_downloaded
    assert state.registry_additional_info_download_url == "https://r.example/ai.json"
    assert state.registry_additional_info_checksum == sc


async def test_setup_additional_info_persist_failure_still_succeeds(
    tmp_path: Path,
) -> None:
    """Additional-info persist failure during setup is non-fatal."""
    entries = [{"id": "s", "name": "S", "llms_txt_url": "https://s.dev/llms.txt"}]
    reg_bytes = json.dumps(entries).encode()
    reg_checksum = _sha256_prefixed(reg_bytes)
    ai_bytes = b'{"useful_md_probe_base_urls":["https://s.dev"]}'
    ai_checksum = _sha256_prefixed(ai_bytes)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("registry_metadata.json"):
            return httpx.Response(
                200,
                json={
                    "version": "2026-03-01",
                    "download_url": "https://r.example/libs.json",
                    "checksum": reg_checksum,
                    "additional_info_download_url": "https://r.example/ai.json",
                    "additional_info_checksum": ai_checksum,
                },
            )
        if request.url.path.endswith("libs.json"):
            return httpx.Response(200, content=reg_bytes)
        if request.url.path.endswith("ai.json"):
            return httpx.Response(200, content=ai_bytes)
        return httpx.Response(404)

    settings = _build_settings(tmp_path)
    with (
        patch(
            "procontext.registry.build_http_client",
            return_value=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        ),
        patch(
            "procontext.registry.save_additional_info_to_disk",
            side_effect=OSError("disk full"),
        ),
    ):
        result = await fetch_registry_for_setup(settings)

    assert result is True
    assert (tmp_path / "registry" / "known-libraries.json").exists()
