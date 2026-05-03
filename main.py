from mcp.server.fastmcp import FastMCP

from browser.state import BrowserState
from browser.tools import register_browser_tools
from memory.tools import register_memory_tools
from tasks.tools import load_tasks_as_prompts, register_task_tools


mcp = FastMCP("BrowserAgentServer")
browser_state = BrowserState()

load_tasks_as_prompts(mcp)
register_task_tools(mcp)
register_browser_tools(mcp, browser_state)
register_memory_tools(mcp)


if __name__ == "__main__":
    mcp.run()
