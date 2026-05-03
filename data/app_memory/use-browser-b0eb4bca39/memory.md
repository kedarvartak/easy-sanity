# App Understanding Map: use_browser

- Repo Path: `/home/kedar/Desktop/Projects/use_browser`
- Repo ID: `use-browser-b0eb4bca39`
- Last Synced At: `2026-05-03T16:09:49.047773+00:00`
- Sync Runs: `1`

## Summary

use_browser appears to use Cypress, Playwright, Python. Detected workflows: admin, auth, checkout, dashboard, onboarding, profile, search, settings. Main surfaces: admin workflow, auth workflow, authentication surface, checkout workflow, commerce surface, dashboard workflow, data-management surface, messaging surface, navigation surface, onboarding workflow, profile workflow, reporting surface, search workflow, settings workflow.

## Tech Stack

- Cypress
- Playwright
- Python

## Entrypoints

- `README.md`
- `main.py`
- `pyproject.toml`

## Route Hints


## Workflow Hints

### Admin

- `README.md`
- `data/tasks.json`
- `docs/features.md`
- `docs/versioning.md`
- `memory/store.py`

### Auth

- `README.md`
- `browser/__init__.py`
- `browser/report_manager.py`
- `browser/state.py`
- `browser/tools.py`
- `data/sample_tasks.json`
- `data/tasks.json`
- `docs/features.md`
- `docs/roadmap.md`
- `docs/testcases.md`
- `docs/versioning.md`
- `memory/store.py`
- `memory/tools.py`
- `tasks/__init__.py`
- `tasks/tools.py`

### Checkout

- `docs/roadmap.md`
- `docs/testcases.md`
- `memory/store.py`
- `tasks/tools.py`

### Dashboard

- `README.md`
- `data/sample_tasks.json`
- `data/tasks.json`
- `docs/features.md`
- `docs/versioning.md`
- `mcp-config-example.json`
- `memory/store.py`
- `memory/tools.py`

### Onboarding

- `README.md`
- `docs/features.md`
- `docs/roadmap.md`
- `docs/testcases.md`
- `memory/store.py`
- `scripts/setup.sh`
- `tasks/tools.py`

### Profile

- `config/settings.py`
- `data/profiles.json`
- `docs/features.md`
- `docs/roadmap.md`
- `memory/store.py`
- `memory/tools.py`
- `tasks/tools.py`

### Search

- `README.md`
- `docs/features.md`
- `docs/roadmap.md`
- `docs/testcases.md`
- `memory/store.py`
- `tasks/tools.py`

### Settings

- `README.md`
- `browser/state.py`
- `browser/tools.py`
- `config/__init__.py`
- `config/settings.py`
- `docs/roadmap.md`
- `docs/testcases.md`
- `mcp-config-example.json`
- `memory/store.py`
- `memory/tools.py`
- `tasks/tools.py`

## Feature Hints

### Authentication

- `README.md`
- `browser/__init__.py`
- `browser/report_manager.py`
- `browser/state.py`
- `browser/tools.py`
- `data/sample_tasks.json`
- `data/tasks.json`
- `docs/features.md`
- `docs/roadmap.md`
- `docs/testcases.md`
- `docs/versioning.md`
- `memory/store.py`

### Commerce

- `data/tasks.json`
- `docs/features.md`
- `docs/roadmap.md`
- `docs/testcases.md`
- `docs/versioning.md`
- `memory/store.py`
- `tasks/tools.py`

### Data-Management

- `README.md`
- `browser/report_manager.py`
- `browser/state.py`
- `data/tasks.json`
- `docs/features.md`
- `docs/roadmap.md`
- `docs/testcases.md`
- `docs/versioning.md`
- `memory/store.py`
- `memory/tools.py`
- `scripts/setup.sh`
- `tasks/tools.py`

### Messaging

