<div align="center">

<h1>Easy Sanity</h1>

<p>
  <img alt="Python 3.12+" src="https://img.shields.io/badge/Python-3.12%2B-3a3a3a?style=flat-square&logo=python&logoColor=ffd43b&labelColor=2f2f2f&color=2563eb">
  <img alt="Playwright Chromium" src="https://img.shields.io/badge/Playwright-Chromium-3a3a3a?style=flat-square&logo=playwright&logoColor=45ba63&labelColor=2f2f2f&color=0f766e">
  <img alt="MCP Server" src="https://img.shields.io/badge/MCP-Server-3a3a3a?style=flat-square&logo=openai&logoColor=ffffff&labelColor=2f2f2f&color=7c3aed">
</p>

<p>
  <img src="artifacts/media/title.png" alt="Easy Sanity title art" width="900">
</p>

<p>
  Browser automation and sanity-testing MCP server for IDE agents.
</p>

<p>
  Official documentation:
  <a href="https://www.kedarvartak.com/agents/easy-sanity">https://www.kedarvartak.com/agents/easy-sanity</a>
</p>

</div>

## Idea

Easy Sanity gives an IDE agent a local browser it can operate through MCP tools.

Instead of building a separate hosted browser API, it keeps the whole loop local:

1. You ask Codex, Claude Code, Cursor, Cline, or another MCP-capable IDE agent to inspect or test a web flow.
2. The agent calls Easy Sanity tools.
3. Easy Sanity drives the browser, captures state, assertions, screenshots, reports, and app memory.
4. The agent uses that structured output to continue the workflow.

The product goal is simple:

- make browser workflows explainable
- make sanity checks repeatable
- keep execution local
- avoid API-key-gated browser services
- preserve evidence with screenshots, action history, and markdown reports

## What It Does

- Runs as an MCP server your IDE agent can call directly
- Supports two browser backends:
  - `playwright` for deterministic automation
  - `browser-harness` for adaptive real-browser control
- Exposes browser actions, waits, extraction tools, and assertions
- Persists reusable tasks as slash-command-style prompts
- Builds application memory from a repo for future sanity runs
- Writes reports, screenshots, and download artifacts locally

## Architecture

```text
Your prompt
   |
   v
IDE agent
   |
   v
Easy Sanity MCP server
   |
   +-- Browser tools
   +-- Task tools
   +-- Memory tools
   |
   v
Browser backend
   +-- Playwright
   +-- browser-harness
```

## Quick Start

### Install without cloning

```bash
uvx easy-sanity install-browser
```

Then point your IDE MCP config at:

```bash
uvx easy-sanity
```

### Install with `pipx`

```bash
pipx install easy-sanity
easy-sanity install-browser
```

Then point your IDE MCP config at:

```bash
easy-sanity
```

### Run from this repo

```bash
./scripts/setup.sh
```

That does:

- `uv sync`
- `uv run playwright install chromium`

## MCP Configuration

This project reads real environment variables. For IDE setups, the simplest pattern is to pass them in the MCP server `env` block.

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

### Claude Code

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

### Cursor

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

## Browser Modes

### `playwright`

Use this when you want deterministic, scriptable automation.

### `browser-harness`

Use this when you want adaptive browser control through the harness backend.

Easy Sanity supports:

- explicit harness attachment through `BROWSER_HARNESS_CDP_URL` or `BROWSER_HARNESS_CDP_WS`
- dedicated Chromium auto-launch for harness mode when autolaunch is enabled
- normalized reporting, assertions, screenshots, and action history across both modes

## Runtime Environment Variables

### Core

- `BROWSER_HEADLESS_DEFAULT`
- `BROWSER_DEFAULT_TIMEOUT_MS`
- `BROWSER_BACKEND_DEFAULT`
- `BROWSER_REPORTS_DIR`
- `BROWSER_SCREENSHOTS_DIR`
- `BROWSER_DOWNLOADS_DIR`
- `APP_MEMORY_DIR`

### Harness

- `BROWSER_HARNESS_ENABLED`
- `BROWSER_HARNESS_COMMAND`
- `BROWSER_HARNESS_REPO`
- `BROWSER_HARNESS_AUTOLAUNCH`
- `BROWSER_HARNESS_BROWSER_PATH`
- `BROWSER_HARNESS_DEBUGGING_PORT`
- `BROWSER_HARNESS_USER_DATA_DIR`
- `BROWSER_HARNESS_CDP_URL`
- `BROWSER_HARNESS_CDP_WS`

## Common Usage

### Start a simple browser run

Tell your IDE agent something like:

```text
Use Easy Sanity to open https://example.com, inspect the page title, and summarize the visible page structure.
```

### Pick a backend explicitly

```text
Call browser_start with task "Login smoke" and backend "playwright"
```

```text
Call browser_start with task "Adaptive browser flow" and backend "browser-harness"
```

### Use saved tasks

```text
Create a browser task named "google_search" with prompt:
"Go to www.google.com, search for OpenAI, and return the first 3 result titles."
```

