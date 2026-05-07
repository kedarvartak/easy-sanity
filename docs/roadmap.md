# Product Roadmap

This project already proves a useful idea: a local MCP server can turn an IDE LLM into an autonomous browser-based sanity testing agent.

Right now, the system is strongest as a lightweight prototype for ad hoc browser automation and reusable natural-language test prompts. The next step is to evolve it from "LLM can drive a browser" into "LLM can run reliable, repeatable sanity tests with evidence and guardrails."

## Product Direction

The goal should be to make the agent:

- easier to set up
- easier to instruct
- easier to trust
- more reusable across apps and environments
- better at producing test evidence and pass/fail outcomes

In short, the project should move from prompt-driven browser control to a true autonomous sanity testing workflow.

## Pending Feature: Browser Harness Integration

An important pending direction is to add an optional `browser-harness` execution mode on top of the existing MCP testing agent.

This should be treated as an additive capability, not a replacement for the current Playwright-backed toolchain.

Why this matters:

- `browser-harness` gives the agent a thin CDP path to a real Chrome session
- it allows helper logic to evolve during execution
- it supports reusable domain skills and interaction skills
- it is a better fit for fluid, hard-to-script browser workflows

Why it should remain optional:

- Easy Sanity still needs explicit assertions, evidence capture, reports, and repeatable pass/fail outcomes
- raw browser freedom is useful, but it does not replace test orchestration
- the current Playwright stack remains valuable for deterministic, local, and headless sanity runs

See [Browser Harness Integration Roadmap](/home/kedar/Desktop/Projects/use_browser/docs/browser-harness-roadmap.md:1).

## Make It Easier To Use

### 1. Add higher-level tools

Today the model has to assemble low-level steps like `navigate`, `click`, and `type` on its own. That works, but it creates avoidable variance.

Add tools such as:

- `browser_find_element(description="email field")`
- `browser_fill_form(fields={...})`
- `browser_click_by_role(role="button", name="Login")`
- `browser_act(goal="submit the login form")`
- `browser_pick_from_dropdown(label="Product", option="Truck")`

These reduce prompt burden and make the agent less dependent on fragile selector guessing.

### 2. Add first-class assertions

A sanity testing agent becomes much more useful once it can clearly decide whether a test passed.

Add tools such as:

- `assert_url_contains`
- `assert_text_visible`
- `assert_text_not_visible`
- `assert_element_exists`
- `assert_element_enabled`
- `assert_page_title`
- `assert_count`

This shifts the project from automation-only toward actual testing.

### 3. Add variables, secrets, and environments

Tasks should not require hardcoded credentials or fixed URLs.

Add support for:

- environment variables in saved tasks
- secret placeholders
- reusable inputs like `{{base_url}}`, `{{email}}`, `{{password}}`
- environment profiles such as `local`, `staging`, and `prod`

This makes tasks portable and safer.

### 4. Improve task authoring UX

Writing long prompts manually is powerful, but not easy.

Make task creation simpler with:

- a task wizard prompt template
- a "record and save as task" flow
- task descriptions with examples
- test step preview before saving
- task linting that catches missing assertions or vague instructions

### 5. Improve setup and onboarding

The project should feel installable in minutes.

Useful upgrades:

- one-command setup for dependencies and browser install
- sample task pack for common smoke-test flows
- better troubleshooting docs
- optional headless/headed defaults in config
- screenshots or demo GIFs in docs

## Make It More Useful

### 1. Turn prompts into structured test cases

Saved tasks are currently prompt templates. They should evolve into structured test definitions with:

- name
- purpose
- inputs
- environment variables
- steps
- assertions
- retry policy
- expected result

This would make runs more consistent and easier to audit.

### 2. Add evidence capture and reports

Every run should produce artifacts that help users understand success or failure.

Add:

- per-step screenshots
- before/after page state snapshots
- extracted evidence
- timestamps
- action logs
- final pass/fail summary
- markdown or JSON reports

This makes the tool much more useful for QA, demos, and debugging regressions.

### 3. Add reusable suites

Most teams want more than one-off tasks.

Support:

- smoke suites
- critical-path suites
- environment-specific suites
- tags like `auth`, `checkout`, `search`
- batch execution of multiple tasks

### 4. Add recovery and retry behavior

A useful autonomous agent should recover from normal UI flakiness.

Examples:

- auto-retry clicks after transient failures
- wait for text or URL changes instead of fixed sleeps
- fallback selector strategies
- re-check state after each mutation
- intelligent recovery when a modal or cookie banner blocks progress

### 5. Add domain understanding

The agent becomes much more useful if it can reason about app structure instead of only raw HTML.

