# Pro-Context: Functional Specification

> **Document**: 02-functional-spec.md
> **Status**: Draft
> **Last Updated**: 2026-02-12
> **Depends on**: 01-competitive-analysis.md

---

## 1. Problem Statement

AI coding agents (Claude Code, Cursor, Windsurf, etc.) hallucinate API details when working with third-party libraries. They generate code using deprecated methods, incorrect parameter names, and outdated patterns because their training data has a knowledge cutoff.

The competitive analysis (01-competitive-analysis.md) identified two core findings:

1. **Accuracy is the primary challenge.** The most popular MCP doc server (Context7) achieves only 59-65% accuracy. The best (Deepcon, 90%) uses a proprietary query-understanding model. No open-source solution achieves high accuracy.

2. **Two paradigms exist for documentation retrieval.** The "server decides" paradigm (Context7, Docfork, Deepcon) returns pre-selected chunks. The "agent decides" paradigm (mcpdoc) gives the agent a navigation index and lets it read what it needs. Neither paradigm alone is optimal — server-side search is efficient but accuracy-limited; agent navigation is more accurate but costs more tool calls.

**Pro-Context** is an open-source, self-hostable MCP server that combines both paradigms. It provides server-side search as a fast path for straightforward queries, and structured documentation navigation for cases where the agent needs to browse and reason about the content — the way a human developer uses docs.

The key architectural bet: **modern coding agents are capable readers**. They can scan a table of contents, decide which pages are relevant, read them progressively, and extract what they need. Pro-Context should enable this capability rather than try to replace it with server-side intelligence.

---

## 2. Target Users

### 2.1 Individual Developer

- Uses Claude Code, Cursor, Windsurf, or similar AI coding agent
- Works primarily with Python libraries (LangChain, FastAPI, Pydantic, etc.)
- Wants accurate, up-to-date documentation injected into agent context
- Runs Pro-Context locally via stdio transport
- Zero configuration required — auto-detects project libraries from `pyproject.toml`, `requirements.txt`, etc.

### 2.2 Development Team

