"""Stack 3.0 Tools - Auto-import all tools for registration"""

# Import all tools to trigger auto-registration
# The registration happens at module level in each tool file

from .base import BaseTool, ToolResult, ToolParam
from .registry import ToolRegistry, get_registry, tool_registry

# Import all tool modules (triggers registration)
from . import agent_tool
from . import ask_question
from . import brief_tool
from . import config_tool
from . import file_edit
from . import file_read
from . import file_write
from . import glob_tool
from . import grep_tool
from . import mcp_tool
from . import messaging
from . import plan_mode
from . import remote_trigger
from . import scheduling
from . import skill_tool
from . import sleep_tool
from . import synthetic_output
from . import task_get
from . import task_management
from . import team_delete
from . import team_tool
from . import todo_tool
from . import tool_discovery
from . import web_fetch
from . import web_search
from . import worktree_tool

__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolParam",
    "ToolRegistry",
    "get_registry",
    "tool_registry",
]
