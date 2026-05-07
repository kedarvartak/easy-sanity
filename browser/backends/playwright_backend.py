from __future__ import annotations

from typing import Any, Optional

from playwright.async_api import Browser, Page, async_playwright

from browser.backends.base import BrowserEventHooks
from config.settings import browser_default_timeout_ms


class PlaywrightBackend:
    """Default browser runtime backed by Playwright Chromium."""

    def __init__(self, hooks: BrowserEventHooks):
        self._hooks = hooks
        self.playwright = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

    @property
    def browser(self) -> Browser | None:
        return self._browser

    @property
    def page(self) -> Page | None:
        return self._page

    async def initialize(self, *, headless: bool = False) -> None:
        if self._browser is None:
            self.playwright = await async_playwright().start()
            self._browser = await self.playwright.chromium.launch(headless=headless)
            page = await self._browser.new_page()
            self.set_active_page(page)

    def set_active_page(self, page: Page) -> None:
        self._page = page
        self._page.set_default_timeout(browser_default_timeout_ms())
        self._attach_page_listeners(page)

    def list_pages(self) -> list[Page]:
        if not self._page:
            return []
        return list(self._page.context.pages)

    async def new_page(self) -> Page:
        if not self._page:
            raise RuntimeError("Browser not started")
        page = await self._page.context.new_page()
        self.set_active_page(page)
        return page

    async def get_cookies(self) -> list[dict[str, Any]]:
        if not self._page:
            raise RuntimeError("Browser not started")
        return await self._page.context.cookies()

    async def cleanup(self) -> None:
        if self._page:
            await self._page.close()
            self._page = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

    def _attach_page_listeners(self, page: Page) -> None:
        page.on("console", self._hooks.on_console)
        page.on("request", self._hooks.on_request)
        page.on("response", self._hooks.on_response)
        page.on("requestfailed", self._hooks.on_request_failed)
