# Feature Testcases

This document defines how we validate shipped features in this project.

The rule going forward is simple:

- every feature push must have matching testcases
- every testcase should say what to do, what tools to use, and what success looks like
- whenever possible, testcases should be runnable through Codex with this MCP server connected

This repo is building toward an autonomous sanity testing agent, so our testcases should reflect both:

- code correctness
- agent behavior correctness

## Testing Philosophy

For each shipped feature, we want to validate three things:

1. The code is wired correctly.
2. The MCP tools behave as intended.
3. The LLM can actually use the feature in realistic workflows.

That means a good feature validation set should include:

- module-level smoke checks
- tool-level behavior checks
- end-to-end natural-language workflows

## Release Rule

For every new shipped feature, add:

- at least one direct tool-level testcase
- at least one realistic workflow testcase
- clear expected results
- any setup notes or environment assumptions

## How To Run These In Codex

Recommended setup:

1. Add this MCP server to Codex using the same local MCP config pattern documented in `README.md`.
2. Restart Codex so the tools are available.
3. Run the workflow prompts below in a clean session.
4. Compare the observed tool usage and results with the expected outcome in this document.

## Testcase Template For Future Features

Use this structure for every new feature:

### Feature Name

- Version:
- Goal:
- Setup:
- Prompt or action:
- Expected tool behavior:
- Expected output:
- Failure signals:

## Shipped Feature Testcases

## 0.1.0 Core MCP Browser Automation

### TC-001: Browser session can start and stop

- Version: `0.1.0`
- Goal: Confirm the MCP server can create and clean up a browser session.
- Setup: MCP server connected in Codex.
- Prompt or action: Ask Codex to start the browser for a simple task, then stop it immediately.
- Expected tool behavior:
  `browser_start` is called once.
  `browser_stop` is called once.
- Expected output:
  `browser_start` returns `status=success`.
  `browser_stop` returns `status=success` and includes the task plus action history.
- Failure signals:
  Browser fails to launch.
  Browser session remains uninitialized.
  Cleanup errors occur during stop.

### TC-002: Navigate and inspect page state

- Version: `0.1.0`
- Goal: Confirm navigation and page inspection work together.
- Setup: MCP server connected in Codex.
- Prompt or action:
  Tell Codex: "Use the browser automation MCP to open https://example.com and tell me the page title."
- Expected tool behavior:
  `browser_start`
  `browser_navigate`
  `browser_get_state`
  `browser_stop`
- Expected output:
  Returned title should match the loaded page.
  `browser_get_state` should include URL, title, visible text, interactive elements, and screenshot data.
- Failure signals:
  Navigation does not complete.
  State payload is missing key fields.
  Screenshot is not included.

### TC-003: Basic low-level interaction flow

- Version: `0.1.0`
- Goal: Confirm click/type/wait/extract flow works at a low level.
- Setup: Use a simple public page or an internal test page with a form.
- Prompt or action:
  Ask Codex to open the page, type into an input using `browser_type`, click a button, wait, and extract a result region.
- Expected tool behavior:
  Low-level tools are called in the intended order.
- Expected output:
  Typed input is accepted.
  Click action succeeds.
  Extracted text reflects the result state.
- Failure signals:
  Selectors fail despite valid visible elements.
  Extract step cannot find expected output.

### TC-004: Task persistence lifecycle

- Version: `0.1.0`
- Goal: Confirm tasks can be created, listed, fetched, and deleted.
- Setup: MCP server connected in Codex.
- Prompt or action:
  Ask Codex to create a test task named `smoke_test_demo`, list tasks, fetch that task, then delete it.
- Expected tool behavior:
  `task_create`
  `task_list`
  `task_get`
  `task_delete`
- Expected output:
  Created task appears in `task_list`.
  `task_get` returns matching name, description, and prompt.
  Deleted task no longer appears after removal.
- Failure signals:
  Task is not persisted to `tasks.json`.
  Prompt registration does not update.
  Deleted task remains available.

## 0.2.0 Higher-Level Browser Interaction Tools

### TC-005: Find likely element candidates from natural language

