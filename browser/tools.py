import asyncio
import base64
import json
from typing import Literal, Optional

from browser.domain import (
    capture_domain_summary,
    domain_snapshot_signature,
    infer_route_context,
    summarize_domain_changes,
    summarize_domain_summary,
)
from mcp.server.fastmcp import FastMCP

from browser.report_manager import (
    ensure_directory,
    iso_timestamp,
    render_markdown_report,
    screenshot_filename,
)
from browser.state import BrowserState
from config.settings import browser_headless_default
from prompts import FIND_ELEMENT_RESULT_MESSAGE, FILL_FIELD_NOT_FOUND_TEMPLATE


def _browser_not_started_error() -> str:
    return json.dumps({"status": "error", "message": "Browser not started"}, indent=2)


def _sanitize_recorded_details(action: str, details: dict) -> dict:
    sanitized = {}
    for key, value in details.items():
        key_lower = str(key).lower()
        value_str = str(value)

        if any(marker in key_lower for marker in ("password", "secret", "token", "api_key", "apikey")):
            sanitized[key] = "***MASKED***"
            continue

        if key_lower == "text":
            field_hint = str(details.get("field", "")) + " " + str(details.get("selector", ""))
            if "password" in field_hint.lower():
                sanitized[key] = "***MASKED***"
                continue

        sanitized[key] = value_str

    return sanitized


async def _record_action(browser_state: BrowserState, action: str, status: str = "success", **details) -> dict:
    browser_state.step_counter += 1
    screenshot_path = None
    current_url = ""
    current_title = ""
    domain_summary = None
    change_summary = []

    if browser_state.page:
        current_url = browser_state.page.url
        try:
            current_title = await browser_state.page.title()
        except Exception:
            current_title = ""

        try:
            domain_summary = await capture_domain_summary(browser_state.page)
            change_summary = summarize_domain_changes(browser_state.last_domain_summary, domain_summary)
            browser_state.last_domain_summary = domain_summary
        except Exception:
            domain_summary = None
            change_summary = []

        if browser_state.screenshots_root:
            ensure_directory(browser_state.screenshots_root)
            screenshot_path = browser_state.screenshots_root / screenshot_filename(
                browser_state.step_counter, action, status
            )
            await browser_state.page.screenshot(path=str(screenshot_path), type="png", full_page=False)

    entry = {
        "step": browser_state.step_counter,
        "action": action,
        "status": status,
        "timestamp": iso_timestamp(),
        "url": current_url,
        "title": current_title,
        "details": _sanitize_recorded_details(action, details),
        "screenshot_path": str(screenshot_path) if screenshot_path else None,
        "domain_summary_text": summarize_domain_summary(domain_summary) if domain_summary else "",
        "route_context": infer_route_context(domain_summary) if domain_summary else {},
        "change_summary": change_summary,
    }
    browser_state.action_history.append(entry)
    return entry


def _assertion_success(assertion: str, message: str, **details) -> str:
    payload = {
        "status": "success",
        "assertion": assertion,
        "passed": True,
        "message": message,
    }
    payload.update(details)
    return json.dumps(payload, indent=2)


def _assertion_failure(assertion: str, message: str, **details) -> str:
    payload = {
        "status": "error",
        "assertion": assertion,
        "passed": False,
        "message": message,
    }
    payload.update(details)
    return json.dumps(payload, indent=2)


def _success_payload(**payload) -> str:
    payload.setdefault("status", "success")
    return json.dumps(payload, indent=2)


async def _resolve_field_locator(browser_state: BrowserState, field: str):
    """
    Resolve a human-friendly field description to a Playwright locator.

    Tries accessibility-first strategies before falling back to common attributes.
    """
    page = browser_state.page
    if page is None:
        return None

    strategies = [
        ("label", page.get_by_label(field, exact=False).first),
        ("placeholder", page.get_by_placeholder(field, exact=False).first),
        ("text", page.get_by_text(field, exact=False).first),
        ("name", page.locator(f'[name="{field}"]').first),
        ("id", page.locator(f'#{field}').first),
        ("data-testid", page.locator(f'[data-testid="{field}"]').first),
    ]

    lowered = field.lower()
    if lowered != field:
        strategies.extend(
            [
                (
                    "name_ci",
                    page.locator(
                        f'input[name="{lowered}"], textarea[name="{lowered}"], select[name="{lowered}"]'
                    ).first,
                ),
                ("id_ci", page.locator(f'#{lowered}').first),
                ("placeholder_ci", page.get_by_placeholder(lowered, exact=False).first),
            ]
        )

    for strategy_name, locator in strategies:
        if await locator.count() > 0:
            return strategy_name, locator

    fallback = page.locator(
        f'input[aria-label*="{field}" i], textarea[aria-label*="{field}" i], '
        f'select[aria-label*="{field}" i], input[placeholder*="{field}" i], '
        f'textarea[placeholder*="{field}" i]'
    ).first
    if await fallback.count() > 0:
        return "attribute_contains", fallback

    return None


