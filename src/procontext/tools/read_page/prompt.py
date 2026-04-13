"""MCP-facing prompt text for the read_page tool."""

# Parameter descriptions
PARAM_URL = "Any URL - index, documentation page, or full documentation URL."
PARAM_OFFSET = "1-based line number to start reading from."
PARAM_LIMIT = "Maximum number of content lines to return."
PARAM_BEFORE = "Number of extra content lines to include before offset for backward context."
PARAM_INCLUDE_OUTLINE = (
    "Set to false to omit the outline from the response. "
    "Useful when paginating and the outline is already known."
)

DESCRIPTION = """
WHEN TO USE READ_PAGE:
- Use this tool to read the contents of a documentation or index page.

HOW TO USE:
- It supports paginated reading with offset and limit. Use the before parameter
  for extra backward context — it is additive and does not reduce the forward
  limit, so the total lines returned is up to before + limit.
- Small pages can be navigated with a few paginated read_page calls. For larger pages,
  use search_page to find relevant sections first.
- This tool also returns a compact outline for quick navigation.
- Pass include_outline as true in the first call and then set it to false to omit
  the outline for subsequent requests. This is useful when paginating through
  a page, saving tokens on subsequent requests.

INSTRUCTIONS FOR READING INDEX PAGE:
- **Always start with read_page on the index_url. This will help you understand the
  structure of the documentation and find the relevant sections and pages to read.**
- IMPORTANT: Directly searching the index may not provide the necessary context to 
  identify the relevant sections and pages.
- You must only use search_page on the index if the page is larger than 1000 lines.

RESPONSE:
```
  url          — the URL of the fetched page
  content      — the content window
  outline      — null when include_outline is false; otherwise contains
                 compact outline (full if small, compacted for large pages) 
                 and count of total entries in full outline
  total_lines  — total line count of the full page
  offset       — 1-based line number where the returned content window starts
  limit        — maximum forward lines requested from the input offset;
                 unchanged even when before > 0
  has_more     — true if more content exists beyond the current window
  next_offset  — line number to pass as offset to continue; null if no more
  content_hash — truncated SHA-256 (12 hex chars); compare across calls
                 to detect if the underlying page changed
```
""".strip()
