"""MCP-facing prompt text for the read_page tool."""

DESCRIPTION = """
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
  content_hash — truncated SHA-256 (12 hex chars); compare across calls
                 to detect if the underlying page changed
  cached       — true if served from cache
  cached_at    — ISO timestamp of last fetch; null for fresh network responses
  stale        — true if cache entry expired; background refresh triggered
""".strip()
