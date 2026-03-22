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
from procontext.models.tools import (
    ReadOutlineOutput,
    ReadPageOutput,
    ResolveLibraryOutput,
    SearchPageOutput,
)

if TYPE_CHECKING:
    from procontext.state import AppState

log = structlog.get_logger()

SERVER_INSTRUCTIONS = """
ProContext acts as a documentation layer for software libraries.:

## Typical Workflow

1. **Start with resolve_library(query)** to locate a library by name, package name, or alias.
   Returns the library's documentation index URL (index_url) and package information.

2. **Use read_page** to browse the documentation index (or any page).
   Returns the first 500 lines of content and an outline of the page structure.

3. **To search within a page (or index)**, use search_page(url, query) to find lines matching
   a keyword or regex pattern. Returns matching lines plus outline context.

4. **For large outlines**, read_page and search_page return compacted outlines (max 50 entries
   or 4000 characters) to save tokens. If the outline is truncated, call read_outline(url)
   to browse the full outline with pagination.

5. **Navigation** - You can use outline or search_page to find the section you need quickly,
   or you can simply paginate through the page with read_page by incrementing the offset.

## Key Details

- **resolve_library input**: Pass only the plain library name (e.g., "langchain", "openai").
  Do not include version specifiers, extras, tags, or source URLs. Examples of supported input:
  - "langchain", "langchain-openai" (package names)
  - "LangChain", "OpenAI" (display names)
  - Aliases defined in the registry

- **read_page/search_page input**: Pass URLs from resolve_library (index_url) or links
  found within previously fetched pages.

- **Caching**: Repeated calls to the same page are served from cache (< 100ms).
  Safe to paginate with read_page or call read_outline multiple times.

## Pro Tips

- It is generally recommended to use search_page or read_page directly first 
  instead of read_outline.
- Call read_outline only when the compacted outline exceeds the display
  limits (max 50 entries or 4000 characters) or when you genuinely need the full outline.
""".strip()

mcp = FastMCP("procontext", instructions=SERVER_INSTRUCTIONS, lifespan=lifespan)
# FastMCP doesn't expose a version kwarg — set it on the underlying Server
# so the MCP initialize handshake reports our version, not the SDK's.
mcp._mcp_server.version = __version__  # pyright: ignore[reportPrivateUsage]


