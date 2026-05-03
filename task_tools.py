import json
import os
import re
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import Prompt

from prompts import TASK_EXECUTION_PROMPT_TEMPLATE, TASK_WIZARD_PROMPT_TEMPLATE
from settings import SAMPLE_TASKS_FILE


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


def load_sample_tasks() -> dict[str, dict]:
    """Load bundled sample tasks for onboarding."""
    if SAMPLE_TASKS_FILE.exists():
        with open(SAMPLE_TASKS_FILE) as f:
            return json.load(f)
    return {}


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


def build_task_wizard_prompt(goal: str, start_url: str, include_placeholders: bool, include_assertions: bool) -> str:
    base_url = "{{base_url}}" if include_placeholders else (start_url or "https://example.com")
    email_value = "{{email}}" if include_placeholders else "user@example.com"
    password_value = "{{password}}" if include_placeholders else "replace-me"

    lines = [
        f"1. Call browser_start with task \"{goal}\".",
        f"2. Call browser_navigate to {base_url}.",
        "3. Call browser_get_state to inspect the page and identify the next actionable elements.",
        "4. Use browser_find_element, browser_fill, browser_click_by_role, browser_click, or browser_type as needed.",
        f"5. If login is required, use {email_value} and {password_value} only through the appropriate fields.",
    ]

    if include_assertions:
        lines.extend(
            [
                "6. Use assertions such as assert_text_visible, assert_url_contains, or assert_element_exists to verify success.",
                "7. Call browser_stop with a clear pass/fail summary.",
            ]
        )
    else:
        lines.extend(
            [
                "6. Clearly verify the expected final state using page state or extracted content.",
                "7. Call browser_stop with a clear summary.",
            ]
        )

    return "\n".join(lines)


