# Easy Sanity Agent Documentation

This document is the full reference for the Easy Sanity agent: what it is, how it works, how to install it, how to configure it, how to use it, what it stores, and every MCP tool it exposes.

## What Easy Sanity Is

Easy Sanity is a local browser automation and sanity-testing MCP server.

It is designed to let an IDE agent such as Codex use natural language to:

- open and inspect web applications
- interact with forms, buttons, dropdowns, dialogs, tables, and cards
- verify app behavior with explicit assertions
- capture screenshots, reports, and action history
- save reusable workflows as slash-command style tasks
- build persistent application understanding from a target code repository

In practice, Easy Sanity sits between your IDE agent and a real Chromium browser driven by Playwright.

## Core Idea

The agent workflow is:

1. You ask the IDE agent to perform or validate a browser workflow.
2. The IDE agent calls Easy Sanity MCP tools.
3. Easy Sanity executes those tool calls in a local Playwright-controlled browser.
4. The IDE agent reads page state, semantic summaries, assertions, screenshots, action history, and reports to decide what to do next.

This turns the IDE agent from a text-only assistant into a browser-based sanity-testing agent.

## Main Capability Areas

Easy Sanity currently supports:

- browser session lifecycle management
- semantic browser actions
- explicit assertions
- synchronization and wait tools
- extraction tools for tables, lists, links, and JSON-like page data
- evidence capture through screenshots and markdown reports
- reusable tasks and slash-command workflows
- variable rendering and environment profiles
- structured task definitions
- persistent repo understanding and testing memory

## Architecture

The codebase is organized into focused modules:

- `main.py`
  Thin MCP entrypoint. Registers task tools, browser tools, and memory tools.

- `browser/`
  Browser session state, browser tools, semantic domain understanding, and report generation.

- `tasks/`
  Saved task system, structured tasks, sample tasks, task rendering, task linting, and profile management.

- `memory/`
  Persistent repo understanding, app memory, testing briefs, and sync-driven learned notes.

- `config/`
  Runtime configuration and environment-backed paths/defaults.

- `prompts/`
  LLM-facing prompt text and reusable prompt templates.

- `data/`
  Saved tasks, profiles, sample tasks, and app memory artifacts.

- `artifacts/`
  Generated screenshots, downloads, and markdown reports.

## Installation

### Quick Start Without Cloning

```bash
uvx easy-sanity install-browser
```

Then point your MCP client at:

```bash
uvx easy-sanity
```

### Permanent Install With `pipx`

```bash
pipx install easy-sanity
easy-sanity install-browser
```

Then point your MCP client at:

```bash
easy-sanity
```

### Source Checkout Setup

```bash
./scripts/setup.sh
```

This does:

- `uv sync`
- `uv run playwright install chromium`

### Manual Setup

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
uv run playwright install chromium
```

## Codex Setup

Codex does not use a plain `.env` file automatically for MCP server startup. The recommended pattern is to pass the runtime values through the MCP server `env` block.

Use a config like this:

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

You can also add the server from the Codex CLI:

```bash
codex mcp add easy-sanity \
  --env BROWSER_HEADLESS_DEFAULT=true \
  --env BROWSER_DEFAULT_TIMEOUT_MS=45000 \
  --env BROWSER_REPORTS_DIR=artifacts/reports \
  --env BROWSER_SCREENSHOTS_DIR=artifacts/screenshots \
  --env BROWSER_DOWNLOADS_DIR=artifacts/downloads \
  --env APP_MEMORY_DIR=data/app_memory \
  -- uvx easy-sanity
```

After setup:

1. Restart Codex.
2. Confirm the server appears in MCP tools.
3. Run a smoke prompt such as:
   `Use easy-sanity to open https://example.com and tell me the page title.`

## Other IDE Setup

Example MCP configuration is also included in:

- `mcp-config-example.json`
- `README.md`

The same packaged launch pattern works for Claude Code, Cursor, and similar IDEs with MCP support:

- `uvx easy-sanity`
- or `easy-sanity` after a `pipx install easy-sanity`

## Environment Variables

The project supports these runtime environment variables:

| Variable | Purpose | Default |
|---|---|---|
| `BROWSER_HEADLESS_DEFAULT` | Whether `browser_start` runs headless by default | `false` |
| `BROWSER_DEFAULT_TIMEOUT_MS` | Default Playwright timeout in milliseconds | `30000` |
| `BROWSER_REPORTS_DIR` | Directory for markdown test reports | user app data `artifacts/reports` when installed; repo-local in source checkout |
| `BROWSER_SCREENSHOTS_DIR` | Directory for per-step screenshots | user app data `artifacts/screenshots` when installed; repo-local in source checkout |
| `BROWSER_DOWNLOADS_DIR` | Directory for downloaded files | user app data `artifacts/downloads` when installed; repo-local in source checkout |
| `APP_MEMORY_DIR` | Directory for persistent app-understanding memory | user app data `data/app_memory` when installed; repo-local in source checkout |

