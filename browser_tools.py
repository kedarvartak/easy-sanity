import asyncio
import base64
import json
from typing import Literal, Optional

from mcp.server.fastmcp import FastMCP

from browser_state import BrowserState
from prompts import FIND_ELEMENT_RESULT_MESSAGE, FILL_FIELD_NOT_FOUND_TEMPLATE


def _browser_not_started_error() -> str:
    return json.dumps({"status": "error", "message": "Browser not started"}, indent=2)


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


def register_browser_tools(mcp: FastMCP, browser_state: BrowserState) -> None:
    @mcp.tool()
    async def browser_start(task: str, headless: bool = False) -> str:
        """
        Start a new browser session.

        Args:
            task: Description of what you want to accomplish.
            headless: Run without showing the browser window (default: False).

        Returns:
            Confirmation with session info.
        """
        try:
            await browser_state.initialize(headless=headless)
            browser_state.task_description = task
            browser_state.action_history = []

            return json.dumps(
                {
                    "status": "success",
                    "message": "Browser started",
                    "task": task,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    @mcp.tool()
    async def browser_get_state() -> str:
        """
        Get the current page state: URL, title, visible text, interactive elements, and screenshot.

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

            screenshot_bytes = await browser_state.page.screenshot(type="png", full_page=False)
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode()

            return json.dumps(
                {
                    "status": "success",
                    "url": url,
                    "title": title,
                    "visible_text": visible_text,
                    "interactive_elements": elements[:20],
                    "screenshot_base64": screenshot_b64,
                    "action_count": len(browser_state.action_history),
                    "task": browser_state.task_description,
                },
                indent=2,
            )

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

            browser_state.action_history.append({"action": "navigate", "url": url})

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

                    function buildCandidate(el, index) {
                        const text = (el.innerText || el.textContent || '').trim();
                        const placeholder = el.getAttribute('placeholder') || '';
                        const ariaLabel = el.getAttribute('aria-label') || '';
                        const name = el.getAttribute('name') || '';
                        const id = el.id || '';
                        const role = el.getAttribute('role') || '';
                        const type = el.getAttribute('type') || '';
                        const label = getLabelText(el);
                        const haystack = [
                            text,
                            placeholder,
                            ariaLabel,
                            name,
                            id,
                            role,
                            type,
                            label,
                            el.tagName.toLowerCase(),
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

                        return {
                            index,
                            score,
                            tag: el.tagName.toLowerCase(),
                            role,
                            type,
                            text: text.substring(0, 120),
                            label: label.substring(0, 120),
                            placeholder: placeholder.substring(0, 120),
                            aria_label: ariaLabel.substring(0, 120),
                            name,
                            id,
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

            browser_state.action_history.append(
                {
                    "action": "find_element",
                    "description": description,
                    "matches": len(candidates),
                }
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

            browser_state.action_history.append(
                {
                    "action": "click_by_role",
                    "role": role,
                    "name": name,
                    "exact": exact,
                }
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

            browser_state.action_history.append(
                {
                    "action": "fill",
                    "field": field,
                    "strategy": strategy_name,
                    "text": text,
                }
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

            browser_state.action_history.append({"action": "click", "selector": selector, "text": text})
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

            browser_state.action_history.append({"action": "type", "selector": selector, "text": text})

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
            browser_state.action_history.append(
                {"action": "scroll", "direction": direction, "amount": amount}
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
                browser_state.action_history.append({"action": "extract", "selector": selector})
                return json.dumps({"status": "success", "extracted_text": text}, indent=2)
            return json.dumps({"status": "error", "message": f"Element not found: {selector}"}, indent=2)
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
            browser_state.action_history.append({"action": "wait", "seconds": seconds})
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
            await browser_state.cleanup()

            return json.dumps(
                {
                    "status": "success",
                    "message": "Browser session ended",
                    "task": task,
                    "actions_taken": len(history),
                    "action_history": history,
                    "final_result": final_result or "Session completed",
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
                "action_count": len(browser_state.action_history),
                "actions": browser_state.action_history,
            },
            indent=2,
        )
