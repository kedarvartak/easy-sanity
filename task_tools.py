import json
import os
import re
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import Prompt

from prompts import TASK_EXECUTION_PROMPT_TEMPLATE


TASKS_FILE = Path(__file__).parent / "tasks.json"
PROFILES_FILE = Path(__file__).parent / "profiles.json"
PLACEHOLDER_PATTERN = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")


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


def load_profiles_from_disk() -> dict[str, dict]:
    """Load saved environment profiles from profiles.json."""
    if PROFILES_FILE.exists():
        with open(PROFILES_FILE) as f:
            return json.load(f)
    return {}


def save_profiles_to_disk(profiles: dict[str, dict]) -> None:
    """Persist environment profiles to profiles.json."""
    with open(PROFILES_FILE, "w") as f:
        json.dump(profiles, f, indent=2)


def extract_placeholders(prompt: str) -> list[str]:
    """Extract ordered unique placeholder names from a task template."""
    seen = set()
    placeholders = []
    for match in PLACEHOLDER_PATTERN.findall(prompt):
        if match not in seen:
            placeholders.append(match)
            seen.add(match)
    return placeholders


def infer_secret_variables(placeholders: list[str]) -> list[str]:
    """Infer which placeholders likely contain secrets."""
    secret_markers = ("password", "secret", "token", "key", "api_key")
    return [name for name in placeholders if any(marker in name.lower() for marker in secret_markers)]


def _sanitize_name(name: str) -> str:
    return "".join(c if c.isalnum() or c == "_" else "_" for c in name).lower()


def _parse_json_object(value: str, field_name: str) -> dict[str, str]:
    try:
        parsed = json.loads(value) if value.strip() else {}
    except json.JSONDecodeError as e:
        raise ValueError(f"{field_name} must be valid JSON: {e.msg}") from e

    if not isinstance(parsed, dict):
        raise ValueError(f"{field_name} must be a JSON object")

    return {str(k): str(v) for k, v in parsed.items()}


def render_task_prompt(
    task: dict,
    profile_values: dict[str, str] | None = None,
    variables: dict[str, str] | None = None,
) -> tuple[str, list[str], dict[str, str]]:
    """
    Render a task prompt using merged values from environment, profile, and explicit variables.

    Precedence: explicit variables > profile values > environment variables.
    """
    profile_values = profile_values or {}
    variables = variables or {}
    placeholders = task.get("variables") or extract_placeholders(task["prompt"])
    merged_values: dict[str, str] = {}
    missing: list[str] = []

    for name in placeholders:
        if name in variables:
            merged_values[name] = variables[name]
        elif name in profile_values:
            merged_values[name] = profile_values[name]
        elif name in os.environ:
            merged_values[name] = os.environ[name]
        else:
            missing.append(name)

    rendered_prompt = task["prompt"]
    for name, value in merged_values.items():
        rendered_prompt = re.sub(r"{{\s*" + re.escape(name) + r"\s*}}", value, rendered_prompt)

    return rendered_prompt, missing, merged_values


