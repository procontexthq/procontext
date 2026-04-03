# ProContext

**Documentation layer for AI coding agents**

[![License: MIT][license-badge]][license-url]
[![Website][website-badge]][website-url]
[![Python 3.12+][python-badge]][python-url]
[![Protocol][protocol-badge]][protocol-url]

Your AI coding agent generates broken code because it relies on outdated, generic information.

ProContext fixes this by feeding it the reference docs it needs - correct version, right API, every time.

[2000+ libraries](https://procontexthq.github.io/) · Works with Claude Code, Cursor, Codex, VS Code (GitHub Copilot), Windsurf, and any MCP-compatible tool

[website-badge]: https://img.shields.io/badge/website-procontext.dev-22d3ee.svg?textColor=black
[website-url]: https://procontext.dev
[license-badge]: https://img.shields.io/badge/License-MIT-green.svg
[license-url]: https://opensource.org/licenses/MIT
[python-badge]: https://img.shields.io/badge/python-3.12%2B-yellow.svg
[python-url]: https://www.python.org/downloads/
[protocol-badge]: https://img.shields.io/badge/protocol-MCP-blue.svg
[protocol-url]: https://modelcontextprotocol.io

---

## Why ProContext

| | Without ProContext | With ProContext |
| --- | --- | --- |
| **Discovery** | Agent guesses APIs from stale training data | Agent reads from a curated registry of 2000+ libraries |
| **Sources** | Web scraping and outdated search results | Hand-picked, verified documentation sources - no scraping, no noise |
| **Freshness** | Docs go stale as libraries update | Registry refreshes automatically in the background |
| **Speed** | Repeated fetches hit the network every time | Every page cached after the first fetch - millisecond lookups |
| **Context** | Entire docs dumped into context | Large pages served in paginated windows to respect token limits |
| **Precision** | Agent scrolls through irrelevant content | Search within a page or browse its outline to jump to the right section |
| **Safety** | Arbitrary URL access risks data leaks | Fetches restricted to known documentation domains |

## Quick Start

### 1. Install ProContext 🚀

Install ProContext using whichever path fits you best.

If you want the smoothest setup, the installer scripts are a good default. They take care of prerequisites like `uv` and run the initial setup step for you.

#### Recommended: Installer Script

#### macOS and Linux

```bash
curl -fsSL https://raw.githubusercontent.com/procontexthq/procontext/main/install.sh | bash
```

#### Windows

Run this in a PowerShell terminal:

```powershell
irm https://raw.githubusercontent.com/procontexthq/procontext/main/install.ps1 | iex
```

#### Alternative: Manual Install Using `uvx`

If you already have `uv`, you can install manually with:

```bash
uvx procontext setup
```

### 2. Verify The Install ✅

Run:

```bash
uvx procontext doctor
```

### 3. Add ProContext To Your MCP Client 🔌

Add ProContext to your MCP client config:

```json
{
  "mcpServers": {
    "procontext": {
      "command": "uvx",
      "args": ["procontext"]
    }
  }
}
```

For local MCP integrations, do not start ProContext yourself in stdio mode. Your agent will launch it automatically after you add it to your MCP client. Start ProContext manually only when you want HTTP mode.

For alternate install paths, version pinning, troubleshooting, and installer reference details, see [docs/installation.md](docs/installation.md) and [docs/installation-options.md](docs/installation-options.md).

ProContext works with any MCP-compatible tool. The **[Integration Guide](docs/integration-guide.md)** has copy-paste configurations for Claude Code, Claude Desktop, Cursor, Windsurf, VS Code (GitHub Copilot), OpenAI Codex CLI, and Amazon Q CLI. Both stdio (local) and HTTP (shared/remote) transports are supported.

## Documentation

- [Integration guide](docs/integration-guide.md)
- [Installation guide](docs/installation.md)
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
