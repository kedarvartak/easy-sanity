from mcp.server.fastmcp import FastMCP

from browser.state import BrowserState
from browser.tools import register_browser_tools
from config.settings import ensure_runtime_layout
from memory.tools import register_memory_tools
from tasks.tools import load_tasks_as_prompts, register_task_tools


def create_mcp() -> FastMCP:
    ensure_runtime_layout()
    mcp = FastMCP("BrowserAgentServer")
    browser_state = BrowserState()

    load_tasks_as_prompts(mcp)
    register_task_tools(mcp)
    register_browser_tools(mcp, browser_state)
    register_memory_tools(mcp)
    return mcp


def run_server() -> None:
    create_mcp().run()