- 3-20 developers sharing an AI-assisted development environment
- Deploys Pro-Context as a shared service via Streamable HTTP transport
- Wants shared documentation cache (one developer's fetch benefits all)
- Needs API key authentication and usage tracking
- May have internal/private library documentation

### 2.3 Enterprise (Future)

- Large organization with custom documentation sources
- Requires audit logging and access controls
- Deploys via Docker in private infrastructure
- Needs custom source adapters for internal docs

---

## 3. Core Concepts

Before defining tools and behavior, this section establishes the key concepts that shape the design.

### 3.1 Two Retrieval Paths

Pro-Context offers agents two ways to access documentation:

```
┌─────────────────────────────────────────────────────┐
│  Agent asks: "How do I use streaming in LangChain?" │
└──────────────┬──────────────────────┬───────────────┘
               │                      │
     ┌─────────▼──────────┐ ┌────────▼──────────────┐
     │  Fast Path          │ │  Navigation Path       │
     │  (server-decides)   │ │  (agent-decides)       │
     │                     │ │                         │
     │  resolve-library    │ │  resolve-library        │
     │       ↓             │ │  (returns TOC)          │
     │  get-docs           │ │       ↓                 │
     │  (BM25 search,      │ │  Agent reads TOC,       │
     │   returns content)  │ │  picks relevant pages   │
     │                     │ │       ↓                 │
     │  2 tool calls       │ │  read-page (1-3x)      │
     │  ~2-5s              │ │                         │
     │  Good for keyword   │ │  3-5 tool calls         │
     │  queries            │ │  ~5-15s                 │
     │                     │ │  Good for conceptual    │
     │                     │ │  queries                │
     └─────────────────────┘ └─────────────────────────┘
```

**The agent chooses which path to use.** For "ChatOpenAI constructor parameters", the fast path is ideal. For "how do I implement a custom retry strategy with LangChain", the navigation path gives better results because the agent can reason about which docs pages are relevant with its full conversation context.

Both paths share the same cache and source infrastructure.

### 3.2 Documentation Sources

Documentation is fetched from authoritative sources in priority order:

| Priority | Source | Content Type | Coverage |
|----------|--------|-------------|----------|
| 1 | **llms.txt** | LLM-optimized markdown, authored by library maintainers | Growing: 500+ sites, accelerating via Mintlify (10K+ companies) and Fern |
| 2 | **GitHub** | Raw markdown from /docs/, README.md | Near-universal for open-source libraries |
| 3 | **Custom** | User-configured URLs, local files | Enterprise/internal docs |

**llms.txt is the preferred source** because it is authored by the library maintainers, structured for LLM consumption, and delivered as clean markdown — no scraping or HTML parsing required. Where llms.txt is not available, the GitHub adapter provides a universal fallback.

### 3.3 The Table of Contents (TOC)

Every resolved library has a table of contents — a structured index of available documentation pages. This is the foundation of the navigation path.

**For libraries with llms.txt**: The TOC is the parsed llms.txt content — a list of pages with titles, URLs, and one-sentence descriptions.

**For libraries without llms.txt**: The TOC is generated from the GitHub repository structure — /docs/ directory listing, README.md sections, wiki pages.

The TOC is returned as part of the `resolve-library` response and also available as an MCP resource. This gives the agent what it needs to navigate without extra tool calls.

### 3.4 Project-Scoped Libraries

Pro-Context can auto-detect which libraries a project uses by scanning project files:

| File | Ecosystem | What's Extracted |
|------|-----------|-----------------|
| `pyproject.toml` | Python | `[project.dependencies]`, `[tool.poetry.dependencies]` |
| `requirements.txt` | Python | Package names and version constraints |
| `Pipfile` | Python | `[packages]` section |
| `package.json` | JS/TS (future) | `dependencies`, `devDependencies` |

Detected libraries are pre-resolved at startup. Their TOCs are registered as MCP resources, making them immediately visible to the agent without any tool calls.

---

## 4. User Stories

### US-1: Resolve a Library and See Its Documentation Index

> As a developer, when I ask "look up LangChain docs", the agent should identify the library, resolve its version, and get a table of contents so it can navigate the documentation.

**Acceptance criteria:**
- Agent calls `resolve-library` with a natural language query
- Server returns canonical library ID, version info, available sources, and TOC
- TOC contains page titles, URLs, and descriptions from llms.txt (or generated from GitHub)
- Fuzzy matching handles typos (e.g., "langchan" → "langchain")
- Language filter narrows results (e.g., `language: "python"`)

### US-2: Quick Documentation Lookup (Fast Path)

> As a developer, when I ask "what are the parameters for FastAPI's Depends()", the agent should get a focused answer quickly.

**Acceptance criteria:**
- Agent calls `get-docs` with library ID, topic, and optional version
- Server searches cached/indexed documentation using BM25
- Returns focused markdown content with source URL, version, confidence score
- Cached responses return in <500ms
- JIT fetch + index + search completes in <5s
- Response includes `relatedPages` — links to pages the agent can read for more depth

### US-3: Navigate Documentation (Navigation Path)

> As a developer, when I ask "how do I implement a custom retry strategy with LangChain", the agent should be able to browse the documentation and find the right pages.

**Acceptance criteria:**
- Agent receives TOC from `resolve-library` (or reads it from a resource)
- Agent reasons about which pages are relevant based on titles and descriptions
- Agent calls `read-page` with a specific documentation URL
- Server fetches the page, caches it, and returns clean markdown
- Agent can call `read-page` multiple times to explore different pages
- Fetched pages are cached for subsequent requests

### US-4: Search Across Documentation

> As a developer, when I ask "find all places LangChain mentions retry logic", the agent should search across the library's documentation and return ranked results with links.

**Acceptance criteria:**
- Agent calls `search-docs` with library ID and search query
- Server returns ranked results with title, snippet, relevance score, and URL
- Each result URL can be passed to `read-page` for full content
- If documentation is not yet indexed, server triggers JIT fetch and index

### US-5: List Available Libraries

> As a developer, I want to know which libraries Pro-Context can provide docs for.

**Acceptance criteria:**
- Agent calls `list-libraries` with optional language and category filters
- Returns curated (known-libraries registry) and previously-cached libraries
- Project-detected libraries are included with a `projectDetected: true` flag

### US-6: Version-Specific Documentation

> As a developer, I need documentation for a specific library version, not just "latest".

**Acceptance criteria:**
- All tools accept an optional `version` parameter
- Version resolves to exact release via PyPI (Python) or npm (JS/TS)
- If version is omitted, server uses latest stable version
- Cached documentation is version-specific (v0.2 and v0.3 stored separately)

### US-7: Project Auto-Detection

> As a developer, I want Pro-Context to know which libraries my project uses without me configuring anything.

**Acceptance criteria:**
- Server scans the working directory for `pyproject.toml`, `requirements.txt`, `Pipfile`
- Detected libraries are pre-resolved at startup
- Their TOCs are registered as MCP resources
- `list-libraries` includes detected libraries
- Auto-detection can be disabled in config

### US-8: Team Deployment with API Keys

> As a team lead, I want to deploy Pro-Context as a shared service so all team members benefit from cached documentation.

**Acceptance criteria:**
- Server starts in HTTP mode with `transport: http`
- API keys are required for all requests
- Admin CLI (`pro-context-admin`) can create, list, and revoke keys
- Each key has configurable rate limits
- Shared cache means one developer's fetch benefits all others

### US-9: Graceful Degradation

> As a developer, I expect useful responses even when documentation sources are temporarily unavailable.

**Acceptance criteria:**
- If primary source (llms.txt) fails, server falls back to GitHub adapter
- If all sources fail but cache exists, stale cache is served with a warning
- If library is unknown, server returns fuzzy suggestions
- Error responses include actionable recovery suggestions

---

## 5. MCP Tool Definitions

Pro-Context exposes **5 tools**. The tool set is designed to support both the fast path (server-decides) and the navigation path (agent-decides).

**Design decision — replacing `get-examples` with `read-page`**: The previous spec had a `get-examples` tool that extracted code blocks from documentation. This is dropped in favor of `read-page`, which enables agent-driven navigation. The rationale: extracting code examples is something the agent does naturally when it reads a documentation page. A dedicated tool adds server complexity without meaningfully improving accuracy. Meanwhile, `read-page` is the enabling tool for the entire navigation paradigm — without it, the agent cannot follow up on TOC entries or search results.

### 5.1 `resolve-library`

Resolves a natural language library query to a canonical identifier and returns the documentation index (TOC).

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Library name or natural language query (e.g., 'langchain', 'python fastapi', 'pydantic v2')"
    },
    "language": {
      "type": "string",
      "enum": ["python"],
      "description": "Programming language filter. Currently only Python is fully supported."
    }
  },
  "required": ["query"]
}
```

**Output Schema:**
```json
{
  "type": "object",
  "properties": {
    "libraryId": {
      "type": "string",
      "description": "Canonical library identifier (e.g., 'langchain-ai/langchain')"
    },
    "name": {
      "type": "string",
      "description": "Human-readable library name"
    },
    "description": {
      "type": "string",
      "description": "Brief library description"
    },
    "language": {
      "type": "string",
      "description": "Programming language"
    },
    "defaultVersion": {
      "type": "string",
      "description": "Latest stable version"
    },
    "availableVersions": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Recent available versions (most recent first, max 10)"
    },
    "sources": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Available documentation sources (e.g., ['llms.txt', 'github'])"
    },
    "toc": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "title": { "type": "string", "description": "Page title" },
          "url": { "type": "string", "description": "Page URL (can be passed to read-page)" },
          "description": { "type": "string", "description": "One-sentence description of the page" },
          "section": { "type": "string", "description": "Section grouping (e.g., 'Getting Started', 'API Reference')" }
        }
      },
      "description": "Table of contents — documentation pages available for this library. Use read-page to fetch any of these URLs."
    }
  }
}
```

**Behavior:**
1. Fuzzy-match `query` against known library registry
2. If no match, attempt resolution via PyPI registry
3. If still no match, return error with fuzzy suggestions
4. Fetch available versions from package registry (cached for 1 hour)
5. Determine available documentation sources (check for llms.txt, GitHub)
6. Fetch and parse the TOC:
   - If llms.txt available → parse it into structured TOC entries
   - If no llms.txt → generate TOC from GitHub repo structure (/docs/ listing, README sections)
7. Cache the TOC
8. Return library metadata + TOC

**Why the TOC is included here**: This is the most important design decision in the tool set. Including the TOC in the resolve response means the agent can start navigating documentation after a single tool call. Without this, the agent would need a second call (`fetch_docs` on the llms.txt URL, as mcpdoc does) just to see the index. Since every tool call costs latency and tokens, front-loading the TOC saves one round-trip for the most common workflow.

**Error cases:**
- Unknown library → `LIBRARY_NOT_FOUND` with fuzzy suggestion
- Registry timeout → `REGISTRY_TIMEOUT` with retry advice
- No documentation sources found → returns metadata without TOC, with a note that no docs are indexed

---

### 5.2 `get-docs`

The **fast path** tool. Retrieves focused documentation for a specific topic using server-side search (BM25). Best for keyword-heavy queries where the server can match effectively.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "libraryId": {
      "type": "string",
      "description": "Canonical library ID from resolve-library"
    },
    "topic": {
      "type": "string",
      "description": "Documentation topic (e.g., 'chat models', 'streaming', 'dependency injection')"
    },
    "version": {
      "type": "string",
      "description": "Library version. Defaults to latest stable if omitted."
    },
    "maxTokens": {
      "type": "number",
      "description": "Maximum tokens to return. Default: 5000. Range: 500-10000.",
      "default": 5000,
      "minimum": 500,
      "maximum": 10000
    }
  },
  "required": ["libraryId", "topic"]
}
```