def register_task_as_prompt(mcp: FastMCP, name: str, prompt_text: str, description: str) -> None:
    """
    Dynamically register a task as an MCP prompt so it appears as /name in the IDE.

    The prompt instructs the IDE's LLM to execute the task using the browser tools.
    Uses default argument binding to correctly capture prompt_text in the closure.
    """

    def task_fn(prompt_text=prompt_text):
        unresolved_variables = extract_placeholders(prompt_text)
        variable_note = ""
        if unresolved_variables:
            joined = ", ".join(unresolved_variables)
            variable_note = (
                f"\n\nThis task template contains placeholders: {joined}."
                f" Resolve them with task_render before execution if they are not already substituted."
            )
        return [
            {
                "role": "user",
                "content": TASK_EXECUTION_PROMPT_TEMPLATE.format(task_prompt=prompt_text) + variable_note,
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
    def task_create(
        name: str,
        prompt: str,
        description: str = "",
        secret_variables_json: str = "[]",
    ) -> str:
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
            secret_variables_json: Optional JSON array of placeholder names that should be treated as secrets.

        Returns:
            Confirmation that the task was created and registered as /name.

        Example:
            task_create(
                name="check_google",
                prompt="Go to www.google.com, type 'OpenAI' in the search box, press enter, and tell me the first result title.",
                description="Search Google for OpenAI"
            )
        """
        safe_name = _sanitize_name(name)
        placeholders = extract_placeholders(prompt)
        inferred_secret_variables = infer_secret_variables(placeholders)
        try:
            provided_secret_variables = json.loads(secret_variables_json) if secret_variables_json.strip() else []
        except json.JSONDecodeError as e:
            return json.dumps(
                {"status": "error", "message": f"secret_variables_json must be valid JSON: {e.msg}"},
                indent=2,
            )

        if not isinstance(provided_secret_variables, list):
            return json.dumps(
                {"status": "error", "message": "secret_variables_json must be a JSON array"},
                indent=2,
            )

        secret_variables = sorted(
            {
                str(name)
                for name in provided_secret_variables + inferred_secret_variables
                if str(name) in placeholders
            }
        )

        tasks = load_tasks_from_disk()
        already_existed = safe_name in tasks

        tasks[safe_name] = {
            "prompt": prompt,
            "description": description or f"Browser task: {safe_name}",
            "variables": placeholders,
            "secret_variables": secret_variables,
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
                "variables": placeholders,
                "secret_variables": secret_variables,
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
                "variables": task.get("variables", extract_placeholders(task["prompt"])),
                "secret_variables": task.get("secret_variables", []),
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
                "variables": task.get("variables", extract_placeholders(task["prompt"])),
                "secret_variables": task.get("secret_variables", []),
            },
            indent=2,
        )

    @mcp.tool()
    def task_render(name: str, profile: str = "", variables_json: str = "{}", mask_secrets: bool = False) -> str:
        """
        Render a task template using environment variables, an optional profile, and explicit variables.

        Args:
            name: Task name to render.
            profile: Optional saved profile name such as "local", "staging", or "prod".
            variables_json: JSON object of explicit variable values. These override profile and environment values.
            mask_secrets: When true, secret variables are masked in the rendered preview.

        Returns:
            Rendered prompt plus variable-resolution details.
        """
        tasks = load_tasks_from_disk()
        if name not in tasks:
            return json.dumps(
                {"status": "error", "message": f"Task '{name}' not found."},
                indent=2,
            )

        try:
            explicit_variables = _parse_json_object(variables_json, "variables_json")
        except ValueError as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

        profiles = load_profiles_from_disk()
        profile_values = {}
        if profile:
            if profile not in profiles:
                return json.dumps(
                    {"status": "error", "message": f"Profile '{profile}' not found."},
                    indent=2,
                )
            profile_values = profiles[profile].get("variables", {})

        task = tasks[name]
        rendered_prompt, missing, resolved_values = render_task_prompt(task, profile_values, explicit_variables)
        display_values = dict(resolved_values)
        if mask_secrets:
            for secret_name in task.get("secret_variables", []):
                if secret_name in display_values:
                    display_values[secret_name] = "***MASKED***"
                    rendered_prompt = re.sub(
                        r"{{\s*" + re.escape(secret_name) + r"\s*}}",
                        display_values[secret_name],
                        rendered_prompt,
                    )
                    if resolved_values.get(secret_name):
                        rendered_prompt = rendered_prompt.replace(resolved_values[secret_name], "***MASKED***")

        return json.dumps(
            {
                "status": "success",
                "name": name,
                "profile": profile or None,
                "variables": task.get("variables", []),
                "secret_variables": task.get("secret_variables", []),
                "resolved_values": display_values,
                "missing_variables": missing,
                "is_fully_resolved": len(missing) == 0,
                "rendered_prompt": rendered_prompt,
            },
            indent=2,
        )

    @mcp.tool()
    def profile_save(name: str, variables_json: str, description: str = "") -> str:
        """
        Create or update an environment profile for task rendering.

        Args:
            name: Profile name such as "local", "staging", or "prod".
            variables_json: JSON object of variables for this profile.
            description: Optional human-readable description.

        Returns:
            Confirmation and saved profile details.
        """
        safe_name = _sanitize_name(name)
        try:
            variables = _parse_json_object(variables_json, "variables_json")
        except ValueError as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

        profiles = load_profiles_from_disk()
        already_existed = safe_name in profiles
        profiles[safe_name] = {
            "description": description or f"Environment profile: {safe_name}",
            "variables": variables,
        }
        save_profiles_to_disk(profiles)

        return json.dumps(
            {
                "status": "success",
                "message": f"Profile '{safe_name}' {'updated' if already_existed else 'created'}.",
                "name": safe_name,
                "description": profiles[safe_name]["description"],
                "variables": variables,
            },
            indent=2,
        )

    @mcp.tool()
    def profile_list() -> str:
        """
        List all saved environment profiles.

        Returns:
            Summary of saved profiles and their variable names.
        """
        profiles = load_profiles_from_disk()
        profile_items = [
            {
                "name": name,
                "description": profile.get("description", ""),
                "variables": sorted(profile.get("variables", {}).keys()),
            }
            for name, profile in profiles.items()
        ]
        return json.dumps(
            {
                "status": "success",
                "count": len(profile_items),
                "profiles": profile_items,
            },
            indent=2,
        )

    @mcp.tool()
    def profile_get(name: str, mask_secrets: bool = True) -> str:
        """
        Get a saved environment profile.

        Args:
            name: Profile name to retrieve.
            mask_secrets: Whether to mask likely secret values in the response.

        Returns:
            Profile details including variable names and values.
        """
        profiles = load_profiles_from_disk()
        if name not in profiles:
            return json.dumps(
                {"status": "error", "message": f"Profile '{name}' not found."},
                indent=2,
            )

        profile = profiles[name]
        variables = dict(profile.get("variables", {}))
        if mask_secrets:
            for key in list(variables.keys()):
                if key in infer_secret_variables([key]):
                    variables[key] = "***MASKED***"

        return json.dumps(
            {
                "status": "success",
                "name": name,
                "description": profile.get("description", ""),
                "variables": variables,
            },
            indent=2,
        )

    @mcp.tool()
    def profile_delete(name: str) -> str:
        """
        Delete an environment profile.

        Args:
            name: Profile name to delete.

        Returns:
            Confirmation of deletion.
        """
        profiles = load_profiles_from_disk()
        if name not in profiles:
            return json.dumps(
                {"status": "error", "message": f"Profile '{name}' not found."},
                indent=2,
            )

        del profiles[name]
        save_profiles_to_disk(profiles)
        return json.dumps(
            {
                "status": "success",
                "message": f"Profile '{name}' deleted.",
            },
            indent=2,
        )
