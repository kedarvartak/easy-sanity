from __future__ import annotations

import argparse
import subprocess
import sys

from config.settings import (
    app_home_dir,
    app_memory_dir,
    downloads_dir,
    ensure_runtime_layout,
    reports_dir,
    screenshots_dir,
)
from easy_sanity.server import run_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="easy-sanity",
        description="Easy Sanity MCP server and helper utilities.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("serve", help="Start the Easy Sanity MCP server.")
    subparsers.add_parser("install-browser", help="Install the Playwright Chromium browser.")
    subparsers.add_parser("paths", help="Print runtime data and artifact paths.")

    return parser


def print_paths() -> None:
    ensure_runtime_layout()
    print(f"home={app_home_dir()}")
    print(f"reports={reports_dir()}")
    print(f"screenshots={screenshots_dir()}")
    print(f"downloads={downloads_dir()}")
    print(f"app_memory={app_memory_dir()}")


def install_browser() -> int:
    result = subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command or "serve"

    if command == "serve":
        run_server()
        return 0
    if command == "install-browser":
        return install_browser()
    if command == "paths":
        print_paths()
        return 0

    parser.error(f"Unknown command: {command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
