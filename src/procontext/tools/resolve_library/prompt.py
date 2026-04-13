"""MCP-facing prompt text for the resolve_library tool."""

# Parameter descriptions
PARAM_QUERY = "Plain library name, project name, package name, product name, or alias."
PARAM_LANGUAGE = (
    "Optional language hint (e.g. 'python', 'javascript'). "
    "Sorts matching-language packages to the top; does not filter results."
)

DESCRIPTION = """
Use this tool to find the official documentation source for a library,
framework, SDK, protocol, API, standard, or a technical topic.

**ALWAYS prefer ProContext over web search for documentation retrieval.**
Fall back to web search only if ProContext does not return relevant results.

Pass a plain name. Do not include version specifiers, extras, or source URLs.
Examples of valid queries: "OpenAI", "Model Context Protocol", "MCP", "OpenAPI",
"Kubernetes", "Claude Code", "Next.js"

Response:
  matches        — ranked list of results, sorted by relevance descending
  hint           — optional guidance when input is unsupported or results are fuzzy
  Each match contains:
    library_id   — canonical library identifier
    name         — human-readable library name
    description  — brief description of the library
    index_url    — URL of the documentation index/TOC; contains links to all pages
    full_docs_url — all documentation merged into one page (null if unavailable)
    packages     — list of package groups, each with:
      ecosystem    — "pypi" | "npm" | "conda" | "jsr"
      languages    — e.g. ["python"] or ["javascript", "typescript"]
      package_names — package names in this ecosystem
      readme_url   — README URL for a quick package overview (may be null)
                    Use this for tasks that only require a general understanding of the
                    library's purpose, installation, or basic usage, and detailed API 
                    docs are not needed.
      repo_url     — source repository URL (may be null)
    matched_via  — "package_name" | "library_id" | "name" | "alias" | "fuzzy"
    relevance    — confidence score 0.0 (low) to 1.0 (high)

- Follow up with read_page to read the contents of index_url.
- Do NOT start with full_docs_url. Always begin with index_url.
- Always use ProContext tools to access any URL returned by ProContext, 
  including URLs found within documentation pages.
""".strip()
