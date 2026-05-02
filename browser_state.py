from typing import Optional

from playwright.async_api import Browser, Page, async_playwright


class BrowserState:
    """Manages browser lifecycle across tool calls."""

    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.task_description: str = ""
        self.action_history: list = []

    async def initialize(self, headless: bool = False):
        if self.browser is None:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=headless)
            self.page = await self.browser.new_page()
            self.page.set_default_timeout(30000)

    async def cleanup(self):
        if self.page:
            await self.page.close()
            self.page = None
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        self.action_history = []
        self.task_description = ""
