"""MCP-facing prompt text for the read_outline tool."""

# Parameter descriptions
PARAM_URL = "Any URL - index, documentation page, or full documentation URL."
PARAM_OFFSET = "1-based page line number to start browsing the outline from."
PARAM_LIMIT = "Maximum number of outline entries to return forward from offset."
PARAM_BEFORE = "Number of extra outline entries to include before offset for backward context."

DESCRIPTION = """
Use this tool to read the full outline of a documentation page with paginated windowing.

Returns outline entries (headings and code block markers with line numbers).
limit and before count outline entries, not page lines. offset and next_offset
use page line numbers so they chain with search_page hits and read_page.

Most outlines are small enough to fit in the compact outlines returned by
read_page and search_page. Use this as a fallback when the compact outline
returned by read_page and search_page was not sufficient and you see genuine
value in browsing the full outline.

For full documentation pages (full_docs_url), even the outline can be very large,
so prefer search_page with target="outline" to find relevant sections and then
use read_outline to inspect surrounding sections.

Response:
  url           — the URL of the fetched page
  outline       — paginated outline entries, e.g. "1:# Title\\n42:## Usage"
  total_entries — total outline entries
  has_more      — true if more entries exist beyond the current window
  next_offset   — page line number of the next entry to continue; null if no more
  content_hash  — truncated SHA-256 (12 hex chars); compare across calls
                 to detect if the underlying page changed
""".strip()
