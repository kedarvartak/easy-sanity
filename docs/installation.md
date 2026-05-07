# Easy Sanity Installation Guide

This guide covers the recommended ways to install and run Easy Sanity:

- `uvx` for the fastest no-clone setup
- `pipx` for a permanent global install
- source checkout setup for development

## Recommended: `uvx` Install

This is the easiest way to run Easy Sanity without cloning the repository.

### 1. Install the Playwright browser

```bash
uvx easy-sanity install-browser
```

### 2. Configure your MCP client

Use this launch command:

```bash
uvx easy-sanity
```

Example MCP config:

```json
{
  "mcpServers": {
    "easy-sanity": {
      "command": "uvx",
      "args": ["easy-sanity"],
      "env": {
        "BROWSER_HEADLESS_DEFAULT": "true",
        "BROWSER_DEFAULT_TIMEOUT_MS": "45000",
        "BROWSER_BACKEND_DEFAULT": "playwright",
        "BROWSER_HARNESS_ENABLED": "false",
        "BROWSER_REPORTS_DIR": "artifacts/reports",
        "BROWSER_SCREENSHOTS_DIR": "artifacts/screenshots",
        "BROWSER_DOWNLOADS_DIR": "artifacts/downloads",
        "APP_MEMORY_DIR": "data/app_memory"
      }
    }
  }
}
```

## Permanent Install: `pipx`

Use this if you want a globally available `easy-sanity` command.

### 1. Install the package

```bash
pipx install easy-sanity
```

### 2. Install the Playwright browser

```bash
easy-sanity install-browser
```

### 3. Configure your MCP client

Use this launch command:

```bash
easy-sanity
```

Example MCP config:

```json
{
  "mcpServers": {
    "easy-sanity": {
      "command": "easy-sanity",
      "args": [],
      "env": {
        "BROWSER_HEADLESS_DEFAULT": "true",
        "BROWSER_DEFAULT_TIMEOUT_MS": "45000"
      }
    }
  }
}
```

## Development Install From Source

Use this when you are working on the repo itself.

### Quick setup

```bash
./scripts/setup.sh
```

This does:

- `uv sync`
- `uv run easy-sanity install-browser`

### Manual setup

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
uv run easy-sanity install-browser
```

### Run from the repo

```bash
uv run easy-sanity
```

## MCP Client Examples

### Codex

```json
{
  "mcpServers": {
    "easy-sanity": {
      "command": "uvx",
      "args": ["easy-sanity"],
      "env": {
        "BROWSER_HEADLESS_DEFAULT": "true",
        "BROWSER_DEFAULT_TIMEOUT_MS": "45000",
        "BROWSER_REPORTS_DIR": "artifacts/reports",
        "BROWSER_SCREENSHOTS_DIR": "artifacts/screenshots",
        "BROWSER_DOWNLOADS_DIR": "artifacts/downloads",
        "APP_MEMORY_DIR": "data/app_memory"
      }
    }
  }
}
```

### Claude Code

```json
{
  "mcpServers": {
    "browser-automation": {
      "command": "easy-sanity",
      "args": [],
      "env": {
        "BROWSER_HEADLESS_DEFAULT": "true",
        "BROWSER_DEFAULT_TIMEOUT_MS": "45000"
      }
    }
  }
}
```

### Cursor

```json
{
  "mcpServers": {
    "browser-automation": {
      "command": "easy-sanity",
      "args": [],
      "env": {
        "BROWSER_HEADLESS_DEFAULT": "true",
        "BROWSER_DEFAULT_TIMEOUT_MS": "45000"
      }
    }
  }
}
```

### Cline

```json
{
  "mcpServers": {
    "browser-automation": {
      "command": "easy-sanity",
      "args": [],
      "env": {
        "BROWSER_HEADLESS_DEFAULT": "true",
        "BROWSER_DEFAULT_TIMEOUT_MS": "45000"
      }
    }
  }
}
```

## Runtime Paths

Installed builds default to a user-owned app data directory.

Source-checkout runs keep using repo-local paths unless you override them with environment variables.

Useful environment variables:

- `BROWSER_HEADLESS_DEFAULT`
- `BROWSER_DEFAULT_TIMEOUT_MS`
- `BROWSER_BACKEND_DEFAULT`
- `BROWSER_HARNESS_ENABLED`
- `BROWSER_HARNESS_COMMAND`
- `BROWSER_HARNESS_REPO`
- `BROWSER_REPORTS_DIR`
- `BROWSER_SCREENSHOTS_DIR`
- `BROWSER_DOWNLOADS_DIR`
- `APP_MEMORY_DIR`
- `EASY_SANITY_HOME`

You can inspect the active runtime paths with:

```bash
easy-sanity paths
```

Or from a repo checkout:

```bash
uv run easy-sanity paths
```

## Troubleshooting

### `easy-sanity: command not found`

- If you used `pipx`, confirm `pipx` is on your shell path.
- If you used `uvx`, run the server through `uvx easy-sanity` instead of `easy-sanity`.

### Browser launch fails

Install Chromium first:

```bash
easy-sanity install-browser
```

Or with `uvx`:

```bash
uvx easy-sanity install-browser
```

### MCP client starts but no tools appear

- Restart the MCP client or IDE fully.
- Re-check the `command`, `args`, and `env` fields in the MCP config.
- Try running the same launch command directly in a terminal first.
