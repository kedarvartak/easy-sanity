# Versioning

This document tracks meaningful feature pushes and architectural updates to the project over time.

It is meant to serve as a lightweight product and engineering changelog, especially for roadmap-driven improvements.

Feature validation coverage is tracked separately in [testcases.md](/home/kedar/Desktop/Projects/use_browser/docs/testcases.md:1).

## 0.1.0

Initial public prototype.

Included:

- local MCP server for browser automation
- Playwright-backed Chromium control
- browser tools for start, navigate, inspect, click, type, scroll, extract, wait, stop, and history
- saved task support through `tasks.json`
- MCP prompt registration for reusable slash-command style tasks

## 0.2.0

Roadmap Task 1: higher-level browser interaction tools.

Added:

- `browser_find_element(description, limit=5)`
- `browser_click_by_role(role, name, exact=False)`
- `browser_fill(field, text, press_enter=False)`

Why this matters:

- reduces dependence on fragile raw selectors
- gives the LLM more semantic ways to act on forms and controls
- improves usability for natural-language sanity testing flows

Impact:

- tasks can now describe elements in more human terms like "email field" or "login button"
- form interactions are more robust through label, placeholder, name, id, and `data-testid` matching
- role-based interactions align better with accessible page structure

## 0.3.0

Codebase modularity refactor.

Changed:

- split the monolithic `main.py` into focused modules
- kept `main.py` as a thin entrypoint
- moved task logic into `task_tools.py`
- moved browser lifecycle management into `browser_state.py`
- moved browser tool registration and implementation into `browser_tools.py`
- kept LLM-facing prompt text isolated in `prompts/browser_prompts.py`

Why this matters:

- makes the repo easier to extend safely
- reduces cognitive load when adding new tools
- creates cleaner boundaries between state management, task logic, prompts, and browser actions

Impact:

- future roadmap work can be implemented in smaller, more focused files
- prompt text and execution logic are easier to evolve independently
- the project is better positioned for additional tools, assertions, and test reporting

## 0.3.1

Higher-level browser tool quality fix and testcase-driven validation follow-up.

Changed:

- improved `browser_find_element` ranking in `browser_tools.py`
- made actionable controls rank above standalone labels
- ensured label-linked inputs inherit useful scoring from their associated label text
- added a stable local validation page at `test_pages/login_form.html`

Why this matters:

- the first semantic-finder validation exposed a usability gap rather than a hard failure
- `browser_find_element("email field")` returned a `<label>` first, which was technically useful but not the best result for an autonomous agent
- fixing ranking quality makes the higher-level tool more trustworthy in real workflows

Testcase experience from this ship:

- the shipped features were validated against the testcase matrix in `docs/testcases.md`
- modularity checks passed: tool registration, task loading, and shared browser state all worked after the refactor
- the higher-level browser workflow passed end to end once Playwright Chromium was installed locally
- the first testcase run exposed one caveat in `TC-005`, which is exactly the kind of issue the testcase matrix is meant to catch
- after the ranking fix, `TC-005` passed cleanly and the broader semantic login workflow still remained green

What we learned:

- feature testcases should not only catch failures, they should also catch low-quality behavior
- stable local test pages are valuable because they make browser-tool validation repeatable
- environment readiness matters: browser-dependent testcase runs should assume Playwright browsers are installed or make that prerequisite explicit

Impact:

- the semantic element finder now returns more actionable top candidates
- testcase coverage proved useful as a product-quality tool, not just an engineering checklist
- this ship validated the workflow of "feature push -> testcase run -> caveat found -> targeted fix -> testcase rerun"

## 0.4.0

First-class assertion tools for sanity testing workflows.

Added:

- `assert_url_contains`
- `assert_text_visible`
- `assert_text_not_visible`
- `assert_element_exists`
- `assert_element_enabled`
- `assert_page_title`
- `assert_count`

Why this matters:

- the project now moves beyond browser automation into explicit pass/fail testing behavior
- the LLM can validate outcomes directly instead of only inferring success from raw page state
- this makes the server more useful as an autonomous sanity testing agent rather than only a browser operator

Testcase experience from this ship:

- assertion tools were validated against the stable local page in `test_pages/login_form.html`
- direct positive assertions passed for URL, title, visible text, absent text, selector existence, enabled state, and exact counts
- assertions also worked correctly inside a realistic semantic login workflow
- a negative testcase using `assert_count(selector="input", expected=3)` returned the intended structured failure payload with expected and actual values
- assertion steps were successfully recorded in shared browser history, which improves test traceability

What we learned:

- assertions become much more valuable when they produce consistent structured payloads
- negative testcase coverage is important because assertion tools must fail clearly, not just pass cleanly
- integrating assertions into shared action history makes the agent more audit-friendly for sanity testing

Impact:

- the MCP server now has a real testing vocabulary, not just browser control primitives
- future saved tasks and natural-language workflows can end in explicit validation steps
- this ship lays the foundation for pass/fail summaries, test reports, and more formalized sanity suites
