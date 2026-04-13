"""resolve_library tool package."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import structlog
from mcp.server.fastmcp import Context  # noqa: TC002 - FastMCP evaluates tool annotations
from pydantic import Field

from procontext.errors import ProContextError
from procontext.models.tools import ResolveLibraryOutput
from procontext.tools.resolve_library.handler import handle
from procontext.tools.resolve_library.prompt import (
    DESCRIPTION,
    PARAM_LANGUAGE,
    PARAM_QUERY,
)

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from procontext.state import AppState

__all__ = ["handle", "register"]

log = structlog.get_logger()


def register(mcp: FastMCP) -> None:
    """Register the resolve_library tool on the MCP server."""

    @mcp.tool(description=DESCRIPTION)
    async def resolve_library(
        query: Annotated[str, Field(description=PARAM_QUERY)],
        ctx: Context,
        language: Annotated[str | None, Field(description=PARAM_LANGUAGE)] = None,
    ) -> ResolveLibraryOutput:
        """Resolve a library name to its documentation source."""
        state: AppState = ctx.request_context.lifespan_context
        try:
            return ResolveLibraryOutput.model_validate(
                await handle(query, state, language=language)
            )
        except ProContextError as exc:
            log.warning("tool_error", tool="resolve_library", code=exc.code, message=exc.message)
            raise
        except Exception:
            log.error("tool_unexpected_error", tool="resolve_library", exc_info=True)
            raise
