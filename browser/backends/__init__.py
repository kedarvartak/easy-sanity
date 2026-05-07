"""Browser backend implementations."""

from browser.backends.base import BrowserBackend, BrowserEventHooks
from browser.backends.factory import (
    BrowserBackendConfigurationError,
    BrowserBackendError,
    BrowserBackendUnavailableError,
    create_backend,
)
from browser.backends.playwright_backend import PlaywrightBackend

__all__ = [
    "BrowserBackend",
    "BrowserBackendConfigurationError",
    "BrowserBackendError",
    "BrowserBackendUnavailableError",
    "BrowserEventHooks",
    "PlaywrightBackend",
    "create_backend",
]
