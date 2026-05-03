from pathlib import Path
from typing import Optional

from playwright.async_api import Browser, Page, async_playwright

from browser.report_manager import ensure_directory, report_filename, slugify, utc_timestamp_slug
from config.settings import browser_default_timeout_ms, reports_dir, screenshots_dir


class BrowserState:
    """Manages browser lifecycle across tool calls."""

    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.task_description: str = ""
        self.action_history: list = []
        self.session_slug: str = ""
        self.started_at: str = ""
        self.report_path: Optional[Path] = None
        self.screenshots_root: Optional[Path] = None
        self.step_counter: int = 0
        self.last_domain_summary: Optional[dict] = None

    async def initialize(self, headless: bool = False):
        if self.browser is None:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=headless)
            self.page = await self.browser.new_page()
            self.page.set_default_timeout(browser_default_timeout_ms())

    def begin_session(self, task: str) -> None:
        timestamp = utc_timestamp_slug()
        task_slug = slugify(task or "browser-session", default="browser-session")
        self.session_slug = f"{timestamp}-{task_slug}"
        self.started_at = timestamp
        self.report_path = ensure_directory(reports_dir()) / report_filename(self.session_slug)
        self.screenshots_root = ensure_directory(screenshots_dir()) / self.session_slug
        ensure_directory(self.screenshots_root)
        self.step_counter = 0

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
        self.session_slug = ""
        self.started_at = ""
        self.report_path = None
        self.screenshots_root = None
        self.step_counter = 0
        self.last_domain_summary = None
