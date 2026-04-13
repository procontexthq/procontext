"""MCP-facing prompt text for the search_page tool."""

# Parameter descriptions
PARAM_URL = "URL of the page to search. Can be any URL."
PARAM_QUERY = "Search term or regex pattern."
PARAM_TARGET = "content: search page content lines. outline: search the outline entries only."
PARAM_MODE = "literal: exact substring match. regex: treat query as a regular expression."
PARAM_CASE_MODE = (
    "smart: lowercase query → case-insensitive; mixed/uppercase → case-sensitive. "
    "insensitive: always case-insensitive. "
    "sensitive: always case-sensitive."
)
PARAM_WHOLE_WORD = "When true, match only at word boundaries."
PARAM_OFFSET = "1-based line number to start searching from."
PARAM_MAX_RESULTS = "Maximum number of matching lines to return."

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
  outline      — null when search mode is outline; otherwise contains
                 compact outline (full if small, compacted for large pages) 
                 and count of total enteries in full outline
  total_lines  — total line count of the page
  has_more     — true if more matches exist beyond the returned set
  next_offset  — line number to pass as offset to continue paginating
  content_hash — truncated SHA-256 (12 hex chars); compare across calls
                 to detect if the underlying page changed
""".strip()
