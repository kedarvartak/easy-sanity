"""Browser backend implementations."""

from browser.backends.base import BrowserBackend, BrowserEventHooks
from browser.backends.playwright_backend import PlaywrightBackend

__all__ = ["BrowserBackend", "BrowserEventHooks", "PlaywrightBackend"]
