# Pro-Context: Library Resolution Strategy

> **Document**: 05-library-resolution.md
> **Status**: Draft
> **Last Updated**: 2026-02-16
> **Depends on**: 02-functional-spec.md (v3)

---

## 1. The Problem

When an agent calls `resolve-library("langchain")` or `get-docs([{libraryId: "langchain"}], "streaming")`, the server must figure out where to find documentation. This is harder than it sounds because:

1. **Packages are not libraries.** `langchain`, `langchain-openai`, `langchain-community`, and `langchain-core` are four separate PyPI packages, but they all share the same documentation site (docs.langchain.com). They should resolve to one documentation source, not four.

2. **Not everything is on PyPI.** Some libraries are GitHub-only (no PyPI package). Some are installed via conda. Some are internal/private.

3. **Extras are not separate libraries.** `langchain[openai]` and `langchain[vertexai]` are pip extras — they install additional dependencies but the core library is the same. They shouldn't create separate entries.

4. **Multi-language libraries exist.** `protobuf`, `grpc`, `tensorflow` exist across Python, JavaScript, Go, etc. Each language variant may have different docs or shared docs.

5. **Ecosystems have sub-projects.** Pydantic has `pydantic` (docs.pydantic.dev) and `pydantic-ai` (ai.pydantic.dev) — related but separate documentation sites.

The current spec hand-waves this with a "known-libraries registry." This document defines how that registry actually works.

---

## 2. Core Model: Documentation Sources, Not Packages

The fundamental unit in Pro-Context's registry is a **Documentation Source** — a place where documentation lives. Packages are secondary; they're pointers to documentation sources.

```
┌──────────────────────────────────────────────────────┐
│                  Documentation Source                  │
│                                                       │
│  id: "langchain"                                      │
│  name: "LangChain"                                    │
│  docsUrl: "https://docs.langchain.com"                │
│  repoUrl: "https://github.com/langchain-ai/langchain" │
│  languages: ["python"]                                │
│                                                       │
│  packages:                                            │
│    pypi: ["langchain", "langchain-openai",            │
│           "langchain-community", "langchain-core",    │
│           "langchain-text-splitters"]                  │
│                                                       │
│  aliases: ["lang-chain", "lang chain"]                │
│                                                       │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│                  Documentation Source                  │
│                                                       │
│  id: "langgraph"                                      │
│  name: "LangGraph"                                    │
│  docsUrl: "https://langchain-ai.github.io/langgraph"  │
│  repoUrl: "https://github.com/langchain-ai/langgraph" │
│  languages: ["python"]                                │
│                                                       │
│  packages:                                            │
│    pypi: ["langgraph", "langgraph-sdk",               │
│           "langgraph-checkpoint"]                      │
│                                                       │
└──────────────────────────────────────────────────────┘
```

**Key insight**: When the agent queries "langchain-openai", the server resolves it to the "langchain" documentation source. The agent gets LangChain's full TOC — not a separate "langchain-openai" documentation site, because one doesn't exist.

---

## 3. Registry Schema

### 3.1 Documentation Source Entry

```typescript
interface DocSource {
  /** Unique identifier (human-readable, stable) */
  id: string;

  /** Display name */
  name: string;

  /** Documentation site URL (server tries {docsUrl}/llms.txt) */
  docsUrl: string | null;

  /** Primary GitHub repository */
  repoUrl: string | null;

  /** Languages this library supports */
  languages: string[];

  /** Package registry mappings — multiple packages can map to one source */
  packages: {
    pypi?: string[];        // PyPI package names
    npm?: string[];         // npm package names (future)
    crates?: string[];      // crates.io names (future)
  };

  /** Alternative names/spellings for fuzzy matching */
  aliases: string[];

  /** Version URL pattern (how to construct versioned docs URLs) */
  versionPattern?: string;  // e.g., "https://docs.pydantic.dev/{version}/llms.txt"
}
```

### 3.2 Example Entries