def lint_task_prompt(prompt: str) -> dict[str, list[str] | int]:
    lowered = prompt.lower()
    warnings: list[str] = []
    suggestions: list[str] = []
    strengths: list[str] = []

    has_steps = bool(re.search(r"(^|\n)\s*(step\s+\d+|[0-9]+\.)", prompt, re.IGNORECASE))
    has_assertions = any(word in lowered for word in ("assert", "verify", "confirm", "check", "ensure"))
    has_url = "http://" in lowered or "https://" in lowered or "{{base_url}}" in lowered
    has_cleanup = "browser_stop" in prompt or "stop with" in lowered or "summary" in lowered
    placeholders = extract_placeholders(prompt)

    if has_steps:
        strengths.append("Task has step-like structure.")
    else:
        warnings.append("Task is unstructured. Consider numbered steps or explicit phases.")

    if has_assertions:
        strengths.append("Task includes verification or assertion language.")
    else:
        warnings.append("Task lacks explicit verification. Add assert/verify/confirm/check steps.")

    if has_url:
        strengths.append("Task includes a concrete starting URL or {{base_url}} placeholder.")
    else:
        warnings.append("Task does not specify a starting URL or base_url placeholder.")

    if has_cleanup:
        strengths.append("Task includes an explicit completion or cleanup expectation.")
    else:
        suggestions.append("Add a final browser_stop summary step so the run ends cleanly.")

    if len(prompt.strip()) < 80:
        warnings.append("Task prompt is very short and may be too vague for reliable execution.")

    if any(word in lowered for word in ("password", "token", "secret", "api key", "apikey")) and "{{" not in prompt:
        warnings.append("Task appears to include secret-like values without placeholders.")
        suggestions.append("Replace credentials or secrets with placeholders like {{password}} or {{api_key}}.")

    if "{{" in prompt and not placeholders:
        warnings.append("Task contains malformed placeholder syntax.")

    if placeholders:
        strengths.append(f"Task uses reusable placeholders: {', '.join(placeholders)}.")

    quality_score = 100 - (len(warnings) * 15) - (0 if has_assertions else 10) - (0 if has_steps else 10)
    quality_score = max(0, min(100, quality_score))

    return {
        "warnings": warnings,
        "suggestions": suggestions,
        "strengths": strengths,
        "quality_score": quality_score,
    }


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
    def sample_tasks_list() -> str:
        """
        List the bundled sample tasks available for onboarding and quick smoke testing.

        Returns:
            Summary of sample task names, descriptions, and variable placeholders.
        """
        sample_tasks = load_sample_tasks()
        items = [
            {
                "name": name,
                "description": task.get("description", ""),
                "variables": task.get("variables", extract_placeholders(task.get("prompt", ""))),
                "secret_variables": task.get("secret_variables", []),
            }
            for name, task in sample_tasks.items()
        ]
        return json.dumps(
            {
                "status": "success",
                "count": len(items),
                "tasks": items,
            },
            indent=2,
        )

    @mcp.tool()
    def sample_tasks_import(names_json: str = "[]", overwrite: bool = False) -> str:
        """
        Import bundled sample tasks into tasks.json and register them as prompts.

        Args:
            names_json: Optional JSON array of sample task names to import. Imports all if empty.
            overwrite: Whether to overwrite existing tasks with the same names.

        Returns:
            Summary of imported, skipped, and missing sample task names.
        """
        sample_tasks = load_sample_tasks()
        try:
            requested_names = json.loads(names_json) if names_json.strip() else []
        except json.JSONDecodeError as e:
            return json.dumps(
                {"status": "error", "message": f"names_json must be valid JSON: {e.msg}"},
                indent=2,
            )

        if not isinstance(requested_names, list):
            return json.dumps(
                {"status": "error", "message": "names_json must be a JSON array"},
                indent=2,
            )

        selected_names = [str(name) for name in requested_names] if requested_names else sorted(sample_tasks.keys())
        tasks = load_tasks_from_disk()
        imported: list[str] = []
        skipped: list[str] = []
        missing: list[str] = []

        for name in selected_names:
            if name not in sample_tasks:
                missing.append(name)
                continue
            if name in tasks and not overwrite:
                skipped.append(name)
                continue

            task = sample_tasks[name]
            tasks[name] = {
                "prompt": task["prompt"],
                "description": task.get("description", f"Sample task: {name}"),
                "variables": task.get("variables", extract_placeholders(task["prompt"])),
                "secret_variables": task.get("secret_variables", []),
            }
            mcp._prompt_manager._prompts.pop(name, None)
            register_task_as_prompt(mcp, name, tasks[name]["prompt"], tasks[name]["description"])
            imported.append(name)

        save_tasks_to_disk(tasks)
        return json.dumps(
            {
                "status": "success",
                "imported": imported,
                "skipped": skipped,
                "missing": missing,
                "message": "Sample task import complete.",
            },
            indent=2,
        )

    @mcp.tool()
    def task_wizard_template(
        goal: str,
        start_url: str = "",
        task_name: str = "",
        include_placeholders: bool = True,
        include_assertions: bool = True,
    ) -> str:
        """
        Generate a starter template for authoring a new browser automation task.

        Args:
            goal: Human description of what the task should accomplish.
            start_url: Optional starting URL or page path.
            task_name: Optional suggested task name. If omitted, one will be inferred.
            include_placeholders: Whether to use reusable placeholders such as {{base_url}} and {{password}}.
            include_assertions: Whether to include explicit assertion guidance in the template.

        Returns:
            A structured task draft plus metadata to help the user save it.
        """
        safe_name = _sanitize_name(task_name or goal[:40] or "browser_task")
        suggested_prompt = build_task_wizard_prompt(goal, start_url, include_placeholders, include_assertions)
        variables = extract_placeholders(suggested_prompt)
        secret_variables = infer_secret_variables(variables)
        template_preview = TASK_WIZARD_PROMPT_TEMPLATE.format(
            goal=goal,
            start_url=start_url or ("{{base_url}}" if include_placeholders else "https://example.com"),
            task_prompt=suggested_prompt,
        )

        return json.dumps(
            {
                "status": "success",
                "suggested_name": safe_name,
                "suggested_description": f"Browser task: {goal}",
                "suggested_prompt": suggested_prompt,
                "template_preview": template_preview,
                "variables": variables,
                "secret_variables": secret_variables,
                "next_step": "Review the suggested prompt, customize it, then save it with task_create.",
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
    def task_lint(name: str = "", prompt: str = "") -> str:
        """
        Lint a saved task or a draft prompt to catch vague instructions and missing verification.

        Args:
            name: Optional saved task name to lint.
            prompt: Optional raw task prompt to lint directly.

        Returns:
            Quality summary with warnings, strengths, and suggestions.
        """
        task_name = name.strip()
        task_prompt = prompt.strip()

        if not task_name and not task_prompt:
            return json.dumps(
                {"status": "error", "message": "Provide either a saved task name or a prompt to lint."},
                indent=2,
            )

        if task_name:
            tasks = load_tasks_from_disk()
            if task_name not in tasks:
                return json.dumps(
                    {"status": "error", "message": f"Task '{task_name}' not found."},
                    indent=2,
                )
            task_prompt = tasks[task_name]["prompt"]

        lint_result = lint_task_prompt(task_prompt)
        return json.dumps(
            {
                "status": "success",
                "name": task_name or None,
                "variables": extract_placeholders(task_prompt),
                **lint_result,
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
