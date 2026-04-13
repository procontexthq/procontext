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
WHEN TO USE SEARCH_PAGE:
- Use this tool to search across indexes, individual pages, or the full documentation.
- This tool returns the full text of each matching line.

IMPORTANT:
- Performance drops drastically with longer phrases. Always use short keywords.
- This tool supports searching multiple keywords efficiently by combining them into
  a single regex pattern (e.g. 'foo|bar|baz').
- When searching for long phrases, try to break them down into multiple short
  keywords and combine with regex patterns (e.g. 'foo|bar|baz' instead of 'foo bar baz').

INSTRUCTIONS FOR SEARCHING INDEX (index_url):
- Index may not contain the exact keyword, so always use single keywords and combine
  multiple queries using regex patterns to find relevant sections.
- If unable to find the relevant sections, fallback to reading the page using read_page.

INSTRUCTIONS FOR SEARCHING FULL DOCUMENTATION (full_docs_url):
- When searching full documentation (full_docs_url), always start with target="outline".
  Fallback to content search if outline search does not return relevant results.

RESPONSE:
```
  url          — the URL that was searched.
  query        — the search query as provided.
  matches      — matching lines as 'line_number:content', one per line.
  outline      — compact outline (full if small, compacted for large pages)
                 and count of total entries in full outline.
  total_lines  — total line count of the page.
  has_more     — true if more matches exist beyond the returned set.
  next_offset  — line number to pass as offset to continue paginating.
  content_hash — truncated SHA-256 (12 hex chars); compare across calls
                 to detect if the underlying page changed.
```
""".strip()