- Version: `0.2.0`
- Goal: Confirm `browser_find_element` can map descriptions to likely controls.
- Setup: Use a page containing a form with recognizable labels such as email, password, and login button.
- Prompt or action:
  Ask Codex: "Open the page and use `browser_find_element` to find the email field and login button."
- Expected tool behavior:
  `browser_get_state` may be called first.
  `browser_find_element` should be used with natural-language descriptions.
- Expected output:
  The returned matches should include reasonable candidates with useful fields like `tag`, `role`, `text`, `label`, `name`, or `id`.
- Failure signals:
  No likely candidates returned for obvious controls.
  Returned elements are irrelevant or missing identifiers.

### TC-006: Fill a field semantically

- Version: `0.2.0`
- Goal: Confirm `browser_fill` can locate an input by label-like description.
- Setup: Use a form with labeled inputs.
- Prompt or action:
  Ask Codex: "Use `browser_fill` to enter `test@example.com` into the email field."
- Expected tool behavior:
  `browser_fill(field="email", text="test@example.com")` or similar semantic description.
- Expected output:
  Tool returns success and includes `matched_by`.
  Field should contain the entered value.
- Failure signals:
  The tool cannot find a clear labeled field.
  `matched_by` is inconsistent with the actual DOM situation.

### TC-007: Click by accessible role

- Version: `0.2.0`
- Goal: Confirm `browser_click_by_role` works for accessible controls.
- Setup: Use a page with a clear button or link name.
- Prompt or action:
  Ask Codex: "Click the Login button using the higher-level role-based tool."
- Expected tool behavior:
  `browser_click_by_role(role="button", name="Login")`
- Expected output:
  Tool returns success and the page advances or mutates as expected.
- Failure signals:
  Role-based click fails on a clearly accessible control.
  The wrong element is clicked.

### TC-008: End-to-end semantic login workflow

- Version: `0.2.0`
- Goal: Confirm the new higher-level tools reduce low-level selector guessing.
- Setup: Use a login page or internal test app.
- Prompt or action:
  Tell Codex:
  "Open the login page, find the email and password fields semantically, fill them, click the sign-in button by role, and confirm whether login succeeded."
- Expected tool behavior:
  Prefer `browser_fill`, `browser_click_by_role`, and `browser_find_element` over raw selectors.
- Expected output:
  Workflow completes with less reliance on CSS selectors.
  Final summary explains whether login succeeded.
- Failure signals:
  Codex still has to fall back to brittle raw selectors for obvious elements.
  Higher-level tools fail where low-level tools would have worked.

## 0.3.0 Modularity Refactor

### TC-009: Thin entrypoint boot still works

- Version: `0.3.0`
- Goal: Confirm the modular split did not change runtime startup behavior.
- Setup: Run the MCP server through the existing Codex MCP configuration.
- Prompt or action:
  Start a fresh Codex session and verify the MCP server loads and exposes all expected tools.
- Expected tool behavior:
  All task tools and browser tools should still be registered and available.
- Expected output:
  Codex can call the same tools as before the refactor.
- Failure signals:
  Missing tools after startup.
  Import errors due to module boundaries.
  Prompt registration no longer works.

### TC-010: Saved task prompts still load after refactor

- Version: `0.3.0`
- Goal: Confirm `tasks.json` is still read and prompts are still registered at startup.
- Setup: Ensure at least one saved task exists in `tasks.json`.
- Prompt or action:
  Start the MCP server and inspect whether the saved task is available for invocation in Codex.
- Expected tool behavior:
  Startup should call task prompt loading through the modularized task layer.
- Expected output:
  Saved tasks remain available exactly as before the refactor.
- Failure signals:
  Saved tasks disappear.
  Prompt registration no longer reflects `tasks.json`.

### TC-011: Browser tools still share the same session state

- Version: `0.3.0`
- Goal: Confirm `browser_state.py` remains the single source of browser session truth.
- Setup: Start a browser, navigate somewhere, perform one or two actions, and inspect history.
- Prompt or action:
  Ask Codex to start a session, navigate, click or scroll, call `browser_get_history`, then stop.
- Expected tool behavior:
  Actions recorded in browser tools should appear in shared history consistently.
