# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.2] - 2026-04-14

### Changed

- **Structured outline in tool responses** — `read_page` and `search_page` now
  return the outline as `{text, total_entries}` instead of a plain string,
  giving agents the total entry count alongside the compact outline text.
- **`search_page` always returns outline context** — the `outline` field is no
  longer nullable. Both `target="content"` and `target="outline"` modes return
  a compact outline with ancestor heading context, so agents always have
  structural orientation alongside search results.
- **`read_outline` pagination counts entries, not page lines** — `limit` and
  `before` now count outline entries rather than raw page line numbers, making
  pagination predictable regardless of heading density.
- **Cache metadata removed from tool responses** — internal cache fields
  (`cached`, `cache_age`, `stale`) are no longer included in tool output.
  Agents should use `content_hash` to detect content changes.
- **Default allowlist expansion widened** — `fetcher.allowlist_expansion` now
  defaults to `discovered` instead of `registry`, so documentation pages that
  link to sibling hosts resolve successfully out of the box.
- **Rewritten MCP tool descriptions** — server-level instructions slimmed to
  avoid duplicating per-tool guidance. Each tool description now leads with
  purpose, includes workflow hints (e.g. outline-first strategy for
  `full_docs_url`), and documents response fields consistently.

## [0.2.1] - 2026-04-06

### Changed

- **Improved server instructions for better agent navigation** — the MCP server
  instructions now include a complete workflow guide (resolve → search → outline
  → read), explicit caching and restriction rules, and a "when to use" section
  that directs agents to prefer ProContext over web search. Duplicated guidance
  previously scattered across individual tool descriptions has been consolidated
  into the server-level prompt.
- **Tool registration order matches recommended workflow** — tools are now
  registered in workflow priority order (resolve_library → search_page →
  read_outline → read_page), improving discoverability in `tools/list` responses.
- **Self-contained tool descriptions** — `read_outline`'s `before` parameter
  description no longer cross-references `read_page`, and redundant caching and
  stale-while-revalidate text has been removed from individual tool descriptions
  in favor of the centralized server instructions.

## [0.2.0] - 2026-04-05

### Added

- **HTML content processing** — documentation pages served as HTML are now
  automatically converted to clean markdown via a configurable processor
  pipeline (default: markitdown). Agents receive readable content instead of
  raw HTML when a library's documentation does not provide native markdown.

### Changed

- **Smarter outline context in search results** — `search_page` now returns
  more useful outline context for content-mode searches. Small outlines are
  returned in full; oversized outlines are trimmed to the match range with the
  active ancestor heading chain prepended for structural context. Outline
  character budgets are now configurable separately for `read_page` and
  `search_page`.

## [0.1.2] - 2026-04-01

Maintenance release focused on runtime hardening, safer startup behavior, and
security fixes.

### Fixed

- **Malformed outline lines no longer crash page processing** — outline parsing
  now skips malformed entries gracefully instead of failing during page reads or
  search operations.
- **Invalid numeric configuration now fails fast at startup** — settings such as
  cache TTLs and polling intervals are validated on load so negative or zero
  values cannot silently produce broken runtime behavior.
- **First-run client identity creation is safe under concurrent startup** — the
  persisted anonymous client ID is now created atomically, avoiding races when
  multiple processes initialize the data directory at the same time.
- **Runtime guards no longer depend on Python assertions** — internal cache and
  fetch initialization checks now raise proper runtime errors even when Python
  is run with optimizations enabled.

### Security

- **Bearer token comparison now uses a constant-time check** — HTTP auth no
  longer relies on plain string comparison, reducing timing side-channel risk.
- **Security-sensitive dependencies were refreshed** — the release updates
  vulnerable dependency paths, including the `cryptography` chain used by the
  runtime.

## [0.1.1] - 2026-03-25

First public release. A complete MCP server for agent-driven documentation
navigation: resolve libraries, fetch pages, search content, and browse outlines
— backed by a curated registry, SSRF protection, and a SQLite cache.

### Added

- **Four MCP tools** — `resolve_library` (fuzzy name resolution against a
  curated registry), `read_page` (fetch documentation with offset/limit
  windowing and compacted outlines), `search_page` (grep-like search with
  literal/regex modes, smart case, and word boundaries), and `read_outline`
  (paginated outline browsing for large pages).
- **`before` parameter** — `read_page` and `read_outline` accept a `before`
  argument for backward context lines. It is additive — the total lines
  returned equals `before + limit`, and `next_offset` is unaffected.
- **`include_outline` toggle** — `read_page` accepts `include_outline=false`
  to omit the outline from paginated responses, saving tokens when the
  outline is already known from the first call.
