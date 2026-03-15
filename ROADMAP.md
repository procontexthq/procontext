# Roadmap

> **Note for contributors**: This file is maintained by the core team and reflects decisions that have been discussed and committed to. It is not open to direct edits via pull request. To propose a feature, new library, or direction — open a [GitHub Discussion](https://github.com/procontexthq/procontext/discussions) or a [GitHub Issue](https://github.com/procontexthq/procontext/issues). Well-reasoned proposals consistent with the project's goals will be considered and, if accepted, added here.

---

## Where we are — v0.1.0

v0.1.0 ships a complete MCP server with the core documentation workflow in place. An agent can resolve a library name, fetch its llms.txt table of contents, search within pages, browse full outlines when needed, and read specific sections — all from a curated registry with SSRF protection and a SQLite cache.

- **`resolve_library`** — resolves a library name or pip specifier to a known documentation source via fuzzy matching against a curated registry; returns documentation URLs for use with `read_page` and `search_page`
- **`read_page`** — fetches a documentation page (including llms.txt indexes) with offset/limit windowing and a compacted outline for section navigation
- **`search_page`** — grep-like search within a documentation page; supports literal and regex modes, smart case sensitivity, word boundary matching, and paginated results
- **`read_outline`** — returns the full paginated outline of a page for cases where the inline outline is too large to fit comfortably in `read_page`
- **stdio transport** — default; process lifecycle managed by the MCP client
- **HTTP transport** — MCP Streamable HTTP (spec 2025-11-25) with security middleware (bearer auth, origin validation, protocol version checks)
- **CLI commands** — `procontext setup` for one-time registry bootstrap and `procontext doctor` for environment, registry, cache, and network diagnostics
- **SQLite cache** — 24-hour TTL, WAL mode, synchronous refresh on stale entries, and stale fallback when the source is unavailable
- **SSRF protection** — domain allowlist derived from the registry, optional runtime allowlist expansion, and private IP blocking
- **Background registry updates** — startup checks in stdio mode and scheduled checks in long-running HTTP mode
- **Cross-platform** — config and data paths resolve automatically on Linux, macOS, and Windows

---

## What's next

The core server is solid. Future work focuses on three areas: expanding what the server knows, where it can run, and how well it helps agents navigate documentation.

### Registry coverage

The value of ProContext scales directly with the breadth and quality of the registry. Expanding coverage — more libraries, MCP servers, AI frameworks, and ecosystem tooling — is the highest-leverage work. Registry contributions are maintained separately at [procontexthq/procontexthq.github.io](https://github.com/procontexthq/procontexthq.github.io).

### Deployment

- **PyPI release** — `uvx procontext` as a first-class install path, no git clone required
- **Docker image** — official image for HTTP transport deployments; the most-requested path for shared team and self-hosted setups

### Tool quality

- **Additional documentation formats** — as the ecosystem evolves, the server should serve documentation from formats that emerge alongside or complement llms.txt
- **Outline quality improvements** — there are known opportunities around setext headings, indented heading-like lines, and large-outline summarisation. These are intentionally deferred for now: the current outline pipeline is useful and stable, and any changes here need to earn their added complexity against real documentation examples rather than theory alone.

### Performance

- Improvements for high-concurrency HTTP deployments — connection pooling, response streaming, and load testing at scale

---

## How we decide what to build

ProContext follows a spec-first development process. Significant changes are designed in [`docs/specs/`](docs/specs/) before any code is written — this keeps the architecture intentional and makes it easier for contributors to understand why things work the way they do.

Priority order: things that make the server more useful to agents today, then things that make it easier to deploy and operate, then developer experience improvements. Features that don't serve the agent-first use case don't belong here regardless of how popular the request is.

If you want to influence the roadmap, open a [discussion](https://github.com/procontexthq/procontext/discussions) before opening a PR.