```json
[
  {
    "id": "langchain",
    "name": "LangChain",
    "docsUrl": "https://docs.langchain.com",
    "repoUrl": "https://github.com/langchain-ai/langchain",
    "languages": ["python"],
    "packages": {
      "pypi": ["langchain", "langchain-openai", "langchain-anthropic", "langchain-community", "langchain-core", "langchain-text-splitters"]
    },
    "aliases": ["lang-chain", "lang chain"]
  },
  {
    "id": "langgraph",
    "name": "LangGraph",
    "docsUrl": "https://langchain-ai.github.io/langgraph",
    "repoUrl": "https://github.com/langchain-ai/langgraph",
    "languages": ["python"],
    "packages": {
      "pypi": ["langgraph", "langgraph-sdk", "langgraph-checkpoint", "langgraph-checkpoint-postgres", "langgraph-checkpoint-sqlite"]
    },
    "aliases": ["lang-graph", "lang graph"]
  },
  {
    "id": "pydantic",
    "name": "Pydantic",
    "docsUrl": "https://docs.pydantic.dev/latest",
    "repoUrl": "https://github.com/pydantic/pydantic",
    "languages": ["python"],
    "packages": {
      "pypi": ["pydantic", "pydantic-core", "pydantic-settings", "pydantic-extra-types"]
    },
    "aliases": [],
    "versionPattern": "https://docs.pydantic.dev/{version}/llms.txt"
  },
  {
    "id": "pydantic-ai",
    "name": "Pydantic AI",
    "docsUrl": "https://ai.pydantic.dev",
    "repoUrl": "https://github.com/pydantic/pydantic-ai",
    "languages": ["python"],
    "packages": {
      "pypi": ["pydantic-ai", "pydantic-ai-slim"]
    },
    "aliases": ["pydanticai"]
  },
  {
    "id": "fastapi",
    "name": "FastAPI",
    "docsUrl": "https://fastapi.tiangolo.com",
    "repoUrl": "https://github.com/tiangolo/fastapi",
    "languages": ["python"],
    "packages": {
      "pypi": ["fastapi", "fastapi-cli"]
    },
    "aliases": ["fast-api", "fast api"]
  },
  {
    "id": "protobuf",
    "name": "Protocol Buffers",
    "docsUrl": "https://protobuf.dev",
    "repoUrl": "https://github.com/protocolbuffers/protobuf",
    "languages": ["python", "javascript", "go", "java", "cpp"],
    "packages": {
      "pypi": ["protobuf", "grpcio", "grpcio-tools"],
      "npm": ["protobufjs", "@grpc/grpc-js"]
    },
    "aliases": ["protobuf", "protocol buffers", "proto", "grpc"]
  },
  {
    "id": "tensorflow",
    "name": "TensorFlow",
    "docsUrl": "https://www.tensorflow.org",
    "repoUrl": "https://github.com/tensorflow/tensorflow",
    "languages": ["python", "javascript"],
    "packages": {
      "pypi": ["tensorflow", "tensorflow-gpu", "tensorflow-cpu", "tf-nightly", "keras"],
      "npm": ["@tensorflow/tfjs"]
    },
    "aliases": ["tf"]
  }
]
```

---

## 4. Resolution Algorithm

### 4.1 Input Normalization

Before matching, normalize the input:

```
Input: "langchain[openai]"
  1. Strip pip extras: "langchain[openai]" → "langchain"
  2. Strip version specifiers: "langchain>=0.3" → "langchain"
  3. Lowercase: "LangChain" → "langchain"
  4. Strip whitespace: " langchain " → "langchain"

Input: "langchain-openai"
  → No stripping (this is a real package name, not an extra)
  → Lowercase: "langchain-openai"
```

### 4.2 Resolution Steps

```
resolve-library(query: "langchain-openai", language?: "python")
  │
  ├─ Step 1: Exact package match
  │    Search packages.pypi across all DocSource entries
  │    "langchain-openai" found in DocSource "langchain"
  │    → MATCH: return DocSource "langchain"
  │
  ├─ Step 2: Exact ID match (if step 1 fails)
  │    Search DocSource.id
  │    → No match for "langchain-openai"
  │
  ├─ Step 3: Alias match (if step 2 fails)
  │    Search DocSource.aliases
  │    → No match
  │
  ├─ Step 4: Fuzzy match (if step 3 fails)
  │    Levenshtein distance against all IDs, names, package names, aliases
  │    → Might match "langchain" (distance 7 — too far)
  │    → No useful fuzzy match
  │
  ├─ Step 5: PyPI discovery (if step 4 fails)
  │    GET https://pypi.org/pypi/langchain-openai/json
  │    → Extract project_urls.Documentation → docsUrl
  │    → Extract project_urls.Source → repoUrl
  │    → Create ephemeral DocSource, cache it
  │
  └─ Step 6: GitHub discovery (if step 5 fails)
       If query looks like "owner/repo", try GitHub API
       GET https://api.github.com/repos/{owner}/{repo}
       → Extract homepage → docsUrl
       → Create ephemeral DocSource, cache it
```