**Output Schema:**
```json
{
  "type": "object",
  "properties": {
    "content": {
      "type": "string",
      "description": "Documentation content in markdown format"
    },
    "source": {
      "type": "string",
      "description": "URL where documentation was fetched from"
    },
    "version": {
      "type": "string",
      "description": "Exact version of documentation returned"
    },
    "lastUpdated": {
      "type": "string",
      "format": "date-time",
      "description": "When this documentation was last fetched/verified"
    },
    "confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "Relevance confidence score (1.0 = exact match, 0.0 = no match)"
    },
    "cached": {
      "type": "boolean",
      "description": "Whether this result was served from cache"
    },
    "stale": {
      "type": "boolean",
      "description": "Whether the cached content may be outdated"
    },
    "relatedPages": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "title": { "type": "string" },
          "url": { "type": "string" },
          "description": { "type": "string" }
        }
      },
      "description": "Other documentation pages that may be relevant. Use read-page to fetch them if the above content is insufficient."
    }
  }
}
```

**Behavior:**
1. Resolve version (if not specified, use latest stable)
2. Check cache (memory → SQLite) for matching (libraryId, version, topic)
3. If cached and fresh → return immediately
4. If cached but stale → return stale with `stale: true`, trigger background refresh
5. If not cached → fetch documentation via adapter chain (llms.txt → GitHub → Custom)
6. Chunk fetched content into sections, index with BM25
7. Rank chunks by topic relevance, select top chunk(s) within `maxTokens` budget
8. Identify related pages from the TOC that the agent might want to read for more context
9. Store in cache
10. Return content + related pages

**The `relatedPages` field**: This is the bridge between the fast path and the navigation path. If the server-side BM25 search returns content with low confidence (e.g., <0.6), the `relatedPages` give the agent a way to navigate further. The agent sees "here's what I found, but you might also want to read these pages" — and can use `read-page` to explore them.

**Error cases:**
- Library not found → `LIBRARY_NOT_FOUND`
- Topic not found → `TOPIC_NOT_FOUND` with suggestion to try `search-docs` or browse `relatedPages`
- All sources unavailable → serve stale cache or `SOURCE_UNAVAILABLE`

---

### 5.3 `search-docs`

