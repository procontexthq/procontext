"""read_page tool package."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import structlog
from mcp.server.fastmcp import Context  # noqa: TC002 - FastMCP evaluates tool annotations
from pydantic import Field

from procontext.errors import ProContextError
from procontext.models.tools import ReadPageOutput
from procontext.tools.read_page.handler import handle
from procontext.tools.read_page.prompt import (
    DESCRIPTION,
    PARAM_BEFORE,
    PARAM_INCLUDE_OUTLINE,
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
    """Register the read_page tool on the MCP server."""

    @mcp.tool(description=DESCRIPTION)
    async def read_page(
        url: Annotated[str, Field(description=PARAM_URL)],
        ctx: Context,
        offset: Annotated[int, Field(description=PARAM_OFFSET, ge=1)] = 1,
        limit: Annotated[int, Field(description=PARAM_LIMIT, ge=1)] = 500,
        before: Annotated[int, Field(description=PARAM_BEFORE, ge=0)] = 0,
        include_outline: Annotated[bool, Field(description=PARAM_INCLUDE_OUTLINE)] = True,
    ) -> ReadPageOutput:
        """Fetch the content and outline of a documentation page."""
        state: AppState = ctx.request_context.lifespan_context
        try:
            return ReadPageOutput.model_validate(
                await handle(
                    url,
                    offset,
                    limit,
                    state,
                    before=before,
                    include_outline=include_outline,
                )
            )
        except ProContextError as exc:
            log.warning("tool_error", tool="read_page", code=exc.code, message=exc.message)
            raise
        except Exception:
            log.error("tool_unexpected_error", tool="read_page", exc_info=True)
            raise