### 4.3 Resolution Priority

| Step | Source | Speed | Coverage | When Used |
|------|--------|-------|----------|-----------|
| 1 | Package name → DocSource mapping | <1ms | Curated libraries only | Always (first check) |
| 2 | DocSource ID exact match | <1ms | Curated libraries only | Agent uses known IDs |
| 3 | Alias match | <1ms | Curated libraries only | Typos, alternative names |
| 4 | Fuzzy match (Levenshtein) | <10ms | Curated libraries only | Misspellings |
| 5 | PyPI metadata discovery | ~500ms | Any PyPI package | Unknown libraries |
| 6 | GitHub discovery | ~500ms | Any GitHub repo | Non-PyPI libraries |

Steps 1-4 are in-memory, fast, and depend on registry quality.
Steps 5-6 are network calls, slower, but handle any library.

### 4.4 What `resolve-library` Returns

`resolve-library` returns **DocSource** matches, not package matches. If "langchain-openai" resolves to the "langchain" DocSource, the response is:

```json
{
  "results": [
    {
      "libraryId": "langchain",
      "name": "LangChain",
      "description": "Build context-aware reasoning applications",
      "languages": ["python"],
      "relevance": 1.0,
      "matchedVia": "package:langchain-openai"
    }
  ]
}
```

The `matchedVia` field tells the agent how the match was found — useful for transparency.

---

## 5. Handling Edge Cases

### 5.1 Pip Extras

```
Input: "langchain[openai]"
Normalization: strip extras → "langchain"
Resolution: exact package match → DocSource "langchain"
```

The extras syntax (`[openai]`, `[vertexai]`, etc.) is stripped during normalization. The base package name is what gets resolved. This is correct because extras don't change which documentation site to use.

### 5.2 Sub-packages in Monorepos

LangChain's monorepo publishes multiple PyPI packages:
- `langchain` (main)
- `langchain-openai` (OpenAI integration)
- `langchain-anthropic` (Anthropic integration)
- `langchain-community` (community integrations)
- `langchain-core` (core abstractions)

All map to the same DocSource. The package-to-source mapping handles this — all five package names point to DocSource "langchain".

If the agent is specifically interested in the OpenAI integration docs, the TOC sections (from get-library-info) or search (from search-docs/get-docs) will surface the relevant pages.

### 5.3 Related but Separate Projects

Pydantic and Pydantic AI are related but have separate documentation sites:
- `pydantic` → docs.pydantic.dev
- `pydantic-ai` → ai.pydantic.dev

These are separate DocSource entries. The package-to-source mapping distinguishes them:
- PyPI package `pydantic` → DocSource "pydantic"
- PyPI package `pydantic-ai` → DocSource "pydantic-ai"

### 5.4 Multi-Language Libraries

Protocol Buffers exists in Python, JS, Go, Java, C++. Two approaches:

**Option A: Single DocSource, multiple languages.** The DocSource has `languages: ["python", "javascript", "go", ...]`. The docs URL is the same. When the agent specifies a language, the server can try language-specific doc paths or sections.

**Option B: Separate DocSource per language.** `protobuf-python`, `protobuf-js`, etc. Each with its own docs URL.

**Recommendation: Option A for libraries with unified documentation** (protobuf.dev covers all languages), **Option B for libraries with per-language docs** (if they exist). Most multi-language libraries have unified docs, so Option A covers the majority.

### 5.5 GitHub-Only Libraries

For libraries without a PyPI package:
- The agent (or user) provides a GitHub URL directly
- `resolve-library("github.com/some-org/some-lib")` → triggers GitHub discovery (Step 6)
- The server creates an ephemeral DocSource from the repo metadata
- Subsequent calls can use the generated `libraryId`

### 5.6 Version Variants

Some libraries publish separate packages per version:
- `tensorflow` vs `tf-nightly`
- `torch` vs `torch-nightly`

These are the same documentation source at different versions. The package mapping handles this — both `tensorflow` and `tf-nightly` map to DocSource "tensorflow". Version resolution picks the right docs URL.

---

## 6. Building the Registry

### 6.1 Data Sources

The registry is built from multiple sources, combined and deduplicated:

