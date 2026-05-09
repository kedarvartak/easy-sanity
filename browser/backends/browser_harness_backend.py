from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import textwrap
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

from browser.domain import DOMAIN_SUMMARY_SCRIPT


class BrowserHarnessBackend:
    """Minimal runtime adapter for the upstream browser-harness command."""

    def __init__(
        self,
        command: str,
        repo: str,
        *,
        cdp_url: str = "",
        cdp_ws: str = "",
        auto_launch: bool = True,
        browser_path: str = "",
        user_data_dir: Path | None = None,
        debugging_port: int = 9222,
    ):
        self.command = command
        self.repo = repo
        self.cdp_url = cdp_url
        self.cdp_ws = cdp_ws
        self.auto_launch = auto_launch
        self.browser_path = browser_path
        self.user_data_dir = user_data_dir
        self.debugging_port = debugging_port
        self._initialized = False
        self._has_opened_tab = False
        self._browser_process: subprocess.Popen[str] | None = None
        self._effective_cdp_url = cdp_url
        self._headless = False

    @property
    def browser(self) -> None:
        return None

    @property
    def page(self) -> None:
        return None

    @property
    def initialized(self) -> bool:
        return self._initialized

    async def initialize(self, *, headless: bool = False) -> None:
        self._headless = headless
        await self._ensure_connection(headless=headless)
        await self._run_json(
            """
            info = page_info()
            if not isinstance(info, dict):
                info = {"page_info": str(info)}
            print(json.dumps(info))
            """
        )
        self._initialized = True

    def set_active_page(self, page: Any) -> None:
        del page
        raise RuntimeError("browser-harness manages the active tab externally.")

    def list_pages(self) -> list[Any]:
        return []

    async def new_page(self) -> Any:
        raise RuntimeError("browser-harness does not expose Page objects.")

    async def get_cookies(self) -> list[dict[str, Any]]:
        raise RuntimeError("browser-harness does not support browser_get_storage yet.")

    async def cleanup(self) -> None:
        self._initialized = False
        self._has_opened_tab = False
        if self._browser_process and self._browser_process.poll() is None:
            self._browser_process.terminate()
            try:
                self._browser_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._browser_process.kill()
                self._browser_process.wait(timeout=5)
        self._browser_process = None

    def connection_metadata(self) -> dict[str, Any]:
        if self.cdp_ws:
            return {
                "connection_mode": "explicit-cdp-ws",
                "session_profile": "external",
                "cdp_ws": self.cdp_ws,
            }
        if self.cdp_url:
            return {
                "connection_mode": "explicit-cdp-url",
                "session_profile": "external",
                "cdp_url": self.cdp_url,
            }
        return {
            "connection_mode": "auto-launched-chromium" if self.auto_launch else "local-profile-discovery",
            "session_profile": "isolated" if self.auto_launch else "user-profile",
            "cdp_url": self._effective_cdp_url or None,
            "user_data_dir": str(self.user_data_dir) if self.user_data_dir else None,
            "browser_path": self.browser_path or None,
        }

    async def navigate(self, url: str) -> dict[str, Any]:
        navigation_call = f"new_tab({json.dumps(url)})" if not self._has_opened_tab else f"goto({json.dumps(url)})"
        payload = await self._run_json(
            f"""
            {navigation_call}
            wait_for_load()
            info = page_info()
            if not isinstance(info, dict):
                info = {{"page_info": str(info)}}
            print(json.dumps(info))
            """
        )
        self._initialized = True
        self._has_opened_tab = True
        return payload

    async def get_state(self) -> dict[str, Any]:
        payload = await self._run_json(
            f"""
            import base64
            visible_text = js({json.dumps(self._visible_text_script())})
            interactive_elements = js({json.dumps(self._interactive_elements_script())})
            semantic_summary = js({json.dumps(f"({DOMAIN_SUMMARY_SCRIPT})()")})
            screenshot_path = capture_screenshot()
            info = page_info()
            if not isinstance(info, dict):
                info = {{"page_info": str(info)}}
            screenshot_b64 = base64.b64encode(open(screenshot_path, "rb").read()).decode("ascii")
            print(json.dumps({{
                "page": info,
                "visible_text": visible_text or "",
                "interactive_elements": interactive_elements or [],
                "semantic_summary": semantic_summary or {{}},
                "screenshot_base64": screenshot_b64,
            }}))
            """
        )
        self._initialized = True
        return payload

    async def click(
        self,
        *,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        element_index: Optional[int] = None,
    ) -> dict[str, Any]:
        payload = await self._run_json(
            f"""
            target = js({json.dumps(self._click_target_script(selector, text, element_index))})
            if not target:
                raise RuntimeError("Could not resolve a clickable target.")
            click_at_xy(target["x"], target["y"])
            wait_for_load()
            info = page_info()
            if not isinstance(info, dict):
                info = {{"page_info": str(info)}}
            print(json.dumps({{"page": info, "target": target}}))
            """
        )
        self._initialized = True
        return payload

    async def fill(self, *, field: str, text: str, press_enter: bool = False) -> dict[str, Any]:
        payload = await self._run_json(
            f"""
            field_result = js({json.dumps(self._fill_field_script(field, text, press_enter))})
            if not field_result or not field_result.get("ok"):
                raise RuntimeError(field_result.get("message", "Could not find a matching field."))
            info = page_info()
            if not isinstance(info, dict):
                info = {{"page_info": str(info)}}
            print(json.dumps({{"page": info, "field": field_result}}))
            """
        )
        self._initialized = True
        return payload

    async def type(self, *, selector: str, text: str, press_enter: bool = False) -> dict[str, Any]:
        payload = await self._run_json(
            f"""
            type_result = js({json.dumps(self._type_script(selector, text, press_enter))})
            if not type_result or not type_result.get("ok"):
                raise RuntimeError(type_result.get("message", "Could not type into the target element."))
            info = page_info()
            if not isinstance(info, dict):
                info = {{"page_info": str(info)}}
            print(json.dumps({{"page": info, "typed": type_result}}))
            """
        )
        self._initialized = True
        return payload

    async def wait_seconds(self, seconds: int) -> None:
        await self._run_json(
            f"""
            import time
            time.sleep({max(seconds, 0)})
            print(json.dumps({{"waited_seconds": {max(seconds, 0)}}}))
            """
        )

    async def wait_for_text(self, text: str, timeout_ms: int) -> dict[str, Any]:
        payload = await self._run_json(
            f"""
            import time
            deadline = time.time() + ({max(timeout_ms, 1)} / 1000.0)
            matched = False
            while time.time() < deadline:
                body_text = js("(() => (document.body?.innerText || document.body?.textContent || '').slice(0, 20000))()")
                if {json.dumps(text)}.lower() in str(body_text).lower():
                    matched = True
                    break
                time.sleep(0.25)
            if not matched:
                raise RuntimeError("Timed out waiting for visible text.")
            info = page_info()
            if not isinstance(info, dict):
                info = {{"page_info": str(info)}}
            print(json.dumps({{"page": info, "text": {json.dumps(text)}}}))
            """
        )
        return payload

    async def wait_for_element(self, selector: str, state: str, timeout_ms: int) -> dict[str, Any]:
        if state not in {"visible", "attached", "hidden", "detached"}:
            raise RuntimeError(f"Unsupported wait state for browser-harness backend: {state}")

        payload = await self._run_json(
            f"""
            import time
            deadline = time.time() + ({max(timeout_ms, 1)} / 1000.0)
            matched = False
            while time.time() < deadline:
                state_result = js({json.dumps(self._element_state_script(selector))})
                exists = bool(state_result and state_result.get("exists"))
                visible = bool(state_result and state_result.get("visible"))
                target_state = {json.dumps(state)}
                if (target_state == "attached" and exists) or (target_state == "visible" and visible) or (target_state == "hidden" and exists and not visible) or (target_state == "detached" and not exists):
                    matched = True
                    break
                time.sleep(0.25)
            if not matched:
                raise RuntimeError("Timed out waiting for element state.")
            info = page_info()
            if not isinstance(info, dict):
                info = {{"page_info": str(info)}}
            print(json.dumps({{"page": info, "selector": {json.dumps(selector)}, "state": {json.dumps(state)}}}))
            """
        )
        return payload

    async def wait_for_url(self, pattern: str, timeout_ms: int) -> dict[str, Any]:
        payload = await self._run_json(
            f"""
            import time
            deadline = time.time() + ({max(timeout_ms, 1)} / 1000.0)
            latest_info = page_info()
            while time.time() < deadline:
                latest_info = page_info()
                current_url = latest_info.get("url", "") if isinstance(latest_info, dict) else str(latest_info)
                if {json.dumps(pattern)} in current_url:
                    break
                time.sleep(0.25)
            else:
                raise RuntimeError("Timed out waiting for URL pattern.")
            if not isinstance(latest_info, dict):
                latest_info = {{"page_info": str(latest_info), "url": str(latest_info)}}
            print(json.dumps({{"page": latest_info, "pattern": {json.dumps(pattern)}}}))
            """
        )
        return payload

    async def wait_for_navigation(self, timeout_ms: int) -> dict[str, Any]:
        payload = await self._run_json(
            f"""
            wait_for_load()
            info = page_info()
            if not isinstance(info, dict):
                info = {{"page_info": str(info)}}
            print(json.dumps({{"page": info}}))
            """
        )
        return payload

    async def extract(self, selector: str) -> str:
        payload = await self._run_json(
            f"""
            extracted = js({json.dumps(self._extract_script(selector))})
            if extracted is None:
                raise RuntimeError("Element not found.")
            print(json.dumps({{"text": extracted}}))
            """
        )
        return str(payload.get("text", ""))

    async def inspect_selector(self, selector: str) -> dict[str, Any]:
        payload = await self._run_json(
            f"""
            inspected = js({json.dumps(self._inspect_selector_script(selector))})
            if inspected is None:
                inspected = {{"count": 0, "visible": False, "enabled": False, "value": "", "text": ""}}
            print(json.dumps(inspected))
            """
        )
        return {
            "count": int(payload.get("count", 0) or 0),
            "visible": bool(payload.get("visible", False)),
            "enabled": bool(payload.get("enabled", False)),
            "value": str(payload.get("value", "") or ""),
            "text": str(payload.get("text", "") or ""),
        }

    async def _ensure_connection(self, *, headless: bool) -> None:
        if self.cdp_ws:
            return

        if self.cdp_url:
            self._effective_cdp_url = self.cdp_url
            return

        if not self.auto_launch:
            return

        preferred_port = self.debugging_port
        if self._devtools_http_ready(preferred_port):
            self._effective_cdp_url = f"http://127.0.0.1:{preferred_port}"
            return

        if self._browser_process and self._browser_process.poll() is None and self._effective_cdp_url:
            return

        if not self.browser_path:
            raise RuntimeError(
                "browser-harness could not find a Chromium executable to auto-launch. "
                "Set BROWSER_HARNESS_BROWSER_PATH or configure BROWSER_HARNESS_CDP_URL/BROWSER_HARNESS_CDP_WS."
            )

        port = self._pick_debugging_port(preferred_port)
        profile_dir = self.user_data_dir or (Path.cwd() / ".local-tools" / "browser-harness-profile")
        profile_dir.mkdir(parents=True, exist_ok=True)

        launch_args = [
            self.browser_path,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "about:blank",
        ]
        if headless:
            launch_args.insert(1, "--headless=new")

        self._browser_process = subprocess.Popen(
            launch_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        self._effective_cdp_url = f"http://127.0.0.1:{port}"
        await self._wait_for_devtools(self._effective_cdp_url)

    async def _run_json(self, body: str) -> dict[str, Any]:
        script = textwrap.dedent(
            f"""
            import json
            {body}
            """
        ).strip()
        env = os.environ.copy()
        if self.cdp_ws:
            env["BU_CDP_WS"] = self.cdp_ws
        elif self._effective_cdp_url:
            env["BU_CDP_URL"] = self._effective_cdp_url
        attempts = 2 if self.auto_launch and not (self.cdp_url or self.cdp_ws) else 1
        last_message = ""
        for attempt in range(attempts):
            process = await asyncio.create_subprocess_exec(
                self.command,
                "-c",
                script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await process.communicate()
            stdout_text = stdout.decode("utf-8", errors="replace").strip()
            stderr_text = stderr.decode("utf-8", errors="replace").strip()

            if process.returncode == 0:
                payload = self._extract_json(stdout_text)
                if payload is None:
                    raise RuntimeError(
                        f"{self.command} returned no JSON payload. stdout={stdout_text!r} stderr={stderr_text!r}"
                    )
                return payload

            last_message = stderr_text or stdout_text or f"{self.command} exited with code {process.returncode}"
            if attempt + 1 < attempts and self._is_attach_failure_message(last_message):
                await self._recover_connection()
                env = os.environ.copy()
                if self.cdp_ws:
                    env["BU_CDP_WS"] = self.cdp_ws
                elif self._effective_cdp_url:
                    env["BU_CDP_URL"] = self._effective_cdp_url
                continue
            break
        raise RuntimeError(last_message)

    async def _wait_for_devtools(self, base_url: str) -> None:
        deadline = asyncio.get_running_loop().time() + 30
        last_error: Exception | None = None
        while asyncio.get_running_loop().time() < deadline:
            try:
                with urllib.request.urlopen(f"{base_url.rstrip('/')}/json/version", timeout=2) as response:
                    payload = json.loads(response.read().decode("utf-8", errors="replace"))
                    if payload.get("webSocketDebuggerUrl"):
                        return
            except Exception as exc:
                last_error = exc
                await asyncio.sleep(0.5)
        raise RuntimeError(
            f"Timed out waiting for dedicated Chromium debug endpoint at {base_url}: {last_error}"
        )

    async def _recover_connection(self) -> None:
        if self._browser_process and self._browser_process.poll() is None:
            self._browser_process.terminate()
            try:
                self._browser_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._browser_process.kill()
                self._browser_process.wait(timeout=5)
        self._browser_process = None
        self._effective_cdp_url = self.cdp_url
        await self._ensure_connection(headless=self._headless)

    @staticmethod
    def _extract_json(stdout_text: str) -> Optional[dict[str, Any]]:
        for line in reversed([item.strip() for item in stdout_text.splitlines() if item.strip()]):
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
            return {"value": value}
        return None

    @staticmethod
    def _devtools_http_ready(port: int) -> bool:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
                return bool(payload.get("webSocketDebuggerUrl"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
            return False

    @staticmethod
    def _is_attach_failure_message(message: str) -> bool:
        lower = message.lower()
        return any(
            marker in lower
            for marker in (
                "devtoolsactiveport",
                "allow remote debugging",
                "bu_cdp_url",
                "websocketdebuggerurl",
                "debug endpoint",
                "daemon",
                "chrome://inspect",
            )
        )

    @staticmethod
    def _pick_debugging_port(preferred_port: int) -> int:
        if BrowserHarnessBackend._port_available(preferred_port):
            return preferred_port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    @staticmethod
    def _port_available(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            return sock.connect_ex(("127.0.0.1", port)) != 0

    @staticmethod
    def _visible_text_script() -> str:
        return """
        (() => {
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
            let text = '';
            let node;
            while ((node = walker.nextNode())) {
                const trimmed = (node.textContent || '').trim();
                if (trimmed) text += trimmed + ' ';
            }
            return text.substring(0, 3000);
        })()
        """

    @staticmethod
    def _interactive_elements_script() -> str:
        return """
        (() => {
            const clickable = Array.from(document.querySelectorAll('a, button, input, select, textarea'));
            return clickable.slice(0, 50).map((el, idx) => ({
                index: idx,
                tag: (el.tagName || '').toLowerCase(),
                type: el.type || '',
                text: (el.innerText || el.textContent || '').substring(0, 50),
                placeholder: el.placeholder || '',
                id: el.id || '',
                href: el.href || ''
            }));
        })()
        """

    @staticmethod
    def _click_target_script(selector: Optional[str], text: Optional[str], element_index: Optional[int]) -> str:
        return f"""
        (() => {{
            function visible(el) {{
                if (!el) return false;
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
            }}

            let el = null;
            const selector = {json.dumps(selector)};
            const text = {json.dumps(text)};
            const elementIndex = {json.dumps(element_index)};

            if (selector) {{
                el = document.querySelector(selector);
            }} else if (text) {{
                const candidates = Array.from(document.querySelectorAll('a, button, input, select, textarea, [role="button"]'));
                el = candidates.find((candidate) => ((candidate.innerText || candidate.textContent || '')).toLowerCase().includes(text.toLowerCase())) || null;
            }} else if (elementIndex !== null) {{
                const candidates = Array.from(document.querySelectorAll('a, button, input, select, textarea'));
                el = candidates[elementIndex] || null;
            }}

            if (!visible(el)) return null;
            const rect = el.getBoundingClientRect();
            return {{
                x: Math.round(rect.left + rect.width / 2),
                y: Math.round(rect.top + rect.height / 2),
                tag: (el.tagName || '').toLowerCase(),
                text: (el.innerText || el.textContent || '').trim().slice(0, 120),
                selector: selector || '',
            }};
        }})()
        """

    @staticmethod
    def _fill_field_script(field: str, text: str, press_enter: bool) -> str:
        return f"""
        (() => {{
            const field = {json.dumps(field)};
            const value = {json.dumps(text)};
            const pressEnter = {json.dumps(press_enter)};

            function visible(el) {{
                if (!el) return false;
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
            }}

            function byLabel(name) {{
                const labels = Array.from(document.querySelectorAll('label'));
                for (const label of labels) {{
                    const labelText = (label.innerText || label.textContent || '').trim().toLowerCase();
                    if (!labelText.includes(name.toLowerCase())) continue;
                    if (label.control) return label.control;
                    const forId = label.getAttribute('for');
                    if (forId) return document.getElementById(forId);
                }}
                return null;
            }}

            const inputs = Array.from(document.querySelectorAll('input, textarea, select'));
            const candidates = [
                byLabel(field),
                ...inputs.filter((el) => (el.name || '').toLowerCase() === field.toLowerCase()),
                document.getElementById(field),
                ...inputs.filter((el) => (el.placeholder || '').toLowerCase().includes(field.toLowerCase())),
                ...inputs.filter((el) => (el.getAttribute('aria-label') || '').toLowerCase().includes(field.toLowerCase())),
            ].filter(Boolean);

            const target = candidates.find(visible) || candidates[0] || null;
            if (!target) {{
                return {{ ok: false, message: `Could not find field '${{field}}'.` }};
            }}

            target.focus();
            if ('value' in target) {{
                target.value = value;
            }}
            target.dispatchEvent(new Event('input', {{ bubbles: true }}));
            target.dispatchEvent(new Event('change', {{ bubbles: true }}));
            if (pressEnter) {{
                target.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter', bubbles: true }}));
                target.dispatchEvent(new KeyboardEvent('keyup', {{ key: 'Enter', bubbles: true }}));
            }}

            return {{
                ok: true,
                field,
                matched_by: target.id ? 'id' : target.name ? 'name' : target.placeholder ? 'placeholder' : 'label',
                tag: (target.tagName || '').toLowerCase(),
            }};
        }})()
        """

    @staticmethod
    def _type_script(selector: str, text: str, press_enter: bool) -> str:
        return f"""
        (() => {{
            const selector = {json.dumps(selector)};
            const value = {json.dumps(text)};
            const pressEnter = {json.dumps(press_enter)};
            const target = document.querySelector(selector);
            if (!target) {{
                return {{ ok: false, message: `Element not found for selector: ${{selector}}` }};
            }}
            target.focus();
            if ('value' in target) {{
                target.value = value;
            }}
            target.dispatchEvent(new Event('input', {{ bubbles: true }}));
            target.dispatchEvent(new Event('change', {{ bubbles: true }}));
            if (pressEnter) {{
                target.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter', bubbles: true }}));
                target.dispatchEvent(new KeyboardEvent('keyup', {{ key: 'Enter', bubbles: true }}));
            }}
            return {{ ok: true, selector }};
        }})()
        """

    @staticmethod
    def _element_state_script(selector: str) -> str:
        return f"""
        (() => {{
            const target = document.querySelector({json.dumps(selector)});
            if (!target) return {{ exists: false, visible: false }};
            const style = window.getComputedStyle(target);
            const rect = target.getBoundingClientRect();
            return {{
                exists: true,
                visible: style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0,
            }};
        }})()
        """

    @staticmethod
    def _extract_script(selector: str) -> str:
        return f"""
        (() => {{
            const target = document.querySelector({json.dumps(selector)});
            if (!target) return null;
            return (target.innerText || target.textContent || '').trim();
        }})()
        """

    @staticmethod
    def _inspect_selector_script(selector: str) -> str:
        return f"""
        (() => {{
            const matches = Array.from(document.querySelectorAll({json.dumps(selector)}));
            if (!matches.length) {{
                return {{ count: 0, visible: false, enabled: false, value: '', text: '' }};
            }}

            function isVisible(el) {{
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
            }}

            const first = matches[0];
            const visible = isVisible(first);
            const enabled = !first.disabled && first.getAttribute('aria-disabled') !== 'true';
            const value = 'value' in first ? String(first.value || '') : '';
            const text = String(first.innerText || first.textContent || '').trim();

            return {{
                count: matches.length,
                visible,
                enabled,
                value,
                text,
            }};
        }})()
        """
