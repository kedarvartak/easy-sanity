import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import Prompt

from prompts import TASK_EXECUTION_PROMPT_TEMPLATE


TASKS_FILE = Path(__file__).parent / "tasks.json"


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


def register_task_as_prompt(mcp: FastMCP, name: str, prompt_text: str, description: str) -> None:
    """
    Dynamically register a task as an MCP prompt so it appears as /name in the IDE.

    The prompt instructs the IDE's LLM to execute the task using the browser tools.
    Uses default argument binding to correctly capture prompt_text in the closure.
    """

    def task_fn(prompt_text=prompt_text):
        return [
            {
                "role": "user",
                "content": TASK_EXECUTION_PROMPT_TEMPLATE.format(task_prompt=prompt_text),
            }
        ]

    task_fn.__name__ = name
    task_fn.__doc__ = description

    prompt = Prompt.from_function(task_fn, name=name, description=description)
    mcp.add_prompt(prompt)


def load_tasks_as_prompts(mcp: FastMCP) -> None:
    """Load all persisted tasks and register them as MCP prompts at startup."""
    tasks = load_tasks_from_disk()
    for name, task in tasks.items():
        register_task_as_prompt(mcp, name, task["prompt"], task.get("description", ""))


def register_task_tools(mcp: FastMCP) -> None:
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
        safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in name).lower()

        tasks = load_tasks_from_disk()
        already_existed = safe_name in tasks

        tasks[safe_name] = {
            "prompt": prompt,
            "description": description or f"Browser task: {safe_name}",
        }
        save_tasks_to_disk(tasks)

        if already_existed:
            mcp._prompt_manager._prompts.pop(safe_name, None)

        register_task_as_prompt(mcp, safe_name, prompt, tasks[safe_name]["description"])

        action = "updated" if already_existed else "created"
        return json.dumps(
            {
                "status": "success",
                "message": f"Task '{safe_name}' {action}. Invoke it in your IDE with /{safe_name}",
                "name": safe_name,
                "prompt": prompt,
                "description": tasks[safe_name]["description"],
            },
            indent=2,
        )

    @mcp.tool()
    def task_list() -> str:
        """
        List all saved browser automation tasks.

        Returns:
            JSON list of all tasks with their names, descriptions, and prompts.
        """
        tasks = load_tasks_from_disk()
        if not tasks:
            return json.dumps(
                {
                    "status": "success",
                    "message": "No tasks saved yet. Use task_create to add one.",
                    "tasks": [],
                },
                indent=2,
            )

        task_list_items = [
            {
                "name": name,
                "slash_command": f"/{name}",
                "description": task.get("description", ""),
                "prompt": task["prompt"],
            }
            for name, task in tasks.items()
        ]

        return json.dumps(
            {
                "status": "success",
                "count": len(task_list_items),
                "tasks": task_list_items,
            },
            indent=2,
        )

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
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Task '{name}' not found. Use task_list to see all tasks.",
                },
                indent=2,
            )

        del tasks[name]
        save_tasks_to_disk(tasks)
        mcp._prompt_manager._prompts.pop(name, None)

        return json.dumps(
            {
                "status": "success",
                "message": f"Task '{name}' deleted.",
            },
            indent=2,
        )

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
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Task '{name}' not found.",
                },
                indent=2,
            )

        task = tasks[name]
        return json.dumps(
            {
                "status": "success",
                "name": name,
                "slash_command": f"/{name}",
                "description": task.get("description", ""),
                "prompt": task["prompt"],
            },
            indent=2,
        )
