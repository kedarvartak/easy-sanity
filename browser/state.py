from pathlib import Path
from typing import TYPE_CHECKING, Optional

from browser.backends import BrowserBackend, BrowserEventHooks, create_backend
from browser.backends.browser_harness_backend import BrowserHarnessBackend
from browser.report_manager import ensure_directory, report_filename, slugify, utc_timestamp_slug
from config.settings import browser_backend_default
from config.settings import downloads_dir, reports_dir, screenshots_dir

if TYPE_CHECKING:
    from playwright.async_api import Browser, Page
else:
    Browser = Page = object


class BrowserState:
    """Manages browser lifecycle across tool calls."""

    def __init__(self):
        self.backend: BrowserBackend | BrowserHarnessBackend | None = None
        self.backend_name: str = browser_backend_default()
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

    async def initialize(self, headless: bool = False, backend_name: Optional[str] = None):
        self.ensure_backend(backend_name)
        if not self.backend:
            raise RuntimeError("No browser backend is configured.")
        await self.backend.initialize(headless=headless)

    def ensure_backend(self, backend_name: Optional[str] = None) -> str:
        target_backend = backend_name or browser_backend_default()
        if self.backend and target_backend == self.backend_name:
            return self.backend_name

        if self.page:
            raise RuntimeError(
                f"Cannot switch browser backend from '{self.backend_name}' to '{target_backend}' while a session is active. "
                "Call browser_stop first."
            )

        selection = create_backend(target_backend, self._event_hooks())
        self.backend = selection.backend
        self.backend_name = selection.name
        return self.backend_name

    @property
    def browser(self) -> Browser | None:
        if not self.backend:
            return None
        return self.backend.browser

    @property
    def page(self) -> Page | None:
        if not self.backend:
            return None
        return self.backend.page

    def has_active_session(self) -> bool:
        if self.page:
            return True
        if self.backend_name == "browser-harness" and isinstance(self.backend, BrowserHarnessBackend):
            return self.backend.initialized
        return False

    def is_browser_harness(self) -> bool:
        return self.backend_name == "browser-harness" and isinstance(self.backend, BrowserHarnessBackend)

    def harness_backend(self) -> BrowserHarnessBackend:
        if not self.is_browser_harness():
            raise RuntimeError("Active backend is not browser-harness.")
        assert isinstance(self.backend, BrowserHarnessBackend)
        return self.backend

    def set_active_page(self, page: Page) -> None:
        if not self.backend:
            raise RuntimeError("No browser backend is configured.")
        self.backend.set_active_page(page)

    def list_pages(self) -> list[Page]:
        if not self.backend:
            return []
        return self.backend.list_pages()

    async def new_page(self) -> Page:
        if not self.backend:
            raise RuntimeError("No browser backend is configured.")
        return await self.backend.new_page()

    async def get_cookies(self) -> list[dict]:
        if not self.backend:
            raise RuntimeError("No browser backend is configured.")
        return await self.backend.get_cookies()

    def _event_hooks(self) -> BrowserEventHooks:
        return BrowserEventHooks(
            on_console=self._handle_console_message,
            on_request=self._handle_request_started,
            on_response=self._handle_response_received,
            on_request_failed=self._handle_request_failed,
        )

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
        if self.backend:
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
