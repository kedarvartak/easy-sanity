from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol


EventHandler = Callable[[Any], None]


@dataclass(slots=True)
class BrowserEventHooks:
    """Callbacks a backend should attach to the active page."""

    on_console: EventHandler
    on_request: EventHandler
    on_response: EventHandler
    on_request_failed: EventHandler


class BrowserBackend(Protocol):
    """Common runtime interface for browser backends."""

    @property
    def browser(self) -> Any | None:
        ...

    @property
    def page(self) -> Any | None:
        ...

    async def initialize(self, *, headless: bool = False) -> None:
        ...

    def set_active_page(self, page: Any) -> None:
        ...

    def list_pages(self) -> list[Any]:
        ...

    async def new_page(self) -> Any:
        ...

    async def get_cookies(self) -> list[dict[str, Any]]:
        ...

    async def cleanup(self) -> None:
        ...
