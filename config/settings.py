import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
SAMPLE_TASKS_FILE = DATA_DIR / "sample_tasks.json"
TASKS_FILE = DATA_DIR / "tasks.json"
PROFILES_FILE = DATA_DIR / "profiles.json"


def browser_headless_default() -> bool:
    value = os.environ.get("BROWSER_HEADLESS_DEFAULT", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def browser_default_timeout_ms() -> int:
    raw = os.environ.get("BROWSER_DEFAULT_TIMEOUT_MS", "30000").strip()
    try:
        timeout = int(raw)
    except ValueError:
        return 30000
    return max(1000, timeout)


def reports_dir() -> Path:
    raw = os.environ.get("BROWSER_REPORTS_DIR", "").strip()
    if raw:
        path = Path(raw).expanduser()
        return path if path.is_absolute() else ROOT_DIR / path
    return ROOT_DIR / "artifacts" / "reports"


def screenshots_dir() -> Path:
    raw = os.environ.get("BROWSER_SCREENSHOTS_DIR", "").strip()
    if raw:
        path = Path(raw).expanduser()
        return path if path.is_absolute() else ROOT_DIR / path
    return ROOT_DIR / "artifacts" / "screenshots"
