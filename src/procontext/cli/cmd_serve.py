"""CLI command: procontext (no subcommand) — start the MCP server."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import structlog

from procontext.config import registry_paths
from procontext.mcp.server import mcp
from procontext.registry import load_registry

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from procontext.config import Settings

log = structlog.get_logger()


def _registry_is_available(settings: Settings) -> bool:
    """Return True when the local registry pair exists and validates."""
    registry_path, registry_state_path = registry_paths(settings)
    return (
        load_registry(local_registry_path=registry_path, local_state_path=registry_state_path)
        is not None
    )


def _run_http_transport(server: FastMCP, settings: Settings) -> None:
    """Import and start the HTTP transport only when explicitly requested."""
    from procontext.http_transport import run_http_server

    run_http_server(server, settings)


def run_server(settings: Settings) -> None:
    """Ensure the registry is present and launch the MCP server."""
    if not _registry_is_available(settings):
        log.critical(
            "registry_not_initialised",
            hint=(
                "Run 'procontext setup' to download the registry. "
                "If local state looks a little unwell, summon the doctor with "
                "'procontext doctor --fix'."
            ),
        )
        sys.exit(1)

    if settings.server.transport == "http":
        _run_http_transport(mcp, settings)
        return

    mcp.run()
