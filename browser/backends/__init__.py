"""Browser backend implementations."""

from browser.backends.base import BrowserBackend, BrowserEventHooks
from browser.backends.factory import (
    BrowserBackendConfigurationError,
    BrowserBackendError,
    BrowserBackendUnavailableError,
    create_backend,
)

__all__ = [
    "BrowserBackend",
    "BrowserBackendConfigurationError",
    "BrowserBackendError",
    "BrowserBackendUnavailableError",
    "BrowserEventHooks",
    "create_backend",
]
