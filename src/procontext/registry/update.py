"""Remote registry update and setup download logic."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

import httpx
import structlog

from procontext.models.registry import (
    RegistryAdditionalInfo,
    RegistryEntry,
    RegistryIndexes,
    RegistryState,
)
from procontext.registry.local import (
    _sha256_prefixed,
    advertised_additional_info,
    load_registry_state,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from procontext.state import AppState

log = structlog.get_logger()

REGISTRY_SUCCESS_INTERVAL_SECONDS = 24 * 60 * 60
REGISTRY_INITIAL_BACKOFF_SECONDS = 60
REGISTRY_MAX_BACKOFF_SECONDS = 60 * 60
REGISTRY_MAX_TRANSIENT_BACKOFF_ATTEMPTS = 8

RegistryUpdateOutcome = Literal["success", "transient_failure", "semantic_failure"]


@dataclass
class _NewRegistryData:
    """Validated registry download ready to be applied or persisted."""

    registry_bytes: bytes
    version: str
    checksum: str
    entries: list[RegistryEntry]


@dataclass(frozen=True)
class _AdditionalInfoMetadata:
    """Validated sidecar metadata advertised by registry metadata."""

    download_url: str
    checksum: str


@dataclass(frozen=True)
class _RegistryMetadata:
    """Validated remote registry metadata response."""

    version: str
    download_url: str
    checksum: str
    additional_info: _AdditionalInfoMetadata | None


@dataclass(frozen=True)
class _DownloadedAdditionalInfo:
    """Validated additional-info payload ready to be persisted or applied."""

    raw_bytes: bytes
    data: RegistryAdditionalInfo


_REGISTRY_TIMEOUT = httpx.Timeout(300.0, connect=5.0)
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


async def _download_registry_if_newer(
    http_client: httpx.AsyncClient,
    *,
    metadata_url: str,
    current_version: str | None,
    metadata_timeout: float | httpx.Timeout = _REGISTRY_TIMEOUT,
    registry_timeout: float | httpx.Timeout = _REGISTRY_TIMEOUT,
) -> _NewRegistryData | RegistryUpdateOutcome:
    """Fetch registry metadata and download the full payload if the version changed."""
    metadata = await _fetch_registry_metadata(
        http_client,
        metadata_url=metadata_url,
        timeout=metadata_timeout,
    )
    if isinstance(metadata, str):
        return metadata

    if metadata.version == current_version:
        log.info("registry_up_to_date", version=metadata.version)
        return "success"

    return await _download_registry_payload(
        http_client,
        download_url=metadata.download_url,
        expected_checksum=metadata.checksum,
        version=metadata.version,
        timeout=registry_timeout,
    )


async def _fetch_registry_metadata(
    http_client: httpx.AsyncClient,
    *,
    metadata_url: str,
    timeout: float | httpx.Timeout,
) -> _RegistryMetadata | RegistryUpdateOutcome:
    """Fetch and validate the remote registry metadata response."""
    metadata_response = await _safe_get(http_client, metadata_url, timeout=timeout)
    if metadata_response is None:
        return "transient_failure"

    if not metadata_response.is_success:
        return _classify_http_failure(
            url=metadata_url,
            status_code=metadata_response.status_code,
            context="metadata",
        )

    try:
        return _parse_registry_metadata(metadata_response.json())
    except Exception:
        log.warning("registry_update_semantic_failure", reason="invalid_metadata", exc_info=True)
        return "semantic_failure"


async def _download_registry_payload(
    http_client: httpx.AsyncClient,
    *,
    download_url: str,
    expected_checksum: str,
    version: str,
    timeout: float | httpx.Timeout,
) -> _NewRegistryData | RegistryUpdateOutcome:
    """Download and validate known-libraries.json."""
    registry_response = await _safe_get(http_client, download_url, timeout=timeout)
    if registry_response is None:
        return "transient_failure"

    if not registry_response.is_success:
        return _classify_http_failure(
            url=download_url,
            status_code=registry_response.status_code,
            context="registry_download",
        )

    actual_checksum = _sha256_prefixed(registry_response.content)
    if actual_checksum != expected_checksum:
        log.warning(
            "registry_checksum_mismatch",
            expected=expected_checksum,
            actual=actual_checksum,
        )
        return "semantic_failure"

    try:
        raw_entries = registry_response.json()
        new_entries = [RegistryEntry(**entry) for entry in raw_entries]
    except Exception:
        log.warning(
            "registry_update_semantic_failure",
            reason="invalid_registry_schema",
            exc_info=True,
        )
        return "semantic_failure"

    return _NewRegistryData(
        registry_bytes=registry_response.content,
        version=version,
        checksum=expected_checksum,
        entries=new_entries,
    )


def _parse_registry_metadata(metadata: object) -> _RegistryMetadata:
    if not isinstance(metadata, dict):
        raise ValueError("metadata response must be an object")

    remote_version = metadata["version"]
    download_url = metadata["download_url"]
    expected_checksum = metadata["checksum"]
    if not isinstance(remote_version, str) or not remote_version:
        raise ValueError("'version' must be a non-empty string")
    if not isinstance(download_url, str) or not download_url:
        raise ValueError("'download_url' must be a non-empty string")
    if not isinstance(expected_checksum, str) or not expected_checksum.startswith("sha256:"):
        raise ValueError("'checksum' must be in 'sha256:<hex>' format")

    additional_info = _parse_additional_info_metadata(metadata)
    return _RegistryMetadata(
        version=remote_version,
        download_url=download_url,
        checksum=expected_checksum,
        additional_info=additional_info,
    )


def _parse_additional_info_metadata(
    metadata: dict[object, object],
) -> _AdditionalInfoMetadata | None:
    raw_download_url = metadata.get("additional_info_download_url")
    raw_checksum = metadata.get("additional_info_checksum")
    if raw_download_url is None and raw_checksum is None:
        return None
    if not isinstance(raw_download_url, str) or not raw_download_url:
        log.warning(
            "registry_additional_info_metadata_ignored",
            reason="invalid_download_url",
        )
        return None
    if not isinstance(raw_checksum, str) or not _SHA256_RE.match(raw_checksum):
        log.warning(
            "registry_additional_info_metadata_ignored",
            reason="invalid_checksum",
        )
        return None
    return _AdditionalInfoMetadata(
        download_url=raw_download_url,
        checksum=raw_checksum,
    )


async def _download_additional_info(
    http_client: httpx.AsyncClient,
    *,
    metadata: _AdditionalInfoMetadata,
    timeout: float | httpx.Timeout,
) -> _DownloadedAdditionalInfo | None:
    """Best-effort download of additional-info.json."""
    response = await _safe_get(http_client, metadata.download_url, timeout=timeout)
    if response is None:
        return None
    if not response.is_success:
        # Log-only: _classify_http_failure logs the status; return value is
        # intentionally discarded because all HTTP failures are non-fatal for
        # the best-effort sidecar download.
        _classify_http_failure(
            url=metadata.download_url,
            status_code=response.status_code,
            context="additional_info_download",
        )
        return None

    actual_checksum = _sha256_prefixed(response.content)
    if actual_checksum != metadata.checksum:
        log.warning(
            "registry_additional_info_invalid",
            reason="checksum_mismatch",
            expected=metadata.checksum,
            actual=actual_checksum,
        )
        return None

    try:
        data = RegistryAdditionalInfo.model_validate_json(response.content)
    except Exception:
        log.warning(
            "registry_additional_info_invalid",
            reason="invalid_schema",
            exc_info=True,
        )
        return None

    return _DownloadedAdditionalInfo(raw_bytes=response.content, data=data)


async def check_for_registry_update(
    state: AppState,
    *,
    build_indexes_fn: Callable[[list[RegistryEntry]], RegistryIndexes],
    build_allowlist_fn: Callable[..., frozenset[str]],
    save_registry_to_disk_fn: Callable[..., None],
    save_additional_info_to_disk_fn: Callable[..., None],
    write_registry_state_fn: Callable[..., None],
    write_last_checked_at_fn: Callable[[Path], None],
    metadata_timeout: float | httpx.Timeout = _REGISTRY_TIMEOUT,
    registry_timeout: float | httpx.Timeout = _REGISTRY_TIMEOUT,
) -> RegistryUpdateOutcome:
    """Check remote metadata and apply a registry update when available."""
    if state.http_client is None:
        return "semantic_failure"

    metadata = await _fetch_registry_metadata(
        state.http_client,
        metadata_url=state.settings.registry.metadata_url,
        timeout=metadata_timeout,
    )
    if isinstance(metadata, str):
        return metadata

    current_additional_info = (
        state.registry_additional_info_download_url,
        state.registry_additional_info_checksum,
    )
    remote_additional_info = (
        (metadata.additional_info.download_url, metadata.additional_info.checksum)
        if metadata.additional_info is not None
        else (None, None)
    )
    registry_changed = metadata.version != state.registry_version
    additional_info_changed = remote_additional_info != current_additional_info

    if not registry_changed and not additional_info_changed:
        if state.registry_state_path is not None:
            write_last_checked_at_fn(state.registry_state_path)
        log.info("registry_up_to_date", version=metadata.version)
        return "success"

    registry_data: _NewRegistryData | None = None
    if registry_changed:
        registry_result = await _download_registry_payload(
            state.http_client,
            download_url=metadata.download_url,
            expected_checksum=metadata.checksum,
            version=metadata.version,
            timeout=registry_timeout,
        )
        if isinstance(registry_result, str):
            return registry_result
        registry_data = registry_result

    downloaded_additional_info: _DownloadedAdditionalInfo | None = None
    attempted_additional_info_download = False
    if metadata.additional_info is not None and (registry_changed or additional_info_changed):
        attempted_additional_info_download = True
        downloaded_additional_info = await _download_additional_info(
            state.http_client,
            metadata=metadata.additional_info,
            timeout=registry_timeout,
        )

    if registry_data is not None:
        new_indexes = build_indexes_fn(registry_data.entries)
        new_allowlist = build_allowlist_fn(
            registry_data.entries,
            extra_domains=state.settings.fetcher.extra_allowed_domains,
        )
        state.indexes = new_indexes
        state.allowlist = new_allowlist
        state.registry_version = registry_data.version

    if metadata.additional_info is None:
        state.md_probe_base_urls = frozenset()
        state.registry_additional_info_download_url = None
        state.registry_additional_info_checksum = None
    elif downloaded_additional_info is not None:
        state.md_probe_base_urls = frozenset(
            downloaded_additional_info.data.useful_md_probe_base_urls
        )
        state.registry_additional_info_download_url = metadata.additional_info.download_url
        state.registry_additional_info_checksum = metadata.additional_info.checksum
    elif additional_info_changed:
        state.md_probe_base_urls = frozenset()
        state.registry_additional_info_download_url = metadata.additional_info.download_url
        state.registry_additional_info_checksum = metadata.additional_info.checksum
    elif attempted_additional_info_download:
        log.warning("registry_additional_info_kept_existing", reason="download_failed")

    if state.registry_path is not None and state.registry_state_path is not None:
        try:
            if registry_data is not None:
                save_registry_to_disk_fn(
                    registry_bytes=registry_data.registry_bytes,
                    version=metadata.version,
                    checksum=metadata.checksum,
                    registry_path=state.registry_path,
                    state_path=state.registry_state_path,
                    additional_info_download_url=state.registry_additional_info_download_url,
                    additional_info_checksum=state.registry_additional_info_checksum,
                )
            else:
                existing_state = load_registry_state(state.registry_state_path)
                if existing_state is not None:
                    write_registry_state_fn(
                        state.registry_state_path,
                        state=RegistryState(
                            version=existing_state.version,
                            checksum=existing_state.checksum,
                            updated_at=existing_state.updated_at,
                            last_checked_at=datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
                            additional_info_download_url=state.registry_additional_info_download_url,
                            additional_info_checksum=state.registry_additional_info_checksum,
                        ),
                    )
        except Exception as exc:
            log.warning(
                "registry_persist_failed",
                version=metadata.version,
                error=str(exc),
                exc_info=True,
            )

    if downloaded_additional_info is not None and state.registry_additional_info_path is not None:
        try:
            save_additional_info_to_disk_fn(
                additional_info_bytes=downloaded_additional_info.raw_bytes,
                additional_info_path=state.registry_additional_info_path,
            )
        except Exception:
            log.warning("registry_additional_info_persist_failed", exc_info=True)

    if registry_data is not None:
        log.info("registry_updated", version=metadata.version, entries=len(registry_data.entries))
    elif additional_info_changed:
        log.info("registry_additional_info_updated", version=metadata.version)
    return "success"


async def fetch_registry_for_setup(
    *,
    http_client: httpx.AsyncClient,
    metadata_url: str,
    registry_path: Path,
    registry_state_path: Path,
    registry_additional_info_path: Path,
    save_registry_to_disk_fn: Callable[..., None],
    save_additional_info_to_disk_fn: Callable[..., None],
) -> bool:
    """Fetch and persist the registry for initial bootstrap."""
    metadata = await _fetch_registry_metadata(
        http_client,
        metadata_url=metadata_url,
        timeout=_REGISTRY_TIMEOUT,
    )
    if isinstance(metadata, str):
        return metadata == "success"

    result = await _download_registry_payload(
        http_client,
        download_url=metadata.download_url,
        expected_checksum=metadata.checksum,
        version=metadata.version,
        timeout=_REGISTRY_TIMEOUT,
    )
    if isinstance(result, str):
        return result == "success"

    additional_info = None
    if metadata.additional_info is not None:
        additional_info = await _download_additional_info(
            http_client,
            metadata=metadata.additional_info,
            timeout=_REGISTRY_TIMEOUT,
        )

    try:
        save_registry_to_disk_fn(
            registry_bytes=result.registry_bytes,
            version=result.version,
            checksum=result.checksum,
            registry_path=registry_path,
            state_path=registry_state_path,
            additional_info_download_url=(
                metadata.additional_info.download_url if metadata.additional_info else None
            ),
            additional_info_checksum=(
                metadata.additional_info.checksum if metadata.additional_info else None
            ),
        )
    except Exception:
        log.warning("registry_setup_persist_failed", exc_info=True)
        return False

    if additional_info is not None:
        try:
            save_additional_info_to_disk_fn(
                additional_info_bytes=additional_info.raw_bytes,
                additional_info_path=registry_additional_info_path,
            )
        except Exception:
            log.warning("registry_additional_info_setup_persist_failed", exc_info=True)

    log.info("registry_setup_complete", version=result.version, entries=len(result.entries))
    return True


async def fetch_registry_additional_info_for_setup(
    *,
    http_client: httpx.AsyncClient,
    registry_state_path: Path,
    registry_additional_info_path: Path,
    save_additional_info_to_disk_fn: Callable[..., None],
) -> bool:
    """Fetch and persist additional-info.json using the local advertised metadata."""
    state = load_registry_state(registry_state_path)
    if state is None:
        return False
    additional_info_metadata = advertised_additional_info(state)
    if isinstance(additional_info_metadata, str):
        return additional_info_metadata == "not_advertised"

    downloaded = await _download_additional_info(
        http_client,
        metadata=_AdditionalInfoMetadata(
            download_url=additional_info_metadata[0],
            checksum=additional_info_metadata[1],
        ),
        timeout=_REGISTRY_TIMEOUT,
    )
    if downloaded is None:
        return False

    try:
        save_additional_info_to_disk_fn(
            additional_info_bytes=downloaded.raw_bytes,
            additional_info_path=registry_additional_info_path,
        )
    except Exception:
        log.warning("registry_additional_info_setup_persist_failed", exc_info=True)
        return False

    return True


async def _safe_get(
    http_client: httpx.AsyncClient,
    url: str,
    *,
    timeout: float | httpx.Timeout,
) -> httpx.Response | None:
    try:
        return await http_client.get(url, timeout=timeout)
    except httpx.HTTPError:
        log.warning(
            "registry_update_transient_failure",
            reason="network_error",
            url=url,
            exc_info=True,
        )
        return None


def _classify_http_failure(*, url: str, status_code: int, context: str) -> RegistryUpdateOutcome:
    if status_code >= 500 or status_code in {408, 429}:
        log.warning(
            "registry_update_transient_failure",
            reason="http_status",
            context=context,
            url=url,
            status_code=status_code,
        )
        return "transient_failure"

    log.warning(
        "registry_update_semantic_failure",
        reason="http_status",
        context=context,
        url=url,
        status_code=status_code,
    )
    return "semantic_failure"
