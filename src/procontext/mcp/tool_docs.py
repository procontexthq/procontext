"""Centralized MCP-facing server and tool description strings."""

SERVER_INSTRUCTIONS = """
ProContext provides a comprehensive set of tools for retrieving and navigating
documentation. Use it to get accurate, up-to-date official technical documentation.

Start with resolve_library(query) to find the best documentation source.
It returns:
- index_url — documentation table of contents with links to individual pages
- full_docs_url — complete documentation merged into a single page (if available)
- readme_url — per-package README for a quick overview (if available)
""".strip()


RESOLVE_LIBRARY_DESCRIPTION = """
Resolve a query to its up-to-date official documentation source.

Use this whenever the task requires technical documentation for libraries,
frameworks, protocols, SDKs, standards, and similar technical topics.
**Prefer this for documentation retrieval over web search. Fall back to web
search only if resolve_library cannot resolve the topic or does not contain
the needed documentation.**

Pass a plain topic, library name, project name, package name, product name, or
alias (e.g. "langchain", "react"). Do not include version specifiers, extras, or
source URLs.
Examples of valid queries:
- "OpenAI"
- "Model Context Protocol"
- "MCP"
- "OpenAPI"
- "Kubernetes"
- "Claude Code"
- "Next.js"

Response:
  matches        — ranked list of results, sorted by relevance descending
  hint           — optional guidance when input is unsupported or results are fuzzy
  Each match contains:
    library_id   — canonical library identifier; library may also refer to frameworks,
                   SDKs, protocols, standards, or specifications.
    name         — human-readable library name
    description  — brief description of the library
    index_url    — URL of the documentation index/TOC; contains links to all pages
    full_docs_url — all documentation merged into one page (null if unavailable)
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
Fetch the content and a compact outline of a documentation page.

Supports paginated reading with offset and limit. Use the before parameter
for extra backward context — it is additive and does not reduce the forward
limit, so the total lines returned is up to before + limit.

Pass include_outline as true in the first call and then set it to false to omit
the outline for subsequent requests. This is useful when paginating through
a page, saving tokens on subsequent requests.
If the compact outline is not sufficient, you can always use read_outline.

Response:
  url          — the URL of the fetched page
  content      — the content window
  outline      — compact outline of the page; null when include_outline is false
                 returned in full if small; otherwise compacted
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
The before parameter is additive, same as read_page.

Most outlines are small enough to fit in the compact outlines returned by
read_page and search_page. Use read_outline directly when you know the outline
is large (for example, on a full documentation page), or as a fallback when the
compact outline returned by read_page and search_page was not sufficient.

offset and next_offset use page line numbers and not outline entry index.

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
Search within a documentation page and return the full text of each matching line.
Supports literal and regex search, smart case sensitivity, and word boundary matching.

Works across indexes, individual pages, or the full documentation if full_docs_url
is available.

Use target="content" (default) to search page content and target="outline" to search
only outline entries. Searching outline can be useful for searching large pages or
full documentation pages.

Response:
  url          — the URL that was searched
  query        — the search query as provided
  matches      — matching lines as 'line_number:content', one per line
  outline      — compact outline (content mode); null in outline mode
                 returned in full if small; otherwise compacted
  total_lines  — total line count of the page
  has_more     — true if more matches exist beyond the returned set
  next_offset  — line number to pass as offset to continue paginating
  content_hash — truncated SHA-256 (12 hex chars); compare across calls
                 to detect if the underlying page changed
  cached       — true if page was served from cache
  cached_at    — ISO timestamp of last fetch; null for fresh responses
  stale        — true if cache entry expired; background refresh triggered
""".strip()