## Tool Reference

Easy Sanity exposes three main tool groups.

### Browser Session and State

- `browser_start`
- `browser_stop`
- `browser_get_state`
- `browser_get_history`
- `browser_list_backends`
- `browser_get_dom_summary`
- `browser_get_accessibility_tree`
- `browser_list_forms`
- `browser_list_links`
- `browser_list_network_errors`
- `browser_get_console_logs`
- `browser_get_requests`
- `browser_get_storage`
- `browser_describe_changes`

### Browser Actions

- `browser_navigate`
- `browser_click`
- `browser_click_by_role`
- `browser_click_by_label`
- `browser_fill`
- `browser_type`
- `browser_select_option`
- `browser_press_key`
- `browser_hover`
- `browser_drag_and_drop`
- `browser_upload_file`
- `browser_download_file`
- `browser_refresh`
- `browser_go_back`
- `browser_go_forward`
- `browser_open_tab`
- `browser_switch_tab`
- `browser_close_tab`
- `browser_scroll`
- `browser_wait`
- `browser_wait_for_text`
- `browser_wait_for_element`
- `browser_wait_for_url`
- `browser_wait_for_navigation`
- `browser_wait_for_network_idle`
- `browser_wait_for_disappearance`

### Browser Extraction and Inspection

- `browser_extract`
- `browser_extract_table`
- `browser_extract_list`
- `browser_extract_json_from_page`
- `browser_extract_links`
- `browser_capture_section`
- `browser_compare_text`
- `browser_find_element`

### Assertions

- `assert_url_contains`
- `assert_url_equals`
- `assert_page_title`
- `assert_text_visible`
- `assert_text_not_visible`
- `assert_text_contains`
- `assert_text_matches`
- `assert_element_exists`
- `assert_element_enabled`
- `assert_element_visible`
- `assert_element_hidden`
- `assert_count`
- `assert_input_value`
- `assert_no_console_errors`
- `assert_no_failed_requests`
- `assert_screenshot_stable`

### Task Tools

- `task_create`
- `task_create_structured`
- `task_preview_structured`
- `task_list`
- `task_get`
- `task_delete`
- `task_lint`
- `task_render`
- `task_wizard_template`
- `sample_tasks_list`
- `sample_tasks_import`
- `profile_save`
- `profile_list`
- `profile_get`
- `profile_delete`

### App Memory Tools

- `app_memory_sync`
- `app_memory_get`
- `app_memory_add_note`
- `app_memory_testing_brief`
- `app_memory_list`

## Saved Tasks and Profiles

### Saved tasks

Saved tasks let you define reusable browser workflows and invoke them through slash commands in your IDE.

Use:

- `task_create` for free-form tasks
- `task_create_structured` for purpose/steps/assertions-driven tasks
- `task_render` to resolve placeholders with profiles and variables
- `task_lint` to catch vague prompts before you run them

### Profiles

Profiles hold reusable environment values for tasks, such as base URLs or credentials placeholders.

Use:

- `profile_save`
- `profile_list`
- `profile_get`
- `profile_delete`

## App Memory

App memory turns Easy Sanity into more than a browser driver.

It can scan a target repo, infer testing surfaces, keep notes, and generate a testing brief for future runs.

Typical flow:

1. `app_memory_sync` on the app repo
2. `app_memory_get` to inspect what was learned
3. `app_memory_testing_brief` to generate a focused smoke-testing brief
4. `app_memory_add_note` to persist manual findings

## Artifacts

Easy Sanity writes local artifacts so runs remain inspectable:

- markdown reports in `artifacts/reports/`
- screenshots in `artifacts/screenshots/`
- downloads in `artifacts/downloads/`
- repo memory in `data/app_memory/`

## Why Use It

- local-first execution
- no browser API subscription
- explainable action history
- screenshot-backed evidence
- reusable task workflows
- repo-aware testing memory
- support for both deterministic and adaptive browser control

## Official Documentation

The canonical product documentation is here:

- https://www.kedarvartak.com/agents/easy-sanity

Additional repo docs:

- [Installation Guide](docs/installation.md)
- [Feature Overview](docs/features.md)
- [Agent Documentation](docs/agent-documentation.md)
- [Browser Harness Roadmap](docs/browser-harness-roadmap.md)
- [Main Roadmap](docs/roadmap.md)
- [Test Cases](docs/testcases.md)

## Troubleshooting

### Playwright browser missing

```bash
uv run playwright install chromium
```

### MCP tools not appearing

- confirm your MCP config path
- restart the IDE completely
- check IDE MCP logs

### Harness mode setup

- start with `browser_list_backends`
- enable `BROWSER_HARNESS_ENABLED=true`
- set `BROWSER_HARNESS_CDP_URL` or `BROWSER_HARNESS_CDP_WS` if you want explicit attach
- or leave autolaunch enabled and let Easy Sanity start a dedicated Chromium debug session

## License

MIT