Searches across a library's indexed documentation and returns ranked results with URLs. The agent can then use `read-page` to fetch full content for any result.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "libraryId": {
      "type": "string",
      "description": "Canonical library ID"
    },
    "query": {
      "type": "string",
      "description": "Search query (e.g., 'retry logic', 'error handling middleware')"
    },
    "version": {
      "type": "string",
      "description": "Library version. Defaults to latest stable."
    },
    "maxResults": {
      "type": "number",
      "description": "Maximum number of results. Default: 5. Range: 1-20.",
      "default": 5,
      "minimum": 1,
      "maximum": 20
    }
  },
  "required": ["libraryId", "query"]
}
```

**Output Schema:**
```json
{
  "type": "object",
  "properties": {
    "results": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "title": { "type": "string", "description": "Section/page title" },
          "snippet": { "type": "string", "description": "Relevant text excerpt (~100 tokens)" },
          "relevance": { "type": "number", "minimum": 0, "maximum": 1, "description": "BM25 relevance score (normalized)" },
          "url": { "type": "string", "description": "Page URL — use read-page to fetch full content" },
          "section": { "type": "string", "description": "Documentation section path" }
        }
      }
    },
    "totalMatches": {
      "type": "number",
      "description": "Total matches found (may exceed maxResults)"
    }
  }
}
```

**Behavior:**
1. Verify library is known and has indexed documentation
2. If documentation not yet indexed, trigger JIT fetch + index, return `INDEXING_IN_PROGRESS`
3. Execute BM25 search across indexed chunks
4. Rank results by relevance score
5. Return top N results with snippets and URLs

**Design decision — results are references, not content**: `search-docs` returns snippets and URLs, not full page content. This keeps the response small (useful for the agent to scan), and the agent can use `read-page` on any result URL to get the full content. This is the "search narrows, agent reads" pattern from the competitive analysis.

**Error cases:**
- Library not indexed → `INDEXING_IN_PROGRESS` with `retryAfter`
- No results → empty results array (not an error — useful signal for the agent)

---

### 5.4 `read-page`

The **navigation path** tool. Fetches a specific documentation page URL and returns its content as markdown. This is the tool that enables agent-driven documentation browsing.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "url": {
      "type": "string",
      "description": "Documentation page URL to fetch. Must be from a resolved library's TOC, a search result, or a relatedPages entry."
    },
    "maxTokens": {
      "type": "number",
      "description": "Maximum tokens to return. Default: 10000. If the page exceeds this limit, content is truncated with a note indicating more content is available.",
      "default": 10000,
      "minimum": 500,
      "maximum": 50000
    }
  },
  "required": ["url"]
}
```

**Output Schema:**
```json
{
  "type": "object",
  "properties": {
    "content": {
      "type": "string",
      "description": "Page content in markdown format"
    },
    "title": {
      "type": "string",
      "description": "Page title"
    },
    "url": {
      "type": "string",
      "description": "Canonical URL of the fetched page"
    },
    "contentLength": {
      "type": "number",
      "description": "Total content length in estimated tokens"
    },
    "truncated": {
      "type": "boolean",
      "description": "Whether the content was truncated due to maxTokens"
    },
    "cached": {
      "type": "boolean",
      "description": "Whether this page was served from cache"
    }
  }
}
```

**Behavior:**
1. Validate URL against the allowlist (see Security, Section 10)
2. Check page cache (memory → SQLite) for this URL
3. If cached and fresh → return immediately
4. If not cached → fetch the URL
   - If URL ends in `.md` or is a known markdown endpoint → fetch directly
   - If URL is an llms.txt page reference → fetch and extract markdown
   - If URL is HTML → convert to markdown (strip nav, headers, footers)
5. Cache the content
6. If content exceeds `maxTokens`, truncate at a section boundary with a note: `[Content truncated. {remaining} tokens not shown. Call read-page again with a higher maxTokens limit to see more.]`
7. Return content

**URL allowlist**: `read-page` does not fetch arbitrary URLs. It only fetches URLs that:
- Appear in a resolved library's TOC
- Are returned by `search-docs` results
- Are from domains in the configured allowlist
- Match documentation domains from the known-libraries registry

This prevents SSRF while allowing flexible navigation within documentation.

**Design decision — higher default maxTokens (10,000)**: `read-page` has a higher default token limit than `get-docs` (10,000 vs 5,000) because when an agent navigates to a specific page, it has already judged relevance. The agent chose this page deliberately; the server should return the full content rather than truncating it. The agent can always read less by lowering `maxTokens`.

**Error cases:**
- URL not in allowlist → `URL_NOT_ALLOWED` with suggestion to resolve the library first
- URL returns 404 → `PAGE_NOT_FOUND`
- URL returns non-documentation content → `INVALID_CONTENT`

---

### 5.5 `list-libraries`

Lists available libraries with optional filtering. Includes curated libraries, cached libraries, and project-detected libraries.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "language": {
      "type": "string",
      "enum": ["python"],
      "description": "Filter by programming language."
    },
    "category": {
      "type": "string",
      "description": "Filter by category (e.g., 'ai', 'web', 'data', 'testing')"
    }
  },
  "required": []
}
```

**Output Schema:**
```json
{
  "type": "object",
  "properties": {
    "libraries": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "name": { "type": "string" },
          "description": { "type": "string" },
          "language": { "type": "string" },
          "defaultVersion": { "type": "string" },
          "categories": { "type": "array", "items": { "type": "string" } },
          "sources": { "type": "array", "items": { "type": "string" } },
          "projectDetected": { "type": "boolean", "description": "Whether this library was detected in the current project" }
        }
      }
    },
    "total": {
      "type": "number"
    }
  }
}
```

**Behavior:**
1. Merge three sources: known-libraries registry + previously-cached libraries + project-detected libraries
2. Apply filters (language, category)
3. Return sorted list, with project-detected libraries first

---

## 6. MCP Resource Definitions

Resources provide data that agents can access without tool calls. Pro-Context uses resources primarily for project-scoped TOCs and server health.

### 6.1 `pro-context://health`

**URI**: `pro-context://health`
**MIME Type**: `application/json`
**Description**: Server health status.

