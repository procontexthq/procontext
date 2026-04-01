# Integration Guide

This guide covers connecting ProContext to your AI coding tool. For installation, see [installation.md](cli/installation.md).

ProContext runs as a **stdio** server by default — your AI tool launches it as a subprocess. Every tool below uses the same underlying command:

```
uv run --project <install-path> procontext
```

Replace `<install-path>` with the checkout path from the installer. The examples below use placeholder paths — substitute your actual path.

---

### Claude Code

Claude Code has a built-in CLI command to add MCP servers.

**Add via CLI (recommended):**

```bash
claude mcp add procontext -s user -- uv run --project /path/to/procontext-source procontext
```

The `-s user` flag makes ProContext available across all your projects. Use `-s project` to scope it to the current project only.

**Or add via project config (`.mcp.json` in project root):**

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

This file can be checked into version control so the whole team gets ProContext automatically.

**Verify it's working:**

```bash
claude mcp list
```

---

### Claude Desktop

Edit the config file directly, then restart Claude Desktop.

**Config file location:**

| Platform | Path |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/claude-desktop/claude_desktop_config.json` |

**Add this to the config file:**

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

If the file already has other MCP servers, add the `"procontext"` entry inside the existing `"mcpServers"` object.

Restart Claude Desktop after saving. Logs are at `~/Library/Logs/Claude/mcp*.log` (macOS) or `%APPDATA%\Claude\logs\` (Windows).

---

### Cursor

Edit the MCP config file. No restart required — Cursor picks up changes automatically.

**Config file location:**

| Scope | Path |
|---|---|
| Project | `.cursor/mcp.json` in project root |
| Global | `~/.cursor/mcp.json` |

**Add this to the config file:**

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

Use the project-level config to share ProContext with your team via version control, or the global config to make it available everywhere.

---

### Windsurf

Edit the Windsurf MCP config file.

**Config file location:** `~/.codeium/windsurf/mcp_config.json`

**Add this to the config file:**

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

---

### VS Code (GitHub Copilot)

Requires VS Code 1.99 or later with GitHub Copilot. MCP servers are configured in `.vscode/mcp.json`.

> **Note:** VS Code uses `"servers"` as the root key, not `"mcpServers"`.

**Add via CLI:**

```bash
code --add-mcp '{"name":"procontext","command":"uv","args":["run","--project","/path/to/procontext-source","procontext"]}'
```

**Or create `.vscode/mcp.json` in your project:**

```json
{
  "servers": {
    "procontext": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/procontext-source", "procontext"]
    }
  }
}
```

This file can be checked into version control.

---

### OpenAI Codex CLI

Codex uses TOML configuration, not JSON.

**Add via CLI:**

```bash
codex mcp add procontext -- uv run --project /path/to/procontext-source procontext
```

**Or edit `~/.codex/config.toml` manually:**

```toml
[mcp_servers.procontext]
command = "uv"
args = ["run", "--project", "/path/to/procontext-source", "procontext"]
```

View active MCP servers in the Codex TUI with the `/mcp` command.

---

### Amazon Q CLI

**Add via CLI:**

```bash
q mcp add --name procontext --command uv --args "run,--project,/path/to/procontext-source,procontext"
```

**Or edit `~/.aws/amazonq/mcp.json`:**

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

Use `/tools trust` in the Q CLI chat to allow ProContext's tools to run without confirmation.

---

## HTTP transport

For shared or remote deployments, ProContext can run as an HTTP server instead of stdio. This is useful when multiple developers or services need to share a single ProContext instance.

### 1. Configure the server

Create `procontext.yaml` in the working directory or in the platform config directory:

```yaml
server:
  transport: http
  host: "127.0.0.1"
  port: 8080
```

Or use environment variables:

```bash
PROCONTEXT__SERVER__TRANSPORT=http PROCONTEXT__SERVER__PORT=8080 uv run --project /path/to/procontext-source procontext
```

### 2. Start the server

```bash
uv run --project /path/to/procontext-source procontext
```

The server listens at `http://127.0.0.1:8080/mcp`.

### 3. Connect your tool

Point your AI tool at the server URL instead of launching a subprocess.

**Claude Code:**

```bash
claude mcp add --transport http procontext http://localhost:8080/mcp
```

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "procontext": {
      "type": "http",
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

**Cursor** (`.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "procontext": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

**Windsurf** (`~/.codeium/windsurf/mcp_config.json`):

```json
{
  "mcpServers": {
    "procontext": {
      "serverUrl": "http://localhost:8080/mcp"
    }
  }
}
```

> **Note:** Windsurf uses `"serverUrl"`, not `"url"`.

**VS Code** (`.vscode/mcp.json`):

```json
{
  "servers": {
    "procontext": {
      "type": "http",
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

**Codex CLI** (`~/.codex/config.toml`):

```toml
[mcp_servers.procontext]
url = "http://localhost:8080/mcp"
```

**Amazon Q CLI** (`~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "procontext": {
      "type": "http",
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

### Optional: bearer token auth

To require authentication on the HTTP server:

```yaml
server:
  transport: http
  host: "127.0.0.1"
  port: 8080
  auth_enabled: true
  auth_key: "your-secret-token"
```

Then pass the token in your client config. For example, in Claude Code:

```bash
claude mcp add --transport http --header "Authorization: Bearer your-secret-token" procontext http://localhost:8080/mcp
```

---

## Verify the connection

After setup, test that ProContext is working by asking your agent:

> "Use ProContext to look up the documentation for langchain"

The agent should call `resolve_library("langchain")` and return documentation URLs.

## Troubleshooting

- **"uv: command not found"** — open a new terminal after installing so `PATH` is updated, or install uv manually from [docs.astral.sh/uv](https://docs.astral.sh/uv/).
- **"No registry found"** — run `uv run --project /path/to/procontext-source procontext setup` to download the library registry.
- **Server not connecting** — run `uv run --project /path/to/procontext-source procontext doctor --fix` to diagnose and repair common issues.
- **Config file not found** — check the exact path for your platform listed above. Create the file if it doesn't exist.
- **Tools not appearing** — some tools require a restart (Claude Desktop) or a new session (Claude Code) after config changes.

For detailed troubleshooting, see [installation.md](cli/installation.md).
