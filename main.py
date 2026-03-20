import asyncio
import base64
import json
from typing import Optional, Literal
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import Prompt
from playwright.async_api import async_playwright, Page, Browser

# Initialize FastMCP server
mcp = FastMCP("BrowserAgentServer")

# Path to persisted task storage
TASKS_FILE = Path(__file__).parent / "tasks.json"


# --- Task Storage ---

def load_tasks_from_disk() -> dict[str, dict]:
    """Load all saved tasks from tasks.json."""
    if TASKS_FILE.exists():
        with open(TASKS_FILE) as f:
            return json.load(f)
    return {}


def save_tasks_to_disk(tasks: dict[str, dict]) -> None:
    """Persist all tasks to tasks.json."""
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2)


def register_task_as_prompt(name: str, prompt_text: str, description: str) -> None:
    """
    Dynamically register a task as an MCP prompt so it appears as /name in the IDE.

    The prompt instructs the IDE's LLM to execute the task using the browser tools.
    Uses default argument binding to correctly capture prompt_text in the closure.
    """
    def task_fn(prompt_text=prompt_text):
        return [
            {
                "role": "user",
                "content": (
                    f"Execute the following browser automation task using the available browser tools.\n\n"
                    f"Task: {prompt_text}\n\n"
                    f"Steps to follow:\n"
                    f"1. Call browser_start with the task description\n"
                    f"2. Use browser_navigate to go to the required URL\n"
                    f"3. Call browser_get_state frequently to see the current page and screenshot\n"
                    f"4. Use browser_click, browser_type, browser_scroll as needed\n"
                    f"5. Use browser_extract to pull out data when required\n"
                    f"6. Call browser_stop with a summary when the task is complete"
                )
            }
        ]

    task_fn.__name__ = name
    task_fn.__doc__ = description

    prompt = Prompt.from_function(task_fn, name=name, description=description)
    mcp.add_prompt(prompt)


def load_tasks_as_prompts() -> None:
    """Load all persisted tasks and register them as MCP prompts at startup."""
    tasks = load_tasks_from_disk()
    for name, task in tasks.items():
        register_task_as_prompt(name, task["prompt"], task.get("description", ""))


# Register all saved tasks when the module is loaded
load_tasks_as_prompts()


# --- Task Management Tools ---

@mcp.tool()
def task_create(name: str, prompt: str, description: str = "") -> str:
    """
    Create a new browser automation task and save it as a /slash-command.

    Once created, you can invoke the task in your IDE by typing /name.
    The task will be persisted across server restarts.

    Args:
        name: Short identifier for the task, used as the slash command (e.g. "google_search").
              Use only letters, numbers, and underscores.
        prompt: The full prompt describing what the browser should do.
                Be as detailed as possible (e.g. "Go to www.google.com, search for Python tutorials,
                and return the titles of the top 3 results").
        description: Optional short description shown in the IDE command palette.

    Returns:
        Confirmation that the task was created and registered as /name.

    Example:
        task_create(
            name="check_google",
            prompt="Go to www.google.com, type 'OpenAI' in the search box, press enter, and tell me the first result title.",
            description="Search Google for OpenAI"
        )
    """
    # Sanitize name - only allow alphanumeric and underscores
    safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in name).lower()

    tasks = load_tasks_from_disk()
    already_existed = safe_name in tasks

    tasks[safe_name] = {
        "prompt": prompt,
        "description": description or f"Browser task: {safe_name}",
    }
    save_tasks_to_disk(tasks)

    # Register as MCP prompt (or re-register if updating)
    if already_existed:
        # Remove old prompt entry before re-registering
        mcp._prompt_manager._prompts.pop(safe_name, None)

    register_task_as_prompt(safe_name, prompt, tasks[safe_name]["description"])

    action = "updated" if already_existed else "created"
    return json.dumps({
        "status": "success",
        "message": f"Task '{safe_name}' {action}. Invoke it in your IDE with /{safe_name}",
        "name": safe_name,
        "prompt": prompt,
        "description": tasks[safe_name]["description"],
    }, indent=2)


@mcp.tool()
def task_list() -> str:
    """
    List all saved browser automation tasks.

    Returns:
        JSON list of all tasks with their names, descriptions, and prompts.
    """
    tasks = load_tasks_from_disk()
    if not tasks:
        return json.dumps({
            "status": "success",
            "message": "No tasks saved yet. Use task_create to add one.",
            "tasks": []
        }, indent=2)

    task_list = [
        {
            "name": name,
            "slash_command": f"/{name}",
            "description": task.get("description", ""),
            "prompt": task["prompt"],
        }
        for name, task in tasks.items()
    ]

    return json.dumps({
        "status": "success",
        "count": len(task_list),
        "tasks": task_list
    }, indent=2)


@mcp.tool()
def task_delete(name: str) -> str:
    """
    Delete a saved browser automation task.

    This removes the task from disk and unregisters its /slash-command.
    Note: The slash command may still appear until you restart the MCP server.

    Args:
        name: The task name to delete.

    Returns:
        Confirmation of deletion.
    """
    tasks = load_tasks_from_disk()

    if name not in tasks:
        return json.dumps({
            "status": "error",
            "message": f"Task '{name}' not found. Use task_list to see all tasks."
        }, indent=2)

    del tasks[name]
    save_tasks_to_disk(tasks)

    # Remove from in-memory prompt registry
    mcp._prompt_manager._prompts.pop(name, None)

    return json.dumps({
        "status": "success",
        "message": f"Task '{name}' deleted.",
    }, indent=2)