```json
{
  "status": "healthy",
  "uptime": 3600,
  "cache": {
    "memoryEntries": 142,
    "sqliteEntries": 1024,
    "hitRate": 0.87
  },
  "adapters": {
    "llms-txt": { "status": "available", "lastSuccess": "2026-02-12T10:00:00Z" },
    "github": { "status": "available", "rateLimitRemaining": 4850 }
  },
  "projectLibraries": ["langchain-ai/langchain", "pydantic/pydantic"],
  "version": "1.0.0"
}
```

### 6.2 `pro-context://libraries`

**URI**: `pro-context://libraries`
**MIME Type**: `application/json`
**Description**: List of project-detected libraries. Gives agents immediate awareness of the project's library stack without a tool call.

```json
{
  "libraries": [
    { "id": "langchain-ai/langchain", "name": "LangChain", "version": "0.3.14" },
    { "id": "pydantic/pydantic", "name": "Pydantic", "version": "2.10.0" }
  ],
  "detectedFrom": ["pyproject.toml"]
}
```

### 6.3 `library://{libraryId}/toc`

**URI Template**: `library://{libraryId}/toc`
**MIME Type**: `text/markdown`
**Description**: Table of contents for a specific library. Contains the same TOC data returned by `resolve-library`, but accessible as a resource for libraries that have already been resolved or were detected in the project.

This resource is dynamically registered:
- At startup, for project-detected libraries
- After `resolve-library` is called for any library

The TOC resource is formatted as markdown with links the agent can follow via `read-page`:

```markdown
# LangChain Documentation

## Getting Started
- [Introduction](https://docs.langchain.com/docs/introduction) — Overview of LangChain's architecture and concepts
- [Installation](https://docs.langchain.com/docs/installation) — How to install LangChain and its dependencies
- [Quick Start](https://docs.langchain.com/docs/quickstart) — Build your first LangChain application

## Chat Models
- [Chat Models Overview](https://docs.langchain.com/docs/chat-models) — Working with chat-based language models
- [Streaming](https://docs.langchain.com/docs/streaming) — Stream responses token by token
...
```

### 6.4 Dynamic Resource Registration

When the server resolves a new library (via `resolve-library` or project detection), it:

1. Registers `library://{libraryId}/toc` as a new resource
2. Emits a `notifications/resources/list_changed` notification per MCP spec
3. MCP clients that support resource subscriptions will see the new resource

This means the set of available library resources grows as the agent uses Pro-Context. A library resolved once remains available as a resource for the rest of the session.

---

## 7. MCP Prompt Templates

Prompt templates provide reusable workflows that agents can invoke. Updated to reference the new tool set.

### 7.1 `migrate-code`

**Name**: `migrate-code`
**Description**: Generate a migration plan for upgrading library code between versions.

**Arguments:**

| Name | Required | Description |
|------|----------|-------------|
| `libraryId` | Yes | Library to migrate |
| `fromVersion` | Yes | Current version |
| `toVersion` | Yes | Target version |
| `codeSnippet` | No | Code to migrate |

**Template:**
```
You are helping migrate code from {libraryId} version {fromVersion} to {toVersion}.

Steps:
1. Use resolve-library to get the documentation index for {libraryId}
2. Look for changelog, migration guide, or "what's new" pages in the TOC
3. Use read-page to fetch the relevant migration/changelog pages
4. If specific APIs in the code snippet need investigation, use get-docs or search-docs

{#if codeSnippet}
Migrate the following code:
```
{codeSnippet}
```
{/if}

Provide:
1. A list of breaking changes between {fromVersion} and {toVersion} that affect this code
2. The migrated code with explanations for each change
3. Any new features in {toVersion} that could improve this code
```

### 7.2 `debug-with-docs`

**Name**: `debug-with-docs`
**Description**: Debug an issue using current library documentation.

**Arguments:**

| Name | Required | Description |
|------|----------|-------------|
| `libraryId` | Yes | Library where the issue occurs |
| `errorMessage` | Yes | Error message or description |
| `codeSnippet` | No | Code that produces the error |

**Template:**
```
You are debugging an issue with {libraryId}.

Error: {errorMessage}

{#if codeSnippet}
Code:
```
{codeSnippet}
```
{/if}

Steps:
1. Use search-docs to find documentation related to this error message or the APIs involved
2. Use read-page on the most relevant search results to understand correct usage
3. If needed, use resolve-library to browse the TOC for related topics

Based on the documentation, identify:
1. The root cause of the error
2. The correct API usage (with documentation source)
3. A fixed version of the code
```

### 7.3 `explain-api`

**Name**: `explain-api`
**Description**: Explain a library API with current documentation and examples.

**Arguments:**

| Name | Required | Description |
|------|----------|-------------|
| `libraryId` | Yes | Library containing the API |
| `apiName` | Yes | API to explain (class, function, module) |
| `version` | No | Specific version |

**Template:**
```
Explain the {apiName} API from {libraryId}{#if version} (version {version}){/if}.

Steps:
1. Use get-docs to fetch documentation for {apiName}
2. If the result has low confidence or is incomplete, use the relatedPages or resolve-library TOC to find more specific pages
3. Use read-page on relevant pages to get complete API documentation
4. If needed, use search-docs to find related APIs or usage patterns

Provide:
1. What {apiName} does and when to use it
2. Complete parameter/argument documentation
3. Return value documentation
4. At least 2 practical examples from the documentation
5. Common pitfalls or gotchas
```

---

## 8. Documentation Source Priority and Adapter Chain

### 8.1 Priority Order

