<div align="left">

# ProContext

**Current library documentation for MCP-based coding agents.**

[![Website][website-badge]][website-url]
[![License: MIT][license-badge]][license-url]
[![Python 3.12+][python-badge]][python-url]
[![Protocol][protocol-badge]][protocol-url]
[![Specification][spec-badge]][spec-url]

</div>

ProContext is an open-source [MCP](https://modelcontextprotocol.io) server for Claude Code, Cursor, Codex, Windsurf, and other MCP clients. It resolves libraries from a curated registry of known documentation sources, then serves live `llms.txt`, README, and documentation pages on demand so agents can work against current APIs instead of stale training data.

Project site: [procontext.dev](https://procontext.dev)

[website-badge]: https://img.shields.io/badge/website-procontext.dev-blue.svg
[website-url]: https://procontext.dev
[license-badge]: https://img.shields.io/badge/License-MIT-blue.svg
[license-url]: https://opensource.org/licenses/MIT
[python-badge]: https://img.shields.io/badge/python-3.12%2B-blue.svg
[python-url]: https://www.python.org/downloads/
[protocol-badge]: https://img.shields.io/badge/protocol-modelcontextprotocol.io-blue.svg
[protocol-url]: https://modelcontextprotocol.io
[spec-badge]: https://img.shields.io/badge/spec-spec.modelcontextprotocol.io-blue.svg
[spec-url]: https://modelcontextprotocol.io/specification/latest

---

## Why ProContext

Coding agents are good at deciding what documentation they need, but they still fail when the underlying library APIs have changed. ProContext keeps the navigation with the agent and makes the retrieval side predictable:

- **Registry-first resolution**: library lookup runs against an in-memory index built from a curated registry of known documentation sources.
- **Live documentation fetches**: agents read current `llms.txt`, README, and documentation pages instead of relying only on model memory.
- **Shared cache with stale fallback**: fetched pages are cached in SQLite and reused across `read_page`, `search_page`, and `read_outline`.
- **Constrained fetch surface**: documentation fetches are limited by an SSRF allowlist derived from the registry, with private IP ranges blocked.
- **MCP-native transports**: supports stdio for local MCP clients and Streamable HTTP for shared deployments.
- **Cross-platform defaults**: config, cache, and data paths resolve through `platformdirs` on macOS, Linux, and Windows.

## Quick Start

Install ProContext:

### macOS and Linux

```bash
curl -fsSL https://raw.githubusercontent.com/procontexthq/procontext/main/install.sh | bash
```

### Windows

Run this in a PowerShell terminal:

```powershell
irm https://raw.githubusercontent.com/procontexthq/procontext/main/install.ps1 | iex
```

Add ProContext to your MCP client config:

```json
{
  "mcpServers": {
    "procontext": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/procontext-source", "procontext"]
    }
  }
}
```

The installer manages a local checkout and prints the path to use with `uv run --project ...`. For manual install, version pinning, troubleshooting, and installer options, see [docs/cli/installation.md](docs/cli/installation.md).

## What ProContext Exposes

ProContext exposes four MCP tools:

- `resolve_library`: resolve a package, library name, or alias to a known documentation source.
- `read_page`: read an `llms.txt` index, README, or documentation page with a compact outline and content window.
- `search_page`: search within a documentation page and return matching lines plus outline context.
- `read_outline`: page through a full outline when a page is too large for the compact outline returned by `read_page` or `search_page`.

Typical flow:

```text
resolve_library("langchain-openai")
  -> index_url

read_page(index_url)
  -> documentation index / links

search_page(page_url, "streaming")
  -> matching lines and sections

read_outline(page_url)
  -> full structure for large pages
```

For detailed request and response contracts, see [docs/specs/04-api-reference.md](docs/specs/04-api-reference.md).

## Integrations

### stdio

Most MCP clients use the same stdio configuration shown in Quick Start. Use the managed checkout path printed by the installer.

For Claude Code:

```bash
claude mcp add procontext -- uv run --project /path/to/procontext-source procontext
```

## HTTP / Deployment Note

ProContext also supports MCP Streamable HTTP for shared or remote deployments.

Client configuration:

```json
{
  "mcpServers": {
    "procontext": {
      "url": "http://your-server:8080/mcp"
    }
  }
}
```

Server configuration:

```yaml
server:
  transport: http
  host: "127.0.0.1"
  port: 8080
```

Then run:

```bash
uv run --project /path/to/procontext-source procontext
```

For full installation, runtime, and troubleshooting details, see [docs/cli/installation.md](docs/cli/installation.md) and [docs/specs/04-api-reference.md](docs/specs/04-api-reference.md).

## Documentation

- [Installation guide](docs/cli/installation.md)
- [CLI docs](docs/cli/README.md)
- [API reference](docs/specs/04-api-reference.md)
- [Technical spec](docs/specs/02-technical-spec.md)
- [Project site](https://procontext.dev)

## Registry

The library registry is maintained in a separate repository: **[procontexthq/procontexthq.github.io](https://github.com/procontexthq/procontexthq.github.io)**

If you want to add a library or update an existing entry, open a PR there rather than in this repository.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contributor setup, development workflow, coding conventions, and pull request guidance.

## License

MIT - see [LICENSE](LICENSE) for details.

---

**Built with ❤️ for AI coding agents**