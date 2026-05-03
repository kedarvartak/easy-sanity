from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re


def utc_timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def iso_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str, default: str = "artifact") -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or default


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def screenshot_filename(step_number: int, action: str, status: str = "") -> str:
    parts = [f"{step_number:03d}", slugify(action)]
    if status:
        parts.append(slugify(status))
    return "-".join(parts) + ".png"


def report_filename(session_slug: str) -> str:
    return f"{session_slug}.md"


def relative_link(from_path: Path, to_path: Path) -> str:
    try:
        return str(to_path.relative_to(from_path.parent))
    except ValueError:
        return str(to_path)


def render_markdown_report(
    *,
    task: str,
    session_slug: str,
    started_at: str,
    finished_at: str,
    final_result: str,
    actions: list[dict],
    screenshots_root: Path,
    report_path: Path,
) -> str:
    lines = [
        f"# Browser Session Report: {task or session_slug}",
        "",
        f"- Session: `{session_slug}`",
        f"- Started At: `{started_at}`",
        f"- Finished At: `{finished_at}`",
        f"- Actions Taken: `{len(actions)}`",
        f"- Final Result: {final_result}",
        "",
        "## Action Summary",
        "",
        "| Step | Action | Status | URL | Screenshot |",
        "|------|--------|--------|-----|------------|",
    ]

    for index, action in enumerate(actions, start=1):
        screenshot_path = action.get("screenshot_path")
        screenshot_display = "-"
        if screenshot_path:
            screenshot_display = f"[image]({relative_link(report_path, Path(screenshot_path))})"
        lines.append(
            f"| {index} | `{action.get('action', '')}` | `{action.get('status', '')}` | "
            f"`{action.get('url', '')}` | {screenshot_display} |"
        )

    lines.extend(["", "## Detailed Steps", ""])

    for index, action in enumerate(actions, start=1):
        lines.append(f"### Step {index}: `{action.get('action', '')}`")
        lines.append("")
        lines.append(f"- Timestamp: `{action.get('timestamp', '')}`")
        lines.append(f"- Status: `{action.get('status', '')}`")
        if action.get("url"):
            lines.append(f"- URL: `{action.get('url')}`")
        if action.get("title"):
            lines.append(f"- Title: `{action.get('title')}`")

        details = action.get("details", {})
        if details:
            lines.append("- Details:")
            for key, value in details.items():
                lines.append(f"  - `{key}`: `{value}`")

        screenshot_path = action.get("screenshot_path")
        if screenshot_path:
            screenshot_link = relative_link(report_path, Path(screenshot_path))
            lines.append(f"- Screenshot: [{Path(screenshot_path).name}]({screenshot_link})")

        lines.append("")

    lines.extend(
        [
            "## Artifact Locations",
            "",
            f"- Report File: `{report_path}`",
            f"- Screenshots Directory: `{screenshots_root}`",
            "",
        ]
    )

    return "\n".join(lines)