- Expected output:
  History reflects the full session correctly.
  State remains coherent across modules.
- Failure signals:
  History is incomplete.
  Session state is lost between tools.
  Browser cleanup does not reset state properly.

## 0.4.0 First-Class Assertions

### TC-012: URL assertion passes on matching route

- Version: `0.4.0`
- Goal: Confirm `assert_url_contains` passes when the current URL contains expected text.
- Setup: Open the local test page.
- Prompt or action:
  Ask Codex to open the page and assert that the URL contains `login_form.html`.
- Expected tool behavior:
  `browser_start`
  `browser_navigate`
  `assert_url_contains`
- Expected output:
  Assertion returns `status=success` and `passed=true`.
- Failure signals:
  Matching URL text still produces a failed assertion.
  Assertion payload omits expected URL details.

### TC-013: Title and text assertions work before interaction

- Version: `0.4.0`
- Goal: Confirm page-title and visible-text assertions work on initial page load.
- Setup: Open the local test page.
- Prompt or action:
  Ask Codex to verify that the page title contains `Browser MCP Test Page` and that visible text includes `Login Demo`.
- Expected tool behavior:
  `assert_page_title`
  `assert_text_visible`
- Expected output:
  Both assertions return `status=success` and `passed=true`.
- Failure signals:
  Visible text is present but assertion fails.
  Title assertion does not reflect actual page title.

### TC-014: Negative text assertion works before submit

- Version: `0.4.0`
- Goal: Confirm `assert_text_not_visible` passes when text is absent.
- Setup: Open the local test page before submitting the form.
- Prompt or action:
  Ask Codex to assert that `Logged in as` is not visible.
- Expected tool behavior:
  `assert_text_not_visible`
- Expected output:
  Assertion returns `status=success` and `passed=true`.
- Failure signals:
  Assertion fails even though the text is absent.
  Hidden or nonexistent text is misreported as visible.

### TC-015: Element existence, enabled state, and count assertions

- Version: `0.4.0`
- Goal: Confirm structure-based assertions work on predictable elements.
- Setup: Open the local test page.
- Prompt or action:
  Ask Codex to:
  assert `#email` exists,
  assert the submit button is enabled,
  assert the page contains exactly 2 `input` elements.
- Expected tool behavior:
  `assert_element_exists`
  `assert_element_enabled`
  `assert_count`
- Expected output:
  All assertions return `status=success` and `passed=true`.
- Failure signals:
  Existing selectors are reported missing.
  Enabled elements are reported disabled.
  Accurate counts are reported incorrectly.

### TC-016: Assertions work inside a realistic semantic login flow

- Version: `0.4.0`
- Goal: Confirm assertions can be used as first-class validation steps within a realistic workflow.
- Setup: Open the local test page.
- Prompt or action:
  Tell Codex:
  "Open the page, fill the email and password fields semantically, click Login, then assert that `Logged in as test@example.com` is visible and `Missing credentials` is not visible."
- Expected tool behavior:
  Prefer `browser_fill`, `browser_click_by_role`, `assert_text_visible`, and `assert_text_not_visible`.
- Expected output:
  Workflow completes successfully and assertions clearly describe pass/fail outcome.
- Failure signals:
  Assertions cannot be used reliably after page interaction.
  Workflow completes but assertions do not reflect post-submit state.

### TC-017: Failed assertions return explicit structured failure

- Version: `0.4.0`
- Goal: Confirm failing assertions return useful structured failure payloads rather than ambiguous tool errors.
- Setup: Open the local test page.
- Prompt or action:
  Ask Codex to assert that the selector `input` has count `3`.
- Expected tool behavior:
  `assert_count(selector="input", expected=3)`
- Expected output:
  Assertion returns `status=error`, `passed=false`, and includes `expected`, `actual`, and a clear failure message.
- Failure signals:
  Failure returns no expected/actual comparison.
  Assertion failure is indistinguishable from an implementation crash.

### TC-018: Assertion steps appear in shared browser history

- Version: `0.4.0`
- Goal: Confirm assertions are captured in `browser_get_history` for auditability.
- Setup: Run a small workflow using several assertion tools.
- Prompt or action:
  Ask Codex to run assertions, then call `browser_get_history`.
