from __future__ import annotations

from dataclasses import dataclass

from browser.backends.base import BrowserBackend, BrowserEventHooks
from browser.backends.playwright_backend import PlaywrightBackend
from config.settings import (
    browser_harness_command,
    browser_harness_enabled,
    browser_harness_repo,
    browser_harness_status,
    normalize_browser_backend,
)


class BrowserBackendError(RuntimeError):
    """Base error for backend selection and startup."""


class BrowserBackendConfigurationError(BrowserBackendError):
    """Raised when backend configuration is invalid."""


class BrowserBackendUnavailableError(BrowserBackendError):
    """Raised when a selected backend is not available."""


@dataclass(slots=True)
class BackendSelection:
    name: str
    backend: BrowserBackend


def create_backend(name: str, hooks: BrowserEventHooks) -> BackendSelection:
    resolved = normalize_browser_backend(name)

    if resolved == "playwright":
        return BackendSelection(name=resolved, backend=PlaywrightBackend(hooks))

    if resolved == "browser-harness":
        if not browser_harness_enabled():
            raise BrowserBackendUnavailableError(
                "browser-harness backend is disabled. "
                "Set BROWSER_HARNESS_ENABLED=true to allow real-browser attach mode."
            )

        status = browser_harness_status()
        command = browser_harness_command()
        repo = browser_harness_repo()
        if not status["available"]:
            raise BrowserBackendUnavailableError(
                "browser-harness backend is selected but not available. "
                f"Command '{command}' was not found on PATH. "
                f"Install it from {repo} and configure Chrome per the upstream install.md instructions."
            )

        raise BrowserBackendUnavailableError(
            "browser-harness backend is detected but not implemented in Easy Sanity yet. "
            "Phase 3 will add the runtime adapter."
        )

    raise BrowserBackendConfigurationError(f"Unsupported browser backend: {name}")