```
┌──────────────────────┐
│  top-pypi-packages   │  15,000 packages ranked by downloads
│  (monthly snapshot)  │  Source: hugovk/top-pypi-packages
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  PyPI JSON API       │  Metadata per package: name, summary,
│  (per-package)       │  project_urls (Documentation, Source)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  llms.txt probe      │  HEAD {docsUrl}/llms.txt → exists?
│  (per docs URL)      │  Determines if llms.txt adapter can work
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Manual curation     │  Package grouping (langchain ecosystem),
│  (human review)      │  aliases, version patterns, corrections
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  known-libraries.json│  Final registry file shipped with
│  (output)            │  Pro-Context
└──────────────────────┘
```

### 6.2 Build Script

A build script (not part of the runtime server) generates the registry:

```
build-registry.ts

1. Fetch top-pypi-packages (top 5,000 by downloads)

2. For each package:
   a. GET https://pypi.org/pypi/{name}/json
   b. Extract: name, summary, project_urls
   c. Determine docsUrl from project_urls.Documentation or project_urls.Homepage
   d. Determine repoUrl from project_urls.Source or project_urls.Repository

3. Group packages by documentation URL:
   - If two packages share the same docsUrl → same DocSource
   - Example: langchain, langchain-openai, langchain-core all have
     Documentation → docs.langchain.com → grouped into one DocSource

4. For each unique docsUrl:
   a. HEAD {docsUrl}/llms.txt → flag hasLlmsTxt
   b. If no docsUrl, check if repoUrl has /docs/ directory

5. Apply manual overrides:
   - Package groupings that PyPI metadata can't detect
   - Aliases for common misspellings
   - Version URL patterns
   - docsUrl corrections (some PyPI metadata is wrong/stale)

6. Output known-libraries.json
```

### 6.3 Package Grouping Heuristic

How do we know that `langchain-openai` belongs with `langchain`?

**Heuristic 1: Shared documentation URL.** If two PyPI packages list the same `project_urls.Documentation`, they belong to the same DocSource. This catches most monorepo sub-packages.

**Heuristic 2: Prefix matching with shared org.** If `langchain-openai` and `langchain` have the same GitHub org (`langchain-ai`), and `langchain-openai` doesn't have its own documentation URL (or it points to the parent docs), group them.

**Heuristic 3: Manual override.** For cases the heuristics miss, a manual override file specifies explicit groupings.

### 6.4 Registry Size Estimates

| Filter | Packages | Unique DocSources | Registry File Size |
|--------|----------|-------------------|-------------------|
| Top 1,000 by downloads | 1,000 | ~600-700 | ~150KB |
| Top 5,000 by downloads | 5,000 | ~3,000-3,500 | ~700KB |
| All with llms.txt | ~500+ | ~500+ | ~100KB |

The package-to-source deduplication is significant — top 1,000 packages collapse to ~600-700 unique documentation sources because of ecosystem grouping.

### 6.5 Registry Refresh Cadence

- **Monthly**: Re-run build script against latest top-pypi-packages
- **On PR**: Community can submit PRs to add/correct entries in an overrides file
- **CI validation**: Build script runs in CI to verify the registry is valid (all URLs resolve, no duplicates)

---

## 7. Runtime Resolution Architecture

### 7.1 In-Memory Index

At startup, the server loads `known-libraries.json` into memory and builds three lookup indexes:

```typescript
class LibraryRegistry {
  // Primary index: DocSource by ID
  private byId: Map<string, DocSource>;

  // Package name → DocSource ID (many-to-one)
  private byPackage: Map<string, string>;

  // All searchable names for fuzzy matching
  // (IDs, names, package names, aliases — all lowercased)
  private fuzzyCorpus: { term: string; sourceId: string }[];
}
```

### 7.2 Resolution Flow in Detail

```typescript
async function resolveLibrary(query: string, language?: string): Promise<DocSource[]> {
  const normalized = normalizeQuery(query);
  // "langchain[openai]>=0.3" → "langchain"
  // "LangChain" → "langchain"

  // Step 1: Exact package match
  const byPackage = registry.byPackage.get(normalized);
  if (byPackage) return [registry.byId.get(byPackage)!];

  // Step 2: Exact ID match
  const byId = registry.byId.get(normalized);
  if (byId) return [byId];

  // Step 3: Fuzzy match against all known names
  const fuzzyMatches = fuzzySearch(normalized, registry.fuzzyCorpus);
  if (fuzzyMatches.length > 0) return fuzzyMatches.map(m => registry.byId.get(m.sourceId)!);

  // Step 4: PyPI discovery (if Python)
  if (!language || language === "python") {
    const pypiSource = await discoverFromPyPI(normalized);
    if (pypiSource) {
      registry.addEphemeral(pypiSource); // Cache for session
      return [pypiSource];
    }
  }

  // Step 5: GitHub discovery (if looks like a repo path)
  if (normalized.includes("/")) {
    const ghSource = await discoverFromGitHub(normalized);
    if (ghSource) {
      registry.addEphemeral(ghSource);
      return [ghSource];
    }
  }

  // No match
  return [];
}
```

