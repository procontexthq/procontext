# Roadmap

> **Note for contributors**: This file is maintained by the core team and reflects decisions that have been discussed and committed to. It is not open to direct edits via pull request. To propose a feature, new library, or direction — open a [GitHub Discussion](https://github.com/procontexthq/procontext/discussions) or a [GitHub Issue](https://github.com/procontexthq/procontext/issues). Well-reasoned proposals consistent with the project's goals will be considered and, if accepted, added here.

---

## Where we are — v0.1.1

v0.1.1 is the first public release. It ships a complete MCP server with the core documentation workflow in place. An agent can resolve a library name, fetch its llms.txt table of contents, search within pages, browse full outlines when needed, and read specific sections — all backed by a curated registry, SSRF protection, and a SQLite cache.

- **`resolve_library`** — resolves a library name, package name, or alias to its documentation source via exact and fuzzy matching against a curated registry. Returns `index_url` (llms.txt table of contents), `full_docs_url` (llms-full.txt merged documentation, when available), and per-package `readme_url`/`repo_url` metadata. An optional `language` hint sorts matching-language packages to the top.
- **`read_page`** — fetches a documentation page with offset/limit windowing and a smart compacted outline (≤50 entries, ≤4000 chars). The `before` parameter adds backward context lines without reducing the forward limit. Set `include_outline=false` on pagination calls to skip the outline and save tokens.
- **`search_page`** — grep-like search within a page; supports literal and regex modes, smart case sensitivity, word boundaries, and paginated results. Use `target="outline"` to search only structural headings instead of page content.
- **`read_outline`** — paginated access to the full outline of a page, with page-line windowing and `before` for backward context. Used as a fallback when the smart outline in `read_page` or `search_page` indicates trimming.
- **Server instructions** — centralized usage guidance embedded in the MCP server, teaching agents how to navigate the tool workflow (resolve → read/search → paginate)
- **stdio transport** — default; process lifecycle managed by the MCP client
- **HTTP transport** — MCP Streamable HTTP (spec 2025-11-25) with security middleware (bearer auth, origin validation, protocol version checks)
- **CLI commands** — `procontext setup` for one-time registry bootstrap and `procontext doctor` for environment, registry, cache, and network diagnostics
- **SQLite cache** — 24-hour TTL, WAL mode, stale-while-revalidate with background refresh (15-minute cooldown, dedup of in-flight refreshes), periodic cleanup of entries expired beyond 7 days
- **SSRF protection** — domain allowlist derived from the registry, optional runtime allowlist expansion, and private IP blocking
- **Registry sidecar (`additional-info.json`)** — optional checksum-validated metadata file alongside the main registry, currently providing an origin-based allowlist for `.md` URL probing
- **Smarter `.md` probing** — `read_page` tries appending `.md` to extensionless URLs, but only for documentation origins in the registry-provided allowlist, reducing unnecessary failed probes
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

- **Content size cap** — `read_page` limits by line count, not total content size. A page with 500 short lines is fine, but 500 lines of wide tables or long code signatures can blow up an agent's context window. A configurable character cap on the `content` field — truncating at the last complete line that fits, adjusting `has_more`/`next_offset`, and flagging `truncated: true` — adds a safety net beneath the existing line windowing without changing the pagination model.
- **Additional documentation formats** — as the ecosystem evolves, the server should serve documentation from formats that emerge alongside or complement llms.txt
- **Outline quality improvements** — there are known opportunities around setext headings, indented heading-like lines, and large-outline summarisation. These are intentionally deferred for now: the current outline pipeline is useful and stable, and any changes here need to earn their added complexity against real documentation examples rather than theory alone.

### Annotations

- **Agent annotations** — allow agents to attach notes to specific lines of a documentation page. When the same page is fetched in a future session, saved annotations are returned alongside the content. This gives agents a form of cross-conversation memory tied to documentation — for example, marking a function as deprecated, flagging a gotcha, or bookmarking a section for later use.

### Custom documentation sources

- **User-defined documentation** — allow operators to register their own documentation sources (internal libraries, private APIs, team-specific tools) without contributing to the public registry. A local configuration path (e.g., entries in `procontext.yaml`) that merges with the curated registry at startup, giving teams a way to use ProContext for their own stack alongside the public ecosystem.

### Context hub

- **Context hub integration** — support pulling documentation from Andrew Ng's [Context hub](https://github.com/andrewyng/context-hub), giving agents access to a broader range of curated documentation sources beyond the ProContext registry.

### Performance

- Improvements for high-concurrency HTTP deployments — connection pooling, response streaming, and load testing at scale

---

## How we decide what to build

ProContext follows a spec-first development process. Significant changes are designed in [`docs/specs/`](docs/specs/) before any code is written — this keeps the architecture intentional and makes it easier for contributors to understand why things work the way they do.

Priority order: things that make the server more useful to agents today, then things that make it easier to deploy and operate, then developer experience improvements. Features that don't serve the agent-first use case don't belong here regardless of how popular the request is.

If you want to influence the roadmap, open a [discussion](https://github.com/procontexthq/procontext/discussions) before opening a PR.
