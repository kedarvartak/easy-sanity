from __future__ import annotations

from dataclasses import dataclass

from browser.backends.base import BrowserBackend, BrowserEventHooks
from config.settings import (
    browser_harness_autolaunch,
    browser_harness_browser_path,
    browser_harness_command,
    browser_harness_cdp_url,
    browser_harness_cdp_ws,
    browser_harness_debugging_port,
    browser_harness_enabled,
    browser_harness_repo,
    browser_harness_status,
    browser_harness_user_data_dir,
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
        try:
            from browser.backends.playwright_backend import PlaywrightBackend
        except ModuleNotFoundError as exc:
            raise BrowserBackendUnavailableError(
                "playwright backend is selected but Playwright is not installed. "
                "Install the project dependencies and run easy-sanity install-browser."
            ) from exc
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

        from browser.backends.browser_harness_backend import BrowserHarnessBackend

        return BackendSelection(
            name=resolved,
            backend=BrowserHarnessBackend(
                command=command,
                repo=repo,
                cdp_url=browser_harness_cdp_url(),
                cdp_ws=browser_harness_cdp_ws(),
                auto_launch=browser_harness_autolaunch(),
                browser_path=browser_harness_browser_path(),
                user_data_dir=browser_harness_user_data_dir(),
                debugging_port=browser_harness_debugging_port(),
            ),
        )

    raise BrowserBackendConfigurationError(f"Unsupported browser backend: {name}")
