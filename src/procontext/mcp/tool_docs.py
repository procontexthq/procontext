"""Centralized MCP-facing server and tool description strings."""

SERVER_INSTRUCTIONS = """
ProContext provides AI agents with accurate, up-to-date library documentation.

## Getting Started

Use **resolve_library(query)** to find a library by name, package name, or alias.
It returns:
- **index_url** — documentation table of contents with links to individual pages
- **full_docs_url** — complete documentation merged into a single page (if available)
- **readme_url** — per-package README for a quick overview (if available)

Pass only the plain library name (e.g., "langchain", "openai"). Do not include
version specifiers, extras, tags, or source URLs.

## Reading Documentation

**read_page(url)** fetches content and a structural outline of any documentation page.
Supports paginated reading — use offset and limit to navigate through large pages.
When has_more is true, pass next_offset to continue reading.

All page tools (read_page, search_page, read_outline) accept any URL returned by
resolve_library — index_url, full_docs_url, readme_url, or individual page URLs
found within the index.

## Searching

**search_page(url, query)** finds matching lines within a page. Supports literal
and regex search, smart case sensitivity, and word boundary matching.

- Use **target="content"** (default) to search page content — returns matching
  lines and a structural outline.
- Use **target="outline"** to search only the structural outline entries.
- For broad searches across all documentation, pass full_docs_url if available.

Both targets support pagination via offset and max_results.

## Outlines

read_page and search_page include a smartly compacted outline in their response. 
If the full page outline is needed, **read_outline(url)** provides paginated access
to the full outline.

## Caching

Repeated calls to the same page are served from cache (sub-100ms), so paginating
or searching the same page multiple times is inexpensive. Compare content_hash
across paginated calls to detect if the underlying page changed between requests.
""".strip()


RESOLVE_LIBRARY_DESCRIPTION = """
Resolve a library name to its documentation source.

This is the starting point for documentation retrieval. Pass a plain library
name, package name, or alias (e.g., "langchain", "pydantic-settings"). Do not
include version specifiers, extras, or source URLs.

Response:
  matches        — ranked list of results, sorted by relevance descending
  hint           — optional guidance when input is unsupported or results are fuzzy
  Each match contains:
    library_id   — canonical library identifier
    name         — human-readable library name
    description  — brief description of the library
    index_url    — URL of the documentation index/TOC; contains links to all pages
    full_docs_url — all documentation merged into one page; useful for broad search
                   (null if unavailable)
    packages     — list of package groups, each with:
      ecosystem    — "pypi" | "npm" | "conda" | "jsr"
      languages    — e.g. ["python"] or ["javascript", "typescript"]
      package_names — package names in this ecosystem
      readme_url   — README URL for a quick package overview (may be null)
      repo_url     — source repository URL (may be null)
    matched_via  — "package_name" | "library_id" | "name" | "alias" | "fuzzy"
    relevance    — confidence score 0.0 (low) to 1.0 (high)
""".strip()


READ_PAGE_DESCRIPTION = """
Fetch the content and a smart outline of a documentation page.

Supports paginated reading with offset and limit. Use the before parameter
for extra backward context — it is additive and does not reduce the forward
limit, so the total lines returned equals before + limit.

For full documentation URLs, find the relevant section first using search_page
or read_outline rather than reading from the beginning.

Set include_outline to false to omit the outline from the response (the outline
field is returned as null). This is useful when paginating through a page where
the outline is already known from the first call, saving tokens on subsequent
requests.

The outline is returned in full when it is under 50 entries and 4000 characters.
Larger outlines are progressively trimmed to fit — the response indicates when
trimming occurred. Use read_outline for paginated access to the full outline.

Response:
  url          — the URL of the fetched page
  content      — the content window
  outline      — smart outline of the page; null when include_outline is false
  total_lines  — total line count of the full page
  offset       — 1-based line number where the returned content window starts
  limit        — maximum forward lines requested from the input offset;
                 unchanged even when before > 0
  has_more     — true if more content exists beyond the current window
  next_offset  — line number to pass as offset to continue; null if no more
  content_hash — truncated SHA-256 (12 hex chars); compare across paginated
                 calls to detect if the underlying page changed
  cached       — true if served from cache
  cached_at    — ISO timestamp of last fetch; null for fresh network responses
  stale        — true if cache entry expired; background refresh triggered

If has_more is true, call again with offset=next_offset to continue reading.
Repeated calls to the same URL are served from cache (sub-100ms), and the
cache is shared across all tools.

The server uses stale-while-revalidate caching. If content_hash changes between
paginated calls, the underlying page was refreshed in the background — refetch
the previous window to get consistent content.
""".strip()


READ_OUTLINE_DESCRIPTION = """
Browse the full outline of a documentation page with paginated windowing.

Returns outline entries (headings and code block markers with line numbers).
Code block markers without content are removed. The before parameter is additive, same as
read_page.

Most outlines are small enough to fit in the smart outlines returned by
read_page and search_page. Use read_outline directly when you know the outline
is large (for example, on a full documentation page), or as a fallback when the
smart outline indicates it was trimmed.

Response:
  url           — the URL of the fetched page
  outline       — paginated outline entries, e.g. "1:# Title\\n42:## Usage"
  total_entries — total outline entries
  has_more      — true if more entries exist beyond the current window
  next_offset   — page line number to pass as offset to continue; null if no more
  content_hash  — truncated SHA-256 (12 hex chars); compare across calls
                  to detect if the underlying page changed
  cached        — true if served from cache
  cached_at     — ISO timestamp of last fetch; null for fresh network responses
  stale         — true if cache entry expired; background refresh triggered
""".strip()


SEARCH_PAGE_DESCRIPTION = """
Search within a documentation page and return complete matching lines.

Works across indexes, individual pages, or the full documentation if
full_docs_url is available. Supports literal and regex search, smart case
sensitivity, and word boundary matching.

Use target="content" (default) to search page content — the response includes
a smart outline for structural context. Small outlines are returned in full;
larger ones are trimmed to the match range and then progressively compacted,
similar to read_page. Any trimming is noted in the response. Use
target="outline" to search only outline entries — the outline field is null
since the matches themselves are outline entries.

Response:
  url          — the URL that was searched
  query        — the search query as provided
  matches      — matching lines as 'line_number:content', one per line
  outline      — smart outline (content mode); null in outline mode
  total_lines  — total line count of the page
  has_more     — true if more matches exist beyond the returned set
  next_offset  — line number to pass as offset to continue paginating
  content_hash — truncated SHA-256 (12 hex chars); compare across calls
                 to detect if the underlying page changed
  cached       — true if page was served from cache
  cached_at    — ISO timestamp of last fetch; null for fresh responses
  stale        — true if cache entry expired; background refresh triggered
""".strip()
