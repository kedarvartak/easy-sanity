import os
from importlib.resources import files
from pathlib import Path

from platformdirs import user_data_dir


APP_NAME = "easy-sanity"
ROOT_DIR = Path(__file__).resolve().parent.parent


def _is_source_checkout() -> bool:
    return (
        (ROOT_DIR / "pyproject.toml").exists()
        and (ROOT_DIR / "main.py").exists()
        and (ROOT_DIR / "browser").is_dir()
        and (ROOT_DIR / "tasks").is_dir()
    )


def _installed_home_dir() -> Path:
    raw = os.environ.get("EASY_SANITY_HOME", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return Path(user_data_dir(APP_NAME, appauthor=False))


def app_home_dir() -> Path:
    return ROOT_DIR if _is_source_checkout() else _installed_home_dir()


def runtime_root_dir() -> Path:
    return app_home_dir()


def data_dir() -> Path:
    return runtime_root_dir() / "data"


def artifacts_dir() -> Path:
    return runtime_root_dir() / "artifacts"


def sample_tasks_resource_text() -> str:
    source_file = ROOT_DIR / "data" / "sample_tasks.json"
    if source_file.exists():
        return source_file.read_text(encoding="utf-8")
    return files("easy_sanity.resources").joinpath("sample_tasks.json").read_text(encoding="utf-8")


TASKS_FILE = data_dir() / "tasks.json"
PROFILES_FILE = data_dir() / "profiles.json"


def _resolve_runtime_path(raw: str, default: Path) -> Path:
    value = raw.strip()
    if not value:
        return default

    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return Path.cwd() / path


def ensure_runtime_layout() -> None:
    data_dir().mkdir(parents=True, exist_ok=True)
    reports_dir().mkdir(parents=True, exist_ok=True)
    screenshots_dir().mkdir(parents=True, exist_ok=True)
    downloads_dir().mkdir(parents=True, exist_ok=True)
    app_memory_dir().mkdir(parents=True, exist_ok=True)


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
    return _resolve_runtime_path(
        os.environ.get("BROWSER_REPORTS_DIR", ""),
        artifacts_dir() / "reports",
    )


def screenshots_dir() -> Path:
    return _resolve_runtime_path(
        os.environ.get("BROWSER_SCREENSHOTS_DIR", ""),
        artifacts_dir() / "screenshots",
    )


def downloads_dir() -> Path:
    return _resolve_runtime_path(
        os.environ.get("BROWSER_DOWNLOADS_DIR", ""),
        artifacts_dir() / "downloads",
    )


def app_memory_dir() -> Path:
    return _resolve_runtime_path(
        os.environ.get("APP_MEMORY_DIR", ""),
        data_dir() / "app_memory",
    )