### 7.3 Query Normalization Rules

```
1. Strip pip extras:       "package[extra]" → "package"
2. Strip version specs:    "package>=1.0"   → "package"
                           "package==1.0.0" → "package"
                           "package~=1.0"   → "package"
3. Lowercase:              "FastAPI"        → "fastapi"
4. Trim whitespace:        " package "      → "package"
5. Normalize separators:   "lang chain"     → match against aliases
                           "lang-chain"     → match against aliases
6. Keep hyphens/underscores as-is for exact matching:
                           "langchain-openai" stays "langchain-openai"
                           (PyPI normalizes _ to - but we match both)
```

---

## 8. Comparison: PyPI vs GitHub as Primary Source

| Dimension | PyPI | GitHub |
|-----------|------|--------|
| **Coverage (Python)** | ~500K packages. Covers all pip-installable libraries | Near-universal for open source. Also has non-Python projects |
| **Structured metadata** | Yes: name, summary, project_urls, version list, classifiers | Limited: description, homepage, topics. No package-level metadata |
| **Documentation URL** | Often in `project_urls.Documentation` — but not always set, sometimes stale | Homepage field — may or may not be docs. Often points to the repo itself |
| **Download/popularity data** | Via BigQuery or top-pypi-packages dataset. Well-established | Stars, forks. Less reliable as popularity metric |
| **Package grouping** | Possible via shared docs URL. Explicit package names | Monorepos are visible but sub-packages aren't distinct |
| **Multi-language** | Python only | All languages |
| **Non-public libraries** | Not on PyPI | May be on GitHub Enterprise, or not on GitHub at all |
| **Rate limits** | No auth needed for JSON API. No rate limit documented | 60 req/hr unauthenticated, 5,000 with PAT |

**Recommendation: PyPI is the primary source for the build script.** It has structured metadata, a reliable popularity ranking (via top-pypi-packages), and the `project_urls` field often points to documentation. GitHub is the fallback at runtime — when a library isn't in the registry and isn't on PyPI, the GitHub adapter can fetch docs from the repo.

The build script uses PyPI for discovery and enrichment. The runtime server uses the pre-built registry for fast resolution and falls back to PyPI/GitHub for unknown libraries.

---

## 9. Open Questions

### Q1: Should ephemeral discoveries be persisted?

When the server discovers a library via PyPI at runtime (Step 5), should it persist the DocSource to SQLite so it's available across sessions? Or is session-scoped caching sufficient?

**Lean**: Persist to SQLite with a TTL (e.g., 7 days). If a library is queried once, it's likely to be queried again. Persisting avoids repeated PyPI lookups.

### Q2: How do we handle packages that share a docs URL but shouldn't be grouped?

For example, if two unrelated packages happen to link to the same documentation hosting platform (e.g., both link to readthedocs.io root). The grouping heuristic would incorrectly merge them.

**Lean**: Only group when the full docs URL matches (not just the domain). `readthedocs.io` wouldn't match, but `langchain.readthedocs.io` would correctly group LangChain packages.

### Q3: Should the registry include packages below a popularity threshold?

The top-pypi-packages dataset has 15,000 packages. Should we include all of them, or filter?

**Lean**: Start with top 5,000 (>572K monthly downloads). This covers every library a typical developer encounters. The PyPI discovery fallback handles the long tail. We can expand later based on user feedback.

### Q4: How do we handle the agent passing a requirements.txt dump?

An agent might call `resolve-library` with each line from a requirements.txt. Some of those will be transitive dependencies (e.g., `certifi`, `urllib3`) that the developer never directly uses and doesn't need docs for.

**Lean**: Not our problem. The agent decides what to resolve. If it's smart, it resolves direct dependencies only. Pro-Context resolves whatever it's asked to resolve.
