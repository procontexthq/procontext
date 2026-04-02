"""MCP-facing prompt text for the read_outline tool."""

DESCRIPTION = """
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