- **Outline search** — `search_page` accepts `target="outline"` to search
  only structural headings instead of page content. Both targets support
  pagination.
- **Full documentation URL** — `resolve_library` returns a `full_docs_url`
  (llms-full.txt) for libraries that offer a single merged documentation
  page, useful for broad search across all sections.
- **Per-package metadata** — `resolve_library` returns `readme_url` and
  `repo_url` per package group, giving agents quick access to READMEs and
  source repositories.
- **Language hint** — `resolve_library` accepts an optional `language`
  parameter that sorts matching-language packages to the top of results
  without filtering.
- **Server instructions** — centralized MCP server instructions guide agents
  through the documentation workflow (resolve → read/search → paginate),
  embedded via the MCP `instructions` field.
- **Two transport modes** — stdio (default, for local MCP clients) and HTTP
  (MCP Streamable HTTP with bearer auth, origin validation, and protocol
  version enforcement via pure ASGI middleware).
- **CLI commands** — `procontext setup` for one-time registry bootstrap and
  `procontext doctor` for environment, registry, cache, and network diagnostics
  with `--fix` for automated repair.
- **SQLite cache** — 24-hour TTL, WAL mode, stale-while-revalidate with
  background refresh (15-minute cooldown, dedup of in-flight refreshes).
  Periodic cleanup of entries expired beyond 7 days.
- **SSRF protection** — domain allowlist derived from the registry at startup,
  per-hop private IP blocking on redirects, and optional runtime expansion from
  discovered domains in fetched content.
- **Background registry updates** — one-shot startup check in stdio mode,
  scheduled polling in HTTP mode. Bounded backoff for transient failures (max 8
  fast retries, then 24-hour cadence). Atomic temp+fsync+rename persistence
  with SHA-256 checksum validation.
- **Registry sidecar (`additional-info.json`)** — optional checksum-validated
  metadata file alongside the main registry, downloaded and verified during
  setup and background updates. Currently provides an origin-based allowlist
  for `.md` URL probing.
- **Formalized registry state** — `registry-state.json` is validated via a
  Pydantic model (`RegistryState`) with checksum format enforcement and
  optional sidecar metadata pointers.
- **Outline compaction** — `read_page` and `search_page` return compacted
  outlines (≤50 entries and ≤4000 chars via progressive depth reduction:
  H6 → H5 → fenced content → H4 → H3). Both entry count and character
  budget must be satisfied. Pages with irreducibly large outlines direct
  the agent to `read_outline`.
- **`.md` URL probing** — `read_page` tries appending `.md` to extensionless
  URLs before falling back to the original, but only for documentation
  origins in a registry-provided allowlist (`additional-info.json`),
  reducing unnecessary failed probes.
- **`content_hash` in tool responses** — truncated SHA-256 (12 hex chars) of
  full page content, allowing agents to detect content changes between
  paginated calls.
- **Auto-setup on first run** — if no local registry is found at startup, the
  server attempts a one-time fetch before failing with an actionable error
  message pointing to `procontext setup`.
- **Stdout guard in stdio mode** — writes to stdout from application code are
  intercepted, preventing corruption of the MCP JSON-RPC stream.
- **Anonymous client identity** — a random UUID generated on first run and
  persisted to the data directory. No hardware fingerprinting or PII.
- **Full configuration** — `procontext.yaml` with `PROCONTEXT__*` environment
  variable overrides. Covers server, registry, cache, fetcher, resolver, and
  logging settings. Unknown fields are rejected at startup.
- **Cross-platform** — config and data paths resolve automatically on Linux,
  macOS, and Windows via platformdirs.
- **Structured logging** — JSON or text output to stderr via structlog.

### Security

- **HTTP server binds to `127.0.0.1` by default** — does not listen on all
  interfaces unless explicitly configured.
- **SLSA provenance attestation on releases** — build provenance verification
  for release artifacts.
- **MIT license** — permissive open-source license.

## [0.1.0] - 2026-02-28 (alpha)

Internal alpha. Initial implementation of the MCP server with `resolve_library`,
`read_page`, registry loading, SQLite cache, stdio/HTTP transports, and SSRF
protection. Not recommended for production use.

[Unreleased]: https://github.com/procontexthq/procontext/compare/v0.2.2...HEAD
[0.2.2]: https://github.com/procontexthq/procontext/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/procontexthq/procontext/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/procontexthq/procontext/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/procontexthq/procontext/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/procontexthq/procontext/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/procontexthq/procontext/releases/tag/v0.1.0
