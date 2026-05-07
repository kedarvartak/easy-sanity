# Browser Harness Integration Roadmap

This document defines how Easy Sanity should integrate `browser-harness` end to end.

The decision here is explicit:

- use `browser-harness` as the only adaptive browser-control path
- keep the current Playwright path for deterministic local runs
- do not build a second custom CDP harness inside this repo

That means Easy Sanity will become a dual-mode testing agent:

- `playwright` mode for local controlled browser automation
- `browser-harness` mode for attaching to a real Chrome session through the open source harness

## Goal

The goal is not to replace the existing browser agent.

The goal is to make Easy Sanity better at hard, real-world browser tasks while preserving what already makes it valuable:

- explicit testing assertions
- artifacts and evidence
- action history
- reusable tasks
- repo-aware testing memory
- pass/fail-oriented reporting

`browser-harness` provides flexible execution.
Easy Sanity must remain the orchestration and testing layer above it.

## Product Positioning

After this integration, the project should be described as:

"An autonomous testing agent with two execution modes: deterministic Playwright control and adaptive real-browser control through `browser-harness`."

This distinction matters.

- `browser-harness` is the execution substrate for flexible real-browser interaction
- Easy Sanity remains the system that plans, verifies, records, retries, and reports

## Non-Goals

To avoid architectural drift, this integration should not do the following:

- build a separate in-house CDP runtime that competes with `browser-harness`
- expose raw CDP as the primary user-facing abstraction
- let generated helper code become the source of truth for test outcomes
- replace assertions with informal LLM judgment
- couple every existing tool directly to harness-specific behavior on day one

## Integration Principles

### 1. Preserve the MCP contract

Existing browser tools should continue to exist.
Where possible, the same MCP tool names should work regardless of backend.

Examples:

- `browser_start`
- `browser_navigate`
- `browser_get_state`
- `browser_click`
- `browser_fill`
- `browser_wait_for_text`
- `browser_stop`

The difference should be internal backend execution, not a wholesale external API break.

### 2. Keep Easy Sanity in charge of testing

`browser-harness` should execute actions.
Easy Sanity should still own:

- assertions
- evidence capture
- action history
- retries and recovery policy
- domain summaries
- final report generation
- task rendering and profile usage

### 3. Treat adaptive learning as controlled persistence

The harness can learn helper logic and domain skills, but Easy Sanity should define when learned behavior is trusted, referenced, surfaced, and documented.

### 4. Prefer fallback over replacement

The ideal behavior is:

- start with current high-level actions
- delegate to `browser-harness` when the task needs real-browser flexibility
- keep deterministic Playwright for simpler, repeatable runs

## End-to-End Architecture

The resulting architecture should look like this:

1. User or saved task asks for a browser workflow.
2. Easy Sanity decides which execution mode to use.
3. Easy Sanity runs browser actions through the selected backend.
4. Easy Sanity captures state, assertions, evidence, and reports.
5. If `browser-harness` learns something reusable, Easy Sanity records that in a controlled way.
6. The session ends with a test-oriented result, not just a sequence of actions.

## Target Code Structure

The implementation should evolve toward these modules:

- `browser/backends/base.py`
  Shared backend interface

- `browser/backends/playwright_backend.py`
  Wrap current Playwright lifecycle and page actions

- `browser/backends/browser_harness_backend.py`
  Bridge Easy Sanity calls to the external `browser-harness` runtime

- `browser/backend_router.py`
  Chooses active backend for the session

- `browser/harness_adapter.py`
  Formats calls, captures outputs, and normalizes harness results

- `browser/harness_state.py`
  Stores attach state, selected tabs, harness session metadata, and skill references

- `browser/harness_sync.py`
  Reads useful domain-skill metadata and makes it available to the planner

- `docs/browser-harness-roadmap.md`
  This roadmap and implementation contract

The current [browser/state.py](/home/kedar/Desktop/Projects/use_browser/browser/state.py:1) should stop owning the browser implementation details directly.
It should either become a façade over the selected backend or be split into session state plus backend runtime state.

## Phase-by-Phase Plan

## Phase 0: Design Lock

Before code changes, lock these decisions:

- `browser-harness` is the only adaptive real-browser integration target
- the integration is optional and backend-based
- the MCP surface should remain mostly stable
- assertions and reporting stay in Easy Sanity
- the harness repo remains an external dependency, not vendored core logic

Deliverables:

- this roadmap
- updated product roadmap entry
- updated feature documentation