Reference template:

- `.env.example`

Important note:

- `.env.example` is a template only
- the project reads real environment variables
- if you want values loaded automatically from a `.env` file, you must load them externally or pass them through the MCP server config

## Generated Data and Artifacts

### Saved Data

- `data/tasks.json`
  Saved reusable tasks

- `data/profiles.json`
  Reusable variable and environment profiles

- `data/sample_tasks.json`
  Built-in onboarding and smoke-test samples

- `data/app_memory/`
  Persistent repo-understanding memory for target applications

### Runtime Artifacts

- `artifacts/reports/`
  Markdown reports written at the end of browser sessions

- `artifacts/screenshots/`
  Per-step screenshots grouped by session

- `artifacts/downloads/`
  Downloaded files grouped by session

## Reporting Model

Each browser session can produce:

- step-by-step action history
- timestamps
- semantic route and page-change context
- screenshots
- final markdown report

Reports are useful for:

- QA evidence
- debugging regressions
- demo artifacts
- sharing what the agent saw and did

## App Memory Model

Easy Sanity can also learn a target application repository over time.

The app memory layer can:

- scan a local code repository
- infer tech stack
- detect likely workflows
- detect route and entrypoint hints
- detect environment and test asset hints
- generate testing guidance
- persist manual notes and learned notes
- update over time across multiple sync runs

This is stored per repo under `APP_MEMORY_DIR`.

## Tasks and Profiles

The task system is designed to make long browser workflows reusable.

It supports:

- free-form prompt tasks
- structured tasks
- placeholders such as `{{base_url}}` or `{{password}}`
- secret variable detection
- reusable profiles such as `dev`, `staging`, or `prod`
- sample task import
- linting and task-authoring helpers

Important current behavior:

- saved slash-command tasks store a prompt template
- profiles and task rendering are supported
- profile-backed direct slash-command execution may still require the IDE agent to render or bind profile values intentionally

## Tool Reference

This section documents every MCP tool currently exposed by the agent.

## Browser Session Tools

### `browser_start(task, headless=None)`

Starts a new browser session.

Use it to:

- begin a browser workflow
- optionally override headless mode
- initialize report, screenshot, and download directories for the session

### `browser_stop(final_result=None)`

Ends the browser session and writes the final report.

Use it to:

- close the browser cleanly
- finalize action history
- generate the markdown run report
- return report and screenshot paths

### `browser_get_history()`

Returns session action history.

Includes:

- action list
- semantic change summaries
- route context
- report path
- screenshot directory

## Browser Inspection Tools

### `browser_get_state()`

Returns the current page state.

Includes:

- URL
- title
- visible text
- interactive elements
- screenshot as base64
- semantic page summary
- route context
- recent semantic change summary

### `browser_get_dom_summary()`

Returns a semantic page understanding summary.

Useful for:

- understanding forms
- understanding cards and tables
- identifying dialogs, alerts, headings, and workflow step context

### `browser_get_accessibility_tree()`

Returns a simplified accessibility-oriented tree of interactive elements.

Useful for:

- robust role/name-based interaction
- accessibility-friendly selectors

### `browser_list_forms()`

Returns visible forms and their fields.

Includes:

- labels
- names
- placeholders
- required flags
- disabled state
- submit buttons

### `browser_list_links()`

Returns visible links on the page.

Useful for:

- navigation validation
- crawl-like sanity workflows

### `browser_list_network_errors()`

Returns failed network requests and error-level console messages seen during the session.

### `browser_get_console_logs(level="")`

Returns session console logs.

Optional filter:

- `error`
- `warning`
- `log`

### `browser_get_requests(limit=100)`

Returns recent request and response activity captured for the page.

### `browser_get_storage()`

Returns browser storage details.

Includes:

- cookies
- `localStorage`
- `sessionStorage`

### `browser_describe_changes()`

Compares the current page to the last semantic snapshot and describes what changed.

Useful for:

- confirming route changes
- workflow-step changes
- dialog openings
- alert changes

## Browser Navigation and Interaction Tools

### `browser_navigate(url)`

Navigates to a URL and waits for page load/network idle behavior.

### `browser_find_element(description, limit=5)`

Finds likely interactive elements using a natural-language description.

Useful prompts:

- `email field`
- `login button`
- `search input`

### `browser_click(selector=None, text=None, element_index=None)`

Low-level click tool.

Supports:

- CSS selector click
- visible text click
- `browser_get_state()` element index click

### `browser_click_by_role(role, name, exact=False)`

