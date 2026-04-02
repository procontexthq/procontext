# ProContext: API Reference

> **Document**: 04-api-reference.md
> **Status**: Draft v2
> **Last Updated**: 2026-03-21
> **Depends on**: 01-functional-spec.md, 02-technical-spec.md

---

## Table of Contents

- [1. Protocol Overview](#1-protocol-overview)
  - [1.1 Transport & Framing](#11-transport--framing)
  - [1.2 Initialization Handshake](#12-initialization-handshake)
  - [1.3 Calling a Tool](#13-calling-a-tool)
  - [1.4 Tool Errors vs Protocol Errors](#14-tool-errors-vs-protocol-errors)
- [2. Tool: resolve_library](#2-tool-resolve_library)
  - [2.1 Input Schema](#21-input-schema)
  - [2.2 Output Schema](#22-output-schema)
  - [2.3 Examples](#23-examples)
  - [2.4 Error Cases](#24-error-cases)
- [3. Tool: read_page](#3-tool-read_page)
  - [3.1 Input Schema](#31-input-schema)
  - [3.2 Output Schema](#32-output-schema)
  - [3.3 Examples](#33-examples)
  - [3.4 Error Cases](#34-error-cases)
- [4. Tool: search_page](#4-tool-search_page)
  - [4.1 Input Schema](#41-input-schema)
  - [4.2 Output Schema](#42-output-schema)
  - [4.3 Examples](#43-examples)
  - [4.4 Error Cases](#44-error-cases)
- [5. Tool: read_outline](#5-tool-read_outline)
  - [5.1 Input Schema](#51-input-schema)
  - [5.2 Output Schema](#52-output-schema)
  - [5.3 Examples](#53-examples)
  - [5.4 Error Cases](#54-error-cases)
- [6. Resource: session/libraries](#6-resource-sessionlibraries)
  - [6.1 URI](#61-uri)
  - [6.2 Schema](#62-schema)
  - [6.3 Example](#63-example)
- [7. Error Reference](#7-error-reference)
  - [7.1 Error Envelope](#71-error-envelope)
  - [7.2 Error Code Catalogue](#72-error-code-catalogue)
- [8. Transport Reference](#8-transport-reference)
  - [8.1 stdio Transport](#81-stdio-transport)
  - [8.2 HTTP Transport](#82-http-transport)
- [9. Versioning Policy](#9-versioning-policy)

---

## 1. Protocol Overview

### 1.1 Transport & Framing

ProContext implements the [Model Context Protocol](https://modelcontextprotocol.io) (MCP) over JSON-RPC 2.0. All messages are UTF-8 JSON.

**stdio transport**: Each message is a single JSON object terminated by a newline (`\n`). Input is read from stdin; output is written to stdout. No HTTP headers, no framing beyond newline delimiters.

**HTTP transport**: JSON-RPC messages are sent as HTTP POST to `/mcp`. Server-sent events (SSE) are streamed as HTTP GET from `/mcp`. Session identity is tracked via the `MCP-Session-Id` header.

Both transports expose the identical set of tools. MCP resources are planned but not yet implemented (see Section 6).

---

### 1.2 Initialization Handshake

> **Note**: The initialization handshake is part of the MCP protocol specification and is handled automatically by the MCP SDK. ProContext does not implement this manually — it is documented here for the benefit of MCP client developers who need to understand the wire protocol.

Every MCP session begins with an `initialize` → `initialized` exchange. Clients must complete this before calling any tools.

**Client → Server** (`initialize`):

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-11-25",
    "capabilities": {},
    "clientInfo": {
      "name": "claude-code",
      "version": "1.0.0"
    }
  }
}
```

**Server → Client** (response):

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-11-25",
    "capabilities": {
      "tools": {},
      "resources": {}
    },
    "instructions": "Use ProContext tools in this order: 1. Call resolve_library first...",
    "serverInfo": {
      "name": "procontext",
      "version": "0.1.0"
    }
  }
}
```

**Client → Server** (`notifications/initialized`):

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized"
}
```

After `notifications/initialized` is received, the server is ready to handle tool calls and resource reads.

The `instructions` field provides detailed server-wide guidance for using the toolset together. ProContext instructions are advisory rather than mandatory, and include:

- **Core workflow**: `resolve_library` returns the documentation index URL, which is then explored via `read_page` to browse the index structure. Links found in pages lead to deeper documentation.
- **Outline navigation**: Both `read_page` and `search_page` return compacted outlines with line numbers for jumping to sections. `read_outline` provides full pagination when compacted outlines are too large.
- **Input formatting**: `resolve_library` accepts plain library names without version specifiers. `read_page` and `search_page` accept URLs from `resolve_library` or discovered within pages.
- **Search strategy**: Use `search_page` when searching for a known keyword; use `read_page` to browse structure; use `read_outline` for full pagination of large pages.
- **Performance**: Calls to the same page are cached (< 100ms), making pagination and repeated reads safe and efficient.

**Supported protocol versions**: `2025-11-25`, `2025-03-26`. If the client requests an unsupported version via the `MCP-Protocol-Version` header (HTTP mode), the server returns HTTP 400.

---

### 1.3 Calling a Tool

All tools are invoked via the `tools/call` JSON-RPC method.

**Request**:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "<tool-name>",
    "arguments": {}
  }
}
```

**Success response** — tool result is returned as a text content block:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "<JSON string of tool output>"
      }
    ]
  }
}
```

The `text` field is a JSON-encoded string. Clients parse it to get the structured output object.

**Listing available tools** (`tools/list`):

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```

---

### 1.4 Tool Errors vs Protocol Errors

There are two distinct error channels:

**Tool-level errors** — business logic failures (unknown library, SSRF block, fetch failure). These are returned inside the MCP `result` envelope with `isError: true`. The agent receives the error and can take corrective action.

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"error\": {\"code\": \"PAGE_NOT_FOUND\", \"message\": \"...\", \"suggestion\": \"...\", \"recoverable\": false}}"
      }
    ],
    "isError": true
  }
}
```

**Protocol-level errors** — malformed JSON-RPC, unknown methods, invalid params before tool dispatch. These use the JSON-RPC `error` field:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "error": {
    "code": -32600,
    "message": "Invalid Request"
  }
}
```

Tool authors and MCP client implementors need to handle both. The agent should only ever encounter tool-level errors during normal operation.

---

## 2. Tool: resolve_library

**Purpose**: Resolve a library name or package identifier to a known documentation source. Always call this first to obtain the library's documentation URLs for use with `read_page` and `search_page`.

### 2.1 Input Schema

```json
{
  "name": "resolve_library",
  "description": "Resolve a library name, package name, or alias to a known documentation source. Returns zero or more matches with documentation URLs. Always the first step — provides the index_url used with read_page and search_page, and packages entries with readme_url and repo_url.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Plain library name, package name, display name, or alias. Examples: 'langchain', 'langchain-openai', 'LangChain', 'Babel Core'.",
        "minLength": 3,
        "maxLength": 500
      },
      "language": {
        "type": ["string", "null"],
        "default": null,
        "description": "Optional language preference (e.g. 'python', 'javascript'). When provided, results are sorted so libraries matching the preferred language appear first. Does not filter — all matches are still returned."
      }
    },
    "required": ["query"]
  }
}
```

**Preprocessing applied before matching**: package lookup trims outer whitespace and lowercases the query; text and fuzzy lookup trim, lowercase, and collapse repeated internal whitespace. Dependency specifiers, tags, extras, and source refs are not rewritten.

**Matching order**:

1. Dependency/source-spec input → immediate empty `matches` list plus `UNSUPPORTED_QUERY_SYNTAX`
2. Exact package lookup against published package names
3. Exact text lookup against library IDs, display names, and aliases
4. Merge and deduplicate exact hits, with package hits ordered before text hits
5. Levenshtein fuzzy match (score threshold: 70%) only if the merged exact set is empty; attach `FUZZY_FALLBACK_USED`
6. No match → empty `matches` list

All matching is in-memory. No network calls.

### 2.2 Output Schema

```json
{
  "type": "object",
  "properties": {
    "matches": {
      "type": "array",
      "description": "Ranked list of matching libraries. Empty array if no match found.",
      "items": {
        "type": "object",
        "properties": {
          "library_id": {
            "type": "string",
            "description": "Stable identifier for the library.",
            "pattern": "^[a-z0-9][a-z0-9_-]*$"
          },
          "name": {
            "type": "string",
            "description": "Human-readable display name."
          },
          "description": {
            "type": "string",
            "description": "Short description of what the library does. May be empty for older registry entries."
          },
          "index_url": {
            "type": "string",
            "description": "URL to the library's llms.txt documentation index. Pass to read_page to browse the table of contents, or to search_page to find specific topics."
          },
          "full_docs_url": {
            "type": ["string", "null"],
            "description": "URL to the library's merged full documentation (llms-full.txt). May be null when the registry does not advertise a merged full-docs page."
          },
          "packages": {
            "type": "array",
            "description": "Package ecosystem entries. Languages, README URLs, and repository URLs live here.",
            "items": {
              "type": "object",
              "properties": {
                "ecosystem": {
                  "type": "string",
                  "enum": ["pypi", "npm", "conda", "jsr"],
                  "description": "Package ecosystem."
                },
                "languages": {
                  "type": "array",
                  "items": { "type": "string" },
                  "description": "Languages for this package ecosystem entry, e.g. ['python']."
                },
                "package_names": {
                  "type": "array",
                  "items": { "type": "string" },
                  "description": "Package names in this ecosystem, e.g. ['langchain', 'langchain-core']."
                },
                "readme_url": {
                  "type": ["string", "null"],
                  "description": "URL to the library's README file (typically raw content from GitHub). May be null."
                },
                "repo_url": {
                  "type": ["string", "null"],
                  "description": "URL to the source repository. May be null."
                }
              },
              "required": ["ecosystem", "languages", "package_names", "readme_url", "repo_url"]
            }
          },
          "matched_via": {
            "type": "string",
            "enum": ["package_name", "library_id", "name", "alias", "fuzzy"],
            "description": "How the match was made."
          },
          "relevance": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Match confidence. 1.0 for exact matches; proportional to edit distance for fuzzy matches."
          }
        },
        "required": [
          "library_id",
          "name",
          "description",
          "index_url",
          "full_docs_url",
          "packages",
          "matched_via",
          "relevance"
        ]
      }
    },
    "hint": {
      "type": ["object", "null"],
      "description": "Optional actionable guidance for recoverable non-error cases. Omitted or null for ordinary exact results, ordinary no-match, and exact multi-match results.",
      "properties": {
        "code": {
          "type": "string",
          "enum": ["UNSUPPORTED_QUERY_SYNTAX", "FUZZY_FALLBACK_USED"]
        },
        "message": {
          "type": "string"
        }
      },
      "required": ["code", "message"]
    }
  },
  "required": ["matches"]
}
```

### 2.3 Examples

**Exact package name match**:

Request arguments:

```json
{ "query": "langchain-openai" }
```

Result (`text` field, parsed):

```json
{
  "matches": [
    {
      "library_id": "langchain",
      "name": "LangChain",
      "description": "Framework for building LLM-powered applications.",
      "index_url": "https://python.langchain.com/llms.txt",
      "packages": [
        {
          "ecosystem": "pypi",
          "languages": ["python"],
          "package_names": ["langchain", "langchain-core", "langchain-openai"],
          "readme_url": "https://raw.githubusercontent.com/langchain-ai/langchain/master/README.md",
          "repo_url": "https://github.com/langchain-ai/langchain"
        }
      ],
      "matched_via": "package_name",
      "relevance": 1.0
    }
  ]
}
```

**Exact display name match**:

Request arguments:

```json
{ "query": "Babel Core" }
```

Result:

```json
{
  "matches": [
    {
      "library_id": "babel-core",
      "name": "Babel Core",
      "description": "JavaScript compiler core package.",
      "index_url": "https://babeljs.io/llms.txt",
      "packages": [
        {
          "ecosystem": "npm",
          "languages": ["javascript", "typescript"],
          "package_names": ["@babel/core"],
          "readme_url": null,
          "repo_url": null
        }
      ],
      "matched_via": "name",
      "relevance": 1.0
    }
  ]
}
```

**Source-spec / GitHub-like input**:

Request arguments:

```json
{ "query": "https://github.com/openai/openai-python" }
```

Result:

```json
    {
      "matches": [],
      "hint": {
        "code": "UNSUPPORTED_QUERY_SYNTAX",
        "message": "Provide only the published package name, library ID, display name, or alias without version specifiers, extras, tags, or source URLs."
      }
    }
```

**Fuzzy match (typo)**:

Request arguments:

```json
{ "query": "fasapi" }
```

Result:

```json
  {
    "matches": [
    {
      "library_id": "fastapi",
      "name": "FastAPI",
      "description": "Modern Python web framework for building APIs.",
      "index_url": "https://docs.fastapi.tiangolo.com/llms.txt",
      "packages": [
        {
          "ecosystem": "pypi",
          "languages": ["python"],
          "package_names": ["fastapi"],
          "readme_url": null,
          "repo_url": null
        }
      ],
      "matched_via": "fuzzy",
      "relevance": 0.92
    }
  ],
  "hint": {
    "code": "FUZZY_FALLBACK_USED",
    "message": "No exact match was found. Verify the fuzzy match before continuing."
  }
}
```

**No match**:

Request arguments:

```json
{ "query": "xyzzy-nonexistent" }
```

Result:

```json
{
  "matches": []
}
```

An empty `matches` list is a valid, non-error outcome. The library is simply not in the registry unless a `hint` explains a recoverable input issue.

### 2.4 Error Cases

`resolve_library` does not raise tool-level errors for recoverable lookup outcomes. An unrecognised library returns an empty list. Recoverable unsupported-input cases may return a `hint` instead of an error. The only failure path is `INVALID_INPUT` if the input fails Pydantic validation (e.g. query under 3 characters or over 500 characters).

---

## 3. Tool: read_page

**Purpose**: Fetch any documentation URL — llms.txt indexes, README files, or documentation pages. Returns a compacted structural outline (≤50 entries) and a windowed slice of content. Before fetch and cache lookup, the server applies minimal URL normalization: trim outer whitespace, lowercase scheme and host, and remove default ports while preserving path, query string, fragment, and trailing slash. If the URL does not end with `.md`, the server tries the `.md` variant first only when the URL passes the existing probe heuristic and its normalized origin exactly matches one of the `useful_md_probe_base_urls` loaded from the optional registry additional-info sidecar. On any probe failure (404, timeout, network error) it falls back to the normalized URL. A 200 HTML response from the `.md` probe is accepted as-is. If the sidecar is missing or invalid, `.md` probing is disabled. `.md` is never appended to redirect targets.

### 3.1 Input Schema

```json
{
  "name": "read_page",
  "description": "Fetch a documentation page, llms.txt index, or README from a URL. Returns a compacted outline (≤50 entries) and a content window. The outline lists H1–H6 headings with line numbers. Use outline line numbers to jump to sections with offset. For pages with very large outlines, use read_outline for paginated browsing. Use search_page to find specific content by keyword.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "url": {
        "type": "string",
      "description": "URL to read. Typically from resolve_library output (index_url, or readme_url from a packages entry) or from links found in a documentation index. Must use http or https. Must be a domain from the library registry. Before fetch and cache lookup, the server applies minimal normalization: trim outer whitespace, lowercase scheme and host, and remove default ports. Path, query string, fragment, and trailing slash are preserved. If the URL does not end with .md, the server tries url+\".md\" first; on any failure it falls back to the normalized URL.",
        "maxLength": 2048
      },
      "offset": {
        "type": "integer",
        "minimum": 1,
        "default": 1,
        "description": "1-based line number to start reading from. Defaults to 1. Use a heading's line number to jump directly to that section."
      },
      "limit": {
        "type": "integer",
        "minimum": 1,
        "default": 500,
        "description": "Maximum number of lines to return from the offset. Defaults to 500."
      },
      "before": {
        "type": "integer",
        "minimum": 0,
        "default": 0,
        "description": "Number of extra lines to include before offset for backward context. Defaults to 0."
      },
      "include_outline": {
        "type": "boolean",
        "default": true,
        "description": "When false, omit the outline from the response and return outline as null. Useful when paginating and the outline is already known."
      }
    },
    "required": ["url"]
  }
}
```

**Navigation workflow**:
1. Call `read_page` to get the compacted outline and the first 500 lines.
2. Find the heading closest to the section you need and note its line number.
3. Call again with `offset=<that line number>` to read the section.
4. Add `before` when you need some backward context before that line without reducing the forward `limit`.
5. Set `include_outline=false` on later pagination calls if you already have the page structure and want to save tokens.

For pages where the outline is replaced by a status message (very large pages), use `read_outline` to browse the full outline with pagination.

### 3.2 Output Schema

```json
{
  "type": "object",
  "properties": {
    "url": {
      "type": "string",
      "description": "The normalized URL used for fetch and cache identity. Path, query string, fragment, and trailing slash are preserved, so '/page' and '/page/' remain distinct."
    },
    "outline": {
      "type": ["string", "null"],
      "description": "Compacted structural outline of the page (target ≤50 entries and the configured read_page outline character budget). Progressive depth reduction removes lower-priority headings. When the page outline is too large even after maximum compaction, contains a status message directing to read_outline. Each entry formatted as '<line_number>:<emitted outline text>'; ATX headings and fence markers preserve the source line, while supported setext headings are normalized to synthetic '#'/ '##' entries. Null when include_outline=false."
    },
    "total_lines": {
      "type": "integer",
      "description": "Total number of lines in the full page. Always present."
    },
    "offset": {
      "type": "integer",
      "description": "The 1-based line number the returned content actually starts from after applying before."
    },
    "limit": {
      "type": "integer",
      "description": "The maximum number of forward lines requested from the input offset."
    },
    "content": {
      "type": "string",
      "description": "Page markdown for the returned window. When before > 0, this includes backward context before the input offset."
    },
    "has_more": {
      "type": "boolean",
      "description": "True if more content exists beyond the current window."
    },
    "next_offset": {
      "type": ["integer", "null"],
      "description": "Line number to pass as offset to continue reading. Null if no more content."
    },
    "content_hash": {
      "type": "string",
      "description": "Truncated SHA-256 (12 hex chars) of the full page content. Compare across paginated calls to detect content changes."
    },
    "cached": { "type": "boolean" },
    "cached_at": { "type": ["string", "null"], "format": "date-time" },
    "stale": { "type": "boolean", "description": "True if the cache entry has expired. A background refresh has been triggered. Content is stale but usable." }
  },
  "required": ["url", "outline", "total_lines", "offset", "limit", "content", "has_more", "next_offset", "content_hash", "cached", "cached_at", "stale"]
}
```

**Outline compaction**: The outline is compacted to ≤50 entries and the configured `read_page` outline character budget by progressively removing lower-priority headings (H6 → H5 → fenced content → H4 → H3). If even H1/H2 exceed either limit, the field contains a status message. The full outline and content are cached together so subsequent calls with different offsets don't re-fetch.

**Cache sharing**: `read_page`, `search_page`, and `read_outline` share the same `page_cache`. A page fetched by any tool is immediately available to the others without a re-fetch.

### 3.3 Examples

**Reading an llms.txt index** (URL from `resolve_library`):

Request arguments:

```json
{ "url": "https://python.langchain.com/llms.txt" }
```

Result:

```json
{
  "url": "https://python.langchain.com/llms.txt",
  "outline": "1:# Docs by LangChain\n3:## Concepts\n15:## How-to Guides\n28:## API Reference",
  "total_lines": 45,
  "offset": 1,
  "limit": 500,
  "content": "# Docs by LangChain\n\n## Concepts\n\n- [Chat Models](https://docs.langchain.com/docs/concepts/chat_models.md): Interface for language models...\n...",
  "has_more": false,
  "next_offset": null,
  "content_hash": "a1b2c3d4e5f6",
  "cached": false,
  "cached_at": null,
  "stale": false
}
```

**Jump to a section using offset**:

Request arguments:

```json
{ "url": "https://docs.langchain.com/docs/concepts/streaming.md", "offset": 18, "limit": 10 }
```

Result:

```json
{
  "url": "https://docs.langchain.com/docs/concepts/streaming.md",
  "outline": "1:# Streaming\n3:## Overview\n12:## Streaming with Chat Models\n18:### Using .stream()\n27:### Using .astream()\n35:## Streaming with Chains",
  "total_lines": 42,
  "offset": 18,
  "limit": 10,
  "content": "### Using .stream()\n\nThe `.stream()` method returns an iterator...\n...",
  "has_more": true,
  "next_offset": 28,
  "content_hash": "a1b2c3d4e5f6",
  "cached": true,
  "cached_at": "2026-02-23T10:00:00Z",
  "stale": false
}
```

**Read a section with backward context**:

Request arguments:

```json
{ "url": "https://docs.langchain.com/docs/concepts/streaming.md", "offset": 18, "before": 4, "limit": 10 }
```

Result:

```json
{
  "url": "https://docs.langchain.com/docs/concepts/streaming.md",
  "outline": "1:# Streaming\n3:## Overview\n12:## Streaming with Chat Models\n18:### Using .stream()\n27:### Using .astream()\n35:## Streaming with Chains",
  "total_lines": 42,
  "offset": 14,
  "limit": 10,
  "content": "...\n### Using .stream()\n\nThe `.stream()` method returns an iterator...\n...",
  "has_more": true,
  "next_offset": 28,
  "content_hash": "a1b2c3d4e5f6",
  "cached": true,
  "cached_at": "2026-02-23T10:00:00Z",
  "stale": false
}
```

### 3.4 Error Cases

| Condition                                | Error code           | `recoverable` |
| ---------------------------------------- | -------------------- | ------------- |
| URL domain not in allowlist              | `URL_NOT_ALLOWED`    | `false`       |
| URL scheme not http/https                | `INVALID_INPUT`      | `false`       |
| HTTP 404 for the URL                     | `PAGE_NOT_FOUND`     | `false`       |
| Network error or non-200/404 response (excluding redirect exhaustion) | `PAGE_FETCH_FAILED` | `true`        |
| Redirect chain exceeding 3 hops         | `TOO_MANY_REDIRECTS` | `false`       |
| Redirect hop targets a private IP range  | `URL_NOT_ALLOWED`   | `false`       |
| URL over 2048 characters                 | `INVALID_INPUT`      | `false`       |
| `offset` < 1, `limit` < 1, or `before` < 0 | `INVALID_INPUT`   | `false`       |

**`URL_NOT_ALLOWED` example**:

```json
{
  "error": {
    "code": "URL_NOT_ALLOWED",
    "message": "URL 'https://internal.example.com/docs' is not permitted.",
    "suggestion": "Only URLs from known documentation domains are allowed. Use resolve_library to find valid documentation URLs.",
    "recoverable": false
  }
}
```

---

## 4. Tool: search_page

**Purpose**: Search within a documentation page for lines matching a query. In `target="content"` mode, returns page content matches plus outline context. In `target="outline"` mode, searches stored outline entries only and returns matching outline lines. The agent uses the returned line numbers to inspect context with `read_page` or `read_outline`.

This tool is the equivalent of `grep` for documentation pages. It supports literal keyword search, regex patterns, smart case sensitivity, and word boundary matching.

### 4.1 Input Schema

```json
{
  "name": "search_page",
  "description": "Search within a documentation page for lines matching a query. target='content' searches page content and returns outline context. target='outline' searches stored outline entries only. Matches are returned with page line numbers in both modes. Supports literal and regex search, smart case sensitivity, and word boundary matching.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "url": {
        "type": "string",
      "description": "URL of the page to search. Same URLs accepted by read_page — llms.txt indexes, README files, or documentation pages. The same minimal URL normalization as read_page is applied before fetch and cache lookup.",
        "maxLength": 2048
      },
      "query": {
        "type": "string",
        "description": "Search term or regex pattern.",
        "minLength": 1,
        "maxLength": 200
      },
      "target": {
        "type": "string",
        "enum": ["content", "outline"],
        "default": "content",
        "description": "\"content\": search page content lines. \"outline\": search stored outline entries only."
      },
      "mode": {
        "type": "string",
        "enum": ["literal", "regex"],
        "default": "literal",
        "description": "\"literal\": exact substring match. \"regex\": treat query as a regular expression."
      },
      "case_mode": {
        "type": "string",
        "enum": ["smart", "insensitive", "sensitive"],
        "default": "smart",
        "description": "\"smart\" (default): lowercase query → case-insensitive; mixed/uppercase query → case-sensitive. \"insensitive\": always case-insensitive. \"sensitive\": always case-sensitive."
      },
      "whole_word": {
        "type": "boolean",
        "default": false,
        "description": "When true, match only at word boundaries. Prevents 'api' from matching 'rapid' or 'capital'."
      },
      "offset": {
        "type": "integer",
        "minimum": 1,
        "default": 1,
        "description": "1-based line number to start searching from. Use for paginating through results."
      },
      "max_results": {
        "type": "integer",
        "minimum": 1,
        "default": 20,
        "description": "Maximum number of matching lines to return."
      }
    },
    "required": ["url", "query"]
  }
}
```

**Smart case** (default): If the query string is entirely lowercase, matching is case-insensitive. If the query contains any uppercase character, matching is case-sensitive. This mirrors ripgrep's default behaviour — searching `"redis"` finds `"Redis"`, `"REDIS"`, and `"redis"`; searching `"Redis"` finds only `"Redis"`.

### 4.2 Output Schema

```json
{
  "type": "object",
  "properties": {
    "url": {
      "type": "string",
      "description": "The normalized URL that was searched."
    },
    "query": {
      "type": "string",
      "description": "The search query as provided."
    },
    "outline": {
      "type": ["string", "null"],
      "description": "Structural outline context for content-mode search results. Null when target='outline' because outline context is not applicable in that mode. On oversized pages with matches, the returned outline prepends the active ancestor heading chain immediately preceding the first match. Content-mode search uses a tighter default outline character budget than read_page."
    },
    "matches": {
      "type": "string",
      "description": "Matching lines formatted as '<line_number>:<content>', one per line. In outline mode, these are matching outline entries in the same format. Empty string when no matches found."
    },
    "total_lines": {
      "type": "integer",
      "description": "Total number of lines in the page."
    },
    "has_more": {
      "type": "boolean",
      "description": "True if more matches exist beyond the returned set."
    },
    "next_offset": {
      "type": ["integer", "null"],
      "description": "Line number to pass as offset for the next search call to continue paginating. Null if no more matches."
    },
    "content_hash": {
      "type": "string",
      "description": "Truncated SHA-256 (12 hex chars) of the full page content. Compare across calls to detect content changes."
    },
    "cached": { "type": "boolean" },
    "cached_at": { "type": ["string", "null"], "format": "date-time" }
  },
  "required": ["url", "query", "outline", "matches", "total_lines", "has_more", "next_offset", "content_hash", "cached", "cached_at"]
}
```

### 4.3 Examples

**Search an llms.txt index for a topic**:

Request arguments:

```json
{ "url": "https://python.langchain.com/llms.txt", "query": "streaming" }
```

Result:

```json
{
  "url": "https://python.langchain.com/llms.txt",
  "query": "streaming",
  "outline": "3:## Concepts\n15:## How-to Guides",
  "matches": "7:- [Streaming](https://docs.langchain.com/docs/concepts/streaming.md): Stream model outputs as they are generated.\n22:- [How to stream responses](https://docs.langchain.com/docs/how_to/streaming.md): Step-by-step guide to streaming.",
  "total_lines": 45,
  "has_more": false,
  "next_offset": null,
  "content_hash": "a1b2c3d4e5f6",
  "cached": true,
  "cached_at": "2026-02-23T10:00:00Z"
}
```

**Search stored outline entries**:

Request arguments:

```json
{ "url": "https://python.langchain.com/docs/concepts/streaming.md", "query": "Chat Models", "target": "outline" }
```

Result:

```json
{
  "url": "https://python.langchain.com/docs/concepts/streaming.md",
  "query": "Chat Models",
  "outline": null,
  "matches": "7:## Streaming with Chat Models",
  "total_lines": 21,
  "has_more": false,
  "next_offset": null,
  "content_hash": "a1b2c3d4e5f6",
  "cached": true,
  "cached_at": "2026-02-23T10:00:00Z"
}
```

**Regex search with word boundaries**:

Request arguments:

```json
{ "url": "https://docs.pydantic.dev/concepts/models.md", "query": "model", "whole_word": true }
```

Result:

```json
{
  "url": "https://docs.pydantic.dev/concepts/models.md",
  "query": "model",
  "outline": "1:# Models\n5:## Defining a Model",
  "matches": "1:# Models\n5:## Defining a Model\n7:A Pydantic model is a class that inherits from BaseModel.",
  "total_lines": 65,
  "has_more": true,
  "next_offset": 8,
  "content_hash": "b2c3d4e5f6a1",
  "cached": true,
  "cached_at": "2026-02-23T11:00:00Z"
}
```

**Paginated search (continuation)**:

Request arguments:

```json
{ "url": "https://docs.pydantic.dev/concepts/models.md", "query": "model", "whole_word": true, "offset": 8 }
```

Result contains the next batch of matches starting from line 8.

### 4.4 Error Cases

| Condition                                | Error code           | `recoverable` |
| ---------------------------------------- | -------------------- | ------------- |
| URL domain not in allowlist              | `URL_NOT_ALLOWED`    | `false`       |
| URL scheme not http/https                | `INVALID_INPUT`      | `false`       |
| HTTP 404 for the URL                     | `PAGE_NOT_FOUND`     | `false`       |
| Network error or non-200/404 response    | `PAGE_FETCH_FAILED`  | `true`        |
| Redirect chain exceeding 3 hops         | `TOO_MANY_REDIRECTS` | `false`       |
| URL over 2048 characters                 | `INVALID_INPUT`      | `false`       |
| Empty query                              | `INVALID_INPUT`      | `false`       |
| Query over 200 characters                | `INVALID_INPUT`      | `false`       |
| Invalid regex pattern (when `mode="regex"`) | `INVALID_INPUT`   | `false`       |
| `offset` < 1 or `max_results` < 1       | `INVALID_INPUT`      | `false`       |

---

## 5. Tool: read_outline

**Purpose**: Browse the full structural outline of a documentation page using page-line windowing. Use when `read_page` or `search_page` return an outline status message indicating the page outline is too large, or to explore page structure without fetching content.

### 5.1 Input Schema

```json
{
  "name": "read_outline",
  "description": "Browse the full structural outline of a documentation page using page-line windowing. Each entry shows a heading or fence marker with its line number in the page content. Use when read_page returns an outline status message for very large pages, or to explore page structure without fetching content.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "url": {
        "type": "string",
      "description": "URL of the page. Same URLs accepted by read_page. The same minimal URL normalization as read_page is applied before fetch and cache lookup.",
        "maxLength": 2048
      },
      "offset": {
        "type": "integer",
        "minimum": 1,
        "default": 1,
        "description": "1-based page line number to start browsing the outline from."
      },
      "limit": {
        "type": "integer",
        "minimum": 1,
        "default": 1000,
        "description": "Maximum forward page lines to include from offset."
      },
      "before": {
        "type": "integer",
        "minimum": 0,
        "default": 0,
        "description": "Number of extra page lines to include before offset for backward outline context."
      }
    },
    "required": ["url"]
  }
}
```

### 5.2 Output Schema

```json
{
  "type": "object",
  "properties": {
    "url": {
      "type": "string",
      "description": "The normalized URL of the page."
    },
    "outline": {
      "type": "string",
      "description": "Paginated outline entries in '<line_number>:<emitted outline text>' format, joined by newlines. ATX headings and fence markers preserve the source line, while supported setext headings are normalized to synthetic '#'/ '##' entries."
    },
    "total_entries": {
      "type": "integer",
      "description": "Total number of entries in the full outline (after stripping empty fences)."
    },
    "has_more": {
      "type": "boolean",
      "description": "True if more entries exist beyond the current window."
    },
    "next_offset": {
      "type": ["integer", "null"],
      "description": "Page line number to pass as offset to continue browsing. Null if no more outline entries exist beyond the returned window."
    },
    "content_hash": {
      "type": "string",
      "description": "Truncated SHA-256 (12 hex chars) of the full page content. Compare across paginated calls to detect content changes."
    },
    "cached": { "type": "boolean" },
    "cached_at": { "type": ["string", "null"], "format": "date-time" },
    "stale": { "type": "boolean", "description": "True if the cache entry has expired. A background refresh has been triggered. Content is stale but usable." }
  },
  "required": ["url", "outline", "total_entries", "has_more", "next_offset", "content_hash", "cached", "cached_at", "stale"]
}
```

### 5.3 Examples

**Browse the outline of a large API reference**:

Request arguments:

```json
{ "url": "https://docs.langchain.com/docs/api_reference.md" }
```

Result:

```json
{
  "url": "https://docs.langchain.com/docs/api_reference.md",
  "outline": "1:# API Reference\n5:## Authentication\n12:### API Keys\n28:### OAuth\n45:## Endpoints\n...",
  "total_entries": 847,
  "has_more": true,
  "next_offset": 1001,
  "content_hash": "a1b2c3d4e5f6",
  "cached": true,
  "cached_at": "2026-02-23T10:00:00Z",
  "stale": false
}
```

**Browse outline context around a line**:

Request arguments:

```json
{ "url": "https://docs.langchain.com/docs/api_reference.md", "offset": 200, "before": 40, "limit": 120 }
```

Result:

```json
{
  "url": "https://docs.langchain.com/docs/api_reference.md",
  "outline": "165:## Authentication\n188:### API Keys\n214:### OAuth",
  "total_entries": 847,
  "has_more": true,
  "next_offset": 320,
  "content_hash": "a1b2c3d4e5f6",
  "cached": true,
  "cached_at": "2026-02-23T10:00:00Z",
  "stale": false
}
```

**Paginated continuation**:

Request arguments:

```json
{ "url": "https://docs.langchain.com/docs/api_reference.md", "offset": 1001 }
```

Result contains entries 1001+ with pagination metadata.

### 5.4 Error Cases

| Condition                                | Error code           | `recoverable` |
| ---------------------------------------- | -------------------- | ------------- |
| URL domain not in allowlist              | `URL_NOT_ALLOWED`    | `false`       |
| URL scheme not http/https                | `INVALID_INPUT`      | `false`       |
| HTTP 404 for the URL                     | `PAGE_NOT_FOUND`     | `false`       |
| Network error or non-200/404 response    | `PAGE_FETCH_FAILED`  | `true`        |
| Redirect chain exceeding 3 hops         | `TOO_MANY_REDIRECTS` | `false`       |
| URL over 2048 characters                 | `INVALID_INPUT`      | `false`       |
| `offset` < 1 or `limit` < 1             | `INVALID_INPUT`      | `false`       |

---

## 6. Resource: session/libraries

> **Status**: Planned — not yet implemented. The server currently registers no MCP resources. This section documents the intended design for a future release.

### 6.1 URI

```
procontext://session/libraries
```

### 6.2 Schema

Read via `resources/read`:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "resources/read",
  "params": {
    "uri": "procontext://session/libraries"
  }
}
```

Response:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "contents": [
      {
        "uri": "procontext://session/libraries",
        "mimeType": "application/json",
        "text": "<JSON string>"
      }
    ]
  }
}
```

The `text` field (parsed):

```json
{
  "type": "object",
  "properties": {
    "resolved_libraries": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "library_id": { "type": "string" },
          "name": { "type": "string" },
          "resolved_at": { "type": "string", "format": "date-time" }
        },
        "required": ["library_id", "name", "resolved_at"]
      }
    }
  },
  "required": ["resolved_libraries"]
}
```

### 6.3 Example

```json
{
  "resolved_libraries": [
    {
      "library_id": "langchain",
      "name": "LangChain",
      "resolved_at": "2026-02-23T10:00:00Z"
    },
    {
      "library_id": "pydantic",
      "name": "Pydantic",
      "resolved_at": "2026-02-23T10:05:00Z"
    }
  ]
}
```

**Purpose**: Allows the agent to recall which libraries have already been resolved in the current session, without re-calling `resolve_library`. Empty list at session start. Populated by each successful `resolve_library` call.

**Listing available resources** (`resources/list`):

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "resources/list",
  "params": {}
}
```

Response:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "resources": [
      {
        "uri": "procontext://session/libraries",
        "name": "Session Libraries",
        "description": "Libraries resolved in the current session.",
        "mimeType": "application/json"
      }
    ]
  }
}
```

---

## 7. Error Reference

### 7.1 Error Envelope

All tool-level errors share the same envelope:

```json
{
  "error": {
    "code": "<ErrorCode>",
    "message": "<human-readable description>",
    "suggestion": "<actionable next step for the agent>",
    "recoverable": true | false
  }
}
```

| Field         | Type    | Description                                                                    |
| ------------- | ------- | ------------------------------------------------------------------------------ |
| `code`        | string  | Machine-readable error code (see table below)                                  |
| `message`     | string  | What went wrong, in plain language                                             |
| `suggestion`  | string  | What the agent should do next                                                  |
| `recoverable` | boolean | Whether retrying the same request might succeed (e.g. transient network error) |

This envelope is returned inside the MCP `result` content with `isError: true` — not as a JSON-RPC protocol error.

### 7.2 Error Code Catalogue

| Code                    | Raised by                    | Description                                                                                    | `recoverable` |
| ----------------------- | ---------------------------- | ---------------------------------------------------------------------------------------------- | ------------- |
| `PAGE_NOT_FOUND`        | `read_page`, `search_page`, `read_outline` | HTTP 404 for the requested URL                                                                 | `false`       |
| `PAGE_FETCH_FAILED`     | `read_page`, `search_page`, `read_outline` | Network error, timeout, or non-200/404 HTTP response (excluding redirect exhaustion)           | `true`        |
| `TOO_MANY_REDIRECTS`    | `read_page`, `search_page`, `read_outline` | Redirect chain exceeded the 3-hop safety limit                                                 | `false`       |
| `URL_NOT_ALLOWED`       | `read_page`, `search_page`, `read_outline` | Initial URL domain is not in the SSRF allowlist, or any hop targets a private IP range         | `false`       |
| `INVALID_INPUT`         | Any tool                     | Input failed Pydantic validation (query too short, URL too long, invalid regex pattern, etc.)  | `false`       |

**On `recoverable: true`**: The same request may succeed if retried after a brief delay. Network errors and upstream failures are the typical cause. The agent should inform the user rather than retry indefinitely.

**On `recoverable: false`**: Retrying the identical request will not succeed. The agent must take a different action (e.g. use `resolve_library` to find valid documentation URLs, or check the URL is from a known documentation domain).

---

## 8. Transport Reference

### 8.1 stdio Transport

**How it works**: The MCP client spawns ProContext as a subprocess. Messages are newline-delimited JSON over stdin/stdout. stderr is reserved for structured log output (does not affect the JSON-RPC stream).

**MCP client configuration** (Claude Code, Cursor, Windsurf):

```json
{
  "mcpServers": {
    "procontext": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/procontext", "procontext"]
    }
  }
}
```

> **Note**: Once published to PyPI this simplifies to `"command": "uvx", "args": ["procontext"]`.

**With a local config file**:

Place `procontext.yaml` in the directory you run the command from, or in the platform config directory (`platformdirs.user_config_dir("procontext")`). There is no `--config` CLI flag — the config file is discovered automatically.

```json
{
  "mcpServers": {
    "procontext": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/procontext", "procontext"],
      "env": {
        "PROCONTEXT__CACHE__TTL_HOURS": "48"
      }
    }
  }
}
```

Settings can also be passed as environment variables using the `PROCONTEXT__` prefix with `__` as the nested delimiter.

**Process lifecycle**: The MCP client manages the process. ProContext exits when stdin is closed.

**No authentication**: stdio transport is inherently local. No API keys or tokens required.

---

### 8.2 HTTP Transport

**Endpoint**: `POST /mcp` for JSON-RPC requests, `GET /mcp` for SSE streams.

**Protocol**: MCP Streamable HTTP (spec 2025-11-25).

**Starting the server**:

```yaml
# procontext.yaml
server:
  transport: http
  host: "127.0.0.1"
  port: 8080
  auth_enabled: false
  auth_key: ""
```

```bash
uv run procontext
# or via env var (no config file needed):
PROCONTEXT__SERVER__TRANSPORT=http uv run procontext
```

**Request headers**:

| Header                 | Required             | Description                                                                                                                   |
| ---------------------- | -------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `Authorization`        | Conditional          | Required when `server.auth_enabled=true`. Format: `Bearer <key>`. Missing or incorrect key (when auth is enabled) → HTTP 401. |
| `Content-Type`         | Yes                  | `application/json`                                                                                                            |
| `MCP-Session-Id`       | Yes (after init)     | Session identifier returned in `initialize` response. Must be included on all subsequent requests in the session.             |
| `MCP-Protocol-Version` | Recommended          | `2025-11-25` or `2025-03-26`. Validated if present; unknown version → HTTP 400.                                               |
| `Origin`               | Browser clients only | Must be a loopback origin (`localhost`, `127.0.0.1`, `[::1]`, with optional port). Non-loopback origins → HTTP 403.          |

**Security constraints**:

1. **Optional bearer key authentication**: Authentication is controlled by `server.auth_enabled` (default `false`). If `auth_enabled=true`, HTTP requests must include `Authorization: Bearer <key>`. Missing or incorrect keys are rejected with HTTP 401. If `auth_enabled=true` and `server.auth_key` is empty, a key is auto-generated at startup and logged to stderr. If `auth_enabled=false`, authentication is disabled and a startup warning is logged. Configure via `server.auth_enabled` / `server.auth_key` in `procontext.yaml` or `PROCONTEXT__SERVER__AUTH_ENABLED` / `PROCONTEXT__SERVER__AUTH_KEY`. Stdio mode is unaffected — no authentication is required.

2. **Origin validation**: Requests with a non-loopback `Origin` header are rejected with HTTP 403. Loopback origins such as `http://localhost`, `http://127.0.0.1`, and `http://[::1]` are allowed. Requests without an `Origin` header (standard API clients, curl) are allowed.

3. **Protocol version validation**: If `MCP-Protocol-Version` is present and not in `{"2025-11-25", "2025-03-26"}`, the server returns HTTP 400.

4. **SSRF protection**: Applies to all documentation fetches, regardless of transport mode (see Section 7.2, `URL_NOT_ALLOWED`).

**Example POST request**:

Example below assumes `server.auth_enabled=true` and a key is configured or auto-generated:

```
POST /mcp HTTP/1.1
Host: localhost:8080
Authorization: Bearer <key>
Content-Type: application/json
MCP-Session-Id: sess_abc123
MCP-Protocol-Version: 2025-11-25

{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"resolve_library","arguments":{"query":"langchain"}}}
```

**SSE stream** (GET `/mcp`):

Used for server-initiated notifications. Connect once per session; the server sends events as they occur. Most clients use this for progress updates and push notifications. For simple request-response tool calls, the POST endpoint suffices.

---

## 9. Versioning Policy

### Server Version

ProContext follows [Semantic Versioning](https://semver.org) (`MAJOR.MINOR.PATCH`).

| Change type                            | Version bump |
| -------------------------------------- | ------------ |
| New tool or resource                   | MINOR        |
| New optional field in response         | MINOR        |
| Breaking change to input/output schema | MAJOR        |
| Bug fix, performance improvement       | PATCH        |
| Registry update (no server change)     | No bump      |

The server version is returned in the `initialize` response (`serverInfo.version`).

### MCP Protocol Version

ProContext supports two MCP protocol versions simultaneously:

| Version      | Status                    |
| ------------ | ------------------------- |
| `2025-11-25` | Supported (primary)       |
| `2025-03-26` | Supported (compatibility) |

When a new MCP specification version is published, ProContext adds support in the next MINOR release. The oldest supported version is dropped when it is no longer used by any major MCP client.

### Registry Version

The library registry (`known-libraries.json`) has its own version, independent of the server version. The registry is updated weekly on GitHub Pages. The server checks for registry updates in the background after startup, but it still requires a valid local registry pair on disk before it can start. Registry version changes never require a server update — the server is always forward-compatible with newer registry files.

The current registry version loaded by a running server instance is visible in the `server_started` log event (`registry_version` field). This value is sourced from `<data_dir>/registry/registry-state.json` (where `<data_dir>` is resolved by `platformdirs.user_data_dir("procontext")`) when a valid local registry pair is present. The same state file may also advertise an optional `additional-info.json` sidecar used to gate `.md` probing by exact normalized origin. If the local pair is missing or invalid (for example, first run before `procontext setup` has been run), startup exits with an error instructing the operator to run `procontext setup`.
