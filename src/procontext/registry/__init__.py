"""Library registry public API: local loading, persistence, and update checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from procontext.fetch.client import build_http_client
from procontext.fetch.security import build_allowlist

from . import storage as registry_storage
from . import update as registry_update
from .local import build_indexes, load_registry, load_registry_additional_info, load_registry_state
from .storage import (
    registry_check_is_due,
    save_additional_info_to_disk,
    save_registry_to_disk,
    write_registry_state,
)
from .update import (
    REGISTRY_INITIAL_BACKOFF_SECONDS,
    REGISTRY_MAX_BACKOFF_SECONDS,
    REGISTRY_MAX_TRANSIENT_BACKOFF_ATTEMPTS,
    REGISTRY_SUCCESS_INTERVAL_SECONDS,
    RegistryUpdateOutcome,
)

if TYPE_CHECKING:
    from procontext.config import Settings
    from procontext.state import AppState

__all__ = [
    "REGISTRY_INITIAL_BACKOFF_SECONDS",
    "REGISTRY_MAX_BACKOFF_SECONDS",
    "REGISTRY_MAX_TRANSIENT_BACKOFF_ATTEMPTS",
    "REGISTRY_SUCCESS_INTERVAL_SECONDS",
    "RegistryUpdateOutcome",
    "build_indexes",
    "check_for_registry_update",
    "fetch_registry_for_setup",
    "fetch_registry_additional_info_for_setup",
    "load_registry",
    "load_registry_additional_info",
    "load_registry_state",
    "registry_check_is_due",
    "save_additional_info_to_disk",
    "save_registry_to_disk",
]


async def check_for_registry_update(state: AppState) -> RegistryUpdateOutcome:
    """Check remote metadata and apply a registry update when available."""
    return await registry_update.check_for_registry_update(
        state,
        build_indexes_fn=build_indexes,
        build_allowlist_fn=build_allowlist,
        save_registry_to_disk_fn=save_registry_to_disk,
        save_additional_info_to_disk_fn=save_additional_info_to_disk,
        write_registry_state_fn=write_registry_state,
        write_last_checked_at_fn=registry_storage.write_last_checked_at,
    )


async def fetch_registry_for_setup(settings: Settings) -> bool:
    """Fetch and persist the registry for initial bootstrap.

    Builds an HTTP client internally and closes it when done — callers
    do not need to manage transport-level resources.
    """
    from procontext.config import (
        registry_additional_info_path,
        registry_paths,
    )  # avoid circular import

    registry_path, registry_state_path = registry_paths(settings)
    additional_info_path = registry_additional_info_path(settings)
    http_client = build_http_client(settings.fetcher)
    try:
        return await registry_update.fetch_registry_for_setup(
            http_client=http_client,
            metadata_url=settings.registry.metadata_url,
            registry_path=registry_path,
            registry_state_path=registry_state_path,
            registry_additional_info_path=additional_info_path,
            save_registry_to_disk_fn=save_registry_to_disk,
            save_additional_info_to_disk_fn=save_additional_info_to_disk,
        )
    finally:
        await http_client.aclose()


async def fetch_registry_additional_info_for_setup(settings: Settings) -> bool:
    """Fetch and persist additional-info.json using the current local state."""
    from procontext.config import (
        registry_additional_info_path,
        registry_paths,
    )  # avoid circular import

    _, registry_state_path = registry_paths(settings)
    additional_info_path = registry_additional_info_path(settings)
    http_client = build_http_client(settings.fetcher)
    try:
        return await registry_update.fetch_registry_additional_info_for_setup(
            http_client=http_client,
            registry_state_path=registry_state_path,
            registry_additional_info_path=additional_info_path,
            save_additional_info_to_disk_fn=save_additional_info_to_disk,
        )
    finally:
        await http_client.aclose()
