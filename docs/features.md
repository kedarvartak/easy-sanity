# Features And Usefulness

This project is a local autonomous sanity testing agent powered by MCP, Playwright, and your IDE's built-in LLM.

Its main value is simple: you can describe a browser-based test in natural language, and the agent can operate a real browser, inspect what happened, and work step by step toward a testing goal.

## What This Agent Is

This agent is:

- a local MCP server
- a browser automation layer for IDE-native LLMs
- a natural-language sanity testing assistant
- a reusable task runner for browser-based workflows

It is especially useful for fast validation of product flows without writing a full Playwright test first.

## Why It Is Useful

### 1. Natural-language testing

You can describe a scenario in plain English instead of writing code.

Examples:

- log into the app and verify the dashboard loads
- create a new session and confirm it appears in the list
- search for a product and return the top results
- open a page and confirm a CTA button is visible

This lowers the barrier to testing for founders, PMs, designers, QA, and engineers.

### 2. Fast sanity coverage

This is useful when you want quick confidence on:

- login still works
- a critical page still loads
- a key form still submits
- the happy path is not visibly broken
- recent UI changes did not break core flows

It fits especially well for smoke tests and pre-release checks.

### 3. Visual reasoning

The agent does not rely only on hardcoded selectors. It can inspect page state and screenshots, then decide what to do next through the IDE LLM.

That makes it helpful for:

- exploratory testing
- UIs that change often
- early-stage products without mature test coverage
- verifying flows where visual context matters

### 4. Local and low-cost

The project runs locally and uses the LLM that already exists in your IDE setup.

Benefits:

- no separate browser automation API cost
- no external hosted browser service required
- more privacy for internal workflows
- easy experimentation

### 5. Reusable sanity tasks

The task system allows browser workflows to be saved and reused.

That means a team can gradually build a library of sanity checks for:

- auth
- onboarding
- search
- dashboards
- admin flows
- regression checks

## Core Features

### MCP-based browser tools

The server exposes browser tools to the IDE LLM so it can:

- start a browser
- navigate to URLs
- inspect current page state
- click elements
- type into inputs
- scroll
- extract text
- wait for UI changes
- stop the session and return a summary

### Screenshot-aware page inspection

The `browser_get_state` tool returns:

- current URL
- page title
- visible text
- interactive elements
- a screenshot encoded for the LLM

This gives the model enough context to choose the next action.

### Persistent saved tasks

The project stores task definitions in `tasks.json` and registers them as MCP prompts.

This enables:

- repeatable natural-language workflows
- slash-command style invocation in supported IDEs
- reusable testing prompts across sessions

### Action history

The browser session tracks actions taken during the run.

This helps with:

- debugging agent behavior
- understanding what happened
- summarizing the final result

## Practical Use Cases

This agent is most useful for:

- smoke testing new builds
- sanity testing staging environments
- validating onboarding or login flows
- checking whether a bug fix works in the UI
- reproducing a user flow from a written description
- creating quick regression checks before writing formal tests
- demo automation for internal workflows

## Who It Helps

### Engineers

Engineers can use it to validate flows quickly before investing in full coded tests.

### QA

QA can use it to run exploratory or repeatable sanity checks from natural-language instructions.

### PMs and founders

Non-engineers can describe what they want verified without needing Playwright syntax.

### Early-stage teams

Teams without a mature test suite can still get meaningful browser-based validation.

## What Makes It Different

Compared with traditional test automation, this project emphasizes:

- natural-language instructions over code-first authoring
- visual reasoning over selector-only control
- lightweight setup over large test infrastructure
- local execution over hosted browser APIs

Compared with generic browser agents, it is better framed as a sanity testing system because the goal is not only to do tasks, but to verify that core product flows still work.

## Current Strengths

The current version is already strong at:

- ad hoc browser automation from English instructions
- simple end-to-end sanity flows
- converting repeated workflows into reusable tasks
- local browser control through Playwright
- leveraging an IDE's existing LLM for reasoning

## Current Limitations

The current version is still early in a few important ways:

- it depends heavily on the quality of the external LLM's reasoning
- it exposes mostly low-level actions
- assertions are not first-class tools yet
- reporting is still lightweight
- task definitions are prompt-based rather than structured test cases
- session handling is simple and single-threaded

These limitations are normal for a prototype, and they point directly to the next set of improvements.

## Long-Term Value

If expanded with assertions, semantic inspection, evidence capture, and reusable suites, this project can become:

- a browser-native smoke testing agent
- a fast regression-checking layer for product teams
- a bridge between exploratory testing and formal automated testing
- a practical way to describe and validate UI workflows in plain English

In that stronger form, the project would not just automate the browser. It would help teams ask, in natural language, "is the product still working?" and get a grounded, evidence-backed answer.