async def _resolve_clickable_by_label(browser_state: BrowserState, name: str):
    page = browser_state.page
    if page is None:
        return None

    strategies = [
        ("label", page.get_by_label(name, exact=False).first),
        ("text", page.get_by_text(name, exact=False).first),
        ("button", page.get_by_role("button", name=name, exact=False).first),
        ("link", page.get_by_role("link", name=name, exact=False).first),
    ]
    for strategy_name, locator in strategies:
        if await locator.count() > 0:
            return strategy_name, locator
    return None


def register_browser_tools(mcp: FastMCP, browser_state: BrowserState) -> None:
    @mcp.tool()
    async def assert_url_contains(expected_text: str) -> str:
        """
        Assert that the current page URL contains the expected text.

        Args:
            expected_text: Text that should appear in the current URL.

        Returns:
            Assertion result with pass/fail details.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            current_url = browser_state.page.url
            passed = expected_text in current_url
            await _record_action(
                browser_state,
                "assert_url_contains",
                "passed" if passed else "failed",
                expected_text=expected_text,
                passed=passed,
            )
            if passed:
                return _assertion_success(
                    "assert_url_contains",
                    f"URL contains '{expected_text}'",
                    current_url=current_url,
                    expected_text=expected_text,
                )
            return _assertion_failure(
                "assert_url_contains",
                f"URL does not contain '{expected_text}'",
                current_url=current_url,
                expected_text=expected_text,
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def assert_text_visible(text: str) -> str:
        """
        Assert that visible page text contains the expected string.

        Args:
            text: Text that should be visible on the page.

        Returns:
            Assertion result with pass/fail details.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            locator = browser_state.page.get_by_text(text, exact=False).first
            passed = await locator.count() > 0 and await locator.is_visible()
            await _record_action(
                browser_state,
                "assert_text_visible",
                "passed" if passed else "failed",
                text=text,
                passed=passed,
            )
            if passed:
                return _assertion_success(
                    "assert_text_visible",
                    f"Visible text found for '{text}'",
                    text=text,
                )
            return _assertion_failure(
                "assert_text_visible",
                f"Visible text not found for '{text}'",
                text=text,
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def assert_text_not_visible(text: str) -> str:
        """
        Assert that visible page text does not contain the specified string.

        Args:
            text: Text that should not be visible on the page.

        Returns:
            Assertion result with pass/fail details.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            locator = browser_state.page.get_by_text(text, exact=False).first
            visible = await locator.count() > 0 and await locator.is_visible()
            passed = not visible
            await _record_action(
                browser_state,
                "assert_text_not_visible",
                "passed" if passed else "failed",
                text=text,
                passed=passed,
            )
            if passed:
                return _assertion_success(
                    "assert_text_not_visible",
                    f"Text '{text}' is not visible",
                    text=text,
                )
            return _assertion_failure(
                "assert_text_not_visible",
                f"Text '{text}' is visible",
                text=text,
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def assert_element_exists(selector: str) -> str:
        """
        Assert that at least one element exists for a CSS selector.

        Args:
            selector: CSS selector to check.

        Returns:
            Assertion result with pass/fail details.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            count = await browser_state.page.locator(selector).count()
            passed = count > 0
            await _record_action(
                browser_state,
                "assert_element_exists",
                "passed" if passed else "failed",
                selector=selector,
                passed=passed,
                count=count,
            )
            if passed:
                return _assertion_success(
                    "assert_element_exists",
                    f"Element exists for selector '{selector}'",
                    selector=selector,
                    count=count,
                )
            return _assertion_failure(
                "assert_element_exists",
                f"No element found for selector '{selector}'",
                selector=selector,
                count=count,
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def assert_element_enabled(selector: str) -> str:
        """
        Assert that a selected element exists and is enabled.

        Args:
            selector: CSS selector of the target element.

        Returns:
            Assertion result with pass/fail details.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            locator = browser_state.page.locator(selector).first
            count = await locator.count()
            if count == 0:
                await _record_action(
                    browser_state,
                    "assert_element_enabled",
                    "failed",
                    selector=selector,
                    passed=False,
                    reason="missing",
                )
                return _assertion_failure(
                    "assert_element_enabled",
                    f"No element found for selector '{selector}'",
                    selector=selector,
                )

            enabled = await locator.is_enabled()
            await _record_action(
                browser_state,
                "assert_element_enabled",
                "passed" if enabled else "failed",
                selector=selector,
                passed=enabled,
            )
            if enabled:
                return _assertion_success(
                    "assert_element_enabled",
                    f"Element '{selector}' is enabled",
                    selector=selector,
                )
            return _assertion_failure(
                "assert_element_enabled",
                f"Element '{selector}' is disabled",
                selector=selector,
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def assert_page_title(expected_text: str) -> str:
        """
        Assert that the page title contains the expected text.

        Args:
            expected_text: Text that should appear in the page title.

        Returns:
            Assertion result with pass/fail details.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            title = await browser_state.page.title()
            passed = expected_text in title
            await _record_action(
                browser_state,
                "assert_page_title",
                "passed" if passed else "failed",
                expected_text=expected_text,
                passed=passed,
            )
            if passed:
                return _assertion_success(
                    "assert_page_title",
                    f"Page title contains '{expected_text}'",
                    title=title,
                    expected_text=expected_text,
                )
            return _assertion_failure(
                "assert_page_title",
                f"Page title does not contain '{expected_text}'",
                title=title,
                expected_text=expected_text,
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def assert_count(selector: str, expected: int) -> str:
        """
        Assert that a CSS selector matches exactly the expected number of elements.

        Args:
            selector: CSS selector to count.
            expected: Exact expected match count.

        Returns:
            Assertion result with pass/fail details.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            actual = await browser_state.page.locator(selector).count()
            passed = actual == expected
            await _record_action(
                browser_state,
                "assert_count",
                "passed" if passed else "failed",
                selector=selector,
                expected=expected,
                actual=actual,
                passed=passed,
            )
            if passed:
                return _assertion_success(
                    "assert_count",
                    f"Selector '{selector}' matched expected count {expected}",
                    selector=selector,
                    expected=expected,
                    actual=actual,
                )
            return _assertion_failure(
                "assert_count",
                f"Selector '{selector}' matched {actual} elements instead of {expected}",
                selector=selector,
                expected=expected,
                actual=actual,
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_start(task: str, headless: Optional[bool] = None) -> str:
        """
        Start a new browser session.

        Args:
            task: Description of what you want to accomplish.
            headless: Run without showing the browser window. If omitted, uses config default.

        Returns:
            Confirmation with session info.
        """
        try:
            resolved_headless = browser_headless_default() if headless is None else headless
            await browser_state.initialize(headless=resolved_headless)
            browser_state.task_description = task
            browser_state.action_history = []
            browser_state.begin_session(task)
            await _record_action(
                browser_state,
                "browser_start",
                "success",
                task=task,
                headless=resolved_headless,
            )

            return json.dumps(
                {
                    "status": "success",
                    "message": "Browser started",
                    "task": task,
                    "headless": resolved_headless,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_get_state() -> str:
        """
        Get the current page state: URL, title, visible text, interactive elements, semantic summary, and screenshot.

        Returns:
            JSON with page state including screenshot_base64 (PNG).
        """
        if not browser_state.page:
            return json.dumps(
                {
                    "status": "error",
                    "message": "Browser not started. Call browser_start first.",
                },
                indent=2,
            )

        try:
            url = browser_state.page.url
            title = await browser_state.page.title()

            visible_text = await browser_state.page.evaluate(
                """
                () => {
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT, null
                    );
                    let text = '';
                    let node;
                    while (node = walker.nextNode()) {
                        const trimmed = node.textContent.trim();
                        if (trimmed) text += trimmed + ' ';
                    }
                    return text.substring(0, 3000);
                }
                """
            )

            elements = await browser_state.page.evaluate(
                """
                () => {
                    const clickable = Array.from(document.querySelectorAll('a, button, input, select, textarea'));
                    return clickable.slice(0, 50).map((el, idx) => ({
                        index: idx,
                        tag: el.tagName.toLowerCase(),
                        type: el.type || '',
                        text: el.innerText?.substring(0, 50) || '',
                        placeholder: el.placeholder || '',
                        id: el.id || '',
                        href: el.href || ''
                    }));
                }
                """
            )

            domain_summary = await capture_domain_summary(browser_state.page)
            route_context = infer_route_context(domain_summary)
            change_summary = summarize_domain_changes(browser_state.last_domain_summary, domain_summary)
            browser_state.last_domain_summary = domain_summary

            screenshot_bytes = await browser_state.page.screenshot(type="png", full_page=False)
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode()

            return json.dumps(
                {
                    "status": "success",
                    "url": url,
                    "title": title,
                    "visible_text": visible_text,
                    "interactive_elements": elements[:20],
                    "semantic_summary": domain_summary,
                    "semantic_summary_text": summarize_domain_summary(domain_summary),
                    "route_context": route_context,
                    "change_summary": change_summary,
                    "screenshot_base64": screenshot_b64,
                    "action_count": len(browser_state.action_history),
                    "task": browser_state.task_description,
                },
                indent=2,
            )

        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_get_accessibility_tree() -> str:
        """
        Return an accessibility-oriented snapshot of interactive page elements.

        Returns:
            A simplified accessibility tree with roles, accessible names, labels, and disabled state.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            tree = await browser_state.page.evaluate(
                """
                () => {
                    function safeText(value, limit = 120) {
                        return (value || '').replace(/\\s+/g, ' ').trim().slice(0, limit);
                    }

                    function labelText(el) {
                        if (el.labels && el.labels.length) {
                            return Array.from(el.labels)
                                .map((label) => safeText(label.innerText || label.textContent || '', 80))
                                .filter(Boolean)
                                .join(' ');
                        }
                        if (el.id) {
                            const label = document.querySelector(`label[for="${el.id}"]`);
                            if (label) {
                                return safeText(label.innerText || label.textContent || '', 80);
                            }
                        }
                        return '';
                    }

                    const selectors = 'a, button, input, select, textarea, [role], summary';
                    return Array.from(document.querySelectorAll(selectors)).slice(0, 120).map((el, index) => ({
                        index,
                        tag: el.tagName.toLowerCase(),
                        role: el.getAttribute('role') || '',
                        name: safeText(
                            el.getAttribute('aria-label') ||
                            el.innerText ||
                            el.textContent ||
                            el.getAttribute('value') ||
                            '',
                            120
                        ),
                        label: labelText(el),
                        placeholder: safeText(el.getAttribute('placeholder') || '', 80),
                        type: el.getAttribute('type') || '',
                        disabled: !!el.disabled || el.getAttribute('aria-disabled') === 'true',
                        id: el.id || '',
                        name_attr: el.getAttribute('name') || '',
                    })).filter((item) => item.name || item.label || item.role || item.placeholder);
                }
                """
            )
            await _record_action(browser_state, "get_accessibility_tree", "success", nodes=len(tree))
            return _success_payload(nodes=tree, node_count=len(tree))
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_list_links() -> str:
        """
        List visible links on the current page.

        Returns:
            Link text, href, and a small accessibility-friendly summary.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            links = await browser_state.page.evaluate(
                """
                () => Array.from(document.querySelectorAll('a[href]')).slice(0, 120).map((el, index) => ({
                    index,
                    text: (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 120),
                    href: el.href || '',
                    title: el.getAttribute('title') || '',
                    aria_label: el.getAttribute('aria-label') || '',
                })).filter((item) => item.text || item.href)
                """
            )
            await _record_action(browser_state, "list_links", "success", links=len(links))
            return _success_payload(links=links, link_count=len(links))
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_list_network_errors() -> str:
        """
        List failed network requests and error-level console messages captured in this session.

        Returns:
            Runtime network and console failures useful for sanity-test debugging.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            console_errors = [entry for entry in browser_state.console_logs if entry.get("type") == "error"]
            await _record_action(
                browser_state,
                "list_network_errors",
                "success",
                failed_requests=len(browser_state.failed_requests),
                console_errors=len(console_errors),
            )
            return _success_payload(
                failed_requests=browser_state.failed_requests,
                console_errors=console_errors,
                failure_count=len(browser_state.failed_requests) + len(console_errors),
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_get_console_logs(level: str = "") -> str:
        """
        Return captured console logs for the current browser session.

        Args:
            level: Optional filter such as "error", "warning", or "log".

        Returns:
            Session console messages, optionally filtered by type.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            logs = browser_state.console_logs
            if level:
                logs = [entry for entry in logs if entry.get("type") == level]
            await _record_action(browser_state, "get_console_logs", "success", level=level or "all", count=len(logs))
            return _success_payload(logs=logs, count=len(logs), level=level or "all")
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_get_requests(limit: int = 100) -> str:
        """
        Return recent network request activity for the current session.

        Args:
            limit: Maximum number of request events to return.

        Returns:
            Recent request and response events captured by the browser session.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            requests = browser_state.network_requests[-max(limit, 1) :]
            await _record_action(browser_state, "get_requests", "success", count=len(requests), limit=limit)
            return _success_payload(requests=requests, count=len(requests))
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_get_storage() -> str:
        """
        Inspect cookies, localStorage, and sessionStorage for the current page.

        Returns:
            Browser storage useful for auth and session debugging.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            cookies = await browser_state.page.context.cookies()
            storage = await browser_state.page.evaluate(
                """
                () => ({
                    local_storage: Object.fromEntries(
                        Array.from({ length: window.localStorage.length }, (_, i) => {
                            const key = window.localStorage.key(i);
                            return [key, window.localStorage.getItem(key)];
                        })
                    ),
                    session_storage: Object.fromEntries(
                        Array.from({ length: window.sessionStorage.length }, (_, i) => {
                            const key = window.sessionStorage.key(i);
                            return [key, window.sessionStorage.getItem(key)];
                        })
                    ),
                })
                """
            )
            await _record_action(
                browser_state,
                "get_storage",
                "success",
                cookies=len(cookies),
                local_storage_keys=len(storage.get("local_storage", {})),
                session_storage_keys=len(storage.get("session_storage", {})),
            )
            return _success_payload(cookies=cookies, **storage)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_navigate(url: str) -> str:
        """
        Navigate to a URL.

        Args:
            url: Full URL including http:// or https://.

        Returns:
            Confirmation with new page title and URL.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            await browser_state.page.goto(url, wait_until="networkidle")
            title = await browser_state.page.title()

            await _record_action(browser_state, "navigate", "success", target_url=url)

            return json.dumps(
                {
                    "status": "success",
                    "message": f"Navigated to {url}",
                    "title": title,
                    "url": browser_state.page.url,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_find_element(description: str, limit: int = 5) -> str:
        """
        Find likely interactive elements that match a natural-language description.

        Args:
            description: Human description such as "email field", "login button", or "search input".
            limit: Max number of matches to return (default: 5).

        Returns:
            Ranked candidate elements with suggested selector hints.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            candidates = await browser_state.page.evaluate(
                """
                ({ description, limit }) => {
                    const normalizedDescription = description.toLowerCase().trim();
                    const tokens = normalizedDescription.split(/\\s+/).filter(Boolean);
                    const selectors = 'a, button, input, select, textarea, [role], [aria-label], label';
                    const elements = Array.from(document.querySelectorAll(selectors));

                    function getLabelText(el) {
                        if (el.labels && el.labels.length) {
                            return Array.from(el.labels)
                                .map((label) => label.innerText || label.textContent || '')
                                .join(' ')
                                .trim();
                        }
                        if (el.id) {
                            const label = document.querySelector(`label[for="${el.id}"]`);
                            if (label) {
                                return (label.innerText || label.textContent || '').trim();
                            }
                        }
                        return '';
                    }

                    function getAssociatedControl(el) {
                        if (el.tagName.toLowerCase() === 'label') {
                            if (el.control) {
                                return el.control;
                            }
                            const forId = el.getAttribute('for');
                            if (forId) {
                                return document.getElementById(forId);
                            }
                        }
                        return null;
                    }

                    function buildCandidate(el, index) {
                        const associatedControl = getAssociatedControl(el);
                        const targetEl = associatedControl || el;
                        const targetTag = targetEl.tagName.toLowerCase();
                        const targetType = targetEl.getAttribute('type') || '';
                        const isLabelOnly = el.tagName.toLowerCase() === 'label' && !!associatedControl;
                        const text = (el.innerText || el.textContent || '').trim();
                        const placeholder = targetEl.getAttribute('placeholder') || '';
                        const ariaLabel = targetEl.getAttribute('aria-label') || '';
                        const name = targetEl.getAttribute('name') || '';
                        const id = targetEl.id || '';
                        const role = targetEl.getAttribute('role') || '';
                        const type = targetType;
                        const label = associatedControl ? text : getLabelText(el);
                        const haystack = [
                            text,
                            placeholder,
                            ariaLabel,
                            name,
                            id,
                            role,
                            type,
                            label,
                            targetTag,
                        ].join(' ').toLowerCase();

                        let score = 0;
                        if (haystack.includes(normalizedDescription)) {
                            score += 8;
                        }
                        for (const token of tokens) {
                            if (haystack.includes(token)) {
                                score += 2;
                            }
                        }
                        if (text.toLowerCase() === normalizedDescription) {
                            score += 4;
                        }
                        if (label.toLowerCase().includes(normalizedDescription)) {
                            score += 4;
                        }
                        if ((ariaLabel || placeholder).toLowerCase().includes(normalizedDescription)) {
                            score += 3;
                        }
                        if (['input', 'textarea', 'select', 'button', 'a'].includes(targetTag)) {
                            score += 3;
                        }
                        if (isLabelOnly) {
                            score -= 4;
                        }
                        if (associatedControl && label.toLowerCase().includes(normalizedDescription)) {
                            score += 5;
                        }

                        return {
                            index,
                            score,
                            tag: targetTag,
                            role,
                            type,
                            text: (associatedControl ? (targetEl.innerText || targetEl.textContent || '') : text).substring(0, 120),
                            label: label.substring(0, 120),
                            placeholder: placeholder.substring(0, 120),
                            aria_label: ariaLabel.substring(0, 120),
                            name,
                            id,
                            matched_via_label: !!associatedControl,
                        };
                    }

                    return elements
                        .map(buildCandidate)
                        .filter((item) => item.score > 0)
                        .sort((a, b) => b.score - a.score)
                        .slice(0, limit);
                }
                """,
                {"description": description, "limit": limit},
            )

            await _record_action(
                browser_state,
                "find_element",
                "success",
                description=description,
                matches=len(candidates),
            )

            return json.dumps(
                {
                    "status": "success",
                    "description": description,
                    "matches": candidates,
                    "message": FIND_ELEMENT_RESULT_MESSAGE,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_click_by_role(role: str, name: str, exact: bool = False) -> str:
        """
        Click an element using accessible role and name.

        Args:
            role: Accessible role such as "button", "link", or "textbox".
            name: Visible or accessible name of the element.
            exact: Whether the name match must be exact.

        Returns:
            Confirmation and current URL.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            locator = browser_state.page.get_by_role(role, name=name, exact=exact).first
            await locator.click()
            await asyncio.sleep(1)

            await _record_action(
                browser_state,
                "click_by_role",
                "success",
                role=role,
                name=name,
                exact=exact,
            )

            return json.dumps(
                {
                    "status": "success",
                    "message": f"Clicked {role} named '{name}'",
                    "url": browser_state.page.url,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_click_by_label(name: str) -> str:
        """
        Click an element using a human-readable label, visible text, or accessible name.

        Args:
            name: Label or visible name of the target element.

        Returns:
            Confirmation of the click and the matched strategy.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            resolved = await _resolve_clickable_by_label(browser_state, name)
            if not resolved:
                return json.dumps(
                    {"status": "error", "message": f"Could not find a clickable element for label '{name}'."},
                    indent=2,
                )

            strategy_name, locator = resolved
            await locator.click()
            await asyncio.sleep(1)

            await _record_action(
                browser_state,
                "click_by_label",
                "success",
                name=name,
                strategy=strategy_name,
            )
            return _success_payload(
                message=f"Clicked element for label '{name}'",
                name=name,
                matched_by=strategy_name,
                url=browser_state.page.url,
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_fill(field: str, text: str, press_enter: bool = False) -> str:
        """
        Fill an input using a human-friendly field description.

        Args:
            field: Label, placeholder, name, or identifier for the input.
            text: Value to type into the field.
            press_enter: Press Enter after filling the field.

        Returns:
            Confirmation of which matching strategy was used.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            resolved = await _resolve_field_locator(browser_state, field)
            if not resolved:
                return json.dumps(
                    {
                        "status": "error",
                        "message": FILL_FIELD_NOT_FOUND_TEMPLATE.format(field=field),
                    },
                    indent=2,
                )

            strategy_name, locator = resolved
            await locator.click()
            await locator.fill(text)
            if press_enter:
                await locator.press("Enter")
                await asyncio.sleep(1)

            await _record_action(
                browser_state,
                "fill",
                "success",
                field=field,
                strategy=strategy_name,
                text=text,
            )

            return json.dumps(
                {
                    "status": "success",
                    "message": f"Filled field '{field}'",
                    "field": field,
                    "matched_by": strategy_name,
                    "pressed_enter": press_enter,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_select_option(label: str, value: str) -> str:
        """
        Select an option from a select control using a human-friendly label.

        Args:
            label: Label or identifier for the select control.
            value: Option value or visible label to choose.

        Returns:
            Confirmation of which matching strategy was used.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            resolved = await _resolve_field_locator(browser_state, label)
            if not resolved:
                return json.dumps(
                    {"status": "error", "message": FILL_FIELD_NOT_FOUND_TEMPLATE.format(field=label)},
                    indent=2,
                )

            strategy_name, locator = resolved
            try:
                await locator.select_option(value=value)
            except Exception:
                await locator.select_option(label=value)

            await _record_action(
                browser_state,
                "select_option",
                "success",
                label=label,
                value=value,
                strategy=strategy_name,
            )
            return _success_payload(
                message=f"Selected '{value}' for '{label}'",
                label=label,
                value=value,
                matched_by=strategy_name,
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_press_key(key: str) -> str:
        """
        Press a keyboard key on the current page.

        Args:
            key: Playwright key name such as Enter, Escape, Tab, ArrowDown, or Control+A.

        Returns:
            Confirmation of the key press.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            await browser_state.page.keyboard.press(key)
            await asyncio.sleep(0.2)
            await _record_action(browser_state, "press_key", "success", key=key)
            return _success_payload(message=f"Pressed key '{key}'", key=key)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_hover(selector: str) -> str:
        """
        Hover over a page element.

        Args:
            selector: CSS selector of the target element.

        Returns:
            Confirmation of the hover action.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            await browser_state.page.hover(selector)
            await asyncio.sleep(0.2)
            await _record_action(browser_state, "hover", "success", selector=selector)
            return _success_payload(message=f"Hovered over {selector}", selector=selector)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_click(
        selector: Optional[str] = None,
        text: Optional[str] = None,
        element_index: Optional[int] = None,
    ) -> str:
        """
        Click an element on the page.

        Provide one of: selector (CSS), text (visible label), or element_index (from browser_get_state).

        Args:
            selector: CSS selector, e.g. "#submit-btn" or "button.primary".
            text: Visible text of the element, e.g. "Login" or "Submit".
            element_index: Index from interactive_elements in browser_get_state.

        Returns:
            Confirmation and updated URL.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            if element_index is not None:
                await browser_state.page.evaluate(
                    f"""
                    () => {{
                        const els = Array.from(document.querySelectorAll('a, button, input, select, textarea'));
                        if (els[{element_index}]) els[{element_index}].click();
                    }}
                    """
                )
            elif selector:
                await browser_state.page.click(selector)
            elif text:
                await browser_state.page.click(f"text={text}")
            else:
                return json.dumps(
                    {"status": "error", "message": "Provide selector, text, or element_index"},
                    indent=2,
                )

            await _record_action(
                browser_state,
                "click",
                "success",
                selector=selector or "",
                text=text or "",
                element_index=element_index if element_index is not None else "",
            )
            await asyncio.sleep(1)

            return json.dumps(
                {
                    "status": "success",
                    "message": "Clicked element",
                    "url": browser_state.page.url,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_type(selector: str, text: str, press_enter: bool = False) -> str:
        """
        Type text into an input field.

        Args:
            selector: CSS selector of the input.
            text: Text to type.
            press_enter: Press Enter after typing (default: False).

        Returns:
            Confirmation of the typing action.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            await browser_state.page.click(selector)
            await browser_state.page.type(selector, text, delay=50)

            if press_enter:
                await browser_state.page.press(selector, "Enter")
                await asyncio.sleep(1)

            await _record_action(
                browser_state,
                "type",
                "success",
                selector=selector,
                text=text,
                pressed_enter=press_enter,
            )

            return json.dumps(
                {
                    "status": "success",
                    "message": f"Typed into {selector}",
                    "pressed_enter": press_enter,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_scroll(direction: Literal["down", "up"] = "down", amount: int = 500) -> str:
        """
        Scroll the page.

        Args:
            direction: "down" or "up" (default: "down").
            amount: Pixels to scroll (default: 500).

        Returns:
            Confirmation.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            scroll_amount = amount if direction == "down" else -amount
            await browser_state.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await _record_action(
                browser_state,
                "scroll",
                "success",
                direction=direction,
                amount=amount,
            )
            await asyncio.sleep(0.5)

            return json.dumps(
                {"status": "success", "message": f"Scrolled {direction} {amount}px"},
                indent=2,
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_extract(selector: str) -> str:
        """
        Extract text content from a page element.

        Args:
            selector: CSS selector of the element.

        Returns:
            The extracted text, or an error if not found.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            element = await browser_state.page.query_selector(selector)
            if element:
                text = await element.inner_text()
                await _record_action(
                    browser_state,
                    "extract",
                    "success",
                    selector=selector,
                )
                return json.dumps({"status": "success", "extracted_text": text}, indent=2)
            return json.dumps({"status": "error", "message": f"Element not found: {selector}"}, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_get_dom_summary() -> str:
        """
        Return a semantic summary of the current page: forms, tables, cards, navs, dialogs, alerts, and route context.

        Returns:
            Structured semantic page understanding for better browser reasoning.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            domain_summary = await capture_domain_summary(browser_state.page)
            route_context = infer_route_context(domain_summary)
            change_summary = summarize_domain_changes(browser_state.last_domain_summary, domain_summary)
            browser_state.last_domain_summary = domain_summary

            await _record_action(
                browser_state,
                "get_dom_summary",
                "success",
                forms=domain_summary.get("counts", {}).get("forms", 0),
                tables=domain_summary.get("counts", {}).get("tables", 0),
                dialogs=domain_summary.get("counts", {}).get("dialogs", 0),
            )

            return json.dumps(
                {
                    "status": "success",
                    "summary_text": summarize_domain_summary(domain_summary),
                    "route_context": route_context,
                    "change_summary": change_summary,
                    "semantic_summary": domain_summary,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_list_forms() -> str:
        """
        List detected forms and their fields using labels and accessibility-oriented metadata.

        Returns:
            Visible forms with field structure and submit actions.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            domain_summary = await capture_domain_summary(browser_state.page)
            browser_state.last_domain_summary = domain_summary
            forms = domain_summary.get("forms", [])

            await _record_action(
                browser_state,
                "list_forms",
                "success",
                forms=len(forms),
                fields=sum(form.get("field_count", 0) for form in forms),
            )

            return json.dumps(
                {
                    "status": "success",
                    "form_count": len(forms),
                    "forms": forms,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_describe_changes() -> str:
        """
        Compare the current page against the last stored semantic snapshot and describe what changed.

        Returns:
            Human-friendly change summary plus the current route/workflow context.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            current_summary = await capture_domain_summary(browser_state.page)
            previous_summary = browser_state.last_domain_summary
            change_summary = summarize_domain_changes(previous_summary, current_summary)
            browser_state.last_domain_summary = current_summary

            await _record_action(
                browser_state,
                "describe_changes",
                "success",
                change_count=len(change_summary),
                signature=domain_snapshot_signature(current_summary),
            )

            return json.dumps(
                {
                    "status": "success",
                    "summary_text": summarize_domain_summary(current_summary),
                    "route_context": infer_route_context(current_summary),
                    "change_summary": change_summary,
                    "workflow_step": current_summary.get("workflow_step"),
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_wait(seconds: int = 2) -> str:
        """
        Wait for a specified number of seconds.

        Useful after clicks that trigger page loads or animations.

        Args:
            seconds: How long to wait (default: 2).

        Returns:
            Confirmation after waiting.
        """
        if not browser_state.page:
            return _browser_not_started_error()

        try:
            await asyncio.sleep(seconds)
            await _record_action(
                browser_state,
                "wait",
                "success",
                seconds=seconds,
            )
            return json.dumps({"status": "success", "message": f"Waited {seconds}s"}, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_stop(final_result: Optional[str] = None) -> str:
        """
        Stop the browser session and clean up.

        Args:
            final_result: Optional summary of what was accomplished.

        Returns:
            Session summary including full action history.
        """
        try:
            history = browser_state.action_history.copy()
            task = browser_state.task_description
            report_path = browser_state.report_path
            screenshots_root = browser_state.screenshots_root
            started_at = browser_state.started_at
            session_slug = browser_state.session_slug
            final_summary = final_result or "Session completed"
            await _record_action(browser_state, "browser_stop", "success", final_result=final_summary)
            history = browser_state.action_history.copy()

            if report_path and screenshots_root:
                markdown = render_markdown_report(
                    task=task,
                    session_slug=session_slug,
                    started_at=started_at,
                    finished_at=iso_timestamp(),
                    final_result=final_summary,
                    actions=history,
                    screenshots_root=screenshots_root,
                    report_path=report_path,
                )
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text(markdown)

            await browser_state.cleanup()

            return json.dumps(
                {
                    "status": "success",
                    "message": "Browser session ended",
                    "task": task,
                    "actions_taken": len(history),
                    "action_history": history,
                    "final_result": final_summary,
                    "report_path": str(report_path) if report_path else None,
                    "screenshots_directory": str(screenshots_root) if screenshots_root else None,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_get_history() -> str:
        """
        Get the action history for the current browser session.

        Returns:
            List of all actions performed so far.
        """
        return json.dumps(
            {
                "status": "success",
                "task": browser_state.task_description,
                "session_slug": browser_state.session_slug,
                "action_count": len(browser_state.action_history),
                "actions": browser_state.action_history,
                "report_path": str(browser_state.report_path) if browser_state.report_path else None,
                "screenshots_directory": (
                    str(browser_state.screenshots_root) if browser_state.screenshots_root else None
                ),
            },
            indent=2,
        )