```
Request
  │
  ▼
[1] llms.txt ──── Best quality. Authored by library maintainers, structured for LLMs.
  │                Checks: {docsUrl}/llms.txt and {docsUrl}/llms-full.txt
  │ fail
  ▼
[2] GitHub ────── Universal fallback. Raw but authoritative.
  │                Fetches: /docs/ directory, README.md
  │ fail
  ▼
[3] Custom ────── User-configured. For internal/private docs.
  │                Sources: URLs, local files, private GitHub repos
  │ fail
  ▼
[4] Stale Cache ─ Last resort. Serves expired cache with stale: true warning.
  │ fail
  ▼
[Error] ───────── LIBRARY_NOT_FOUND or SOURCE_UNAVAILABLE with recovery suggestions.
```

### 8.2 llms.txt Adapter Behavior

The llms.txt adapter operates differently depending on the tool being used:

**For `resolve-library` (TOC):**
1. Fetch `{docsUrl}/llms.txt`
2. Parse the markdown index into structured TOC entries (title, URL, description, section)
3. Cache the parsed TOC

**For `get-docs` (content search):**
1. If `llms-full.txt` is available and not too large (<100K tokens), use it as the content source
2. Otherwise, use individual page URLs from the TOC + `read-page` behavior to fetch specific pages
3. Chunk content, index with BM25, search by topic

**For `read-page` (specific page):**
1. If the URL is a documentation page from an llms.txt TOC entry:
   - Try `{url}.md` first (Mintlify pattern — returns clean markdown)
   - If `.md` fails, fetch the URL directly
   - If HTML, convert to markdown
2. Cache the page content

### 8.3 GitHub Adapter Behavior

**For `resolve-library` (TOC):**
1. Fetch repository structure via GitHub API
2. If `/docs/` directory exists, list its contents as TOC entries
3. If no `/docs/`, parse README.md headings as TOC entries
4. Generate TOC with GitHub raw URLs

**For `get-docs` and `search-docs`:**
1. Fetch documentation files from the repository
2. For `/docs/` directory: fetch all markdown files
3. For README-only: fetch README.md
4. Chunk and index the content

**For `read-page`:**
1. Fetch the raw file from GitHub at the resolved version tag
2. Return as markdown

### 8.4 Custom Adapter Behavior

Custom sources are configured in `pro-context.config.yaml`:

```yaml
sources:
  custom:
    - name: "internal-sdk"
      type: "url"                # "url" | "file" | "github"
      url: "https://internal.docs.company.com/sdk/llms.txt"
      libraryId: "company/internal-sdk"
    - name: "local-docs"
      type: "file"
      path: "/path/to/docs/llms.txt"
      libraryId: "local/my-library"
```

Custom sources follow the same llms.txt or file-based patterns.

---

## 9. Version Resolution

### 9.1 Resolution Rules

1. **Explicit version** (`version: "0.3.14"`): Use exactly that version
2. **Version range** (`version: "0.3.x"`): Resolve to latest patch via package registry
3. **No version**: Resolve to latest stable release
4. **Invalid version**: Return `VERSION_NOT_FOUND` with available versions

### 9.2 Package Registry Integration

| Language | Registry | API |
|----------|----------|-----|
| Python | PyPI | `GET https://pypi.org/pypi/{package}/json` |
| JavaScript (future) | npm | `GET https://registry.npmjs.org/{package}` |

### 9.3 Version → Documentation URL Mapping

This is one of the harder problems. Different documentation sites handle versioning differently:

| Pattern | Example | Libraries |
|---------|---------|-----------|
| Version in URL path | `docs.pydantic.dev/2.10/llms.txt` | Pydantic |
| "latest" URL always current | `docs.langchain.com/llms.txt` | LangChain |
| Subdomain per version | `v3.fastapi.tiangolo.com/` | Some projects |
| No versioned docs | Single version only | Many smaller libs |

The known-libraries registry stores the URL pattern for each library, including how to construct versioned documentation URLs. For libraries not in the registry, the server falls back to the latest/default documentation URL.

### 9.4 Version Caching

- Version lists: cached for 1 hour (versions change infrequently)
- Documentation content: cached per exact version (v0.2.5 and v0.3.0 are separate entries)
- TOC: cached per version, refreshed when version list changes

---

## 10. Security

### 10.1 URL Allowlist (SSRF Prevention)

`read-page` fetches URLs provided by the agent. To prevent SSRF:

**Default allowlist:**
- `github.com`, `raw.githubusercontent.com`
- `*.github.io`
- `pypi.org`, `registry.npmjs.org`
- `*.readthedocs.io`
- Documentation domains from the known-libraries registry
- Domains from any llms.txt file the server has fetched

**Always blocked:**
- Private IPs (127.0.0.1, 10.x, 172.16-31.x, 192.168.x)
- `file://` URLs
- Non-HTTP(S) protocols

**Dynamic allowlist expansion:**
When the server fetches an llms.txt file, all URLs in that file are added to the session allowlist. This means if LangChain's llms.txt links to `docs.langchain.com/some/page`, that URL becomes fetchable via `read-page` — without the user needing to configure it.

Custom source domains from config are also added to the allowlist.

### 10.2 Input Validation

All tool inputs are validated with Zod schemas at the MCP boundary:
- `libraryId`: alphanumeric + `-_./`, max 200 chars
- `topic`, `query`: max 500 chars
- `url`: must be valid URL, must pass allowlist check
- `version`: max 50 chars
- Numeric parameters: validated against min/max ranges

### 10.3 Authentication (HTTP Mode)

- API keys use `pc_` prefix + 40 chars base64url
- Keys are stored as SHA-256 hashes (never plaintext)
- Bearer token authentication via `Authorization` header
- Admin CLI for key creation, listing, revocation

### 10.4 Rate Limiting (HTTP Mode)