- `browser/tools.py`
- `memory/store.py`
- `memory/tools.py`
- `prompts/__init__.py`
- `prompts/browser_prompts.py`

### Navigation

- `README.md`
- `data/sample_tasks.json`
- `data/tasks.json`
- `docs/features.md`
- `docs/roadmap.md`
- `docs/testcases.md`
- `docs/versioning.md`
- `memory/store.py`
- `prompts/browser_prompts.py`
- `tasks/tools.py`

### Reporting

- `browser/__init__.py`
- `browser/report_manager.py`
- `browser/state.py`
- `browser/tools.py`
- `config/settings.py`
- `data/tasks.json`
- `docs/features.md`
- `docs/roadmap.md`
- `docs/versioning.md`
- `memory/store.py`
- `memory/tools.py`

## Environment Hints

- `APP_MEMORY_DIR`
- `BROWSER_DEFAULT_TIMEOUT_MS`
- `BROWSER_HEADLESS_DEFAULT`
- `BROWSER_REPORTS_DIR`
- `BROWSER_SCREENSHOTS_DIR`
- `DATA_DIR`
- `PROFILES_FILE`
- `ROOT_DIR`
- `SAMPLE_TASKS_FILE`
- `TASKS_FILE`

## Existing Test Assets

- `README.md`
- `browser/state.py`
- `browser/tools.py`
- `docs/features.md`
- `docs/versioning.md`
- `memory/store.py`
- `pyproject.toml`
- `scripts/setup.sh`

## Testing Targets

- Verify login, logout, session persistence, and invalid-credential handling.
- Check dashboard rendering, key cards/widgets, and empty states.
- Test query entry, result rendering, and no-results behavior.
- Validate settings forms, save actions, and persistence after refresh.
- Cover cart, checkout, and confirmation states with careful assertions.
- Exercise tables/lists for load, filtering, sorting, and row actions.
- Reuse existing test routes, fixtures, or selectors already present in the repo.
- Confirm required environment configuration before running browser sanity flows.

## Testing Guidance

- Verify login, logout, session persistence, and invalid-credential handling.
- Check dashboard rendering, key cards/widgets, and empty states.
- Test query entry, result rendering, and no-results behavior.
- Validate settings forms, save actions, and persistence after refresh.
- Cover cart, checkout, and confirmation states with careful assertions.
- Exercise tables/lists for load, filtering, sorting, and row actions.
- Reuse existing test routes, fixtures, or selectors already present in the repo.
- Confirm required environment configuration before running browser sanity flows.

## Learned Notes

- [stack] Detected Cypress in the target application. (`Cypress`)
- [stack] Detected Playwright in the target application. (`Playwright`)
- [stack] Detected Python in the target application. (`Python`)
- [workflow] Found a likely admin workflow in the repo. (`README.md, data/tasks.json, docs/features.md`)
- [workflow] Found a likely auth workflow in the repo. (`README.md, browser/__init__.py, browser/report_manager.py`)
- [workflow] Found a likely checkout workflow in the repo. (`docs/roadmap.md, docs/testcases.md, memory/store.py`)
- [workflow] Found a likely dashboard workflow in the repo. (`README.md, data/sample_tasks.json, data/tasks.json`)
- [workflow] Found a likely onboarding workflow in the repo. (`README.md, docs/features.md, docs/roadmap.md`)
- [workflow] Found a likely profile workflow in the repo. (`config/settings.py, data/profiles.json, docs/features.md`)
- [workflow] Found a likely search workflow in the repo. (`README.md, docs/features.md, docs/roadmap.md`)
- [workflow] Found a likely settings workflow in the repo. (`README.md, browser/state.py, browser/tools.py`)
- [sync] Sync observed 29 new, 0 changed, and 0 removed files. (`repo memory`)

## Manual Notes


## Sync History

- 2026-05-03T16:09:49.047773+00:00: scanned 29 files, 0 changed, 29 new, 0 removed (focus: repo memory)
