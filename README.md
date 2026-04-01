<div align="left">

# <img src="https://procontext.dev/favicon.png" alt="ProContext logo" width="22" /> ProContext

**Documentation layer for AI coding agents**

[![License: MIT][license-badge]][license-url]
[![Website][website-badge]][website-url]
[![Python 3.12+][python-badge]][python-url]
[![Protocol][protocol-badge]][protocol-url]

</div>

Your AI coding agent relies on outdated or generic information about the libraries you use.

ProContext fixes this by giving your agent the reference docs it needs - current version, right API, every time.

Open-source [MCP](https://modelcontextprotocol.io) server · 2000+ libraries ([live registry](https://procontexthq.github.io/)) · Works with Claude Code, Cursor, Codex, Windsurf

[website-badge]: https://img.shields.io/badge/website-procontext.dev-aqua.svg
[website-url]: https://procontext.dev
[license-badge]: https://img.shields.io/badge/License-MIT-green.svg
[license-url]: https://opensource.org/licenses/MIT
[python-badge]: https://img.shields.io/badge/python-3.12%2B-yellow.svg
[python-url]: https://www.python.org/downloads/
[protocol-badge]: https://img.shields.io/badge/protocol-MCP-blue.svg
[protocol-url]: https://modelcontextprotocol.io

---

## Why ProContext

Coding agents hallucinate API details when libraries update faster than training data. ProContext fixes this - your agent reads from a curated, verified source instead of guessing from memory.

| | Without ProContext | With ProContext |
| --- | --- | --- |
| 🔍 **Discovery** | Agent guesses APIs from stale training data | Agent reads from a curated registry of 2000+ libraries |
| 📄 **Sources** | Web scraping and outdated search results | Hand-picked, verified documentation sources - no scraping, no noise |
| 🔄 **Freshness** | Docs go stale as libraries update | Registry refreshes automatically in the background |
| ⚡ **Speed** | Repeated fetches hit the network every time | Every page cached after the first fetch - millisecond lookups |
| 📐 **Context** | Entire docs dumped into context | Large pages served in paginated windows to respect token limits |
| 🎯 **Precision** | Agent scrolls through irrelevant content | Search within a page or browse its outline to jump to the right section |
| 🔒 **Safety** | Arbitrary URL access risks data leaks | Fetches restricted to known documentation domains |

## 🚀 Quick Start

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

## 🛠️ Manual Install

For manual install, version pinning, troubleshooting, and installer options, see [docs/cli/installation.md](docs/cli/installation.md).

## 🔌 Integrations

ProContext works with any MCP-compatible tool. The **[Setup Guide](docs/setup.md)** has copy-paste configurations for:

- **Claude Code** - CLI command or `.mcp.json`
- **Claude Desktop** - `claude_desktop_config.json`
- **Cursor** - `.cursor/mcp.json`
- **Windsurf** - `mcp_config.json`
- **VS Code (GitHub Copilot)** - `.vscode/mcp.json`
- **OpenAI Codex CLI** - `config.toml`
- **Amazon Q CLI** - `mcp.json`

Both stdio (local) and HTTP (shared/remote) transports are supported.

## 📖 Documentation

- [Setup guide](docs/setup.md) - install and connect to Claude Code, Cursor, Codex, VS Code, Windsurf, and more
- [Installation guide](docs/cli/installation.md) - installer options, manual install, troubleshooting
- [CLI docs](docs/cli/README.md)
- [API reference](docs/specs/04-api-reference.md)
- [Technical spec](docs/specs/02-technical-spec.md)
- [Project site](https://procontext.dev)

## 📚 Registry

The library registry is maintained in a separate repository: **[procontexthq/procontexthq.github.io](https://github.com/procontexthq/procontexthq.github.io)**

If you want to add a library or update an existing entry, open a PR there rather than in this repository.

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contributor setup, development workflow, coding conventions, and pull request guidance.

## 📝 License

MIT - see [LICENSE](LICENSE) for details.

---

**Built with ❤️ for AI coding agents**