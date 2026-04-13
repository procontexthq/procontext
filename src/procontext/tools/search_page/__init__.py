"""search_page tool package."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

import structlog
from mcp.server.fastmcp import Context  # noqa: TC002 - FastMCP evaluates tool annotations
from pydantic import Field

from procontext.errors import ProContextError
from procontext.models.tools import SearchPageOutput
from procontext.tools.search_page.handler import handle
from procontext.tools.search_page.prompt import (
    DESCRIPTION,
    PARAM_CASE_MODE,
    PARAM_MAX_RESULTS,
    PARAM_MODE,
    PARAM_OFFSET,
    PARAM_QUERY,
    PARAM_TARGET,
    PARAM_URL,
    PARAM_WHOLE_WORD,
)

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from procontext.state import AppState

__all__ = ["handle", "register"]

log = structlog.get_logger()


def register(mcp: FastMCP) -> None:
    """Register the search_page tool on the MCP server."""

    @mcp.tool(description=DESCRIPTION)
    async def search_page(
        url: Annotated[str, Field(description=PARAM_URL)],
        query: Annotated[str, Field(description=PARAM_QUERY)],
        ctx: Context,
        target: Annotated[
            Literal["content", "outline"],
            Field(description=PARAM_TARGET),
        ] = "content",
        mode: Annotated[
            Literal["literal", "regex"],
            Field(description=PARAM_MODE),
        ] = "literal",
        case_mode: Annotated[
            Literal["smart", "insensitive", "sensitive"],
            Field(description=PARAM_CASE_MODE),
        ] = "smart",
        whole_word: Annotated[bool, Field(description=PARAM_WHOLE_WORD)] = False,
        offset: Annotated[int, Field(description=PARAM_OFFSET, ge=1)] = 1,
        max_results: Annotated[int, Field(description=PARAM_MAX_RESULTS, ge=1)] = 20,
    ) -> SearchPageOutput:
        """Search within a documentation page for lines matching a query."""
        state: AppState = ctx.request_context.lifespan_context
        try:
            return SearchPageOutput.model_validate(
                await handle(
                    url,
                    query,
                    state,
                    target=target,
                    mode=mode,
                    case_mode=case_mode,
                    whole_word=whole_word,
                    offset=offset,
                    max_results=max_results,
                )
            )
        except ProContextError as exc:
            log.warning("tool_error", tool="search_page", code=exc.code, message=exc.message)
            raise
        except Exception:
            log.error("tool_unexpected_error", tool="search_page", exc_info=True)
            raise