## Phase 1: Backend Abstraction

Refactor the current browser runtime so tools no longer depend directly on Playwright objects.

Required work:

- define a backend interface for lifecycle, navigation, interaction, extraction, screenshot, and wait operations
- move current Playwright logic behind `PlaywrightBackend`
- make `BrowserState` backend-aware instead of browser-implementation-aware
- keep existing tool behavior unchanged

Primary files likely affected:

- [browser/state.py](/home/kedar/Desktop/Projects/use_browser/browser/state.py:1)
- [browser/tools.py](/home/kedar/Desktop/Projects/use_browser/browser/tools.py:1)
- [easy_sanity/server.py](/home/kedar/Desktop/Projects/use_browser/easy_sanity/server.py:1)

Success criteria:

- all current browser tools still work
- tests and documentation still describe the same user-visible behavior
- backend selection can be introduced without a large second refactor

## Phase 2: `browser-harness` Dependency and Environment Setup

Introduce runtime support for the external harness.

Required work:

- add config for harness enablement and command location
- detect whether `browser-harness` is installed and available on `PATH`
- add optional environment values such as:
  - `BROWSER_BACKEND_DEFAULT`
  - `BROWSER_HARNESS_COMMAND`
  - `BROWSER_HARNESS_REPO`
  - `BROWSER_HARNESS_ENABLED`
- document local setup expectations clearly

Recommended environment model:

- default backend remains `playwright`
- `browser-harness` must be explicitly selected or enabled
- setup errors should be explicit and actionable

Success criteria:

- Easy Sanity can validate whether harness mode is available before a run starts
- failure messages point the user to harness installation and Chrome attach steps

## Phase 3: Minimal Harness Backend

Build the first version of a backend that delegates actions to `browser-harness`.

Scope of the first backend:

- start or attach session metadata
- open or activate tab
- navigate to URL
- fetch page info
- take screenshot or equivalent evidence
- click
- type/fill
- wait
- extract visible text

Important constraint:

The first version should stay narrow.
Do not try to support every current MCP tool immediately.

Approach:

- use a stable adapter layer to invoke `browser-harness`
- normalize outputs into Easy Sanity-shaped payloads
- map harness failures into structured tool errors

Success criteria:

- a small but real subset of existing Easy Sanity flows can run on harness mode
- action history still records each step
- a user can run a visible real-browser workflow through the MCP tools

## Phase 4: Session Routing and Tool Compatibility

Once the minimal harness backend works, make the existing MCP tools backend-aware.

Required work:

- add backend selection to `browser_start`
- optionally add explicit tools like:
  - `browser_start(task, backend="playwright"|"browser-harness")`
  - `browser_attach_real_browser(task)`
- route shared tools through the selected backend
- clearly mark unsupported operations when a backend cannot perform them yet

Compatibility strategy:

- preserve current tool names
- add backend-specific behavior only where needed
- avoid creating a second public tool namespace unless absolutely necessary

Success criteria:

- the user can choose Playwright or harness mode intentionally
- tool responses clearly indicate the active backend
- unsupported features degrade cleanly instead of failing opaquely

## Phase 5: State, Evidence, and Report Normalization

Harness mode must still feel like Easy Sanity, not like a raw shell-out.

Required work:

- normalize page info and visible state into the same reporting shape used today
- continue capturing:
  - URL
  - title
  - screenshots
  - semantic summaries where possible
  - action timestamps
  - final result summary
- adapt domain summary extraction so it works with the active page in harness mode

This is where the current logic in [browser/domain.py](/home/kedar/Desktop/Projects/use_browser/browser/domain.py:1) matters.
The semantic summaries should remain part of the product even when browser control is delegated elsewhere.

Success criteria:

- reports from Playwright and harness mode are comparable
- assertions and evidence work across both modes
- users do not lose observability by choosing the adaptive backend

## Phase 6: Assertion Safety and Recovery Layer

This is the most important product layer above the harness.

Required work:

- keep existing assertion tools backend-agnostic
- add recovery behavior for common harness-mode issues
- classify failures into categories such as:
  - browser attach failure
  - page interaction failure
  - blocked by dialog or cookie banner
  - login or auth gating
  - state verification failure

Add safety policies for real-browser mode:

- file upload requires explicit local path handling
- destructive actions should require stronger intent
- external-site side effects should be logged clearly
- auth/session reuse should be visible in reports

Success criteria:

- adaptive browser control still produces trustworthy pass/fail outcomes
- the user can distinguish a flaky browser failure from an application failure

