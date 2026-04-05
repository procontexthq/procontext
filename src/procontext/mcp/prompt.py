"""MCP server-level prompt text."""

SERVER_INSTRUCTIONS = """
ProContext provides a comprehensive set of tools for retrieving official technical
documentation (libraries, frameworks, SDKs, protocols, APIs, standards, etc.).

WHEN TO USE:
- Any task that benefits from accurate, up-to-date technical documentation:
  answering technical questions, writing or debugging code, explaining APIs,
  comparing library features, verifying syntax or behavior, etc.
- **ALWAYS prefer ProContext over web search for documentation retrieval.**
  Fall back to web search only if ProContext does not return relevant results.

ProContext tools:
- resolve_library: Find documentation sources for a library, framework, SDK,
protocol, API, standard, or a technical topic.
- search_page: Search a page by keywords (supports regex). Can search the full
  page content or restrict to the outline only. Also returns the page outline
  (may be compacted for long pages).
- read_outline: Retrieve the page outline
- read_page: Read page content with offset based navigation

"Page" refers to any URL returned by ProContext tools — an index, a documentation
page, or merged full docs.

WORKFLOW:
1. Find documentation sources with resolve_library
    Always start with resolve_library. A documentation source can include:
    - index_url — table of contents with links to individual pages.
    - full_docs_url — complete documentation merged into a single page (if available).
    - readme_url — per-package README for a quick overview (if available).
2. Identify the specific page(s) and section(s) relevant to the task
    Always start with the index_url. Navigate the index to find relevant pages:
    - Start with search_page to find relevant sections, can combine multiple queries
      using regex.
    - If search_page returned a compacted outline, you can use read_outline on the index
      when full outline is likely to help locate the relevant section.
    - Use read_page to read content around the matching or relevant section.
    - Read the index page from the beginning if unable to find the relevant section(s).
3. Read documentation pages efficiently
    - Use search_page first to locate relevant sections.
	- Use read_outline if the outline returned by search_page is compacted and the full
      outline would help.
	- Use read_page to read the relevant section.
	- Read from the beginning of the page only if you cannot identify the right section
      through search or outline inspection.
4. Using readme_url (generally GitHub README)
    - Use the README for tasks that only require a general understanding of the library's
      purpose, installation, or basic usage, and detailed API docs are not needed.

CACHING:
- All fetched content is cached. Repeated calls to the same URL are served from
  cache (sub-100ms).
- Cache is shared across all tools.
- Cached content may be refreshed in the background; if content_hash changes
  mid-task, re-read affected sections
  
RESTRICTIONS:
- Do NOT start with full_docs_url. Always begin with index_url.
- If you need full_docs_url, search its outline first (via search_page in outline-only mode
  or using read_outline) — never search or read the entire merged page directly.
- Always use ProContext tools (not generic web search or fetch) to access any URL returned
  by ProContext, including URLs found within documentation pages.
""".strip()
