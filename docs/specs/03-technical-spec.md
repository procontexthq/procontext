# Pro-Context: Technical Specification

> **Document**: 03-technical-spec.md
> **Status**: Draft v2
> **Last Updated**: 2026-02-16
> **Depends on**: 02-functional-spec.md (v3)

---

## Table of Contents

- [1. System Architecture](#1-system-architecture)
  - [1.1 High-Level Architecture](#11-high-level-architecture)
  - [1.2 Request Flow](#12-request-flow)
- [2. Technology Stack](#2-technology-stack)
- [3. Data Models](#3-data-models)
  - [3.1 Core Types](#31-core-types)
  - [3.2 Cache Types](#32-cache-types)
  - [3.3 Auth Types (HTTP Mode)](#33-auth-types-http-mode)
  - [3.4 Configuration Types](#34-configuration-types)
- [4. Source Adapter Interface](#4-source-adapter-interface)
  - [4.1 Interface Definition](#41-interface-definition)
  - [4.2 Adapter Chain Execution](#42-adapter-chain-execution)
  - [4.3 Adapter Implementations](#43-adapter-implementations)
- [5. Cache Architecture](#5-cache-architecture)
  - [5.1 Two-Tier Cache Design](#51-two-tier-cache-design)
  - [5.2 Cache Domains](#52-cache-domains)
  - [5.3 Cache Manager](#53-cache-manager)
  - [5.4 Page Cache](#54-page-cache)
  - [5.5 Cache Key Strategy](#55-cache-key-strategy)
  - [5.6 Cache Invalidation Signals](#56-cache-invalidation-signals)
  - [5.7 Background Refresh](#57-background-refresh)
- [6. Search Engine Design](#6-search-engine-design)
  - [6.1 Document Chunking Strategy](#61-document-chunking-strategy)
  - [6.2 BM25 Search Implementation](#62-bm25-search-implementation)
  - [6.3 Cross-Library Search](#63-cross-library-search)
  - [6.4 Incremental Indexing](#64-incremental-indexing)
  - [6.5 Ranking and Token Budgeting](#65-ranking-and-token-budgeting)
- [7. Token Efficiency Strategy](#7-token-efficiency-strategy)
  - [7.1 Target Metrics](#71-target-metrics)
  - [7.2 Techniques](#72-techniques)
  - [7.3 Token Counting](#73-token-counting)
- [8. Transport Layer](#8-transport-layer)
  - [8.1 stdio Transport (Local Mode)](#81-stdio-transport-local-mode)
  - [8.2 Streamable HTTP Transport (HTTP Mode)](#82-streamable-http-transport-http-mode)
- [9. Authentication and API Key Management](#9-authentication-and-api-key-management)
  - [9.1 Key Generation](#91-key-generation)
  - [9.2 Key Validation Flow](#92-key-validation-flow)
  - [9.3 Admin CLI](#93-admin-cli)
- [10. Rate Limiting Design](#10-rate-limiting-design)
  - [10.1 Token Bucket Algorithm](#101-token-bucket-algorithm)
  - [10.2 Rate Limit Headers](#102-rate-limit-headers)
  - [10.3 Per-Key Overrides](#103-per-key-overrides)
- [11. Security Model](#11-security-model)
  - [11.1 Input Validation](#111-input-validation)
  - [11.2 SSRF Prevention](#112-ssrf-prevention)
  - [11.3 Secret Redaction](#113-secret-redaction)
  - [11.4 Content Sanitization](#114-content-sanitization)
- [12. Observability](#12-observability)
  - [12.1 Structured Logging](#121-structured-logging)
  - [12.2 Key Metrics](#122-key-metrics)
  - [12.3 Health Check](#123-health-check)
- [13. Extensibility Points](#13-extensibility-points)
  - [13.1 Adding a New Language](#131-adding-a-new-language)
  - [13.2 Adding a New Documentation Source](#132-adding-a-new-documentation-source)
  - [13.3 Adding a New Tool](#133-adding-a-new-tool)
- [14. Database Schema](#14-database-schema)
  - [14.1 SQLite Tables](#141-sqlite-tables)
  - [14.2 Database Initialization](#142-database-initialization)
  - [14.3 Cleanup Job](#143-cleanup-job)
- [15. Fuzzy Matching](#15-fuzzy-matching)

---

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    MCP Clients                          │
│  (Claude Code, Cursor, Windsurf, VS Code, custom)      │
└──────────────┬──────────────────────┬───────────────────┘
               │ stdio (local)        │ Streamable HTTP (remote)
               ▼                      ▼
┌─────────────────────────────────────────────────────────┐
│                  Pro-Context MCP Server                  │
│                                                         │
│  ┌─────────┐  ┌──────────┐  ┌────────────┐             │
│  │  Tools  │  │Resources │  │  Prompts   │             │
│  │  (5)    │  │  (2)     │  │  (3)       │             │
│  └────┬────┘  └────┬─────┘  └─────┬──────┘             │
│       │             │              │                     │
│  ┌────▼─────────────▼──────────────▼──────┐             │
│  │           Core Engine                   │             │
│  │                                         │             │
│  │  ┌──────────┐  ┌───────────────────┐   │             │
│  │  │ Resolver │  │  Search Engine    │   │             │
│  │  │ (lib ID) │  │  (BM25 ranking)  │   │             │
│  │  └────┬─────┘  └────────┬──────────┘   │             │
│  │       │                  │              │             │
│  │  ┌────▼──────────────────▼──────────┐   │             │
│  │  │       Source Adapters            │   │             │
│  │  │  ┌────────┐ ┌───────┐ ┌───────┐ │   │             │
│  │  │  │llms.txt│ │GitHub │ │Custom │ │   │             │
│  │  │  │Adapter │ │Adapter│ │Adapter│ │   │             │
│  │  │  └────────┘ └───────┘ └───────┘ │   │             │
│  │  └──────────────────────────────────┘   │             │
│  │                                         │             │
│  │  ┌──────────────────────────────────┐   │             │
│  │  │         Cache Layer              │   │             │
│  │  │  ┌──────────┐  ┌─────────────┐  │   │             │
│  │  │  │ Memory   │  │   SQLite    │  │   │             │
│  │  │  │ (LRU)    │  │ (persistent)│  │   │             │
│  │  │  └──────────┘  └─────────────┘  │   │             │
│  │  └──────────────────────────────────┘   │             │
│  └─────────────────────────────────────────┘             │
│                                                         │
│  ┌──────────────────────────────────────────┐           │
│  │  Infrastructure                           │           │
│  │  ┌────────┐ ┌────────┐ ┌──────────────┐  │           │
│  │  │ Logger │ │ Errors │ │ Rate Limiter │  │           │
│  │  │(struct)│ │        │ │              │  │           │
│  │  │  log   │ │        │ │              │  │           │
│  │  └────────┘ └────────┘ └──────────────┘  │           │
│  └──────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
```

### 1.2 Request Flow

```
MCP Client
  │
  ├─ resolve-library("langchain")
  │    │
  │    ├─ 1. Fuzzy match against known-libraries registry
  │    ├─ 2. If no match → query PyPI API
  │    ├─ 3. If still no match → return empty results
  │    └─ 4. Return ranked matches with { libraryId, name, languages, relevance }
  │
  ├─ get-library-info("langchain-ai/langchain")
  │    │
  │    ├─ 1. Look up libraryId in registry (exact match)
  │    ├─ 2. If not found → return LIBRARY_NOT_FOUND error
  │    ├─ 3. Fetch TOC via adapter chain (llms.txt → GitHub → Custom)
  │    ├─ 4. Extract availableSections from TOC
  │    ├─ 5. Apply sections filter if specified
  │    ├─ 6. Cache TOC, add to session resolved list
  │    └─ 7. Return { libraryId, sources, toc, availableSections }
  │
  ├─ get-docs([{libraryId: "langchain-ai/langchain"}], "chat models")
  │    │
  │    ├─ 1. For each library: validate libraryId
  │    ├─ 2. Cache lookup: memory LRU → SQLite
  │    │    ├─ HIT (fresh) → use cached content
  │    │    ├─ HIT (stale) → use cached + trigger background refresh
  │    │    └─ MISS → continue to step 3
  │    ├─ 3. Adapter chain: llms.txt → GitHub → Custom
  │    ├─ 4. Chunk raw content into sections
  │    ├─ 5. Rank chunks across all libraries by topic relevance (BM25)
  │    ├─ 6. Select top chunk(s) within maxTokens budget
  │    ├─ 7. Identify relatedPages from TOC
  │    ├─ 8. Store in cache (memory + SQLite)
  │    └─ 9. Return { libraryId, content, source, version, confidence, relatedPages }
  │
  ├─ search-docs("retry logic", libraryIds: ["langchain-ai/langchain"])
  │    │
  │    ├─ 1. Validate specified libraries exist and have indexed content
  │    ├─ 2. If no libraryIds → search across all indexed content
  │    ├─ 3. Execute BM25 query against indexed chunks
  │    ├─ 4. Rank results by relevance score
  │    └─ 5. Return top N results with { libraryId, snippet, url, relevance }
  │
  └─ read-page("https://docs.langchain.com/docs/streaming.md", offset: 0)
       │
       ├─ 1. Validate URL against allowlist
       ├─ 2. Check page cache for this URL
       │    ├─ HIT → serve from cache (apply offset/maxTokens)
       │    └─ MISS → fetch URL, convert to markdown, cache full page
       ├─ 3. Apply offset + maxTokens: return content slice
       ├─ 4. Index page content for BM25 (background)
       └─ 5. Return { content, totalTokens, offset, tokensReturned, hasMore }
```

---

## 2. Technology Stack

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| Language | Python | 3.12+ | Latest stable, per-interpreter GIL, improved error messages, asyncio improvements |
| Package manager | `uv` (recommended) | latest | 10-100x faster than pip, built-in lock files, better dependency resolution |
| MCP SDK | `mcp` | >=1.0.0,<2.0.0 | Official SDK, maintained by protocol authors |
| Schema validation | Pydantic | >=2.9.0,<3.0.0 | Runtime validation, excellent type integration, v2 Rust core for performance |
| Persistent cache | SQLite via `aiosqlite` | >=0.20.0,<1.0.0 | Async-friendly, zero-config, embedded, no external infra |
| In-memory cache | `cachetools` | >=5.3.0,<6.0.0 | TTL support, LRU eviction, simple async-compatible usage |
| HTTP client | `httpx` | >=0.27.0,<1.0.0 | Async-first, HTTP/2 support, timeout management |
| Search/ranking | BM25 via SQLite FTS5 | — | FTS5 for indexing + custom BM25 scoring; no embedding dependency |
| Logging | `structlog` | >=24.1.0,<25.0.0 | Structured logging, context binding, processor pipelines |
| Testing | `pytest` + `pytest-asyncio` | >=8.1.0,<9.0.0 / >=0.23.0,<1.0.0 | De facto standard, excellent async support, rich plugin ecosystem |
| Linting + Format | `ruff` | >=0.3.0,<1.0.0 | Extremely fast, replaces flake8/black/isort, pyproject.toml config |
| Type checking | `mypy` | >=1.9.0,<2.0.0 | Static type analysis, strict mode enforcement |
| YAML parsing | `pyyaml` | >=6.0.1,<7.0.0 | Standard library equivalent for config parsing |
| Fuzzy matching | `rapidfuzz` | >=3.6.0,<4.0.0 | Fast Levenshtein distance, C++ backend |

**Version Pinning Strategy**: All dependencies use SemVer-compatible ranges. Lower bounds represent minimum tested versions (latest at project start). Lock files (`uv.lock` + `requirements.txt`) pin exact versions for reproducible builds. See Implementation Guide (Doc 04) for detailed dependency management workflow.

### Dependency Justification

- **Python 3.12**: Latest stable release with per-interpreter GIL (better performance), improved error messages, asyncio improvements, all needed features.
- **`uv` over `pip`**: 10-100x faster installation, built-in lock file support, better dependency resolution. Fallback to `pip` + `pip-tools` for compatibility.
- **`aiosqlite` over `sqlite3`**: Async compatibility with `asyncio` event loop. Stdlib `sqlite3` blocks the event loop on writes.
- **`cachetools` over `functools.lru_cache`**: TTL support is essential for cache expiry. `functools.lru_cache` has no TTL mechanism.
- **`httpx` over `aiohttp`**: Cleaner API, better timeout handling, HTTP/2 support, sync/async unified interface.
- **`structlog` over stdlib `logging`**: Context binding (correlation IDs), structured output, processor pipelines for redaction.
- **No vector database**: BM25 handles keyword-heavy documentation search well without requiring an embedding model. Vector search deferred to future phase.
- **No Redis**: SQLite provides sufficient persistence for cache. No external infrastructure needed.
- **No web framework**: MCP SDK handles HTTP transport internally (Starlette under the hood). No FastAPI/Flask needed.

---

## 3. Data Models

### 3.1 Core Types

```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Literal

# ===== Library Types =====

@dataclass
class LibraryMatch:
    """Result from resolve-library query"""
    library_id: str  # Canonical identifier (e.g., "langchain-ai/langchain")
    name: str  # Human-readable name (e.g., "LangChain")
    description: str  # Brief description
    languages: list[str]  # Languages this library is available in
    relevance: float  # Match relevance score (0-1)


@dataclass
class Library:
    """Full library metadata"""
    id: str  # Canonical identifier
    name: str  # Human-readable name
    description: str  # Brief description
    languages: list[str]  # Languages this library is available in
    package_name: str  # Package name in registry (e.g., "langchain" on PyPI)
    docs_url: str | None  # Documentation site URL
    repo_url: str | None  # GitHub repository URL


# ===== TOC Types =====

@dataclass
class TocEntry:
    """Single entry in library table of contents"""
    title: str  # Page title
    url: str  # Page URL (can be passed to read-page)
    description: str  # One-sentence description
    section: str  # Section grouping (e.g., "Getting Started", "API Reference")


@dataclass
class LibraryInfo:
    """Library metadata + TOC from get-library-info"""
    library_id: str
    name: str
    languages: list[str]  # Informational metadata — not used for routing/validation
    sources: list[str]  # Documentation sources (e.g., ["llms.txt", "github"])
    toc: list[TocEntry]  # Full or filtered TOC
    available_sections: list[str]  # All unique section names in TOC
    filtered_by_sections: list[str] | None = None  # Sections filter applied


# ===== Documentation Types =====

@dataclass
class RelatedPage:
    """Reference to a related documentation page"""
    title: str
    url: str
    description: str


@dataclass
class DocResult:
    """Documentation content result from get-docs"""
    library_id: str  # Which library this content is from
    content: str  # Documentation content in markdown
    source: str  # URL where documentation was fetched from
    last_updated: datetime  # When documentation was last fetched/verified
    confidence: float  # Relevance confidence (0-1)
    cached: bool  # Whether result was served from cache
    stale: bool  # Whether cached content may be outdated
    related_pages: list[RelatedPage]  # Related pages the agent can explore


@dataclass
class DocChunk:
    """Indexed documentation chunk for search"""
    id: str  # Chunk identifier (hash)
    library_id: str  # Library this chunk belongs to
    title: str  # Section title/heading
    content: str  # Chunk content in markdown
    section_path: str  # Hierarchical path (e.g., "Getting Started > Chat Models")
    token_count: int  # Approximate token count
    source_url: str  # Source URL


@dataclass
class SearchResult:
    """Search result from search-docs"""
    library_id: str  # Which library this result is from
    title: str  # Section/page title
    snippet: str  # Relevant text excerpt
    relevance: float  # BM25 relevance score (0-1 normalized)
    url: str  # Source URL — use read-page to fetch full content
    section: str  # Documentation section path


# ===== Page Types =====

@dataclass
class PageResult:
    """Page content result from read-page"""
    content: str  # Page content in markdown
    title: str  # Page title
    url: str  # Canonical URL
    total_tokens: int  # Total page content length in estimated tokens
    offset: int  # Token offset this response starts from
    tokens_returned: int  # Number of tokens in this response
    has_more: bool  # Whether more content exists beyond this response
    cached: bool  # Whether page was served from cache


# ===== Error Types =====

class ErrorCode(str, Enum):
    """Error codes for ProContextError"""
    LIBRARY_NOT_FOUND = "LIBRARY_NOT_FOUND"
    TOPIC_NOT_FOUND = "TOPIC_NOT_FOUND"
    PAGE_NOT_FOUND = "PAGE_NOT_FOUND"
    URL_NOT_ALLOWED = "URL_NOT_ALLOWED"
    INVALID_CONTENT = "INVALID_CONTENT"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    NETWORK_FETCH_FAILED = "NETWORK_FETCH_FAILED"
    LLMS_TXT_NOT_FOUND = "LLMS_TXT_NOT_FOUND"
    STALE_CACHE_EXPIRED = "STALE_CACHE_EXPIRED"
    RATE_LIMITED = "RATE_LIMITED"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    AUTH_INVALID = "AUTH_INVALID"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class ProContextError(Exception):
    """Structured error with recovery information"""
    code: ErrorCode  # Machine-readable error code
    message: str  # Human-readable error description
    recoverable: bool  # Whether error can be resolved by retrying or changing input
    suggestion: str  # Actionable suggestion for the user/agent
    retry_after: int | None = None  # Seconds to wait before retrying (if applicable)
    details: dict | None = None  # Additional context (URLs, library names, etc.)
```

### 3.2 Cache Types

```python
@dataclass
class CacheEntry:
    """Entry in documentation cache (doc_cache table)"""
    key: str  # Cache key (SHA-256 hash)
    library_id: str  # Library identifier
    identifier: str  # Topic hash (for get-docs) or URL (for pages)
    content: str  # Cached content
    source_url: str  # Source URL
    content_hash: str  # Content SHA-256 hash (for freshness checking)
    fetched_at: datetime  # When this entry was created
    expires_at: datetime  # When this entry expires
    adapter: str  # Name of the adapter that produced this content


@dataclass
class PageCacheEntry:
    """Entry in page cache (page_cache table)"""
    url: str  # Page URL (cache key)
    content: str  # Full page content in markdown
    title: str  # Page title
    total_tokens: int  # Total content length in estimated tokens
    content_hash: str  # Content SHA-256 hash
    fetched_at: datetime  # When this page was fetched
    expires_at: datetime  # When this entry expires


@dataclass
class CacheStats:
    """Cache statistics for health check"""
    memory_entries: int  # Number of entries in memory cache
    memory_bytes: int  # Memory cache size in bytes
    sqlite_entries: int  # Number of entries in SQLite cache
    hit_rate: float  # Cache hit rate (0-1)
```

### 3.3 Auth Types (HTTP Mode)

```python
@dataclass
class ApiKey:
    """API key for HTTP authentication"""
    id: str  # Unique key identifier (UUID)
    name: str  # Display name for the key
    key_hash: str  # SHA-256 hash of the actual key (never store plaintext)
    key_prefix: str  # Key prefix for display (first 8 chars)
    rate_limit_per_minute: int | None  # Per-key rate limit (None = use default)
    created_at: datetime  # When this key was created
    last_used_at: datetime | None  # When this key was last used
    request_count: int  # Total number of requests made with this key
    active: bool  # Whether this key is active
```

### 3.4 Configuration Types

```python
from typing import Literal

@dataclass
class ServerConfig:
    """Server transport configuration"""
    transport: Literal["stdio", "http"]
    port: int
    host: str


@dataclass
class CacheConfig:
    """Cache configuration"""
    directory: str  # SQLite database directory
    max_memory_mb: int  # Memory cache size limit
    max_memory_entries: int  # Memory cache entry limit
    default_ttl_hours: int  # Default TTL for cache entries
    cleanup_interval_minutes: int  # Cleanup job interval


@dataclass
class CustomSource:
    """User-configured documentation source"""
    name: str
    type: Literal["url", "file", "github"]
    url: str | None = None
    path: str | None = None
    library_id: str
    ttl_hours: int | None = None


@dataclass
class SourcesConfig:
    """Documentation source configuration"""
    llms_txt: dict[str, bool]  # {"enabled": True}
    github: dict[str, bool | str]  # {"enabled": True, "token": "ghp_xxx"}
    custom: list[CustomSource]


@dataclass
class LibraryOverride:
    """Per-library configuration overrides"""
    docs_url: str | None = None
    source: str | None = None
    ttl_hours: int | None = None


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    max_requests_per_minute: int
    burst_size: int


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: Literal["debug", "info", "warn", "error"]
    format: Literal["json", "pretty"]


@dataclass
class SecurityConfig:
    """Security configuration"""
    cors: dict[str, list[str]]  # {"origins": ["*"]}
    url_allowlist: list[str]  # Domain patterns


@dataclass
class ProContextConfig:
    """Complete Pro-Context configuration"""
    server: ServerConfig
    cache: CacheConfig
    sources: SourcesConfig
    library_overrides: dict[str, LibraryOverride]
    rate_limit: RateLimitConfig
    logging: LoggingConfig
    security: SecurityConfig


# Note: PRO_CONTEXT_DEBUG=true env var sets logging.level to "debug"
# See functional spec section 12 for full env var override table
```

---

## 4. Source Adapter Interface

### 4.1 Interface Definition

```python
from abc import ABC, abstractmethod
from typing import Protocol

@dataclass
class RawPageContent:
    """Raw page content fetched by adapters"""
    content: str  # Page content in markdown
    title: str  # Page title (extracted from first heading or URL)
    source_url: str  # Canonical source URL
    content_hash: str  # Content SHA-256 hash
    etag: str | None = None  # ETag header value (if available)
    last_modified: str | None = None  # Last-Modified header (if available)


class SourceAdapter(ABC):
    """Abstract base class for documentation source adapters"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique adapter name (e.g., "llms-txt", "github", "custom")"""
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """Priority order (lower = higher priority)"""
        pass

    @abstractmethod
    async def can_handle(self, library: Library) -> bool:
        """
        Check if this adapter can serve documentation for the given library.
        Should be cheap (no network requests if possible).
        """
        pass

    @abstractmethod
    async def fetch_toc(self, library: Library) -> list[TocEntry] | None:
        """
        Fetch the table of contents for the given library.
        Returns structured TOC entries parsed from llms.txt, GitHub /docs/, etc.
        Always fetches the latest available documentation.
        """
        pass

    @abstractmethod
    async def fetch_page(self, url: str) -> RawPageContent | None:
        """
        Fetch a single documentation page and return markdown content.
        Used by read-page and internally by get-docs for JIT content fetching.
        """
        pass

    @abstractmethod
    async def check_freshness(self, library: Library, cached: CacheEntry) -> bool:
        """
        Check if the cached version is still fresh.
        Uses SHA comparison, ETags, or Last-Modified headers.
        Returns True if cache is still valid (no refetch needed).
        """
        pass
```

### 4.2 Adapter Chain Execution

```python
class AdapterChain:
    """Orchestrates fallback across multiple adapters"""

    def __init__(self, adapters: list[SourceAdapter]):
        # Sort by priority (lower = higher priority)
        self.adapters = sorted(adapters, key=lambda a: a.priority)

    async def fetch_toc(self, library: Library) -> list[TocEntry]:
        """Fetch TOC via adapter chain with fallback"""
        errors: list[Exception] = []

        for adapter in self.adapters:
            if not await adapter.can_handle(library):
                continue

            try:
                result = await adapter.fetch_toc(library)
                if result is not None:
                    return result
            except Exception as e:
                errors.append(e)

        raise AllAdaptersFailedError(errors)

    async def fetch_page(self, url: str) -> RawPageContent:
        """Fetch page via adapter chain with fallback"""
        errors: list[Exception] = []

        for adapter in self.adapters:
            try:
                result = await adapter.fetch_page(url)
                if result is not None:
                    return result
            except Exception as e:
                errors.append(e)

        raise AllAdaptersFailedError(errors)


class AllAdaptersFailedError(Exception):
    """Raised when all adapters fail to fetch content"""

    def __init__(self, errors: list[Exception]):
        self.errors = errors
        super().__init__(f"All adapters failed: {len(errors)} errors")
```

### 4.3 Adapter Implementations

#### llms.txt Adapter

```
canHandle(library):
  1. Check if library.docsUrl is set
  2. Return true if docsUrl is not null

fetchToc(library):
  1. Fetch {library.docsUrl}/llms.txt
  2. If 404, return null
  3. Parse markdown: extract ## headings as sections, list items as entries
  4. For each entry: extract title, URL, description
  5. Return TocEntry[]

fetchPage(url):
  1. Try {url}.md first (Mintlify pattern — returns clean markdown)
  2. If .md fails, fetch the URL directly
  3. If HTML response, convert to markdown (strip nav, headers, footers)
  4. Extract title from first heading
  5. Return { content, title, sourceUrl, contentHash }

checkFreshness(library, cached):
  1. HEAD request to source URL
  2. Compare ETag or Last-Modified headers
  3. If no headers available, compare content SHA
  4. Return true if cache is still valid
```

#### GitHub Adapter

```
canHandle(library):
  1. Check if library.repoUrl is set and is a GitHub URL
  2. Return true if valid GitHub repo

fetchToc(library):
  1. Fetch /docs/ directory listing from repo (default branch)
  3. If /docs/ exists → create TocEntry per file, using directories as sections
  4. If no /docs/ → parse README.md headings as TOC entries
  5. Generate GitHub raw URLs for each entry
  6. Return TocEntry[]

fetchPage(url):
  1. Fetch the raw file from GitHub (default branch)
  2. Return as markdown { content, title, sourceUrl, contentHash }

checkFreshness(library, cached):
  1. GET latest commit SHA from GitHub API
  2. Compare against cached SHA
  3. Return true if SHA matches (content unchanged)
```

#### Custom Adapter

```
canHandle(library):
  1. Check if library.id matches any custom source config
  2. Return true if match found

fetchToc(library):
  1. Determine source type (url, file, github)
  2. For "url": fetch URL, parse as llms.txt format
  3. For "file": read local file, parse as llms.txt format
  4. For "github": delegate to GitHub adapter logic
  5. Return TocEntry[]

fetchPage(url):
  1. Determine source type from URL/path
  2. For "url": fetch URL content
  3. For "file": read local file
  4. Return { content, title, sourceUrl, contentHash }

checkFreshness(library, cached):
  1. For "url": HEAD request + ETag/Last-Modified
  2. For "file": Check file modification time
  3. For "github": Compare commit SHA
  4. Return true if cache is still valid
```

---

## 5. Cache Architecture

### 5.1 Two-Tier Cache Design

```
Query → Memory LRU (Tier 1) → SQLite (Tier 2) → Source Adapters
         │                      │                   │
         ▼                      ▼                   ▼
      <1ms latency           <10ms latency       100ms-3s latency
      500 entries max        Unlimited             Network fetch
      1hr TTL (search)       24hr TTL (default)    Stored on return
      24hr TTL (docs/pages)  Configurable/library
```

### 5.2 Cache Domains

The cache stores three types of content:

| Domain | Key | Content | TTL |
|--------|-----|---------|-----|
| **TOC** | `toc:{libraryId}` | Parsed TocEntry[] | 24 hours |
| **Docs/Chunks** | `doc:{libraryId}:{topicHash}` | BM25-matched content | 24 hours |
| **Pages** | `page:{urlHash}` | Full page markdown | 24 hours |

Pages are cached separately because they're shared across tools — `read-page` and `get-docs` both benefit from cached pages.

### 5.3 Cache Manager

```python
from cachetools import TTLCache
from datetime import datetime

class CacheManager:
    """Two-tier cache orchestrator: memory (LRU) → SQLite → miss"""

    def __init__(self, memory_cache: TTLCache, sqlite_cache: SqliteCache):
        self.memory = memory_cache
        self.sqlite = sqlite_cache

    async def get(self, key: str) -> CacheEntry | None:
        """Get entry from cache (memory → SQLite → miss)"""
        # Tier 1: Memory
        mem_result = self.memory.get(key)
        if mem_result and not self._is_expired(mem_result):
            return mem_result

        # Tier 2: SQLite
        sql_result = await self.sqlite.get(key)
        if sql_result and not self._is_expired(sql_result):
            # Promote to memory cache
            self.memory[key] = sql_result
            return sql_result

        # Return stale entry if exists (caller decides whether to use it)
        return sql_result or mem_result or None

    async def set(self, key: str, entry: CacheEntry) -> None:
        """Write to both cache tiers"""
        self.memory[key] = entry
        await self.sqlite.set(key, entry)

    async def invalidate(self, key: str) -> None:
        """Remove entry from both cache tiers"""
        self.memory.pop(key, None)
        await self.sqlite.delete(key)

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry has expired"""
        return datetime.now() > entry.expires_at
```

### 5.4 Page Cache

Pages fetched by `read-page` are cached in full. Offset-based reads serve slices from the cached page without re-fetching.

```python
class PageCache:
    """Page-specific cache with offset-based slice support"""

    def __init__(self, memory_cache: TTLCache, sqlite_cache: SqlitePageCache):
        self.memory = memory_cache
        self.sqlite = sqlite_cache

    async def get_page(self, url: str) -> PageCacheEntry | None:
        """Get full page from cache (same two-tier pattern as CacheManager)"""
        # Tier 1: Memory
        mem_result = self.memory.get(url)
        if mem_result and not self._is_expired(mem_result):
            return mem_result

        # Tier 2: SQLite
        sql_result = await self.sqlite.get(url)
        if sql_result and not self._is_expired(sql_result):
            self.memory[url] = sql_result
            return sql_result

        return sql_result or mem_result or None

    async def get_slice(
        self, url: str, offset: int, max_tokens: int
    ) -> PageResult | None:
        """Get a slice of the page content at the given offset"""
        page = await self.get_page(url)
        if not page:
            return None

        # Estimate character positions from token counts (1 token ≈ 4 chars)
        start_char = offset * 4
        max_chars = max_tokens * 4
        slice_content = page.content[start_char : start_char + max_chars]
        tokens_returned = len(slice_content) // 4

        return PageResult(
            content=slice_content,
            title=page.title,
            url=url,
            total_tokens=page.total_tokens,
            offset=offset,
            tokens_returned=tokens_returned,
            has_more=start_char + max_chars < len(page.content),
            cached=True,
        )

    def _is_expired(self, entry: PageCacheEntry) -> bool:
        """Check if cache entry has expired"""
        return datetime.now() > entry.expires_at
```

### 5.5 Cache Key Strategy

```
TOC key:  SHA-256("toc:" + libraryId)
Doc key:  SHA-256("doc:" + libraryId + ":" + normalizedTopic)
Page key: SHA-256("page:" + url)
```

### 5.6 Cache Invalidation Signals

| Signal | Trigger | Action |
|--------|---------|--------|
| TTL expiry | Automatic | Entry marked stale; served with `stale: true` |
| SHA mismatch | `checkFreshness()` on read | Refetch from source, update cache |
| Manual invalidation | Admin CLI command | Delete entry from both tiers |
| Cleanup job | Scheduled (configurable interval) | Delete all expired entries from SQLite |

### 5.7 Background Refresh

When a stale cache entry is served, a background refresh is triggered:

```
1. Return stale content immediately (with stale: true)
2. Spawn background task:
   a. Fetch fresh content from adapter chain
   b. Compare content hash with cached
   c. If changed → update cache entry
   d. If unchanged → update expiresAt timestamp only
```

**Handling refresh failures:**

If background refresh fails (network error, site down, 404), the server:

1. **Keeps serving stale content** with `stale: true` flag
2. **Logs warning** with error details and next retry timestamp
3. **Continues retry attempts** on subsequent requests (with exponential backoff)
4. **Maximum stale age**: 7 days (configurable)
   - After 7 days without successful refresh, cache entry is invalidated
   - Next request triggers fresh fetch (not background)
   - If fresh fetch also fails, return `SOURCE_UNAVAILABLE` error

**Agent behavior recommendations:**
- `stale: false` → content is fresh, use confidently
- `stale: true` → content may be outdated but likely still accurate; agent can choose to:
  - Use the content (most cases)
  - Show warning to user ("documentation may be outdated")
  - Skip if absolute freshness required (rare)

---

## 6. Search Engine Design

### 6.1 Document Chunking Strategy

Raw documentation is chunked into focused sections for indexing and retrieval.

**Chunking algorithm:**

```
1. Parse markdown into AST (heading-aware)
2. Split on H1/H2/H3 headings → creates section boundaries
3. For each section:
   a. Estimate token count (chars / 4 approximation)
   b. If section > 1000 tokens → split on paragraphs
   c. If section > 2000 tokens → split on sentences with 200-token overlap
   d. If section < 100 tokens → merge with next section
4. For each chunk:
   a. Assign section path (e.g., "Getting Started > Chat Models > Streaming")
   b. Compute token count
   c. Extract title from nearest heading
   d. Generate chunk ID: SHA-256(libraryId + version + sectionPath + chunkIndex)
```

**Target chunk sizes:**

| Chunk Type | Target Tokens | Min | Max |
|-----------|--------------|-----|-----|
| Section chunk | 500 | 100 | 1,000 |
| Paragraph chunk (oversized sections) | 300 | 100 | 500 |
| Code example chunk | Variable | 50 | 2,000 |

### 6.2 BM25 Search Implementation

BM25 (Best Match 25) is used for keyword-based relevance ranking.

**Parameters:**
- `k1 = 1.5` (term frequency saturation)
- `b = 0.75` (document length normalization)

**Index structure:**

```
For each chunk:
  1. Tokenize content (lowercase, strip punctuation)
  2. Compute term frequencies (TF)
  3. Store in inverted index: term → [(chunkId, TF), ...]

Global:
  - Document count (N)
  - Average document length (avgDL)
  - Document frequencies (DF): term → count of docs containing term
```

**Query execution:**

```
1. Tokenize query
2. For each query term:
   a. Look up inverted index → get matching chunks with TF
   b. Compute IDF: log((N - DF + 0.5) / (DF + 0.5) + 1)
   c. For each matching chunk:
      - Compute BM25 score: IDF * (TF * (k1 + 1)) / (TF + k1 * (1 - b + b * DL/avgDL))
3. Sum BM25 scores across query terms for each chunk
4. Sort by total score (descending)
5. Normalize scores to 0-1 range
6. Return top N results
```

### 6.3 Cross-Library Search

When `search-docs` is called without `libraryIds`, it searches across all indexed content. The BM25 index contains chunks from all libraries, each tagged with their `libraryId`. Results are ranked globally — a highly relevant chunk from library A ranks above a marginally relevant chunk from library B.

The `searchedLibraries` field in the response lists which libraries had indexed content at query time, so the agent knows the search scope.

### 6.4 Incremental Indexing

Pages are indexed for BM25 as they're fetched — by `get-docs` (JIT fetch), `get-library-info` (TOC fetch), and `read-page` (page fetch). The search index grows organically as the agent uses Pro-Context. There is no upfront bulk indexing step.

### 6.5 Ranking and Token Budgeting

When returning results via `get-docs`, the system applies a token budget:

```
1. Rank all matching chunks by BM25 relevance (across all specified libraries)
2. Starting from highest-ranked chunk:
   a. Add chunk to result set
   b. Subtract chunk.tokenCount from remaining budget
   c. If budget exhausted → stop
3. If no chunks match → return TOPIC_NOT_FOUND error
4. Compute confidence score:
   - 1.0 if top chunk BM25 score > 0.8
   - Proportional to top chunk BM25 score otherwise
```

---

## 7. Token Efficiency Strategy

### 7.1 Target Metrics

| Metric | Target | Benchmark |
|--------|--------|-----------|
| Avg tokens per response (get-docs) | <3,000 | Deepcon: 2,365 |
| Accuracy | >85% | Deepcon: 90% |
| Tokens per correct answer | <3,529 | Deepcon: 2,628 |

### 7.2 Techniques

1. **Focused chunking**: Split docs into small, self-contained sections (target: 500 tokens/chunk)
2. **Relevance ranking**: BM25 ensures only relevant chunks are returned
3. **Token budgeting**: `maxTokens` parameter caps response size (default: 5,000 for get-docs, 10,000 for read-page)
4. **Snippet generation**: `search-docs` returns snippets (~100 tokens each), not full content
5. **Section targeting**: Use heading hierarchy to find the most specific relevant section
6. **Offset-based reading**: `read-page` returns slices of large pages, avoiding re-sending content the agent has already seen
7. **TOC section filtering**: `get-library-info` with `sections` parameter returns only relevant sections of large TOCs

### 7.3 Token Counting

Approximate token count using character count / 4. This is sufficient for budgeting purposes — exact token counts are model-specific and not needed.

---

## 8. Transport Layer

### 8.1 stdio Transport (Local Mode)

```python
# src/pro_context/__main__.py
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server

async def main():
    server = Server("pro-context")

    # Register tools, resources, prompts...
    # (See implementation guide for full registration code)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )

if __name__ == "__main__":
    asyncio.run(main())
```

**Characteristics:**
- Zero configuration
- No authentication required
- Single-user (one client connection)
- Communication via stdin/stdout
- Process lifecycle managed by MCP client

### 8.2 Streamable HTTP Transport (HTTP Mode)

```python
# src/pro_context/__main__.py (HTTP mode)
import asyncio
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.middleware.cors import CORSMiddleware
import uvicorn

async def handle_sse(request):
    """Handle SSE MCP transport"""
    # Auth middleware
    if not await authenticate_request(request):
        return JSONResponse(
            {"code": "AUTH_REQUIRED", "message": "..."},
            status_code=401
        )

    # Rate limit middleware
    if not await rate_limit_check(request):
        return JSONResponse(
            {"code": "RATE_LIMITED", "message": "..."},
            status_code=429
        )

    # Delegate to MCP transport
    async with SseServerTransport("/messages") as transport:
        await server.run(
            transport.read_stream,
            transport.write_stream,
            server.create_initialization_options(),
        )

# Create Starlette app
app = Starlette(routes=[Route("/sse", endpoint=handle_sse)])
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.security.cors["origins"],
    allow_methods=["GET", "POST"],
)

# Run with uvicorn
uvicorn.run(app, host=config.server.host, port=config.server.port)
```

**Characteristics:**
- Requires API key authentication
- Multi-user (concurrent connections)
- Shared documentation cache across all users
- Supports SSE transport as per MCP spec
- Per-key rate limiting
- CORS configuration

---

## 9. Authentication and API Key Management

### 9.1 Key Generation

```
1. Generate 32 random bytes using crypto.randomBytes()
2. Encode as base64url → this is the API key (43 chars)
3. Compute SHA-256 hash of the key
4. Store only the hash + prefix (first 8 chars) in SQLite
5. Return the full key to the admin (shown once, never stored)
```

**Key format**: `pc_` prefix + 40 chars base64url = `pc_aBcDeFgH...` (43 chars total)

### 9.2 Key Validation Flow

```
1. Extract Bearer token from Authorization header
2. Compute SHA-256 hash of the provided token
3. Look up hash in api_keys table
4. If found and active → authenticated
5. If found but inactive → AUTH_INVALID
6. If not found → AUTH_INVALID
7. Update last_used_at and request_count
```

### 9.3 Admin CLI

```bash
# Create a new API key
pro-context-admin key create --name "team-dev" --rate-limit 120

# List all keys
pro-context-admin key list

# Revoke a key
pro-context-admin key revoke --id <key-id>

# Show key usage stats
pro-context-admin key stats --id <key-id>
```

The admin CLI is a separate entry point (`src/pro_context/auth/admin_cli.py`) that operates directly on the SQLite database.

---

## 10. Rate Limiting Design

### 10.1 Token Bucket Algorithm

Each API key gets its own token bucket:

```
Bucket parameters:
  - capacity: config.rateLimit.burstSize (default: 10)
  - refillRate: config.rateLimit.maxRequestsPerMinute / 60 (default: 1/sec)
  - tokens: starts at capacity

On request:
  1. Compute tokens to add since last request: elapsed_seconds * refillRate
  2. Add tokens (capped at capacity)
  3. If tokens >= 1 → consume 1 token, allow request
  4. If tokens < 1 → reject with RATE_LIMITED, retryAfter = (1 - tokens) / refillRate
```

### 10.2 Rate Limit Headers

HTTP responses include rate limit headers:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 42
X-RateLimit-Reset: 1707700000
```

### 10.3 Per-Key Overrides

API keys can have custom rate limits:

```sql
-- api_keys table includes rate_limit_per_minute column
-- NULL means use default from config
SELECT rate_limit_per_minute FROM api_keys WHERE key_hash = ?;
```

---

## 11. Security Model

### 11.1 Input Validation

All inputs are validated at the MCP boundary using Pydantic models before any processing:

```python
from pydantic import BaseModel, Field, field_validator
import re

class LibraryInput(BaseModel):
    """Input for a single library reference"""
    library_id: str = Field(min_length=1, max_length=200)

    @field_validator('library_id')
    @classmethod
    def validate_library_id(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9\-_./]+$', v):
            raise ValueError('library_id must contain only alphanumeric, dash, underscore, dot, or slash characters')
        return v

class GetDocsInput(BaseModel):
    """Input schema for get-docs tool"""
    libraries: list[LibraryInput] = Field(min_length=1, max_length=10)
    topic: str = Field(min_length=1, max_length=500)
    max_tokens: int = Field(default=5000, ge=500, le=10000)

class ReadPageInput(BaseModel):
    """Input schema for read-page tool"""
    url: str = Field(max_length=2000)
    max_tokens: int = Field(default=10000, ge=500, le=50000)
    offset: int = Field(default=0, ge=0)

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(v)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError('url must be a valid URL')
        return v
```

### 11.2 SSRF Prevention

URL fetching is restricted to known documentation domains:

```python
from urllib.parse import urlparse
import fnmatch
import ipaddress

DEFAULT_ALLOWLIST = [
    "github.com",
    "raw.githubusercontent.com",
    "pypi.org",
    "registry.npmjs.org",
    "*.readthedocs.io",
    "*.github.io",
]

def is_allowed_url(url: str, allowlist: list[str]) -> bool:
    """Check if URL is allowed based on domain allowlist"""
    parsed = urlparse(url)

    # Block file:// URLs
    if parsed.scheme == "file":
        return False

    # Block private IP addresses
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if ip.is_private or ip.is_loopback:
            return False
    except ValueError:
        # Not an IP address, continue with domain check
        pass

    # Check against allowlist with wildcard matching
    return any(fnmatch.fnmatch(parsed.hostname, pattern) for pattern in allowlist)
```

- No fetching of private IPs (127.0.0.1, 10.x, 192.168.x, etc.)
- No fetching of file:// URLs
- URLs must come from resolved TOCs, search results, relatedPages, or configured allowlist
- Custom sources in config are added to the allowlist
- **Dynamic expansion**: When an llms.txt file is fetched, all URLs in it are added to the session allowlist

### 11.3 Secret Redaction

structlog logger is configured with processor pipelines for secret redaction:

```python
import structlog

def redact_secrets(logger, method_name, event_dict):
    """Processor to redact sensitive fields"""
    sensitive_keys = {
        "authorization", "api_key", "apiKey", "token",
        "password", "secret", "key_hash"
    }

    def redact_dict(d):
        if not isinstance(d, dict):
            return d
        return {
            k: "[REDACTED]" if k.lower() in sensitive_keys else redact_dict(v)
            for k, v in d.items()
        }

    return redact_dict(event_dict)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        redact_secrets,  # Custom redaction processor
        structlog.processors.JSONRenderer(),
    ],
)
```

### 11.4 Content Sanitization

Documentation content is treated as untrusted text:

- No `eval()` or dynamic `import()` of documentation content
- HTML content is sanitized before markdown conversion (future HTML adapter)
- No execution of code examples
- Content stored in SQLite uses parameterized queries (no SQL injection)

---

## 12. Observability

### 12.1 Structured Logging

Every request produces a structured log entry:

```json
{
  "level": "info",
  "time": "2026-02-16T10:00:00.000Z",
  "correlationId": "abc-123-def",
  "tool": "get-docs",
  "libraries": ["langchain-ai/langchain"],
  "topic": "chat models",
  "cacheHit": true,
  "cacheTier": "memory",
  "stale": false,
  "adapter": null,
  "duration": 3,
  "tokenCount": 1250,
  "status": "success"
}
```

### 12.2 Key Metrics

| Metric | Description | Exposed Via |
|--------|-------------|-------------|
| Cache hit rate | % of requests served from cache | health resource |
| Cache tier distribution | memory vs SQLite vs miss | health resource |
| Adapter success rate | % of successful fetches per adapter | health resource |
| Average latency | Per-tool response time | logs |
| Avg tokens per response | Token efficiency tracking | logs |
| Error rate | % of requests returning errors | health resource |
| Rate limit rejections | Count of rate-limited requests | logs |

### 12.3 Health Check

The `pro-context://health` resource returns:

```json
{
  "status": "healthy | degraded | unhealthy",
  "uptime": 3600,
  "cache": { "memoryEntries": 142, "memoryBytes": 52428800, "sqliteEntries": 1024, "hitRate": 0.87 },
  "adapters": {
    "llms-txt": { "status": "available", "lastSuccess": "...", "errorCount": 0 },
    "github": { "status": "available", "rateLimitRemaining": 4850 }
  },
  "version": "1.0.0"
}
```

Status determination:
- `healthy`: All adapters available, cache functional
- `degraded`: Some adapters unavailable, or cache hit rate < 50%
- `unhealthy`: All adapters unavailable, or cache corrupted

---

## 13. Extensibility Points

### 13.1 Adding a New Language

1. **Create registry resolver**: `src/pro_context/registry/{language}_resolver.py`
   - Implement version resolution for the language's package registry
   - Follow the same interface as `pypi_resolver.py`

2. **Add known libraries**: Add entries to `src/pro_context/registry/known_libraries.py`
   - Each entry includes `languages: ["{language}"]` and language-specific metadata

3. **No changes required in**: adapters, cache, search, tools, config
   - Adapters work by URL — they don't care about the language
   - Cache is keyed by libraryId — language-agnostic
   - Search indexes content — language-agnostic

### 13.2 Adding a New Documentation Source

1. **Create adapter**: `src/pro_context/adapters/{source_name}.py`
   - Implement the `SourceAdapter` ABC (can_handle, fetch_toc, fetch_page, check_freshness)
   - Define `priority` property relative to existing adapters

2. **Register adapter**: Add to the adapter chain in `src/pro_context/adapters/chain.py`

3. **No changes required in**: tools, cache, search, config schema (unless source-specific config is needed)

### 13.3 Adding a New Tool

1. **Create tool handler**: `src/pro_context/tools/{tool_name}.py`
   - Define Pydantic input/output schemas
   - Implement async handler function

2. **Register tool**: Add to server setup in `src/pro_context/server.py`

3. **No changes required in**: adapters, cache, search, other tools

---

## 14. Database Schema

### 14.1 SQLite Tables

```sql
-- Documentation cache (chunks from get-docs)
CREATE TABLE IF NOT EXISTS doc_cache (
  key TEXT PRIMARY KEY,
  library_id TEXT NOT NULL,
  identifier TEXT NOT NULL,
  content TEXT NOT NULL,
  source_url TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  adapter TEXT NOT NULL,
  fetched_at TEXT NOT NULL,       -- ISO 8601
  expires_at TEXT NOT NULL,       -- ISO 8601
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_doc_cache_library ON doc_cache(library_id);
CREATE INDEX IF NOT EXISTS idx_doc_cache_expires ON doc_cache(expires_at);

-- Page cache (full pages from read-page)
CREATE TABLE IF NOT EXISTS page_cache (
  url_hash TEXT PRIMARY KEY,
  url TEXT NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  total_tokens INTEGER NOT NULL,
  content_hash TEXT NOT NULL,
  fetched_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_page_cache_expires ON page_cache(expires_at);

-- TOC cache
CREATE TABLE IF NOT EXISTS toc_cache (
  key TEXT PRIMARY KEY,
  library_id TEXT NOT NULL,
  toc_json TEXT NOT NULL,          -- JSON array of TocEntry
  available_sections TEXT NOT NULL, -- JSON array of section names
  fetched_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_toc_cache_library ON toc_cache(library_id);

-- Search index (BM25 term index)
CREATE TABLE IF NOT EXISTS search_chunks (
  id TEXT PRIMARY KEY,
  library_id TEXT NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  section_path TEXT NOT NULL,
  token_count INTEGER NOT NULL,
  source_url TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_search_chunks_library ON search_chunks(library_id);

-- FTS5 virtual table for full-text search (wraps search_chunks)
CREATE VIRTUAL TABLE IF NOT EXISTS search_fts USING fts5(
  title,
  content,
  section_path,
  content='search_chunks',
  content_rowid='rowid',
  tokenize='porter unicode61'
);

-- API keys (HTTP mode only)
CREATE TABLE IF NOT EXISTS api_keys (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  key_hash TEXT NOT NULL UNIQUE,
  key_prefix TEXT NOT NULL,
  rate_limit_per_minute INTEGER,    -- NULL = use default
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  last_used_at TEXT,
  request_count INTEGER NOT NULL DEFAULT 0,
  active INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);

-- Library metadata cache
CREATE TABLE IF NOT EXISTS library_metadata (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  languages TEXT NOT NULL,           -- JSON array
  package_name TEXT NOT NULL,
  docs_url TEXT,
  repo_url TEXT,
  fetched_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_library_metadata_package ON library_metadata(package_name);

-- Session state (resolved libraries in current session)
CREATE TABLE IF NOT EXISTS session_libraries (
  library_id TEXT NOT NULL PRIMARY KEY,
  name TEXT NOT NULL,
  languages TEXT NOT NULL,           -- JSON array (informational metadata)
  resolved_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 14.2 Database Initialization

```python
import aiosqlite

async def initialize_database(db: aiosqlite.Connection) -> None:
    """Initialize SQLite database with pragmas and tables"""
    await db.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging
    await db.execute("PRAGMA busy_timeout = 5000")  # 5s timeout
    await db.execute("PRAGMA synchronous = NORMAL")  # Durability vs performance
    await db.execute("PRAGMA foreign_keys = ON")

    # Run CREATE TABLE statements...
    # (See section 14.1 for full schema)
    await db.commit()
```

### 14.3 Cleanup Job

```python
from datetime import datetime

async def cleanup_expired_entries(db: aiosqlite.Connection) -> None:
    """Remove expired cache entries"""
    now = datetime.now().isoformat()

    await db.execute("DELETE FROM doc_cache WHERE expires_at < ?", (now,))
    await db.execute("DELETE FROM page_cache WHERE expires_at < ?", (now,))
    await db.execute("DELETE FROM toc_cache WHERE expires_at < ?", (now,))
    await db.execute("DELETE FROM library_metadata WHERE expires_at < ?", (now,))
    await db.commit()
    # FTS5 content sync handled by triggers
```

The cleanup job runs on the configured interval (`cache.cleanup_interval_minutes`, default: 60 minutes).

---

## 15. Fuzzy Matching

Library name resolution uses Levenshtein distance for fuzzy matching via `rapidfuzz`:

```python
import re
from rapidfuzz import fuzz

def find_closest_matches(query: str, candidates: list[Library]) -> list[LibraryMatch]:
    """Find library matches using fuzzy string matching"""
    normalized = re.sub(r"[^a-z0-9]", "", query.lower())
    results: list[LibraryMatch] = []

    for candidate in candidates:
        normalized_name = re.sub(r"[^a-z0-9]", "", candidate.name.lower())
        normalized_id = re.sub(r"[^a-z0-9]", "", candidate.id.lower())

        # Use rapidfuzz for fast Levenshtein distance
        name_dist = fuzz.distance(normalized, normalized_name)
        id_dist = fuzz.distance(normalized, normalized_id)
        best_dist = min(name_dist, id_dist)

        if best_dist <= 3:  # Max edit distance: 3
            relevance = 1 - (best_dist / max(len(normalized), 1))
            results.append(
                LibraryMatch(
                    library_id=candidate.id,
                    name=candidate.name,
                    description=candidate.description,
                    languages=candidate.languages,
                    relevance=relevance,
                )
            )

    return sorted(results, key=lambda x: x.relevance, reverse=True)
```

This handles common typos like "langchan" → "langchain", "fasapi" → "fastapi", "pydanctic" → "pydantic". Returns all matches ranked by relevance, not just the best one.
