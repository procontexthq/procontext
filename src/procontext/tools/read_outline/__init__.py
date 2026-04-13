"""read_outline tool package."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import structlog
from mcp.server.fastmcp import Context  # noqa: TC002 - FastMCP evaluates tool annotations
from pydantic import Field

from procontext.errors import ProContextError
from procontext.models.tools import ReadOutlineOutput
from procontext.tools.read_outline.handler import handle
from procontext.tools.read_outline.prompt import (
    DESCRIPTION,
    PARAM_BEFORE,
    PARAM_LIMIT,
    PARAM_OFFSET,
    PARAM_URL,
)

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from procontext.state import AppState

__all__ = ["handle", "register"]

log = structlog.get_logger()


def register(mcp: FastMCP) -> None:
    """Register the read_outline tool on the MCP server."""

    @mcp.tool(description=DESCRIPTION)
    async def read_outline(
        url: Annotated[str, Field(description=PARAM_URL)],
        ctx: Context,
        offset: Annotated[int, Field(description=PARAM_OFFSET, ge=1)] = 1,
        limit: Annotated[int, Field(description=PARAM_LIMIT, ge=1)] = 500,
        before: Annotated[int, Field(description=PARAM_BEFORE, ge=0)] = 0,
    ) -> ReadOutlineOutput:
        """Browse the full outline of a documentation page with outline-entry windowing."""
        state: AppState = ctx.request_context.lifespan_context
        try:
            return ReadOutlineOutput.model_validate(
                await handle(url, offset, limit, state, before=before)
            )
        except ProContextError as exc:
            log.warning("tool_error", tool="read_outline", code=exc.code, message=exc.message)
            raise
        except Exception:
            log.error("tool_unexpected_error", tool="read_outline", exc_info=True)
            raise