Examples:

- identify forms and fields by label
- detect tables, cards, navs, and dialogs
- understand current app route or workflow step
- summarize "what changed" after an action

## Additional Tools To Expose To The LLM

If this project is positioned as an autonomous sanity testing agent, the tool surface should help the model inspect, act, verify, and report.

### Inspection tools

- `browser_get_dom_summary()`  
  Return a cleaner semantic page summary: forms, buttons, inputs, dialogs, tables, alerts, headings.

- `browser_get_accessibility_tree()`  
  Expose accessible roles and names so the model can use robust selectors.

- `browser_list_forms()`  
  Return form fields with labels, names, placeholders, required flags, and current values.

- `browser_list_links()`  
  Useful for navigation verification and crawl-like sanity flows.

- `browser_list_network_errors()`  
  Surface failed requests, console errors, and HTTP failures.

- `browser_get_console_logs()`  
  Very useful for catching broken pages even when visuals look fine.

- `browser_get_requests()`  
  Provide a summary of API requests triggered by a user action.

- `browser_get_storage()`  
  Inspect cookies, localStorage, and sessionStorage when login state matters.

### Action tools

- `browser_click_by_label(name)`
- `browser_click_by_role(role, name)`
- `browser_fill(label, value)`
- `browser_select_option(label, value)`
- `browser_press_key(key)`
- `browser_hover(selector)`
- `browser_drag_and_drop(source, target)`
- `browser_upload_file(selector, path)`
- `browser_download_file(link_or_selector)`
- `browser_refresh()`
- `browser_go_back()`
- `browser_go_forward()`
- `browser_open_tab(url)`
- `browser_switch_tab(index_or_title)`
- `browser_close_tab()`

These make the agent more capable on real applications without forcing it to improvise every low-level action.

### Waiting and synchronization tools

- `browser_wait_for_text(text)`
- `browser_wait_for_element(selector)`
- `browser_wait_for_url(pattern)`
- `browser_wait_for_navigation()`
- `browser_wait_for_network_idle()`
- `browser_wait_for_disappearance(selector)`

These are much more reliable than generic sleeps.

### Assertion tools

- `assert_element_visible`
- `assert_element_hidden`
- `assert_input_value`
- `assert_url_equals`
- `assert_text_contains`
- `assert_text_matches`
- `assert_no_console_errors`
- `assert_no_failed_requests`
- `assert_screenshot_stable`

This gives the model a clear language for pass/fail reasoning.

### Extraction tools

- `browser_extract_table(selector)`
- `browser_extract_list(selector)`
- `browser_extract_json_from_page()`
- `browser_extract_links()`
- `browser_capture_section(selector)`
- `browser_compare_text(selector, expected)`

These help when the goal is data validation rather than simple clicking.

### Reporting tools

- `test_start_run(name, metadata)`
- `test_log_step(step, outcome, evidence)`
- `test_mark_pass(reason)`
- `test_mark_fail(reason, evidence)`
- `test_save_artifact(type, payload)`
- `test_generate_report(format="markdown")`

This would let the LLM build a proper test narrative instead of returning an informal summary.

## Suggested Implementation Phases

### Phase 1: Reliability Foundation

- add assertion tools
- add role/label-based actions
- add smarter waits
- add structured error messages

### Phase 5: Adaptive Browser Mode With `browser-harness`

- integrate `browser-harness` as an optional backend that attaches to the user's real Chrome session
- preserve the existing MCP tool contract while allowing selected tools to delegate to `browser-harness`
- add a controlled skill-sync flow for domain skills and helper learnings
- keep Easy Sanity responsible for assertions, reports, action history, and final pass/fail classification
- add setup, safety, and recovery rules for real-browser attachment mode
- remove hardcoded secrets from saved examples

### Phase 2: Reusability

- add task parameters and environment variables
- support structured task definitions
- add test suite grouping
- add reusable sample tasks

### Phase 3: Observability

- capture screenshots and logs per step
- collect network and console failures
- add run summaries and downloadable reports

### Phase 4: Agent Intelligence

- add semantic DOM summaries
- add recovery strategies
- add record-and-replay style task creation
- add self-healing selector support

## Success Criteria

The project will feel meaningfully more complete when a user can:

- describe a smoke test in plain English
- run it against any environment without editing credentials into the prompt
- get a deterministic pass/fail outcome
- inspect screenshots, logs, and evidence for every step
- save the workflow as a reusable sanity suite
- trust the agent to recover from common UI variability

At that point, the system will have evolved from a free browser automation MCP server into a practical autonomous sanity testing agent.
