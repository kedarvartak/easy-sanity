from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from config.settings import app_memory_dir


IGNORED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".next",
    ".turbo",
    ".idea",
    ".vscode",
    "app_memory",
    "artifacts",
}

TEXT_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".txt",
    ".yml",
    ".yaml",
    ".toml",
    ".env",
    ".html",
    ".css",
    ".scss",
    ".sql",
    ".sh",
}

SIGNAL_FILENAMES = {
    "readme.md",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "pnpm-lock.yaml",
    "package-lock.json",
    "yarn.lock",
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".env.example",
    ".env.local.example",
    "next.config.js",
    "next.config.ts",
    "vite.config.ts",
    "vite.config.js",
    "playwright.config.ts",
    "playwright.config.js",
    "cypress.config.ts",
    "cypress.config.js",
    "manage.py",
    "main.py",
    "app.py",
}

WORKFLOW_KEYWORDS = {
    "auth": ["login", "logout", "signin", "sign-in", "signup", "sign-up", "password", "auth", "session"],
    "dashboard": ["dashboard", "overview", "home", "analytics", "metrics"],
    "search": ["search", "filter", "results", "query"],
    "settings": ["settings", "preferences", "config", "configuration"],
    "profile": ["profile", "account", "user"],
    "admin": ["admin", "management", "moderation", "backoffice"],
    "checkout": ["checkout", "payment", "billing", "cart", "order", "invoice"],
    "onboarding": ["onboarding", "welcome", "getting-started", "setup"],
}

FEATURE_KEYWORDS = {
    "authentication": ["login", "signup", "auth", "password", "session"],
    "navigation": ["navbar", "nav", "sidebar", "menu", "breadcrumb"],
    "reporting": ["report", "analytics", "metrics", "dashboard"],
    "commerce": ["cart", "product", "checkout", "payment", "order"],
    "messaging": ["chat", "message", "notification", "inbox"],
    "data-management": ["table", "list", "grid", "filter", "sort"],
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str, default: str = "repo") -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or default


def repo_memory_id(repo_path: str) -> str:
    resolved = str(Path(repo_path).resolve())
    digest = hashlib.sha1(resolved.encode()).hexdigest()[:10]
    return f"{slugify(Path(resolved).name)}-{digest}"


def repo_memory_root(repo_path: str) -> Path:
    return app_memory_dir() / repo_memory_id(repo_path)


def repo_memory_json_path(repo_path: str) -> Path:
    return repo_memory_root(repo_path) / "memory.json"


def repo_memory_markdown_path(repo_path: str) -> Path:
    return repo_memory_root(repo_path) / "memory.md"