- Token bucket algorithm per API key
- Configurable capacity and refill rate
- Rate limit headers in responses (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`)
- Per-key rate limit overrides

---

## 11. Error Handling

### 11.1 Error Response Format

```json
{
  "code": "ERROR_CODE",
  "message": "Human-readable description.",
  "recoverable": true,
  "suggestion": "Actionable advice for what to do next.",
  "retryAfter": 5
}
```

### 11.2 Error Catalog

| Code | Trigger | Suggestion |
|------|---------|-----------|
| `LIBRARY_NOT_FOUND` | Unknown library query | Did you mean '{suggestion}'? |
| `VERSION_NOT_FOUND` | Invalid version | Available versions: {list} |
| `TOPIC_NOT_FOUND` | BM25 search finds nothing for topic | Try search-docs for broader results, or browse the TOC with read-page. |
| `PAGE_NOT_FOUND` | read-page URL returns 404 | Check the URL or use resolve-library to refresh the TOC. |
| `URL_NOT_ALLOWED` | read-page URL fails allowlist check | Resolve the library first, or add the domain to your config. |
| `SOURCE_UNAVAILABLE` | All adapters fail, no cache | Try again later. |
| `REGISTRY_TIMEOUT` | PyPI/npm unreachable | Try again or specify the library ID directly. |
| `RATE_LIMITED` | Token bucket exhausted | Try again after {retryAfter} seconds. |
| `INDEXING_IN_PROGRESS` | Docs being fetched/indexed | Try again in {retryAfter} seconds. |
| `AUTH_REQUIRED` | Missing API key (HTTP mode) | Provide API key via Authorization header. |
| `AUTH_INVALID` | Bad/revoked API key | Check your API key. |
| `INVALID_CONTENT` | Fetched URL is not documentation | URL does not appear to contain documentation. |
| `INTERNAL_ERROR` | Unexpected server error | This has been logged. Try again. |

### 11.3 Recovery Flows

**Network failure:**
```
Source fetch fails → Retry 2x with exponential backoff (1s, 3s)
  → All retries fail + cache exists → Serve stale cache (stale: true)
  → No cache → SOURCE_UNAVAILABLE
```

**Unknown library with typo:**
```
resolve-library("langchan") → No exact match
  → Fuzzy match (Levenshtein distance ≤ 3) → "langchain"
  → LIBRARY_NOT_FOUND with suggestion
```

**Low-confidence get-docs result:**
```
get-docs returns content with confidence < 0.5
  → Response includes relatedPages from TOC
  → Agent can use read-page to explore related pages for better content
```

---

## 12. Configuration

### 12.1 Configuration File: `pro-context.config.yaml`

```yaml
# Server
server:
  transport: stdio             # "stdio" | "http"
  port: 3100                   # HTTP port (http transport only)
  host: "127.0.0.1"           # HTTP bind address

# Project detection
project:
  autoDetect: true             # Scan working directory for project files
  workingDirectory: "."        # Directory to scan (defaults to CWD)
  libraryOverrides: {}         # Per-library config (see below)

# Cache
cache:
  directory: "~/.pro-context/cache"
  maxMemoryMB: 100
  maxMemoryEntries: 500
  defaultTTLHours: 24
  cleanupIntervalMinutes: 60

# Documentation sources
sources:
  llmsTxt:
    enabled: true
    preferFullTxt: false       # If true, try llms-full.txt first (large but complete)
  github:
    enabled: true
    token: ""                  # GitHub PAT (optional, increases rate limit from 60 to 5000/hr)
  custom: []

# Per-library overrides
# These override auto-detected settings for specific libraries
project:
  libraryOverrides:
    langchain:
      docsUrl: "https://docs.langchain.com"
      ttlHours: 12
    fastapi:
      docsUrl: "https://fastapi.tiangolo.com"
      source: "github"         # Force GitHub adapter (no llms.txt available)
      ttlHours: 48

# Rate limiting (HTTP mode only)
rateLimit:
  maxRequestsPerMinute: 60
  burstSize: 10

# Logging
logging:
  level: "info"                # "debug" | "info" | "warn" | "error"
  format: "json"               # "json" | "pretty"

# Security (HTTP mode only)
security:
  cors:
    origins: ["*"]
  urlAllowlist: []             # Additional allowed domains for read-page
```

### 12.2 Environment Variable Overrides

| Config Key | Environment Variable | Example |
|-----------|---------------------|---------|
| `server.transport` | `PRO_CONTEXT_TRANSPORT` | `http` |
| `server.port` | `PRO_CONTEXT_PORT` | `3100` |
| `cache.directory` | `PRO_CONTEXT_CACHE_DIR` | `/data/cache` |
| `sources.github.token` | `PRO_CONTEXT_GITHUB_TOKEN` | `ghp_xxx` |
| `logging.level` | `PRO_CONTEXT_LOG_LEVEL` | `debug` |
| — | `PRO_CONTEXT_DEBUG=true` | Shorthand for `debug` level |

---

## 13. Language and Source Extensibility

### 13.1 Language Extensibility

Pro-Context is language-agnostic at the data model level. Language-specific behavior is isolated in registry resolvers.

**Current**: Python (PyPI registry)
**Future**: JavaScript/TypeScript (npm), Rust (crates.io), Go (pkg.go.dev)

Adding a new language requires:
1. A registry resolver (e.g., `npm-resolver.ts`) that implements version resolution
2. Known-library entries with `language: "javascript"`
3. No changes to adapters, cache, search, tools, or config

### 13.2 Source Extensibility

New documentation sources are added by implementing the `SourceAdapter` interface:
- `canHandle(library)` — can this adapter serve docs for this library?
- `fetchDocs(library, options)` — fetch documentation
- `fetchToc(library)` — fetch the table of contents
- `checkFreshness(library, cached)` — is the cache still valid?

Current adapters: llms-txt, github, custom

Future adapter candidates:
- HTML scraper (for docs sites without llms.txt or GitHub source)
- ReadTheDocs adapter
- PyPI long-description adapter

---

## 14. Design Decisions and Rationale

This section documents the key decisions made in this spec and why.

### D1: `read-page` replaces `get-examples`

**Decision**: Dropped the `get-examples` tool in favor of `read-page`.

**Rationale**: `get-examples` was a specialized content extraction tool — it fetched docs, found code blocks, and returned them. But modern AI agents are excellent at extracting code examples from documentation they read. What agents cannot do without a tool is navigate to a specific URL. `read-page` enables the entire navigation paradigm (the key insight from the competitive analysis), while `get-examples` solved a problem the agent can solve itself.

### D2: TOC included in `resolve-library` response

**Decision**: The `resolve-library` response includes the full table of contents, not just library metadata.

**Rationale**: The most common workflow is resolve → navigate. If the TOC requires a separate call, every agent interaction starts with 2 tool calls instead of 1. Since llms.txt indexes are typically small (under 10K tokens — Anthropic's is ~8,400), including them doesn't meaningfully inflate the response. The TOC is also registered as a resource for later access without tool calls.

### D3: `get-docs` includes `relatedPages`

**Decision**: The `get-docs` response includes links to related documentation pages.

**Rationale**: This bridges the fast path and navigation path. When BM25 returns a low-confidence result, the agent can see related pages and use `read-page` to explore them. Without this, the agent would need to call `resolve-library` again to get the TOC, then reason about which pages to read. `relatedPages` provides a natural "continue exploring" affordance.

### D4: `search-docs` returns references, not content

**Decision**: Search results contain snippets and URLs, not full page content.

**Rationale**: Search is for narrowing. The agent scans search results to identify promising pages, then uses `read-page` to get full content for the most relevant ones. Returning full content for 5 search results would be 5x the tokens — most of which would be irrelevant. The snippet is enough for the agent to judge relevance.

### D5: Project auto-detection with resource pre-loading

**Decision**: Auto-detect project libraries from `pyproject.toml`/`requirements.txt` and pre-load their TOCs as MCP resources.

**Rationale**: The zero-config experience matters for individual developers. If the server knows the project uses LangChain and Pydantic, it can pre-resolve these libraries and make their TOCs available as resources. The agent starts the session knowing which libraries are available without any tool calls.

### D6: Dynamic URL allowlist via llms.txt

**Decision**: When the server fetches an llms.txt file, all URLs listed in it are added to the session allowlist.

**Rationale**: llms.txt files contain curated links to documentation pages. These links are trustworthy because they come from the library's official documentation site. Automatically allowing them means the agent can navigate any page referenced in the TOC without the user needing to configure domains manually. This is essential for the navigation path to work without friction.

### D7: `read-page` default maxTokens is 10,000 (vs 5,000 for `get-docs`)

**Decision**: Higher default token limit for `read-page`.

**Rationale**: When the agent calls `read-page`, it has already made a relevance judgment — it picked this specific page from the TOC or search results. Truncating at 5,000 tokens would often cut off important content on longer pages. 10,000 tokens accommodates most individual documentation pages while still being a reasonable context budget.

---

## 15. Open Questions

### Q1: Should `read-page` support offset-based pagination?

For very long documentation pages (>10K tokens), should `read-page` accept an `offset` parameter to read from a specific position? This would enable true "scrolling" behavior. The alternative is simply raising `maxTokens` — but that wastes context on content the agent has already seen if it needs to re-read.

**My lean**: Yes, but defer to a later version. Truncation with a note is sufficient for v1.

### Q2: Should `resolve-library` accept a `libraryId` directly (bypass fuzzy matching)?

Currently `resolve-library` takes a `query` string and always does fuzzy matching. If the agent already has a `libraryId` (from a previous call, from a resource, from search results), should it be able to pass it directly to skip the matching step?

**My lean**: Yes — add an optional `libraryId` parameter that bypasses fuzzy matching and goes straight to version resolution + TOC fetch. This is a performance optimization for the common case where the agent already knows the exact library.

### Q3: How large can the TOC realistically get?

For libraries with extensive documentation (Cloudflare, AWS SDK), the llms.txt index could have hundreds of entries. Should we cap the TOC size in the `resolve-library` response? If so, what's the threshold?

**My lean**: Cap at 100 entries in the response. If the llms.txt has more, return the top 100 (prioritizing sections most likely to be queried) and include a `tocTruncated: true` flag. The full TOC remains available via the resource.

### Q4: Should we support `llms-full.txt` at all, or only the index + per-page pattern?

`llms-full.txt` can be enormous (Cloudflare: 3.7M tokens). It doesn't fit in a context window and must be chunked/indexed. The per-page pattern (llms.txt index + read individual pages) is more aligned with the agent navigation paradigm. However, `llms-full.txt` is useful for BM25 indexing — it's one file containing all content.

**My lean**: Use `llms-full.txt` only for server-side indexing (the `get-docs` and `search-docs` BM25 pipeline). Never return it directly to the agent. For agent navigation, always use the index + per-page pattern. This gives us the best of both: BM25 search over the full corpus, and navigable pages for the agent.

### Q5: What happens when multiple libraries match a query?

If `resolve-library("pydantic")` could match both `pydantic/pydantic` and `pydantic/pydantic-ai`, should we return the best match or ask for disambiguation?

**My lean**: Return the best match (highest similarity score) and include alternative matches in the response as `alternatives: [{id, name, description}]`. The agent can decide whether the alternatives are relevant.
