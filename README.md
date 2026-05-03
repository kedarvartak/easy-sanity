# Easy Sanity

A completely free browser automation MCP server that uses your IDE's built-in LLM - no API keys required!

This is a free alternative to paid browser automation services like use-browser API. It runs locally and uses your IDE's AI (Claude Code, Cursor, Cline, etc.) to control the browser.

## Features

- **100% Free** - No API keys, no subscriptions, no usage limits
- **Uses IDE LLMs** - Leverages your IDE's AI (Claude Code, Cursor, etc.)
- **Visual Browser Control** - See the browser as it works (or run headless)
- **Screenshot Analysis** - LLM sees the page and decides what to do
- **Full Browser Actions** - Click, type, navigate, scroll, extract data
- **Session Management** - Persistent browser sessions across multiple actions
- **Saved Tasks** - Create reusable tasks and invoke them with /slash-commands

## Installation

### Quick Start

```bash
./scripts/setup.sh
```

This will:

- install project dependencies with `uv sync`
- install the Playwright Chromium browser
- leave you ready to connect the MCP server in your IDE

### 1. Install dependencies manually

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync

# Install Playwright browsers
uv run playwright install chromium
```

### 2. Configure in your IDE

Add this to your MCP settings:

**Claude Code** (`~/.config/claude-code/mcp.json`):
```json
{
  "mcpServers": {
    "browser-automation": {
      "command": "uv",
      "args": [
        "--directory",
        "/home/kedar/Desktop/Projects/use_browser",
        "run",
        "main.py"
      ]
    }
  }
}
```

**Cursor** (`.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "browser-automation": {
      "command": "uv",
      "args": [
        "--directory",
        "/home/kedar/Desktop/Projects/use_browser",
        "run",
        "main.py"
      ]
    }
  }
}
```

**Cline** (Cline settings - MCP Servers):
```json
{
  "mcpServers": {
    "browser-automation": {
      "command": "uv",
      "args": [
        "--directory",
        "/home/kedar/Desktop/Projects/use_browser",
        "run",
        "main.py"
      ]
    }
  }
}
```

### 3. Restart your IDE

Restart Claude Code/Cursor/Cline to load the MCP server.

### 4. Optional runtime defaults

You can set these environment variables if you want easier first-run defaults:

```bash
export BROWSER_HEADLESS_DEFAULT=true
export BROWSER_DEFAULT_TIMEOUT_MS=45000
```

- `BROWSER_HEADLESS_DEFAULT`: when `true`, `browser_start` runs headless unless explicitly overridden
- `BROWSER_DEFAULT_TIMEOUT_MS`: default Playwright timeout for page actions

### 5. Optional sample task pack

The repo includes bundled sample tasks for quick smoke-test onboarding.

Useful tools:

- `sample_tasks_list` - list the bundled sample tasks
- `sample_tasks_import()` - import all bundled sample tasks
- `sample_tasks_import(names_json='["smoke_example_homepage"]')` - import only selected sample tasks

## Task System

You can save reusable browser automation tasks and invoke them as /slash-commands in your IDE.

### Create a task

In your IDE, tell the AI:

```
Create a browser task named "google_search" with prompt:
"Go to www.google.com, type 'Python tutorials' in the search box,
press Enter, and return the titles of the first 3 results."
```

The AI calls `task_create("google_search", "...")` which:
1. Saves the task to `tasks.json`
2. Registers it as the `/google_search` slash-command in your IDE

### Run a saved task

Type `/google_search` in your IDE's command palette. The IDE's LLM receives
the full browser instruction and executes it using the browser tools automatically.

### Manage tasks

- `task_list` - see all saved tasks
- `task_get(name)` - view a task's full prompt
- `task_delete(name)` - remove a task

Tasks persist across server restarts via `tasks.json`.

## Basic Usage (without saved tasks)

Just give your IDE's AI a prompt like:

```
Use the browser automation MCP to:
1. Go to Google
2. Search for "Python tutorials"
3. Get the top 3 result titles
```

The AI will use these tools automatically:
- `browser_start` - Start a browser
- `browser_navigate` - Go to google.com
- `browser_get_state` - See the page
- `browser_type` - Type in the search box
- `browser_click` - Click search
- `browser_extract` - Get the results
- `browser_stop` - Clean up

## Available Tools

### Task Tools

| Tool | Description |
|------|-------------|
| `task_create` | Create/save a task as a /slash-command |
| `task_list` | List all saved tasks |
| `task_get` | Get details of a specific task |
| `task_delete` | Remove a saved task |
| `task_wizard_template` | Generate a starter task draft |
| `task_lint` | Lint a raw or saved task prompt |
| `task_render` | Render a templated task with variables |
| `profile_save` / `profile_list` / `profile_get` / `profile_delete` | Manage environment profiles |
| `sample_tasks_list` | List bundled sample tasks |
| `sample_tasks_import` | Import bundled sample tasks into saved tasks |

### Browser Tools

| Tool | Description |
|------|-------------|
| `browser_start` | Start a new browser session |
| `browser_get_state` | Get page state + screenshot |
| `browser_navigate` | Navigate to a URL |
| `browser_click` | Click an element |
| `browser_type` | Type text into an input |
| `browser_scroll` | Scroll the page |
| `browser_extract` | Extract text from an element |
| `browser_wait` | Wait N seconds |
| `browser_stop` | End session and clean up |
| `browser_get_history` | View action history |

## How It Works

```
Your Prompt / /slash-command
         |
         v
   IDE's LLM (Claude, etc)  <-- sees screenshots and page state
         |
         v
    MCP Tools
    - navigate
    - click
    - type
    - extract
         |
         v
    Playwright (Browser)
```

1. You give a prompt or invoke a saved /task
2. Your IDE's LLM breaks it down into steps
3. It calls browser tools step by step
4. The LLM sees screenshots to make visual decisions
5. Results are returned to you

## Comparison with use-browser API

| Feature | This MCP Server | use-browser API |
|---------|----------------|-----------------|
| Cost | Free | Paid (credits system) |
| API Keys | None needed | Required |
| Usage Limits | Unlimited | Based on credits |
| Privacy | Runs locally | Sends to API |
| Speed | Local execution | API latency |
| Customization | Full control | Limited |
| LLM | Your IDE's LLM | Their LLM |

## Troubleshooting

**Browser not starting:**
```bash
uv run playwright install chromium
```

Or run:

```bash
./scripts/setup.sh
```

**Tools not showing in IDE:**
1. Check MCP configuration file path
2. Restart IDE completely
3. Check IDE's MCP logs

**Timeouts:**
Use `browser_wait(seconds=5)` after clicks that trigger page loads.

**Need a quick first task:**
1. Run `sample_tasks_list`
2. Import one with `sample_tasks_import`
3. Render it with `task_render` if it uses placeholders

## License

MIT License
