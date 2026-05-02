from mcp.server.fastmcp import FastMCP

from browser_state import BrowserState
from browser_tools import register_browser_tools
from task_tools import load_tasks_as_prompts, register_task_tools


mcp = FastMCP("BrowserAgentServer")
browser_state = BrowserState()

load_tasks_as_prompts(mcp)
register_task_tools(mcp)
register_browser_tools(mcp, browser_state)


if __name__ == "__main__":
    mcp.run()
