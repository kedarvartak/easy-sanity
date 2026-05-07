from pathlib import Path
from typing import Optional

from playwright.async_api import Browser, Page

from browser.backends import BrowserBackend, BrowserEventHooks, PlaywrightBackend
from browser.report_manager import ensure_directory, report_filename, slugify, utc_timestamp_slug
from config.settings import downloads_dir, reports_dir, screenshots_dir


class BrowserState:
    """Manages browser lifecycle across tool calls."""

    def __init__(self):
        self.backend: BrowserBackend = PlaywrightBackend(
            BrowserEventHooks(
                on_console=self._handle_console_message,
                on_request=self._handle_request_started,
                on_response=self._handle_response_received,
                on_request_failed=self._handle_request_failed,
            )
        )
        self.task_description: str = ""
        self.action_history: list = []
        self.session_slug: str = ""
        self.started_at: str = ""
        self.report_path: Optional[Path] = None
        self.screenshots_root: Optional[Path] = None
        self.downloads_root: Optional[Path] = None
        self.step_counter: int = 0
        self.last_domain_summary: Optional[dict] = None
        self.console_logs: list[dict] = []
        self.network_requests: list[dict] = []
        self.failed_requests: list[dict] = []

    async def initialize(self, headless: bool = False):
        await self.backend.initialize(headless=headless)

    @property
    def browser(self) -> Browser | None:
        return self.backend.browser

    @property
    def page(self) -> Page | None:
        return self.backend.page

    def set_active_page(self, page: Page) -> None:
        self.backend.set_active_page(page)

    def list_pages(self) -> list[Page]:
        return self.backend.list_pages()

    async def new_page(self) -> Page:
        return await self.backend.new_page()

    async def get_cookies(self) -> list[dict]:
        return await self.backend.get_cookies()

    def _handle_console_message(self, message) -> None:
        entry = {
            "type": message.type,
            "text": message.text,
            "location": message.location,
        }
        self.console_logs.append(entry)
        self.console_logs = self.console_logs[-200:]

    def _handle_request_started(self, request) -> None:
        entry = {
            "event": "request",
            "method": request.method,
            "url": request.url,
            "resource_type": request.resource_type,
        }
        self.network_requests.append(entry)
        self.network_requests = self.network_requests[-500:]

    def _handle_response_received(self, response) -> None:
        request = response.request
        entry = {
            "event": "response",
            "method": request.method,
            "url": response.url,
            "resource_type": request.resource_type,
            "status": response.status,
            "ok": response.ok,
        }
        self.network_requests.append(entry)
        self.network_requests = self.network_requests[-500:]

    def _handle_request_failed(self, request) -> None:
        failure = request.failure
        if isinstance(failure, str):
            failure_text = failure
        elif failure:
            failure_text = getattr(failure, "error_text", str(failure))
        else:
            failure_text = "unknown failure"
        entry = {
            "event": "requestfailed",
            "method": request.method,
            "url": request.url,
            "resource_type": request.resource_type,
            "failure_text": failure_text,
        }
        self.failed_requests.append(entry)
        self.failed_requests = self.failed_requests[-200:]
        self.network_requests.append(entry)
        self.network_requests = self.network_requests[-500:]

    def begin_session(self, task: str) -> None:
        timestamp = utc_timestamp_slug()
        task_slug = slugify(task or "browser-session", default="browser-session")
        self.session_slug = f"{timestamp}-{task_slug}"
        self.started_at = timestamp
        self.report_path = ensure_directory(reports_dir()) / report_filename(self.session_slug)
        self.screenshots_root = ensure_directory(screenshots_dir()) / self.session_slug
        self.downloads_root = ensure_directory(downloads_dir()) / self.session_slug
        ensure_directory(self.screenshots_root)
        ensure_directory(self.downloads_root)
        self.step_counter = 0
        self.console_logs = []
        self.network_requests = []
        self.failed_requests = []
        self.last_domain_summary = None

    async def cleanup(self):
        await self.backend.cleanup()
        self.action_history = []
        self.task_description = ""
        self.session_slug = ""
        self.started_at = ""
        self.report_path = None
        self.screenshots_root = None
        self.downloads_root = None
        self.step_counter = 0
        self.last_domain_summary = None
        self.console_logs = []
        self.network_requests = []
        self.failed_requests = []
