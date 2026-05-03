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
