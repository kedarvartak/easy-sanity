import os
from pathlib import Path


ROOT_DIR = Path(__file__).parent
SAMPLE_TASKS_FILE = ROOT_DIR / "sample_tasks.json"


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
