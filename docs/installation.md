# Installation

ProContext supports four installation methods:

- script install from the published package using `uvx`
- script install from the GitHub source checkout
- manual install from the published package using `uvx`
- manual install from the GitHub source checkout

The recommended option for most users is the script-based published package install.

## Quick Installs 🚀

### Recommended: Script Install From The Published Package

For most users, these installers are the right choice. By default, they will:

- ensure `uv` is available
- run the published `procontext` package via `uvx`
- run the one-time `procontext setup` step unless you skip it

macOS and Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/procontexthq/procontext/main/install.sh | bash
```

Windows:

```powershell
powershell -c "irm https://raw.githubusercontent.com/procontexthq/procontext/main/install.ps1 | iex"
```

Verify the install:

```bash
uvx procontext doctor
```

### Script Install From GitHub Source

Use this when you want the latest source checkout or when package installation is unavailable.

macOS and Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/procontexthq/procontext/main/install.sh | bash -s -- --from-source
```

Windows:

```powershell
powershell -c "& ([scriptblock]::Create((irm https://raw.githubusercontent.com/procontexthq/procontext/main/install.ps1))) -FromSource"
```

Verify the install with the checkout path printed by the installer:

```bash
uv run --project "/path/to/procontext-source" procontext doctor
```

## Manual Installs 🛠️

### Manual Install From The Published Package

```bash
uvx procontext setup
uvx procontext doctor
```

### Manual Install From GitHub Source

```bash
git clone https://github.com/procontexthq/procontext.git
cd procontext
uv sync --no-dev
uv run --project /path/to/procontext-source procontext setup
uv run --project /path/to/procontext-source procontext doctor
```

Replace `/path/to/procontext-source` with the absolute path to your cloned checkout.

## After Install: Connect Your Agent 🔌

For normal MCP integrations, you do not need to start ProContext yourself in stdio mode. Your agent or MCP client will launch it after you add ProContext to the client configuration.

Add ProContext to your tool using the copy-paste configs in [integration-guide.md](integration-guide.md).

Start ProContext manually only when you want to run it in HTTP mode for a shared or remote deployment. The HTTP setup steps are also in [integration-guide.md](integration-guide.md).

## Need More Detail?

For version pinning, installer flags, troubleshooting, and installer reference details, see [installation-options.md](installation-options.md).