- Expected tool behavior:
  Assertion actions are appended to shared action history.
- Expected output:
  History includes entries such as `assert_url_contains`, `assert_page_title`, `assert_text_visible`, `assert_count`, and associated pass/fail details.
- Failure signals:
  Assertions work but are missing from history.
  History omits whether the assertion passed or failed.

## 0.5.0 Task Variables And Environment Profiles

### TC-019: Task creation extracts placeholders and secret variables

- Version: `0.5.0`
- Goal: Confirm `task_create` detects template placeholders and tracks secret variables.
- Setup: MCP server connected in Codex.
- Prompt or action:
  Ask Codex to create a task containing `{{base_url}}`, `{{email}}`, and `{{password}}`, with `password` marked as secret.
- Expected tool behavior:
  `task_create`
  `task_get`
- Expected output:
  The saved task includes `variables` with `base_url`, `email`, and `password`.
  `secret_variables` includes `password`.
- Failure signals:
  Placeholder metadata is missing.
  Secret placeholders are not tracked.

### TC-020: Profile lifecycle works through MCP tools

- Version: `0.5.0`
- Goal: Confirm environment profiles can be created, listed, retrieved, and deleted.
- Setup: MCP server connected in Codex.
- Prompt or action:
  Ask Codex to create a temporary profile, list profiles, fetch that profile, then delete it.
- Expected tool behavior:
  `profile_save`
  `profile_list`
  `profile_get`
  `profile_delete`
- Expected output:
  The profile appears in `profile_list`.
  `profile_get` returns the stored variable names.
  After deletion, the profile is no longer available.
- Failure signals:
  Profile does not persist.
  Profile list does not update.
  Profile cannot be deleted cleanly.

### TC-021: Profile masking protects likely secret values

- Version: `0.5.0`
- Goal: Confirm `profile_get(mask_secrets=true)` masks likely secret fields.
- Setup: Save a profile with a variable named `password`.
- Prompt or action:
  Ask Codex to retrieve the profile with masking enabled.
- Expected tool behavior:
  `profile_get(name=..., mask_secrets=true)`
- Expected output:
  Secret-like keys such as `password` are returned as `***MASKED***`.
  Non-secret values remain readable.
- Failure signals:
  Secret values are returned in plaintext despite masking.
  Non-secret values are masked unnecessarily.

### TC-022: Task rendering resolves from profile values

- Version: `0.5.0`
- Goal: Confirm `task_render` can fully resolve a task template using a saved profile.
- Setup: Save a task with placeholders and a matching profile with all required values.
- Prompt or action:
  Ask Codex to render the task using that profile.
- Expected tool behavior:
  `task_render`
- Expected output:
  `is_fully_resolved` is `true`.
  `missing_variables` is empty.
  `resolved_values` reflects the selected profile values.
- Failure signals:
  Fully provided profile values still leave unresolved placeholders.
  Render output does not match stored profile values.

### TC-023: Explicit variables override profile values

- Version: `0.5.0`
- Goal: Confirm render precedence follows explicit variables > profile values > environment variables.
- Setup: Save a task and profile, then provide overrides in `variables_json`.
- Prompt or action:
  Ask Codex to render the task using both a profile and explicit overrides for fields like `base_url` or `email`.
- Expected tool behavior:
  `task_render(profile=..., variables_json=...)`
- Expected output:
  The rendered prompt uses explicit variable values instead of profile defaults.
  `resolved_values` reflects the override precedence.
- Failure signals:
  Profile values override explicit inputs.
  Rendered prompt does not match resolved precedence.

### TC-024: Environment values are used when profile values are absent

- Version: `0.5.0`
- Goal: Confirm `task_render` can fall back to process environment variables.
- Setup: Save a task with placeholders and provide one matching environment variable.
- Prompt or action:
  Ask Codex to render the task without a profile but with part of the data available in the environment.
- Expected tool behavior:
  `task_render`
- Expected output:
  Environment-provided values are included in `resolved_values`.
  Missing placeholders are still reported explicitly.
