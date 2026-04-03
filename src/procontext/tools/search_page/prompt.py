"""MCP-facing prompt text for the search_page tool."""

DESCRIPTION = """
Search within a documentation page and return the full text of each matching line.
Supports literal and regex search, smart case sensitivity, and word boundary matching.
For OR-style multi-term search, use mode="regex" with a query like "foo|bar".

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
