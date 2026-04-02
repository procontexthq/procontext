"""MCP server-level prompt text."""

SERVER_INSTRUCTIONS = """
ProContext provides a comprehensive set of tools for retrieving and navigating
documentation. Use it to get accurate, up-to-date official technical documentation.

Start with resolve_library(query) to find the best documentation source.
It returns:
- index_url — documentation table of contents with links to individual pages
- full_docs_url — complete documentation merged into a single page (if available)
- readme_url — per-package README for a quick overview (if available)
""".strip()