- Failure signals:
  Environment values are ignored.
  Missing placeholders are silently omitted.

### TC-025: Incomplete task rendering reports missing variables

- Version: `0.5.0`
- Goal: Confirm partial renders stay safe and report what is still unresolved.
- Setup: Save a task with multiple placeholders, but provide only a subset of values.
- Prompt or action:
  Ask Codex to render the task with only one or two variables supplied.
- Expected tool behavior:
  `task_render`
- Expected output:
  `is_fully_resolved` is `false`.
  `missing_variables` lists the unresolved placeholders.
- Failure signals:
  Missing variables are not reported.
  Task is marked fully resolved when placeholders remain.

### TC-026: Rendered task previews can mask secret substitutions

- Version: `0.5.0`
- Goal: Confirm `task_render(mask_secrets=true)` masks secret values in both `resolved_values` and the rendered prompt preview.
- Setup: Save a task with a secret placeholder and provide a value via profile or environment.
- Prompt or action:
  Ask Codex to render the task with masking enabled.
- Expected tool behavior:
  `task_render(mask_secrets=true)`
- Expected output:
  Secret values appear as `***MASKED***` in both `resolved_values` and the rendered prompt preview.
- Failure signals:
  Secret values are leaked in the rendered preview.
  Masking only applies to metadata but not the rendered prompt.

## 0.6.0 Task Authoring UX Helpers

### TC-027: Wizard template generates a structured reusable draft

- Version: `0.6.0`
- Goal: Confirm `task_wizard_template` generates a strong starter task for realistic browser flows.
- Setup: MCP server connected in Codex.
- Prompt or action:
  Ask Codex to generate a task template for logging into an app and verifying the dashboard loads, with placeholders and assertions enabled.
- Expected tool behavior:
  `task_wizard_template`
- Expected output:
  The response includes a suggested name, description, structured prompt, `base_url`/`email`/`password` placeholders, and assertion guidance.
- Failure signals:
  Template is unstructured.
  Expected placeholders are missing.
  Assertion guidance is not included when requested.

### TC-028: Wizard template can generate a simpler non-parameterized draft

- Version: `0.6.0`
- Goal: Confirm the wizard can also produce a simpler task without placeholders or assertion guidance.
- Setup: MCP server connected in Codex.
- Prompt or action:
  Ask Codex to generate a template for opening a marketing page and confirming a CTA is visible, with placeholders and assertions disabled.
- Expected tool behavior:
  `task_wizard_template(include_placeholders=false, include_assertions=false)`
- Expected output:
  The task contains no placeholder variables and no assertion-specific guidance.
- Failure signals:
  Placeholders are still inserted when disabled.
  Assertion language appears when not requested.

### TC-029: Linter recognizes a strong structured task

- Version: `0.6.0`
- Goal: Confirm `task_lint` gives a strong score to a well-structured draft with verification steps.
- Setup: Use a wizard-generated task prompt with placeholders and assertions enabled.
- Prompt or action:
  Ask Codex to lint the generated prompt directly.
- Expected tool behavior:
  `task_lint(prompt=...)`
- Expected output:
  High quality score, no major warnings, and strengths noting structure and verification.
- Failure signals:
  Strong task gets a low score.
  Linter misses clear strengths.

### TC-030: Linter flags vague prompts

- Version: `0.6.0`
- Goal: Confirm `task_lint` catches short vague task drafts.
- Setup: Use a weak draft such as `check website works`.
- Prompt or action:
  Ask Codex to lint the weak prompt.
- Expected tool behavior:
  `task_lint(prompt=...)`
- Expected output:
  Lower quality score with warnings about missing structure, missing starting URL, and vagueness.
- Failure signals:
  Vague task is treated as high quality.
  Missing verification and structure are not flagged.

### TC-031: Linter warns about hardcoded secret-like values

- Version: `0.6.0`
- Goal: Confirm `task_lint` warns when prompt text appears to contain hardcoded secret-like values.
- Setup: Use a prompt containing terms like `password` or `api key` directly in the text.
- Prompt or action:
  Ask Codex to lint a prompt such as `Go to https://example.com and login with password supersecret and check stuff.`