@mcp.tool()
async def resolve_library(
    query: Annotated[
        str,
        Field(
            description="Query string to identify a library and its documentation. "
            "Can be a plain library name, package name or commonly known name."
            "Must not include version specifiers, extras, tags, or source URLs."
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
    """Resolve a library name to its documentation source.

    Accepts a plain library name, package name, display name, or alias.
    Matched in priority order: exact package lookup, exact text lookup
    (library ID, display name, alias), then fuzzy matching.

    Always call this first to identify a library and obtain its documentation URLs.
    Then pass the index_url to read_page to get the documentation index.

    Response:
      matches        — ranked list of results, sorted by relevance descending
      hint           — optional recoverable guidance for unsupported input or fuzzy fallback
      Each match contains:
        library_id   — canonical library identifier
        name         — human-readable library name
        description  — brief description of the library
        index_url    — URL of the documentation index (pass to read_page)
        packages     — list of package groups, each with:
          ecosystem    — "pypi" | "npm" | "conda" | "jsr"
          languages    — e.g. ["python"] or ["javascript", "typescript"]
          package_names — package names in this ecosystem
          readme_url   — README URL for this package group (may be null)
          repo_url     — source repository URL (may be null)
        matched_via  — "package_name" | "library_id" | "name" | "alias" | "fuzzy"
        relevance    — confidence score 0.0 (low) to 1.0 (high)

    An empty matches list means the library is not in the registry unless hint explains
    how to retry with a plain package or library name.
    """
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


@mcp.tool()
async def read_page(
    url: Annotated[
        str,
        Field(description="Documentation page URL."),
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
) -> ReadPageOutput:
    """Fetch the outline and content of a documentation page.

    Accepts any documentation URL — typically the index_url from
    resolve_library or a link found within a previously fetched page.

    Navigation: Use outline line numbers to identify the section you need,
    then call again with offset=<line>. For pages with very large outlines,
    use read_outline for paginated browsing.

    Response:
      url          — the URL of the fetched page
      content      — the content window
      outline      — compacted structural outline (target ≤50 entries) with
                     1-based line numbers, e.g. "1:# Title\\n42:## Usage"
      total_lines  — total line count of the full page
      offset       — 1-based line number where the content window starts
      limit        — maximum lines in the content window
      has_more     — true if more content exists beyond the current window
      next_offset  — line number to pass as offset to continue; null if no more
      content_hash — truncated SHA-256 (12 hex chars); compare across paginated
                     calls to detect if the underlying page changed
      cached       — true if served from cache
      cached_at    — ISO timestamp of last fetch; null for fresh network responses
      stale        — true if cache entry expired; background refresh triggered

    If has_more is true, call again with offset=next_offset to continue
    reading. Repeated calls on the same URL are served from cache (sub-100ms).
    """
    state: AppState = ctx.request_context.lifespan_context
    try:
        return ReadPageOutput.model_validate(await t_read_page.handle(url, offset, limit, state))
    except ProContextError as exc:
        log.warning("tool_error", tool="read_page", code=exc.code, message=exc.message)
        raise
    except Exception:
        log.error("tool_unexpected_error", tool="read_page", exc_info=True)
        raise


@mcp.tool()
async def read_outline(
    url: Annotated[
        str,
        Field(description="Documentation page URL."),
    ],
    ctx: Context,
    offset: Annotated[
        int,
        Field(description="1-based outline entry index to start from.", ge=1),
    ] = 1,
    limit: Annotated[
        int,
        Field(description="Maximum number of outline entries to return.", ge=1),
    ] = 1000,
) -> ReadOutlineOutput:
    """Browse the full outline of a documentation page with pagination.

    Returns paginated outline entries (headings and fence markers with line
    numbers). Use this when read_page reports that the outline is too large
    for inline display, or when you need to browse the complete page structure.

    Outline entries have empty fence pairs pre-stripped. Pagination uses
    entry indices (not line numbers) — pass next_offset to continue browsing.

    Response:
      url           — the URL of the fetched page
      outline       — paginated outline entries, e.g. "1:# Title\\n42:## Usage"
      total_entries — total outline entries (after stripping empty fences)
      has_more      — true if more entries exist beyond the current window
      next_offset   — entry index to pass as offset to continue; null if no more
      content_hash  — truncated SHA-256 (12 hex chars); compare across calls
                      to detect if the underlying page changed
      cached        — true if served from cache
      cached_at     — ISO timestamp of last fetch; null for fresh network responses
      stale         — true if cache entry expired; background refresh triggered
    """
    state: AppState = ctx.request_context.lifespan_context
    try:
        return ReadOutlineOutput.model_validate(
            await t_read_outline.handle(url, offset, limit, state)
        )
    except ProContextError as exc:
        log.warning("tool_error", tool="read_outline", code=exc.code, message=exc.message)
        raise
    except Exception:
        log.error("tool_unexpected_error", tool="read_outline", exc_info=True)
        raise


@mcp.tool()
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
    """Search within a documentation page for lines matching a query.

    Returns a compacted outline trimmed to the match range and matching lines
    with line numbers. Use the outline and match locations to identify relevant
    sections, then call read_page with the appropriate offset to read content.

    Supports literal and regex search, smart case sensitivity, and word
    boundary matching.

    Response:
      url          — the URL that was searched
      query        — the search query as provided
      matches      — matching lines as 'line_number:content', one per line
      outline      — compacted outline trimmed to match range; empty on zero matches
      total_lines  — total line count of the page
      has_more     — true if more matches exist beyond the returned set
      next_offset  — line number to pass as offset to continue paginating
      content_hash — truncated SHA-256 (12 hex chars); compare across calls
                     to detect if the underlying page changed
      cached       — true if page was served from cache
      cached_at    — ISO timestamp of last fetch; null for fresh responses
    """
    state: AppState = ctx.request_context.lifespan_context
    try:
        return SearchPageOutput.model_validate(
            await t_search_page.handle(
                url,
                query,
                state,
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