@mcp.tool()
def task_get(name: str) -> str:
    """
    Get the full details of a saved task including its prompt.

    Args:
        name: The task name to retrieve.

    Returns:
        Task details including the full prompt text.
    """
    tasks = load_tasks_from_disk()
    if name not in tasks:
        return json.dumps({
            "status": "error",
            "message": f"Task '{name}' not found."
        }, indent=2)

    task = tasks[name]
    return json.dumps({
        "status": "success",
        "name": name,
        "slash_command": f"/{name}",
        "description": task.get("description", ""),
        "prompt": task["prompt"],
    }, indent=2)


# --- Browser State ---

class BrowserState:
    """Manages browser lifecycle across tool calls."""

    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.task_description: str = ""
        self.action_history: list = []

    async def initialize(self, headless: bool = False):
        if self.browser is None:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=headless)
            self.page = await self.browser.new_page()
            self.page.set_default_timeout(30000)

    async def cleanup(self):
        if self.page:
            await self.page.close()
            self.page = None
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        self.action_history = []
        self.task_description = ""


browser_state = BrowserState()


# --- Browser Tools ---

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

        return json.dumps({
            "status": "success",
            "message": "Browser started",
            "task": task,
        }, indent=2)
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
        return json.dumps({
            "status": "error",
            "message": "Browser not started. Call browser_start first."
        }, indent=2)

    try:
        url = browser_state.page.url
        title = await browser_state.page.title()

        visible_text = await browser_state.page.evaluate("""
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
        """)

        elements = await browser_state.page.evaluate("""
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
        """)

        screenshot_bytes = await browser_state.page.screenshot(type="png", full_page=False)
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode()

        return json.dumps({
            "status": "success",
            "url": url,
            "title": title,
            "visible_text": visible_text,
            "interactive_elements": elements[:20],
            "screenshot_base64": screenshot_b64,
            "action_count": len(browser_state.action_history),
            "task": browser_state.task_description
        }, indent=2)

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
        return json.dumps({"status": "error", "message": "Browser not started"}, indent=2)

    try:
        await browser_state.page.goto(url, wait_until="networkidle")
        title = await browser_state.page.title()

        browser_state.action_history.append({"action": "navigate", "url": url})

        return json.dumps({
            "status": "success",
            "message": f"Navigated to {url}",
            "title": title,
            "url": browser_state.page.url
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@mcp.tool()
async def browser_click(
    selector: Optional[str] = None,
    text: Optional[str] = None,
    element_index: Optional[int] = None
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
        return json.dumps({"status": "error", "message": "Browser not started"}, indent=2)

    try:
        if element_index is not None:
            await browser_state.page.evaluate(f"""
                () => {{
                    const els = Array.from(document.querySelectorAll('a, button, input, select, textarea'));
                    if (els[{element_index}]) els[{element_index}].click();
                }}
            """)
        elif selector:
            await browser_state.page.click(selector)
        elif text:
            await browser_state.page.click(f"text={text}")
        else:
            return json.dumps({"status": "error", "message": "Provide selector, text, or element_index"}, indent=2)

        browser_state.action_history.append({"action": "click", "selector": selector, "text": text})
        await asyncio.sleep(1)

        return json.dumps({
            "status": "success",
            "message": "Clicked element",
            "url": browser_state.page.url
        }, indent=2)
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
        return json.dumps({"status": "error", "message": "Browser not started"}, indent=2)

    try:
        await browser_state.page.fill(selector, text)

        if press_enter:
            await browser_state.page.press(selector, "Enter")
            await asyncio.sleep(1)

        browser_state.action_history.append({"action": "type", "selector": selector, "text": text})

        return json.dumps({
            "status": "success",
            "message": f"Typed into {selector}",
            "pressed_enter": press_enter
        }, indent=2)
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
        return json.dumps({"status": "error", "message": "Browser not started"}, indent=2)

    try:
        scroll_amount = amount if direction == "down" else -amount
        await browser_state.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        browser_state.action_history.append({"action": "scroll", "direction": direction, "amount": amount})
        await asyncio.sleep(0.5)

        return json.dumps({"status": "success", "message": f"Scrolled {direction} {amount}px"}, indent=2)
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
        return json.dumps({"status": "error", "message": "Browser not started"}, indent=2)

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
        return json.dumps({"status": "error", "message": "Browser not started"}, indent=2)

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

        return json.dumps({
            "status": "success",
            "message": "Browser session ended",
            "task": task,
            "actions_taken": len(history),
            "action_history": history,
            "final_result": final_result or "Session completed"
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@mcp.tool()
async def browser_get_history() -> str:
    """
    Get the action history for the current browser session.

    Returns:
        List of all actions performed so far.
    """
    return json.dumps({
        "status": "success",
        "task": browser_state.task_description,
        "action_count": len(browser_state.action_history),
        "actions": browser_state.action_history
    }, indent=2)


if __name__ == "__main__":
    mcp.run()
