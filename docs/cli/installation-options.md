# Installation Options And Installer Reference

This page covers alternate installation paths, manual installs, troubleshooting, and the maintainer contract for the repository installer scripts.

For the standard install flow, use [installation.md](installation.md).

## Script-Based Installs

### Default PyPI Install

macOS and Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/procontexthq/procontext/main/install.sh | bash
```

Windows:

```powershell
powershell -c "irm https://raw.githubusercontent.com/procontexthq/procontext/main/install.ps1 | iex"
```

### Version Pinning

macOS and Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/procontexthq/procontext/main/install.sh | bash -s -- --version 0.1.2
```

Windows:

```powershell
powershell -c "& ([scriptblock]::Create((irm https://raw.githubusercontent.com/procontexthq/procontext/main/install.ps1))) -Version 0.1.2"
```

### Skip Setup

macOS and Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/procontexthq/procontext/main/install.sh | bash -s -- --no-setup
```

Windows:

```powershell
powershell -c "& ([scriptblock]::Create((irm https://raw.githubusercontent.com/procontexthq/procontext/main/install.ps1))) -NoSetup"
```

If you skip setup, run:

```bash
uvx procontext setup
uvx procontext doctor
```

### GitHub Source Install

Use the GitHub install when you want the latest source checkout or when package installation is unavailable in your environment.

macOS and Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/procontexthq/procontext/main/install.sh | bash -s -- --from-source
```

Windows:

```powershell
powershell -c "& ([scriptblock]::Create((irm https://raw.githubusercontent.com/procontexthq/procontext/main/install.ps1))) -FromSource"
```

When you use the GitHub install, ProContext should be run with an explicit project path:

```bash
uv run --project "/path/to/procontext-source" procontext
uv run --project "/path/to/procontext-source" procontext setup
uv run --project "/path/to/procontext-source" procontext doctor
```

Replace `/path/to/procontext-source` with the absolute path to your checkout.

For MCP client config in GitHub source mode, use:

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

## Installer Options

### `install.sh`

- `--version VERSION` pins the published package version in the default mode
- `--from-source` switches to the GitHub source install
- `--dir PATH` source mode only: installs or refreshes the checkout at `PATH`
- `--repo URL` source mode only: uses a different Git repository
- `--ref REF` source mode only: installs a branch, tag, or commit
- `--version REF` is also accepted as a deprecated alias for `--ref` in source mode
- `--no-setup` skips `procontext setup`
- `--dry-run` prints the plan without making changes

### `install.ps1`

- `-Version VERSION` pins the published package version in the default mode
- `-FromSource` switches to the GitHub source install
- `-InstallDir PATH` source mode only: installs or refreshes the checkout at `PATH`
- `-RepoUrl URL` source mode only: uses a different Git repository
- `-InstallRef REF` source mode only: installs a branch, tag, or commit
- `-Version REF` is also accepted as a deprecated alias for `-InstallRef` in source mode
- `-NoSetup` skips `procontext setup`
- `-DryRun` prints the plan without making changes

## Manual Installs

### Published Package

If you do not want to use the helper scripts:

```bash
uvx procontext setup
uvx procontext doctor
```

For stdio MCP integrations, do not run `uvx procontext` yourself. Your MCP client will launch ProContext automatically.

Start ProContext manually only when you want HTTP mode:

```bash
PROCONTEXT__SERVER__TRANSPORT=http uvx procontext
```

### GitHub Source Install

If you want a manual GitHub install instead of using the scripts:

```bash
git clone https://github.com/procontexthq/procontext.git
cd procontext
uv sync --no-dev
uv run --project /path/to/procontext-source procontext setup
uv run --project /path/to/procontext-source procontext doctor
```

For stdio MCP integrations, configure the client to launch:

```bash
uv run --project /path/to/procontext-source procontext
```

Start ProContext manually only when you want HTTP mode:

```bash
PROCONTEXT__SERVER__TRANSPORT=http uv run --project /path/to/procontext-source procontext
```

Replace `/path/to/procontext-source` with the absolute path to your cloned checkout.

## Troubleshooting