def ensure_repo_memory_dir(repo_path: str) -> Path:
    path = repo_memory_root(repo_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_repo_memory(repo_path: str) -> dict:
    path = repo_memory_json_path(repo_path)
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_repo_memory(repo_path: str, memory: dict) -> None:
    ensure_repo_memory_dir(repo_path)
    repo_memory_json_path(repo_path).write_text(json.dumps(memory, indent=2))


def write_repo_memory_markdown(repo_path: str, markdown: str) -> None:
    ensure_repo_memory_dir(repo_path)
    repo_memory_markdown_path(repo_path).write_text(markdown)


def should_ignore_path(path: Path) -> bool:
    return any(part in IGNORED_DIRS for part in path.parts)


def list_repo_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in repo_root.rglob("*"):
        if path.is_dir() or should_ignore_path(path):
            continue
        files.append(path)
    return sorted(files)


def iter_repo_files(repo_root: Path, limit: int = 1000) -> list[Path]:
    return list_repo_files(repo_root)[:limit]


def read_text_excerpt(path: Path, char_limit: int = 4000) -> str:
    if path.suffix.lower() not in TEXT_EXTENSIONS and path.name.lower() not in SIGNAL_FILENAMES:
        return ""
    try:
        return path.read_text(errors="ignore")[:char_limit]
    except Exception:
        return ""


def file_signature(path: Path) -> str:
    stat = path.stat()
    return f"{stat.st_size}:{stat.st_mtime_ns}"


def build_repo_manifest(repo_root: Path) -> dict[str, str]:
    manifest: dict[str, str] = {}
    for path in list_repo_files(repo_root):
        manifest[str(path.relative_to(repo_root))] = file_signature(path)
    return manifest


def diff_repo_manifests(previous: dict[str, str], current: dict[str, str]) -> dict[str, list[str]]:
    previous_paths = set(previous)
    current_paths = set(current)
    new_files = sorted(current_paths - previous_paths)
    removed_files = sorted(previous_paths - current_paths)
    changed_files = sorted(
        path for path in (current_paths & previous_paths) if previous.get(path) != current.get(path)
    )
    return {
        "new_files": new_files,
        "changed_files": changed_files,
        "removed_files": removed_files,
    }


def parse_focus_terms(focus: str) -> list[str]:
    return [term for term in re.split(r"[^a-zA-Z0-9]+", focus.lower()) if len(term) > 2]


def path_priority(relative_path: str, focus_terms: list[str]) -> tuple[int, int, str]:
    lowered = relative_path.lower()
    score = 0
    if Path(relative_path).name.lower() in SIGNAL_FILENAMES:
        score += 12
    if any(marker in lowered for marker in ("/app/", "/pages/", "/routes/", "/src/", "/components/", "/tests/")):
        score += 6
    if any(token in lowered for token in ("auth", "login", "dashboard", "search", "checkout", "settings")):
        score += 8
    focus_hits = sum(1 for term in focus_terms if term in lowered)
    score += focus_hits * 10
    return (-score, -focus_hits, lowered)


def select_sync_files(
    repo_root: Path,
    current_manifest: dict[str, str],
    previous_manifest: dict[str, str],
    max_files: int,
    focus: str = "",
) -> tuple[list[Path], dict[str, list[str]]]:
    delta = diff_repo_manifests(previous_manifest, current_manifest)
    focus_terms = parse_focus_terms(focus)
    current_paths = sorted(current_manifest)

    prioritized_paths = []
    seen: set[str] = set()
    groups = [
        delta["changed_files"] + delta["new_files"],
        [path for path in current_paths if any(term in path.lower() for term in focus_terms)],
        [path for path in current_paths if Path(path).name.lower() in SIGNAL_FILENAMES],
        current_paths,
    ]
    for group in groups:
        for relative_path in sorted(group, key=lambda value: path_priority(value, focus_terms)):
            if relative_path in seen:
                continue
            seen.add(relative_path)
            prioritized_paths.append(relative_path)
            if len(prioritized_paths) >= max_files:
                break
        if len(prioritized_paths) >= max_files:
            break

    selected_files = [repo_root / relative_path for relative_path in prioritized_paths]
    return selected_files, delta


def unique_sorted(values: list[str]) -> list[str]:
    return sorted({value for value in values if value})


def merge_unique_lists(previous: list[str], current: list[str], limit: int = 50) -> list[str]:
    return unique_sorted(previous + current)[:limit]


def merge_mapping_lists(
    previous: dict[str, list[str]],
    current: dict[str, list[str]],
    limit_per_key: int = 20,
) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for key in sorted(set(previous) | set(current)):
        merged[key] = merge_unique_lists(previous.get(key, []), current.get(key, []), limit_per_key)
    return merged


def infer_tech_stack(file_paths: list[str], file_contents: dict[str, str]) -> list[str]:
    stack: list[str] = []
    joined_paths = " ".join(file_paths).lower()

    if "package.json" in joined_paths:
        stack.append("Node.js")
    if "pyproject.toml" in joined_paths or "requirements.txt" in joined_paths:
        stack.append("Python")
    if "next.config" in joined_paths or "/app/" in joined_paths or "/pages/" in joined_paths:
        stack.append("Next.js/React-like routing")
    if "vite.config" in joined_paths:
        stack.append("Vite")
    if "manage.py" in joined_paths:
        stack.append("Django")
    if "dockerfile" in joined_paths:
        stack.append("Docker")

    for content in file_contents.values():
        lowered = content.lower()
        if "fastapi" in lowered:
            stack.append("FastAPI")
        if "flask" in lowered:
            stack.append("Flask")
        if "express(" in lowered or "from 'express'" in lowered or 'from "express"' in lowered:
            stack.append("Express")
        if "react" in lowered:
            stack.append("React")
        if "playwright" in lowered:
            stack.append("Playwright")
        if "cypress" in lowered:
            stack.append("Cypress")
        if "tailwindcss" in lowered:
            stack.append("Tailwind CSS")

    return unique_sorted(stack)


def infer_entrypoints(file_paths: list[str]) -> list[str]:
    candidates = []
    names = {
        "main.py",
        "app.py",
        "server.py",
        "manage.py",
        "package.json",
        "pyproject.toml",
        "next.config.js",
        "next.config.ts",
        "vite.config.ts",
        "vite.config.js",
        "readme.md",
    }
    for path in file_paths:
        if Path(path).name.lower() in names:
            candidates.append(path)
    return unique_sorted(candidates)[:20]


def infer_route_hints(file_paths: list[str]) -> list[str]:
    hints = []
    for path in file_paths:
        lowered = path.lower()
        if any(
            marker in lowered
            for marker in ("/pages/", "/app/", "/routes/", "/api/", "route.", "page.", "/views/", "/screens/")
        ):
            hints.append(path)
    return unique_sorted(hints)[:40]


def infer_workflows(file_paths: list[str], file_contents: dict[str, str]) -> dict[str, list[str]]:
    observations: dict[str, list[str]] = {}
    searchable = {path: (path.lower() + "\n" + content.lower()) for path, content in file_contents.items()}
    for workflow, keywords in WORKFLOW_KEYWORDS.items():
        hits = []
        for path, searchable_text in searchable.items():
            if any(keyword in searchable_text for keyword in keywords):
                hits.append(path)
        if hits:
            observations[workflow] = unique_sorted(hits)[:15]
    return observations


def infer_feature_hints(file_paths: list[str], file_contents: dict[str, str]) -> dict[str, list[str]]:
    searchable = {path: (path.lower() + "\n" + content.lower()) for path, content in file_contents.items()}
    observations: dict[str, list[str]] = {}
    for feature, keywords in FEATURE_KEYWORDS.items():
        hits = []
        for path, searchable_text in searchable.items():
            if any(keyword in searchable_text for keyword in keywords):
                hits.append(path)
        if hits:
            observations[feature] = unique_sorted(hits)[:12]
    return observations


def extract_readme_summary(file_contents: dict[str, str]) -> str:
    for path, content in file_contents.items():
        if Path(path).name.lower().startswith("readme"):
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            return "\n".join(lines[:12])
    return ""


def infer_env_hints(file_contents: dict[str, str]) -> list[str]:
    env_names = set()
    pattern = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b")
    for path, content in file_contents.items():
        if ".env" in path.lower() or "config" in path.lower() or "settings" in path.lower():
            for match in pattern.findall(content):
                env_names.add(match)
    return sorted(env_names)[:40]


def infer_test_assets(file_paths: list[str], file_contents: dict[str, str]) -> list[str]:
    hints = []
    for path in file_paths:
        lowered = path.lower()
        if any(token in lowered for token in ("playwright", "cypress", "tests/", "__tests__", ".spec.", ".test.")):
            hints.append(path)
    for path, content in file_contents.items():
        lowered = content.lower()
        if "playwright" in lowered or "cypress" in lowered:
            hints.append(path)
    return unique_sorted(hints)[:25]


def infer_primary_surfaces(
    route_hints: list[str],
    workflow_hints: dict[str, list[str]],
    feature_hints: dict[str, list[str]],
) -> list[str]:
    surfaces = []
    for workflow in workflow_hints:
        surfaces.append(f"{workflow} workflow")
    for feature in feature_hints:
        surfaces.append(f"{feature} surface")
    if route_hints:
        surfaces.append("route-driven UI surface")
    return unique_sorted(surfaces)[:20]


def infer_testing_targets(memory: dict) -> list[str]:
    targets = []
    workflows = memory.get("workflow_hints", {})
    features = memory.get("feature_hints", {})
    test_assets = memory.get("test_asset_hints", [])

    if "auth" in workflows:
        targets.append("Verify login, logout, session persistence, and invalid-credential handling.")
    if "dashboard" in workflows:
        targets.append("Check dashboard rendering, key cards/widgets, and empty states.")
    if "search" in workflows:
        targets.append("Test query entry, result rendering, and no-results behavior.")
    if "settings" in workflows:
        targets.append("Validate settings forms, save actions, and persistence after refresh.")
    if "checkout" in workflows:
        targets.append("Cover cart, checkout, and confirmation states with careful assertions.")
    if "data-management" in features:
        targets.append("Exercise tables/lists for load, filtering, sorting, and row actions.")
    if test_assets:
        targets.append("Reuse existing test routes, fixtures, or selectors already present in the repo.")
    if memory.get("environment_hints"):
        targets.append("Confirm required environment configuration before running browser sanity flows.")
    if not targets:
        targets.append("Start with homepage load, primary navigation, and one critical happy-path workflow.")
    return targets[:12]


def build_repo_summary(memory: dict) -> str:
    tech_stack = ", ".join(memory.get("tech_stack", [])) or "an unknown stack"
    workflows = ", ".join(sorted(memory.get("workflow_hints", {}).keys())) or "no clear workflow hints yet"
    surfaces = ", ".join(memory.get("primary_surfaces", [])) or "no primary surfaces identified yet"
    return (
        f"{memory.get('app_name') or memory.get('repo_name', 'This repository')} appears to use {tech_stack}. "
        f"Detected workflows: {workflows}. Main surfaces: {surfaces}."
    )


def build_testing_guidance(memory: dict) -> list[str]:
    guidance = list(memory.get("testing_targets", []))
    if memory.get("route_hints"):
        guidance.append("Use route hints to map browser pages back to likely source files during failures.")
    if memory.get("manual_notes"):
        guidance.append("Review persistent manual notes before rerunning a flaky or business-critical flow.")
    return guidance[:15]


def build_learned_notes(previous: dict, current: dict, delta: dict[str, list[str]], focus: str) -> list[dict]:
    notes = list(previous.get("learned_notes", []))
    existing_text = {note.get("note", "") for note in notes}
    generated: list[dict] = []

    for stack_item in current.get("tech_stack", []):
        if stack_item not in previous.get("tech_stack", []):
            generated.append(
                {
                    "category": "stack",
                    "note": f"Detected {stack_item} in the target application.",
                    "evidence": stack_item,
                    "added_at": utc_now_iso(),
                }
            )

    for workflow in current.get("workflow_hints", {}):
        if workflow not in previous.get("workflow_hints", {}):
            generated.append(
                {
                    "category": "workflow",
                    "note": f"Found a likely {workflow} workflow in the repo.",
                    "evidence": ", ".join(current["workflow_hints"][workflow][:3]),
                    "added_at": utc_now_iso(),
                }
            )

    if delta.get("changed_files") or delta.get("new_files") or delta.get("removed_files"):
        changed_summary = (
            f"Sync observed {len(delta.get('new_files', []))} new, "
            f"{len(delta.get('changed_files', []))} changed, and "
            f"{len(delta.get('removed_files', []))} removed files."
        )
        generated.append(
            {
                "category": "sync",
                "note": changed_summary,
                "evidence": focus or "full-repo scan",
                "added_at": utc_now_iso(),
            }
        )

    for note in generated:
        if note["note"] not in existing_text:
            notes.append(note)
            existing_text.add(note["note"])

    return notes[-40:]


def build_sync_history(previous: dict, sync_entry: dict) -> list[dict]:
    history = list(previous.get("sync_history", []))
    history.append(sync_entry)
    return history[-20:]


def build_memory_markdown(memory: dict) -> str:
    lines = [
        f"# App Understanding Map: {memory.get('app_name') or memory.get('repo_name')}",
        "",
        f"- Repo Path: `{memory.get('repo_path', '')}`",
        f"- Repo ID: `{memory.get('repo_id', '')}`",
        f"- Last Synced At: `{memory.get('last_synced_at', '')}`",
        f"- Sync Runs: `{memory.get('sync_runs', 0)}`",
        "",
        "## Summary",
        "",
        memory.get("summary", "No summary yet."),
        "",
        "## Tech Stack",
        "",
    ]

    for item in memory.get("tech_stack", []):
        lines.append(f"- {item}")

    lines.extend(["", "## Entrypoints", ""])
    for item in memory.get("entrypoints", []):
        lines.append(f"- `{item}`")

    lines.extend(["", "## Route Hints", ""])
    for item in memory.get("route_hints", []):
        lines.append(f"- `{item}`")

    lines.extend(["", "## Workflow Hints", ""])
    for workflow, hints in memory.get("workflow_hints", {}).items():
        lines.append(f"### {workflow.title()}")
        lines.append("")
        for hint in hints:
            lines.append(f"- `{hint}`")
        lines.append("")

    lines.extend(["## Feature Hints", ""])
    for feature, hints in memory.get("feature_hints", {}).items():
        lines.append(f"### {feature.title()}")
        lines.append("")
        for hint in hints:
            lines.append(f"- `{hint}`")
        lines.append("")

    lines.extend(["## Environment Hints", ""])
    for item in memory.get("environment_hints", []):
        lines.append(f"- `{item}`")

    lines.extend(["", "## Existing Test Assets", ""])
    for item in memory.get("test_asset_hints", []):
        lines.append(f"- `{item}`")

    lines.extend(["", "## Testing Targets", ""])
    for item in memory.get("testing_targets", []):
        lines.append(f"- {item}")

    lines.extend(["", "## Testing Guidance", ""])
    for item in memory.get("testing_guidance", []):
        lines.append(f"- {item}")

    lines.extend(["", "## Learned Notes", ""])
    for note in memory.get("learned_notes", []):
        evidence = note.get("evidence")
        line = f"- [{note.get('category', 'note')}] {note.get('note', '')}"
        if evidence:
            line += f" (`{evidence}`)"
        lines.append(line)

    lines.extend(["", "## Manual Notes", ""])
    for note in memory.get("manual_notes", []):
        lines.append(f"- [{note.get('category', 'note')}] {note.get('note', '')}")

    lines.extend(["", "## Sync History", ""])
    for sync_entry in reversed(memory.get("sync_history", [])[-10:]):
        lines.append(
            "- "
            f"{sync_entry.get('synced_at', '')}: scanned {sync_entry.get('scanned_files_count', 0)} files, "
            f"{sync_entry.get('changed_files_count', 0)} changed, "
            f"{sync_entry.get('new_files_count', 0)} new, "
            f"{sync_entry.get('removed_files_count', 0)} removed"
            + (f" (focus: {sync_entry.get('focus')})" if sync_entry.get("focus") else "")
        )

    return "\n".join(lines).strip() + "\n"
