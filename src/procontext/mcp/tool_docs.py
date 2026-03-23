"""Centralized MCP-facing server and tool description strings."""

SERVER_INSTRUCTIONS = """
ProContext works as a documentation layer for software libraries.

## Typical Workflow

1. **Start with resolve_library(query)** to locate a library by name, package name, or alias.
   Returns the library's documentation index URL (index_url), complete docs URL (full_docs_url
   if available), and package information.

2. **Use read_page** to browse the documentation index (or any page found within index).
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

- **read_page/search_page/read_outline input**: Pass URLs from resolve_library (index_url or 
  full_docs_url) or links found within previously fetched pages.

- **Caching**: Repeated calls to the same page are served from cache (< 100ms).
  Safe to paginate with read_page or call read_outline/search_page multiple times.

## Pro Tips

- For quick searches across entire documentation, you can pass full_docs_url to search_page.
- It is generally recommended to use search_page or read_page directly first instead of 
  read_outline. Call read_outline only when the compacted outline exceeds the display
  limits (max 50 entries or 4000 characters) or when you genuinely need the full outline.
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

Response:
  url          — the URL of the fetched page
  content      — the content window
  outline      — compacted structural outline (target ≤50 entries) with
                 1-based line numbers, e.g. "1:# Title\\n42:## Usage"
                 use read_outline to browse the full outline with pagination.
                 it will be clearly indicated if the outline is truncated.
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