- Expected tool behavior:
  `task_lint(prompt=...)`
- Expected output:
  Warning about secret-like values without placeholders and a suggestion to use placeholders such as `{{password}}`.
- Failure signals:
  Hardcoded secret-like values are not flagged.
  No placeholder suggestion is provided.

### TC-032: Linter works on saved tasks as well as raw drafts

- Version: `0.6.0`
- Goal: Confirm `task_lint(name=...)` can lint a saved task after `task_create`.
- Setup: Save a temporary task using a strong wizard-generated prompt.
- Prompt or action:
  Ask Codex to create a task, lint it by name, then delete it.
- Expected tool behavior:
  `task_create`
  `task_lint(name=...)`
  `task_delete`
- Expected output:
  Linting by saved task name returns the same variable-aware quality summary as linting the raw prompt.
- Failure signals:
  Saved tasks cannot be linted by name.
  Variable metadata disappears during linting of saved tasks.

## 0.7.0 Setup And Onboarding Improvements

### TC-033: Setup script passes shell syntax validation

- Version: `0.7.0`
- Goal: Confirm the one-command setup script is at least syntactically valid and ready for execution.
- Setup: Local repo checkout.
- Prompt or action:
  Run a shell syntax check against `scripts/setup.sh`.
- Expected tool behavior:
  Shell validation completes without syntax errors.
- Expected output:
  The script parses cleanly.
- Failure signals:
  Script contains shell syntax errors.
  Script cannot be parsed by `sh`.

### TC-034: Bundled sample tasks are discoverable

- Version: `0.7.0`
- Goal: Confirm onboarding sample tasks are visible before import.
- Setup: MCP server connected in Codex.
- Prompt or action:
  Ask Codex to call `sample_tasks_list`.
- Expected tool behavior:
  `sample_tasks_list`
- Expected output:
  The response includes the bundled sample task names, descriptions, and placeholder variables.
- Failure signals:
  Sample task pack is empty or unreadable.
  Variable metadata is missing from listed sample tasks.

### TC-035: Sample task import works and keeps metadata

- Version: `0.7.0`
- Goal: Confirm a bundled sample task can be imported into saved tasks and retains reusable metadata.
- Setup: MCP server connected in Codex.
- Prompt or action:
  Ask Codex to import `smoke_example_homepage`, inspect it with `task_get`, and then clean it up if it was imported only for validation.
- Expected tool behavior:
  `sample_tasks_import`
  `task_get`
  `task_delete` when cleanup is needed
- Expected output:
  Imported task is available in saved tasks and still includes `variables` and `secret_variables`.
- Failure signals:
  Import succeeds but task metadata is missing.
  Imported task cannot be retrieved or cleaned up.

### TC-036: Imported sample tasks can be rendered immediately

- Version: `0.7.0`
- Goal: Confirm sample tasks are actually useful for onboarding, not just discoverable.
- Setup: Import a bundled sample task that uses placeholders.
- Prompt or action:
  Ask Codex to render the imported sample with explicit variables.
- Expected tool behavior:
  `task_render`
- Expected output:
  Render succeeds with `is_fully_resolved=true`, no missing variables, and a usable rendered task prompt.
- Failure signals:
  Imported sample tasks cannot be rendered cleanly.
  Placeholders remain unresolved despite supplied values.

### TC-037: Runtime default headless mode is honored

- Version: `0.7.0`
- Goal: Confirm onboarding defaults reduce first-run configuration friction.
- Setup: Set `BROWSER_HEADLESS_DEFAULT=true` in the environment.
- Prompt or action:
  Ask Codex to call `browser_start` without explicitly passing a `headless` argument.
- Expected tool behavior:
  `browser_start`
- Expected output:
  The returned payload reports `headless=true`.
- Failure signals:
  Environment default is ignored.
  Browser starts in headed mode despite the configured default.

### TC-038: Runtime default timeout is configurable

- Version: `0.7.0`
- Goal: Confirm the default browser timeout can be controlled through environment configuration.
- Setup: Set `BROWSER_DEFAULT_TIMEOUT_MS` to a non-default value such as `45000`.
- Prompt or action:
  Validate the timeout helper used by browser state initialization.
