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

You can start with the index_url to discover available pages, then read individual
pages found within the index.

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

This is the starting point for the documentation retrieval flow. It provides
the documentation index URL and merged documentation URL (if available), plus
useful metadata about the library.

Response:
  matches        — ranked list of results, sorted by relevance descending
  hint           — optional recoverable guidance for unsupported input or fuzzy fallback
  Each match contains:
    library_id   — canonical library identifier
    name         — human-readable library name
    description  — brief description of the library
    index_url    — URL of the documentation index/TOC
    full_docs_url — URL of complete merged documentation if available
    packages     — list of package groups, each with:
      ecosystem    — "pypi" | "npm" | "conda" | "jsr"
      languages    — e.g. ["python"] or ["javascript", "typescript"]
      package_names — package names in this ecosystem
      readme_url   — README URL for this package group (may be null)
      repo_url     — source repository URL (may be null)
    matched_via  — "package_name" | "library_id" | "name" | "alias" | "fuzzy"
    relevance    — confidence score 0.0 (low) to 1.0 (high)

Index URL contains the links to all documentation pages. It can be passed as
input to read_page, search_page or read_outline.

Merged documentation URL (if available) contains the full content of all pages
merged into one, which can be useful for global search.

README URLs are tied to specific package groups, if available they can be useful
for getting a quick overview for a package. Supported by all tools as well.
""".strip()


READ_PAGE_DESCRIPTION = """
Fetch the content and outline of a documentation page.

Accepts any documentation URL - typically the index_url from
resolve_library or a link found within a previously fetched page.

This tool supports paginated reading with the offset and limit parameters.
You can use before parameter if you need extra backward context. Backward
context is additive — it does not reduce the forward limit. Total number of
lines returned will be a sum of before and limit.

It accepts full_docs_url as well but note that it may be very large and it is
advisable to find the relevant section first instead of directly reading it.
You can use search_page and read_outline to find the relevant sections.

Set include_outline to false to omit the outline from the response. In that
case the outline field is returned as null. This is
useful when paginating through a page where the outline is already known from
the first call, saving tokens on subsequent requests.

Response:
  url          — the URL of the fetched page
  content      — the content window
  outline      — compacted structural outline (target ≤50 entries) with
                 1-based line numbers, e.g. "1:# Title\\n42:## Usage"
                 use read_outline to browse the full outline with pagination.
                 it will be clearly indicated if the outline is truncated.
                 null when include_outline is false.
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

If has_more is true, call again with offset=next_offset to continue
reading. Repeated calls on the same URL are served from cache (sub-100ms).

The server uses a stale-while-revalidate strategy for caching. content_hash may
rarely change across calls if a new page is fetched in the background between calls.
This would indicate that the content has changed and you might have to refetch the
previous content window.
""".strip()


READ_OUTLINE_DESCRIPTION = """
Browse the full outline of a documentation page with page-line windowing.

Returns paginated outline entries (headings and fence markers with line
numbers). Use this when read_page reports that the outline is too large
for inline display, or when you need to browse the complete page structure.

Outline entries have empty fence pairs pre-stripped. offset is a page line
number, limit is the forward page-line span from that line, and before adds
backward page-line context without reducing limit.

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
Search within a documentation page for lines matching a query.

content target:
  Searches page content lines and returns matching lines plus compacted
  outline context trimmed to the match range.

outline target:
  Searches stored outline entries only. Matches are returned as
  'line_number:outline_text'.

Supports literal and regex search, smart case sensitivity, and word
boundary matching.

Response:
  url          — the URL that was searched
  query        — the search query as provided
  matches      — matching lines as 'line_number:content', one per line;
                 in outline mode, matching outline entries in the same format
  outline      — compacted outline trimmed to match range in content mode;
                 empty on zero matches and always empty in target 'outline' mode
  total_lines  — total line count of the page
  has_more     — true if more matches exist beyond the returned set
  next_offset  — line number to pass as offset to continue paginating
  content_hash — truncated SHA-256 (12 hex chars); compare across calls
                 to detect if the underlying page changed
  cached       — true if page was served from cache
  cached_at    — ISO timestamp of last fetch; null for fresh responses
""".strip()
