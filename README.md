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

Live registry: [procontexthq.github.io](https://procontexthq.github.io/)


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

Coding agents hallucinate API details when libraries update faster than training data. ProContext fixes this - your agent reads from a curated, verified source instead of guessing from memory.

- **First-class llms.txt support** - built around the [llms.txt](https://llmstxt.org/) standard with a growing registry of 650+ libraries and expanding. Documentation pages are served in whatever format they're published - the agent gets clean, structured content regardless of the source.
- **Focused, curated documentation** - your agent pulls from a hand-picked registry of known documentation sources. No web scraping, no outdated search results - just the right docs.
- **Always up to date** - the registry refreshes automatically in the background. No manual pulls, no stale library lists.
- **Fast, cached retrievals** - every page is cached after the first fetch. Repeated reads, searches, and outline lookups return in milliseconds.
- **Paginated to respect token limits** - large pages are served in windows, not dumped whole. Your agent reads only what it needs without blowing up its context.
- **Jump straight to the right section** - search within a page or browse its outline to land on the exact function, class, or example - no scrolling through irrelevant content.
- **Protected from unknown lookups** - fetches are restricted to known documentation domains. No arbitrary URL access, no accidental data leaks.
- **Works with the agent you already use** - Claude Code, Cursor, Codex, VS Code, Windsurf, Amazon Q, and anything else that speaks MCP.
- **Setup in seconds** - one command installs ProContext on macOS, Linux, or Windows. You're up and running before your coffee gets cold.

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

The installer manages a local checkout and prints the path to use with `uv run --project ...`. For tool-specific setup (Claude Code, Cursor, Codex, VS Code, Windsurf, and more), see the **[Setup Guide](docs/setup.md)**.

For manual install, version pinning, troubleshooting, and installer options, see [docs/cli/installation.md](docs/cli/installation.md).

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

ProContext works with any MCP-compatible tool. The **[Setup Guide](docs/setup.md)** has copy-paste configurations for:

- **Claude Code** - CLI command or `.mcp.json`
- **Claude Desktop** - `claude_desktop_config.json`
- **Cursor** - `.cursor/mcp.json`
- **Windsurf** - `mcp_config.json`
- **VS Code (GitHub Copilot)** - `.vscode/mcp.json`
- **OpenAI Codex CLI** - `config.toml`
- **Amazon Q CLI** - `mcp.json`

Both stdio (local) and HTTP (shared/remote) transports are covered.

## Documentation

- [Setup guide](docs/setup.md) - install and connect to Claude Code, Cursor, Codex, VS Code, Windsurf, and more
- [Installation guide](docs/cli/installation.md) - installer options, manual install, troubleshooting
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