## Phase 7: Skill Awareness and Controlled Learning

This is where the integration starts using `browser-harness` the way it was designed to be used.

Required work:

- read harness domain-skill locations and metadata
- surface which domain skills were relevant during a run
- record whether a run succeeded because of an existing domain skill
- optionally add a memory note into Easy Sanity when a new domain pattern proves useful

Important boundary:

Easy Sanity should be aware of learned harness behavior, but it should not silently mutate core product expectations around testing outcomes.

Success criteria:

- harness learnings become inspectable
- domain-specific behavior is no longer invisible magic
- repeated runs on the same surface get better without sacrificing traceability

## Phase 8: Task-System Integration

The task system should be able to request harness mode explicitly.

Required work:

- extend saved tasks and structured tasks with backend preference
- allow templates to declare:
  - `playwright`
  - `browser-harness`
  - `auto`
- update linting to warn when a task clearly needs a real browser session
- update sample tasks and docs with examples for adaptive runs

Primary files likely affected:

- [tasks/tools.py](/home/kedar/Desktop/Projects/use_browser/tasks/tools.py:1)
- [docs/agent-documentation.md](/home/kedar/Desktop/Projects/use_browser/docs/agent-documentation.md:1)

Success criteria:

- a reusable task can intentionally target harness mode
- backend selection becomes part of the task contract, not an ad hoc prompt detail

## Phase 9: Setup and Onboarding

The user experience must be practical.

Required work:

- add install docs for `browser-harness`
- explain when to use Playwright mode versus harness mode
- explain Chrome attach prerequisites
- add troubleshooting for:
  - missing harness binary
  - Chrome not running
  - remote debugging not enabled
  - stale websocket or daemon attach failures

This phase should explicitly align with the upstream harness setup flow documented in `install.md` and `SKILL.md`.

Success criteria:

- a new user can enable harness mode without reading upstream docs first
- the product docs make backend choice understandable

## Phase 10: Validation Matrix

Before calling the integration complete, validate it across representative workflows.

Suggested validation set:

- login flow on a local app
- dashboard smoke test
- file upload flow
- iframe-heavy flow
- cross-origin navigation flow
- download verification flow
- cookie banner recovery case
- one domain-skill-assisted run

Measure:

- pass/fail correctness
- step trace quality
- screenshot/report quality
- backend-specific failure clarity
- setup friction

Success criteria:

- harness mode is useful on tasks where Playwright mode is rigid or brittle
- Playwright mode remains the default for simpler deterministic runs

## Proposed MCP Changes

These should be incremental, not all at once.

Likely additions:

- `browser_start(task, headless=None, backend="playwright")`
- `browser_get_backend()`
- `browser_list_backends()`
- `browser_attach_real_browser(task)`

Likely unchanged but internally routed:

- `browser_navigate`
- `browser_click`
- `browser_fill`
- `browser_wait_for_text`
- `browser_get_state`
- `browser_stop`

Potential later additions:

- `browser_recover(goal)`
- `browser_act(goal, success_criteria="")`

## Risks

### Risk 1: Backend divergence

Playwright mode and harness mode may return different quality or shapes of state.

Mitigation:

- normalize responses through a shared adapter contract
- keep reports backend-agnostic

### Risk 2: Real-browser unpredictability

Harness mode depends on a live Chrome session, user profile state, and attach timing.

Mitigation:

- explicit setup checks
- clearer failure classes
- recovery rules

### Risk 3: Hidden learned behavior

Harness-generated helpers and skills can become opaque over time.

Mitigation:

- surface skill usage in action history and reports
- keep test outcomes tied to explicit assertions

### Risk 4: Product confusion

Users may not understand when to choose which backend.

Mitigation:

- document selection rules
- default to Playwright
- recommend harness mode only for real-browser or fluid interaction cases

## Recommended Near-Term Execution Order

This is the order we should implement in:

1. backend abstraction
2. harness dependency/config detection
3. minimal harness backend
4. backend-aware `browser_start`
5. report/state normalization
6. task-system support
7. setup docs and troubleshooting
8. validation matrix

## Definition Of Done

This feature should only be considered complete when:

- the user can choose `browser-harness` mode intentionally
- core Easy Sanity browser tools work through that mode
- assertions, evidence, and reports still function
- setup errors are clear
- task definitions can declare backend preference
- documentation explains the tradeoffs cleanly
- the integration is validated on real browser workflows that benefit from CDP flexibility
