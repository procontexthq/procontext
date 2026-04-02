"""MCP-facing prompt text for the resolve_library tool."""

DESCRIPTION = """
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
