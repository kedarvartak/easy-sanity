from __future__ import annotations

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from config.settings import app_memory_dir
from memory.store import (
    build_memory_markdown,
    build_learned_notes,
    build_repo_manifest,
    build_repo_summary,
    build_sync_history,
    build_testing_guidance,
    extract_readme_summary,
    infer_entrypoints,
    infer_feature_hints,
    infer_env_hints,
    infer_primary_surfaces,
    infer_route_hints,
    infer_tech_stack,
    infer_test_assets,
    infer_testing_targets,
    infer_workflows,
    load_repo_memory,
    read_text_excerpt,
    repo_memory_json_path,
    repo_memory_markdown_path,
    repo_memory_id,
    select_sync_files,
    save_repo_memory,
    utc_now_iso,
    write_repo_memory_markdown,
)


def register_memory_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def app_memory_sync(repo_path: str, app_name: str = "", focus: str = "", max_files: int = 250) -> str:
        """
        Scan a target application repo and persist an understanding map for future sanity testing runs.

        Args:
            repo_path: Local filesystem path to the application repo being tested.
            app_name: Optional friendly application name.
            focus: Optional sync focus such as "auth flow" or "dashboard workflows".
            max_files: Max number of files to scan during this sync.

        Returns:
            Persistent memory summary plus output paths for the saved memory files.
        """
        root = Path(repo_path).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            return json.dumps(
                {"status": "error", "message": f"Repo path '{repo_path}' is not a readable directory."},
                indent=2,
            )

        previous = load_repo_memory(str(root))
        previous_manifest = previous.get("repo_snapshot", {}).get("manifest", {})
        current_manifest = build_repo_manifest(root)
        files, delta = select_sync_files(
            root,
            current_manifest=current_manifest,
            previous_manifest=previous_manifest,
            max_files=max_files,
            focus=focus,
        )
        relative_paths = [str(path.relative_to(root)) for path in files]
        file_contents: dict[str, str] = {}
        for path in files:
            excerpt = read_text_excerpt(path)
            if excerpt:
                file_contents[str(path.relative_to(root))] = excerpt

        tech_stack = infer_tech_stack(relative_paths, file_contents)
        entrypoints = infer_entrypoints(relative_paths)
        route_hints = infer_route_hints(relative_paths)
        workflow_hints = infer_workflows(relative_paths, file_contents)
        feature_hints = infer_feature_hints(relative_paths, file_contents)
        environment_hints = infer_env_hints(file_contents)
        readme_summary = extract_readme_summary(file_contents)
        test_asset_hints = infer_test_assets(relative_paths, file_contents)

        sync_runs = int(previous.get("sync_runs", 0)) + 1
        memory = {
            "repo_id": repo_memory_id(str(root)),
            "repo_path": str(root),
            "repo_name": root.name,
            "app_name": app_name or previous.get("app_name") or root.name,
            "focus": focus or previous.get("focus", ""),
            "sync_runs": sync_runs,
            "last_synced_at": utc_now_iso(),
            "tech_stack": sorted(set(previous.get("tech_stack", []) + tech_stack)),
            "entrypoints": sorted(set(previous.get("entrypoints", []) + entrypoints))[:20],
            "route_hints": sorted(set(previous.get("route_hints", []) + route_hints))[:40],
            "workflow_hints": {
                key: sorted(set(previous.get("workflow_hints", {}).get(key, []) + workflow_hints.get(key, [])))[:15]
                for key in sorted(set(previous.get("workflow_hints", {})) | set(workflow_hints))
            },
            "feature_hints": {
                key: sorted(set(previous.get("feature_hints", {}).get(key, []) + feature_hints.get(key, [])))[:12]
                for key in sorted(set(previous.get("feature_hints", {})) | set(feature_hints))
            },
            "environment_hints": sorted(set(previous.get("environment_hints", []) + environment_hints))[:40],
            "readme_summary": readme_summary or previous.get("readme_summary", ""),
            "test_asset_hints": sorted(set(previous.get("test_asset_hints", []) + test_asset_hints))[:25],
            "manual_notes": previous.get("manual_notes", []),
            "scanned_files_count": len(relative_paths),
            "sample_files": relative_paths[:40],
            "repo_snapshot": {
                "tracked_files_count": len(current_manifest),
                "manifest": current_manifest,
                "last_delta": delta,
            },
        }
        memory["primary_surfaces"] = infer_primary_surfaces(
            memory.get("route_hints", []),
            memory.get("workflow_hints", {}),
            memory.get("feature_hints", {}),
        )
        memory["testing_targets"] = infer_testing_targets(memory)
        memory["summary"] = build_repo_summary(memory)
        memory["testing_guidance"] = build_testing_guidance(memory)
        memory["learned_notes"] = build_learned_notes(previous, memory, delta, focus)
        memory["sync_history"] = build_sync_history(
            previous,
            {
                "synced_at": memory["last_synced_at"],
                "focus": focus,
                "scanned_files_count": len(relative_paths),
                "new_files_count": len(delta.get("new_files", [])),
                "changed_files_count": len(delta.get("changed_files", [])),
                "removed_files_count": len(delta.get("removed_files", [])),
            },
        )

        save_repo_memory(str(root), memory)
        write_repo_memory_markdown(str(root), build_memory_markdown(memory))

        return json.dumps(
            {
                "status": "success",
                "repo_id": memory["repo_id"],
                "repo_path": str(root),
                "app_name": memory["app_name"],
                "summary": memory["summary"],
                "tech_stack": memory["tech_stack"],
                "workflow_hints": memory["workflow_hints"],
                "feature_hints": memory["feature_hints"],
                "testing_guidance": memory["testing_guidance"],
                "testing_targets": memory["testing_targets"],
                "sync_runs": sync_runs,
                "sync_delta": {
                    "new_files_count": len(delta.get("new_files", [])),
                    "changed_files_count": len(delta.get("changed_files", [])),
                    "removed_files_count": len(delta.get("removed_files", [])),
                },
                "memory_json_path": str(repo_memory_json_path(str(root))),
                "memory_markdown_path": str(repo_memory_markdown_path(str(root))),
            },
            indent=2,
        )

    @mcp.tool()
    def app_memory_get(repo_path: str) -> str:
        """
        Retrieve the persisted understanding map for a previously synced application repo.

        Args:
            repo_path: Local filesystem path to the application repo being tested.

        Returns:
            Current persisted repo memory and artifact file paths.
        """
        root = Path(repo_path).expanduser().resolve()
        memory = load_repo_memory(str(root))
        if not memory:
            return json.dumps(
                {"status": "error", "message": f"No memory found yet for '{root}'. Run app_memory_sync first."},
                indent=2,
            )

        return json.dumps(
            {
                "status": "success",
                "repo_id": memory.get("repo_id"),
                "repo_path": str(root),
                "app_name": memory.get("app_name"),
                "summary": memory.get("summary"),
                "tech_stack": memory.get("tech_stack", []),
                "entrypoints": memory.get("entrypoints", []),
                "route_hints": memory.get("route_hints", []),
                "workflow_hints": memory.get("workflow_hints", {}),
                "feature_hints": memory.get("feature_hints", {}),
                "environment_hints": memory.get("environment_hints", []),
                "test_asset_hints": memory.get("test_asset_hints", []),
                "testing_targets": memory.get("testing_targets", []),
                "testing_guidance": memory.get("testing_guidance", []),
                "learned_notes": memory.get("learned_notes", []),
                "manual_notes": memory.get("manual_notes", []),
                "sync_history": memory.get("sync_history", []),
                "memory_json_path": str(repo_memory_json_path(str(root))),
                "memory_markdown_path": str(repo_memory_markdown_path(str(root))),
            },
            indent=2,
        )

    @mcp.tool()
    def app_memory_add_note(repo_path: str, note: str, category: str = "workflow") -> str:
        """
        Add a persistent manual note to the repo understanding map.

        Args:
            repo_path: Local filesystem path to the application repo being tested.
            note: Observation, workflow note, or domain understanding to persist.
            category: Optional category such as workflow, feature, auth, routing, or testing.

        Returns:
            Confirmation that the note was persisted.
        """
        root = Path(repo_path).expanduser().resolve()
        memory = load_repo_memory(str(root))
        if not memory:
            return json.dumps(
                {"status": "error", "message": f"No memory found yet for '{root}'. Run app_memory_sync first."},
                indent=2,
            )

        memory.setdefault("manual_notes", []).append(
            {
                "category": category,
                "note": note,
                "added_at": utc_now_iso(),
            }
        )
        memory["testing_guidance"] = build_testing_guidance(memory)
        save_repo_memory(str(root), memory)
        write_repo_memory_markdown(str(root), build_memory_markdown(memory))
        return json.dumps(
            {
                "status": "success",
                "message": "Memory note saved.",
                "repo_path": str(root),
                "category": category,
                "note": note,
            },
            indent=2,
        )

    @mcp.tool()
    def app_memory_testing_brief(repo_path: str, goal: str = "") -> str:
        """
        Generate a concise testing brief from persisted repo understanding memory.

        Args:
            repo_path: Local filesystem path to the application repo being tested.
            goal: Optional testing goal such as "login sanity" or "dashboard smoke".

        Returns:
            Focused testing guidance derived from the repo memory map.
        """
        root = Path(repo_path).expanduser().resolve()
        memory = load_repo_memory(str(root))
        if not memory:
            return json.dumps(
                {"status": "error", "message": f"No memory found yet for '{root}'. Run app_memory_sync first."},
                indent=2,
            )

        focus_lines = list(memory.get("testing_guidance", []))
        if goal:
            focus_lines.insert(0, f"Requested goal: {goal}")

        if memory.get("testing_targets"):
            focus_lines.append("Priority test targets:")
            focus_lines.extend([f"- {item}" for item in memory["testing_targets"][:8]])

        if memory.get("route_hints"):
            focus_lines.append("Relevant route/file hints:")
            focus_lines.extend([f"- {path}" for path in memory["route_hints"][:10]])

        if memory.get("learned_notes"):
            focus_lines.append("Learned notes:")
            focus_lines.extend(
                [
                    f"- [{note.get('category', 'note')}] {note.get('note', '')}"
                    for note in memory["learned_notes"][-6:]
                ]
            )

        if memory.get("manual_notes"):
            focus_lines.append("Persistent notes:")
            focus_lines.extend(
                [f"- [{note.get('category', 'note')}] {note.get('note', '')}" for note in memory["manual_notes"][-8:]]
            )

        return json.dumps(
            {
                "status": "success",
                "repo_path": str(root),
                "app_name": memory.get("app_name"),
                "goal": goal or None,
                "summary": memory.get("summary"),
                "testing_brief": focus_lines,
                "memory_markdown_path": str(repo_memory_markdown_path(str(root))),
            },
            indent=2,
        )

    @mcp.tool()
    def app_memory_list() -> str:
        """
        List every persisted application memory map available to the agent.

        Returns:
            Repo memories currently stored under the configured app-memory directory.
        """
        memory_root = app_memory_dir()
        memory_root.mkdir(parents=True, exist_ok=True)
        items = []
        for path in sorted(memory_root.iterdir()):
            memory_path = path / "memory.json"
            if not memory_path.exists():
                continue
            try:
                memory = json.loads(memory_path.read_text())
            except Exception:
                continue
            items.append(
                {
                    "repo_id": memory.get("repo_id"),
                    "app_name": memory.get("app_name"),
                    "repo_path": memory.get("repo_path"),
                    "sync_runs": memory.get("sync_runs", 0),
                    "last_synced_at": memory.get("last_synced_at"),
                    "memory_markdown_path": str(path / "memory.md"),
                }
            )

        return json.dumps({"status": "success", "items": items}, indent=2)