- If `uv` or `uvx` is reported as missing after install, open a new shell so the updated PATH is loaded.
- If package installation fails, or if you want the latest source checkout, use the GitHub install via `--from-source` or `-FromSource`.
- If the managed checkout has local changes, the GitHub installer will not overwrite them during an update.
- If the one-time registry download fails, rerun `procontext setup`, then `procontext doctor`, after fixing connectivity.
- For contributor setup, do not use the runtime installer flow. Use [CONTRIBUTING.md](../../CONTRIBUTING.md) and `uv sync --dev`.

## Maintainer Reference

This section defines the contract for the repository installer scripts:

- [`install.sh`](../../install.sh)
- [`install.ps1`](../../install.ps1)

These are the only supported public installer entrypoints. Do not reintroduce parallel families such as `install_cl.*` or `install_cx.*`.

### Why The Installers Live At The Repo Root

The public install URLs should be short and stable:

- `.../install.sh`
- `.../install.ps1`

Keeping the files at the repository root also makes it obvious which scripts are user-facing and avoids burying the public entrypoints inside a docs or tooling directory.

### Behavioral Contract

Both installers should preserve the same high-level behavior:

- default to a PyPI-first install flow using `uvx procontext`
- keep the GitHub checkout flow available through an explicit source-install flag
- avoid silently or automatically switching from PyPI mode to source mode
- default to the latest published package unless a package version is provided
- run checkout sync (`uv sync --project ... --no-dev`) only in GitHub source mode
- default to the `main` branch only in GitHub source mode unless a ref is provided
- accept raw refs directly in GitHub source mode; do not force a `v` prefix onto tags
- run `procontext setup` by default, with an explicit skip flag
- keep `--dry-run` or `-DryRun` side-effect free
- avoid overwriting a dirty checkout during GitHub source updates
- print `uvx procontext` as the canonical way to start the server

### Platform-Specific Responsibilities

#### `install.sh`

- support macOS and Linux
- bootstrap `uv` through Homebrew or Astral's official installer
- add user-local bin directories to PATH when needed
- bootstrap `git` through Homebrew or the system package manager only in GitHub source mode

#### `install.ps1`

- support Windows PowerShell 5+ and PowerShell 7+
- bootstrap `uv` through `winget`, `choco`, `scoop`, or Astral's official installer
- refresh PATH after package-manager installs so the current shell can continue
- bootstrap `git` through `winget`, `choco`, `scoop`, or portable Git only in GitHub source mode

### End-User Vs Development Setup

The installer scripts are for runtime installation only. They should not create a contributor environment.

Contributor setup belongs in [CONTRIBUTING.md](../../CONTRIBUTING.md) and should continue to use:

```bash
uv sync --dev
```

End-user setup should continue to use:

```bash
uvx procontext
```

### Docs That Must Stay In Sync

If the installer behavior changes, update these docs in the same change:

- [README.md](../../README.md) installation section
- [installation.md](installation.md)
- [CONTRIBUTING.md](../../CONTRIBUTING.md) if development prerequisites or setup guidance changed

### Validation Checklist

When changing the installers, validate at least:

#### Unix

```bash
bash -n install.sh
bash install.sh --dry-run
bash install.sh --from-source --dry-run --dir /tmp/procontext-install-test
```

#### Windows

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -DryRun
powershell -ExecutionPolicy Bypass -File .\install.ps1 -FromSource -DryRun
```

If you have PowerShell 7 available:

```powershell
pwsh -NoProfile -File .\install.ps1 -DryRun
pwsh -NoProfile -File .\install.ps1 -FromSource -DryRun
```

Also verify:

- the docs still use the current flag names
- the installer still points at the correct repository URL for GitHub source mode
- the default MCP config snippet uses `uvx`
- the source-install MCP config snippet still uses `uv run --project`

### PyPI-First Contract

These scripts are intentionally PyPI-first now.

Keep these rules in place unless the public install model changes again:

- one public script per platform remains the rule
- default installation uses `uvx procontext`
- GitHub source installs remain explicit and manual, not an automatic retry path
- `git` is only required in GitHub source mode
- package-version pinning belongs to the default PyPI path
- source-mode knobs (`--dir`, `--repo`, `--ref`, etc.) remain fallback-only
