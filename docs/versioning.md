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
- saved task support through `data/tasks.json`
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

## 0.5.0

Task variables, secret placeholders, and environment profiles.

Added:

- placeholder extraction for saved tasks such as `{{base_url}}`, `{{email}}`, and `{{password}}`
- secret variable tracking on saved tasks
- `task_render` for template rendering with merged values
- environment profile tools:
  `profile_save`
  `profile_list`
  `profile_get`
  `profile_delete`

Why this matters:

- saved tasks no longer need to hardcode URLs or credentials
- the task system can now support reusable flows across `local`, `staging`, and `prod`
- this makes the agent safer and more portable for real sanity-testing workflows

Testcase experience from this ship:

- validation was done through temporary non-sensitive task and profile entries created via the MCP tools
- placeholder extraction and secret-variable tracking worked correctly during `task_create`
- profile lifecycle behavior passed for save, list, get, and delete
- masked profile retrieval hid `password` values while leaving non-secret fields visible
- `task_render` correctly resolved values from profiles, explicit overrides, and environment variables
- precedence behaved as intended: explicit variables overrode profile values, and environment variables filled gaps when profile values were absent
- incomplete renders correctly reported `missing_variables` and did not mark the task as fully resolved
- cleanup succeeded, so the validation workflow did not leave temporary task/profile entries behind

What we learned:

- safe validation of profile support should avoid printing raw secret-bearing files and instead use masked tool responses
- task rendering becomes much more useful when it reports both resolved and missing variables explicitly
- masking behavior must be validated in both metadata and rendered prompt previews, not only in stored profile reads

Impact:

- the project now has the foundation for reusable environment-aware sanity tasks
- future workflows can be templated once and reused across multiple deployment targets
- this ship prepares the ground for safer task sharing, task authoring improvements, and more realistic multi-environment test execution

## 0.6.0

Task authoring UX helpers.

Added:

- `task_wizard_template` to generate structured starter prompts for new browser tasks
- `task_lint` to evaluate raw drafts or saved tasks for quality, vagueness, missing verification, and hardcoded secret-like values
- reusable wizard prompt scaffolding in the prompts module

Why this matters:

- writing long browser tasks manually is powerful, but it is easy to make them too vague or forget verification steps
- the project now helps users author better tasks before they save or run them
- this reduces friction for teams using natural language to define sanity checks

Testcase experience from this ship:

- the wizard tool produced structured drafts with the expected placeholders and assertion guidance for reusable login-style flows
- the simpler wizard mode correctly omitted placeholders and assertion-specific guidance when those options were disabled
- the linter gave a strong draft a high score with no warnings
- the linter correctly downgraded a vague draft like `check website works` and flagged missing structure, missing starting URL, and vagueness
- the linter also caught hardcoded secret-like values and recommended placeholder-based replacements
- linting a saved temporary task by name returned the same useful variable-aware summary as linting a raw draft prompt

What we learned:

- authoring UX improvements are valuable even before execution-time features change, because they improve task quality upstream
- a simple heuristic linter can catch surprisingly meaningful issues in natural-language browser tasks
- having both raw-draft linting and saved-task linting makes the toolset more flexible for iterative authoring

Impact:

- the MCP server now supports not just task execution, but task creation workflows
- users can generate stronger initial drafts and catch task-quality issues earlier
- this ship lays the groundwork for richer task wizards, step previews, and future authoring-time guidance

## 0.7.0

Setup and onboarding improvements.

Added:

- one-command setup script at `scripts/setup.sh`
- runtime defaults through environment-aware settings
- bundled sample task pack in `data/sample_tasks.json`
- onboarding MCP tools:
  `sample_tasks_list`
  `sample_tasks_import`

Why this matters:

- the project should feel useful within minutes, not after a long manual setup
- new users now have a clearer first-run path and sample tasks they can import immediately
- runtime defaults make browser startup less fiddly for common cases like headless execution and longer default timeouts

Testcase experience from this ship:

- the setup script passed shell syntax validation
- bundled sample tasks were discoverable through `sample_tasks_list`
- importing `smoke_example_homepage` succeeded and preserved variable metadata
- the imported sample task rendered cleanly with explicit placeholder values
- the onboarding validation cleaned up the imported sample task afterward so the repo state did not drift
- `browser_start` honored `BROWSER_HEADLESS_DEFAULT=true` when no explicit headless argument was supplied
- the settings layer correctly resolved a custom timeout value of `45000`

What we learned:

- onboarding validation does not always need to re-run dependency installation if the important behavior can be validated more directly and safely
- sample task packs are especially useful when they are immediately renderable, not just listable
- small runtime defaults materially improve first-run ergonomics for browser-based tools

Impact:

- new users now have a clearer path from clone to first useful workflow
- the MCP server is easier to bootstrap into a smoke-testing workflow
- this ship prepares the project for better demos, quicker onboarding, and lower setup friction overall

## 0.8.0

Structured test case support.

Added:

- `task_preview_structured` to preview structured browser sanity tasks without saving them
- `task_create_structured` to save purpose-driven structured tasks
- structured task metadata stored alongside saved tasks
- `task_get` and `task_list` support for exposing whether a task is structured and returning its structured payload

Why this matters:

- saved tasks can now be defined more consistently and audited more easily
- the project moves closer to real test cases instead of only free-form prompt templates
- structured metadata makes future reporting, linting, and suite execution more practical

Testcase experience from this ship:

- structured preview compiled the expected sections for purpose, execution plan, assertions, retry policy, and expected result
- a temporary structured task was created successfully and retained full structured metadata through `task_get`
- `task_list` correctly surfaced `is_structured=true` for the saved structured task
- structured tasks still rendered cleanly through the existing placeholder-resolution layer
- secret placeholders such as `password` remained maskable in rendered previews
- the temporary structured validation task was cleaned up successfully after the checks

What we learned:

- structured test support can be introduced incrementally by compiling to the existing execution prompt model
- backward compatibility is easier to preserve when structured tasks and free-form tasks share the same render and prompt-registration path
- exposing `is_structured` in listing and retrieval APIs is useful immediately for validation and future UI layers

Impact:

- the task system now supports a more formal and auditable testing model
- future work like test suites, reporting, and evidence capture has a better data shape to build on
- this ship is a meaningful step from prompt-driven automation toward reusable structured sanity tests