- Expected tool behavior:
  Settings resolution should return the configured timeout value.
- Expected output:
  The effective default timeout reflects the environment variable.
- Failure signals:
  Invalid or provided timeout values are ignored unexpectedly.
  Effective timeout remains at the old default when valid configuration is present.

## 0.8.0 Structured Test Case Support

### TC-039: Structured task preview compiles expected sections

- Version: `0.8.0`
- Goal: Confirm `task_preview_structured` compiles structured inputs into an execution-ready prompt.
- Setup: MCP server connected in Codex.
- Prompt or action:
  Ask Codex to preview a structured login verification task with purpose, steps, assertions, retry policy, and expected result.
- Expected tool behavior:
  `task_preview_structured`
- Expected output:
  The compiled prompt includes `Purpose:`, `Execution Plan:`, `Assertions:`, `Retry Policy:`, and `Expected Result:`.
- Failure signals:
  Structured sections are missing from the compiled prompt.
  Preview omits variables or secret-variable inference.

### TC-040: Structured task creation persists structured metadata

- Version: `0.8.0`
- Goal: Confirm a structured task can be saved and retains its structured definition.
- Setup: Use a temporary structured task name for validation.
- Prompt or action:
  Ask Codex to save a structured task with purpose, steps, assertions, inputs, environment variables, and expected result.
- Expected tool behavior:
  `task_create_structured`
  `task_get`
- Expected output:
  `task_get` returns `is_structured=true`.
  Structured metadata includes keys such as `purpose`, `steps`, `assertions`, `inputs`, `environment_variables`, `retry_policy`, and `expected_result`.
- Failure signals:
  Task saves only as a flat prompt with no structured metadata.
  Structured fields do not round-trip through `task_get`.

### TC-041: Task list exposes whether a task is structured

- Version: `0.8.0`
- Goal: Confirm `task_list` can distinguish structured tasks from plain prompt tasks.
- Setup: Save a temporary structured task.
- Prompt or action:
  Ask Codex to call `task_list` after saving the structured task.
- Expected tool behavior:
  `task_list`
- Expected output:
  The structured task entry includes `is_structured=true`.
- Failure signals:
  Structured tasks are indistinguishable from legacy prompt tasks in task listings.

### TC-042: Structured task rendering resolves placeholders and masks secrets

- Version: `0.8.0`
- Goal: Confirm structured tasks still work with the existing variable rendering system.
- Setup: Save a structured task containing placeholders such as `{{base_url}}`, `{{email}}`, and `{{password}}`.
- Prompt or action:
  Ask Codex to render the structured task with explicit variable values and secret masking enabled.
- Expected tool behavior:
  `task_render`
- Expected output:
  `is_fully_resolved=true`.
  `missing_variables` is empty.
  The rendered prompt contains resolved non-secret values and masks secret substitutions such as password.
- Failure signals:
  Structured tasks cannot be rendered like regular tasks.
  Secrets are leaked in the rendered preview.

### TC-043: Structured task cleanup leaves no validation residue

- Version: `0.8.0`
- Goal: Confirm structured-task validation can be done safely without leaving test artifacts behind.
- Setup: Use a temporary validation task name.
- Prompt or action:
  Ask Codex to create the structured task, validate it, then delete it.
- Expected tool behavior:
  `task_create_structured`
  `task_delete`
- Expected output:
  Cleanup succeeds and the temporary task is removed after validation.
- Failure signals:
  Temporary structured tasks remain in saved tasks after validation.
  Cleanup fails or leaves prompt registration behind.

## Recommended Workflow For Every Future Feature

When we ship a new feature, we should add all of the following:

- one "tool works directly" testcase
- one "Codex naturally chooses this tool" testcase
- one "this feature works inside a realistic user flow" testcase
- one regression note describing what older behavior must still keep working

## Good Candidate Future Test Pages

To make feature validation easier, we should eventually maintain a small stable set of pages or apps for testing:

- a simple login form
- a search page
- a multi-step form
- a page with accessible buttons and links
- a page with known visible text for extraction checks

That will give us repeatable validation targets for new MCP features without depending too much on changing third-party sites.
