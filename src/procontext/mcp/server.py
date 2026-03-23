"""MCP tool registrations.

Defines the FastMCP instance and registers the ProContext tools.
Startup, logging setup, and lifespan management live in their own modules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

import structlog
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field

import procontext.tools.read_outline as t_read_outline
import procontext.tools.read_page as t_read_page
import procontext.tools.resolve_library as t_resolve
import procontext.tools.search_page as t_search_page
from procontext import __version__
from procontext.errors import ProContextError
from procontext.mcp.lifespan import lifespan
from procontext.mcp.tool_docs import (
    READ_OUTLINE_DESCRIPTION,
    READ_PAGE_DESCRIPTION,
    RESOLVE_LIBRARY_DESCRIPTION,
    SEARCH_PAGE_DESCRIPTION,
    SERVER_INSTRUCTIONS,
)
from procontext.models.tools import (
    ReadOutlineOutput,
    ReadPageOutput,
    ResolveLibraryOutput,
    SearchPageOutput,
)

if TYPE_CHECKING:
    from procontext.state import AppState

log = structlog.get_logger()

mcp = FastMCP("procontext", instructions=SERVER_INSTRUCTIONS, lifespan=lifespan)
# FastMCP doesn't expose a version kwarg — set it on the underlying Server
# so the MCP initialize handshake reports our version, not the SDK's.
mcp._mcp_server.version = __version__  # pyright: ignore[reportPrivateUsage]


@mcp.tool(description=RESOLVE_LIBRARY_DESCRIPTION)
async def resolve_library(
    query: Annotated[
        str,
        Field(
            description="Query string. Can be a plain library name, package name or commonly "
            "known name. Must not include version specifiers, extras, tags, or source URLs."
        ),
    ],
    ctx: Context,
    language: Annotated[
        str | None,
        Field(
            description=(
                "Optional language hint (e.g. 'python', 'javascript'). "
                "Sorts matching-language packages to the top; does not filter results."
            )
        ),
    ] = None,
) -> ResolveLibraryOutput:
    """Resolve a library name to its documentation source."""
    state: AppState = ctx.request_context.lifespan_context
    try:
        return ResolveLibraryOutput.model_validate(
            await t_resolve.handle(query, state, language=language)
        )
    except ProContextError as exc:
        log.warning("tool_error", tool="resolve_library", code=exc.code, message=exc.message)
        raise
    except Exception:
        log.error("tool_unexpected_error", tool="resolve_library", exc_info=True)
        raise


@mcp.tool(description=READ_PAGE_DESCRIPTION)
async def read_page(
    url: Annotated[
        str,
        Field(description="Index or documentation page URL."),
    ],
    ctx: Context,
    offset: Annotated[
        int,
        Field(description="1-based line number to start reading from.", ge=1),
    ] = 1,
    limit: Annotated[
        int,
        Field(description="Maximum number of content lines to return.", ge=1),
    ] = 500,
    before: Annotated[
        int,
        Field(
            description=(
                "Number of extra content lines to include before offset for backward context."
            ),
            ge=0,
        ),
    ] = 0,
    include_outline: Annotated[
        bool,
        Field(
            description=(
                "Set to false to omit the outline from the response. "
                "Useful when paginating and the outline is already known."
            )
        ),
    ] = True,
) -> ReadPageOutput:
    """Fetch the content and outline of a documentation page."""
    state: AppState = ctx.request_context.lifespan_context
    try:
        return ReadPageOutput.model_validate(
            await t_read_page.handle(
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


@mcp.tool(description=READ_OUTLINE_DESCRIPTION)
async def read_outline(
    url: Annotated[
        str,
        Field(description="Documentation page URL."),
    ],
    ctx: Context,
    offset: Annotated[
        int,
        Field(description="1-based page line number to start browsing the outline from.", ge=1),
    ] = 1,
    limit: Annotated[
        int,
        Field(description="Maximum forward page lines to include from offset.", ge=1),
    ] = 1000,
    before: Annotated[
        int,
        Field(
            description=(
                "Number of extra page lines to include before offset for backward outline context."
            ),
            ge=0,
        ),
    ] = 0,
) -> ReadOutlineOutput:
    """Browse the full outline of a documentation page with page-line windowing."""
    state: AppState = ctx.request_context.lifespan_context
    try:
        return ReadOutlineOutput.model_validate(
            await t_read_outline.handle(url, offset, limit, state, before=before)
        )
    except ProContextError as exc:
        log.warning("tool_error", tool="read_outline", code=exc.code, message=exc.message)
        raise
    except Exception:
        log.error("tool_unexpected_error", tool="read_outline", exc_info=True)
        raise


@mcp.tool(description=SEARCH_PAGE_DESCRIPTION)
async def search_page(
    url: Annotated[
        str,
        Field(description="URL of the page to search."),
    ],
    query: Annotated[
        str,
        Field(description="Search term or regex pattern."),
    ],
    ctx: Context,
    target: Annotated[
        Literal["content", "outline"],
        Field(
            description=(
                "content: search page content lines. outline: search the outline entries only."
            )
        ),
    ] = "content",
    mode: Annotated[
        Literal["literal", "regex"],
        Field(
            description=(
                "literal: exact substring match. regex: treat query as a regular expression."
            )
        ),
    ] = "literal",
    case_mode: Annotated[
        Literal["smart", "insensitive", "sensitive"],
        Field(
            description=(
                "smart: lowercase query → case-insensitive; mixed/uppercase → case-sensitive. "
                "insensitive: always case-insensitive. "
                "sensitive: always case-sensitive."
            )
        ),
    ] = "smart",
    whole_word: Annotated[
        bool,
        Field(description="When true, match only at word boundaries."),
    ] = False,
    offset: Annotated[
        int,
        Field(description="1-based line number to start searching from.", ge=1),
    ] = 1,
    max_results: Annotated[
        int,
        Field(description="Maximum number of matching lines to return.", ge=1),
    ] = 20,
) -> SearchPageOutput:
    """Search within a documentation page for lines matching a query."""
    state: AppState = ctx.request_context.lifespan_context
    try:
        return SearchPageOutput.model_validate(
            await t_search_page.handle(
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