Clicks an element by accessible role and name.

Examples:

- button named `Login`
- link named `Dashboard`

### `browser_click_by_label(name)`

Clicks an element by human-readable label or visible name.

### `browser_fill(field, text, press_enter=False)`

Fills a field semantically.

It tries:

- label
- placeholder
- name
- id
- `data-testid`
- fallback aria/attribute matching

### `browser_select_option(label, value)`

Selects a value in a select/dropdown control using a semantic field label.

### `browser_type(selector, text, press_enter=False)`

Low-level typed input by CSS selector.

### `browser_press_key(key)`

Presses a keyboard key such as:

- `Enter`
- `Escape`
- `Tab`

### `browser_hover(selector)`

Hovers over an element by selector.

### `browser_drag_and_drop(source, target)`

Performs drag-and-drop between two selectors.

### `browser_upload_file(selector, path)`

Uploads a local file into a file input.

### `browser_download_file(link_or_selector)`

Triggers a download and stores the file under the session download directory.

### `browser_refresh()`

Refreshes the current page.

### `browser_go_back()`

Moves backward in browser history.

### `browser_go_forward()`

Moves forward in browser history.

### `browser_open_tab(url="")`

Opens a new tab and optionally navigates it.

### `browser_switch_tab(index=-1, title="")`

Switches the active tab by index or title substring.

### `browser_close_tab()`

Closes the current tab and switches to another open tab.

### `browser_scroll(direction="down", amount=500)`

Scrolls the page up or down.

### `browser_wait(seconds=2)`

Simple fixed wait helper.

Useful when:

- waiting for animation
- waiting for unstable UI

Prefer smarter wait tools when possible.

## Synchronization and Wait Tools

### `browser_wait_for_text(text, timeout_ms=10000)`

Waits until visible text appears.

### `browser_wait_for_element(selector, timeout_ms=10000, state="visible")`

Waits for an element to reach a given state.

Common states:

- `visible`
- `attached`
- `hidden`
- `detached`

### `browser_wait_for_url(pattern, timeout_ms=10000)`

Waits until the current URL matches a substring pattern.

### `browser_wait_for_navigation(timeout_ms=10000)`

Waits until page navigation/load completes.

### `browser_wait_for_network_idle(timeout_ms=10000)`

Waits until Playwright reports network-idle state.

### `browser_wait_for_disappearance(selector, timeout_ms=10000)`

Waits until an element disappears or becomes hidden.

## Extraction Tools

### `browser_extract(selector)`

Extracts text from a specific element.

### `browser_extract_table(selector)`

Extracts table headers and row data.

### `browser_extract_list(selector)`

Extracts items from a list-like container.

### `browser_extract_json_from_page()`

Extracts JSON-like page data from:

- JSON script tags
- common framework globals

### `browser_extract_links()`

Extracts link text and URLs from the page.

### `browser_capture_section(selector)`

Captures:

- the section text
- a base64 screenshot of that section

### `browser_compare_text(selector, expected)`

Compares an element’s text to an expected value and returns pass/fail data.

## Assertion Tools

These tools shift Easy Sanity from browser automation into explicit testing.

### `assert_url_contains(expected_text)`

Asserts the current URL contains a substring.

### `assert_url_equals(expected_url)`

Asserts the current URL exactly matches a value.

### `assert_page_title(expected_text)`

Asserts the page title contains the expected text.

### `assert_text_visible(text)`

Asserts specific text is visible on the page.

### `assert_text_not_visible(text)`

Asserts specific text is not visible.

### `assert_text_contains(text)`

Asserts the body text contains a string.

### `assert_text_matches(pattern)`

Asserts the visible page text matches a regex pattern.

### `assert_element_exists(selector)`

Asserts an element exists.

### `assert_element_visible(selector)`

Asserts an element exists and is visible.

### `assert_element_hidden(selector)`

Asserts an element is hidden or absent.

### `assert_element_enabled(selector)`

Asserts an element exists and is enabled.

### `assert_input_value(selector, expected)`

Asserts an input/select/textarea has the expected current value.

### `assert_count(selector, expected)`

Asserts a selector matches an exact number of elements.

### `assert_no_console_errors()`

Asserts no error-level console messages were captured in the session.

### `assert_no_failed_requests()`

Asserts no failed requests were captured in the session.

### `assert_screenshot_stable(selector="body")`

Takes two short-interval screenshots and asserts they are identical.

Useful for:

- checking visual stability
- detecting still-changing UI

## Task Tools

### `task_create(name, prompt, description="")`

Creates a reusable saved task and registers it as a slash-command-style prompt.

### `task_create_structured(...)`

Creates a structured task definition with fields such as purpose, steps, assertions, inputs, retry policy, and expected result.

### `task_preview_structured(...)`

Previews a structured task without saving it.

### `task_list()`

Lists saved tasks.

### `task_get(name)`

Returns the full definition of a saved task.

### `task_delete(name)`

Deletes a saved task.

### `task_render(name, profile="", variables_json="{}", mask_secrets=False)`

Renders a templated task with merged variables.

Precedence:

- explicit variables
- profile values
- environment variables

### `task_lint(name="", prompt="")`

Lints a task prompt for:

- vagueness
- missing URL
- missing verification
- hardcoded secret-like content
- missing structure

### `task_wizard_template(goal, start_url="", include_placeholders=True, include_assertions=True)`

Generates a starter task draft from a goal.

### `sample_tasks_list()`

Lists bundled sample tasks.

### `sample_tasks_import(names_json="[]", overwrite=False)`

Imports bundled sample tasks into saved tasks.

## Profile Tools

### `profile_save(name, variables_json, description="")`

Creates or updates a reusable variable profile.

### `profile_list()`

Lists all profiles.

### `profile_get(name, mask_secrets=True)`

Returns a profile, optionally masking secrets.

### `profile_delete(name)`

Deletes a profile.

## App Memory Tools

### `app_memory_sync(repo_path, app_name="", focus="", max_files=250)`

Scans a target repository and builds or updates a persistent understanding map.

### `app_memory_get(repo_path)`

Returns stored memory for a repo.

### `app_memory_add_note(repo_path, note, category="workflow")`

Adds a manual persistent note to the memory map.

### `app_memory_testing_brief(repo_path, goal="")`

Builds a test-oriented brief from stored repo understanding.

### `app_memory_list()`

Lists all persisted repo memory entries.

## Example Usage Patterns

### Example 1: Simple Browser Inspection

Prompt:

```text
Use easy-sanity to open https://example.com and tell me the page title.
```

Likely tool flow:

- `browser_start`
- `browser_navigate`
- `browser_get_state`
- `browser_stop`

### Example 2: Login Sanity Check

Prompt:

```text
Use easy-sanity to log into the app, verify the dashboard opens, and stop with a pass/fail summary.
```

Likely tools:

- `browser_start`
- `browser_navigate`
- `browser_fill`
- `browser_click_by_role`
- `browser_wait_for_network_idle`
- `assert_url_contains`
- `assert_text_visible`
- `browser_stop`

### Example 3: Reusable Profile-Backed Task

Prompt:

```text
Create a saved browser workflow with placeholders for URL, email, and password.
```

Then:

1. Save the task with `task_create`
2. Save credentials with `profile_save`
3. Render or execute with `task_render`

### Example 4: Repo-Aware Sanity Testing

Prompt:

```text
Use easy-sanity to sync the target app repo into memory and generate a testing brief for the login workflow.
```

Likely tools:

- `app_memory_sync`
- `app_memory_testing_brief`

## Recommended Usage Guidance

For the best results:

- prefer semantic tools before raw selector tools
- prefer wait tools over fixed sleeps
- use assertions for explicit pass/fail checks
- use `browser_get_dom_summary` when a page layout is complex
- use tasks and profiles for repeated flows
- use app memory when the agent also has access to the application repository

## Security and Secret Handling

Recommended practice:

- store passwords and secrets in profiles or external environment variables
- avoid saving credentials directly inside reusable tasks
- use placeholders such as `{{password}}` in tasks
- use `mask_secrets=true` when retrieving or rendering sensitive profiles

Important nuance:

- the secret exists in the runtime values if the agent needs to log in
- masking helps reduce accidental display and persistence in tool output
- it does not replace real secret-management practices

## Current Strengths

Easy Sanity is especially strong for:

- internal smoke tests
- browser-based sanity checks
- navigating real product flows
- collecting step evidence
- reusable LLM-driven workflows
- repo-informed exploratory sanity testing

## Current Limitations

Current limitations include:

- profile-aware direct slash-command execution still requires intentional agent behavior
- some highly dynamic or custom component libraries may still require fallback selectors
- browser automation quality still depends partly on the reasoning quality of the IDE agent
- local runtime environment must have Playwright Chromium installed
- some advanced reporting-tool APIs proposed in the roadmap are not yet implemented

## Related Docs

Other project docs include:

- `docs/roadmap.md`
- `docs/features.md`
- `docs/testcases.md`
- `docs/versioning.md`

## Summary

Easy Sanity is a local MCP browser-testing agent that combines:

- browser control
- semantic page understanding
- explicit assertions
- evidence capture
- reusable tasks
- environment profiles
- persistent app memory

Together, those pieces make it much more than a raw browser driver. It is designed to be an autonomous, reusable, test-oriented browser agent for real application sanity testing.
