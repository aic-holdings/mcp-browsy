"""
mcp-browsy: World-class browser automation MCP using direct CDP.

No extensions required - just launch and automate.
"""

from .server import mcp, main
from .browser import browser_manager, Browser, BrowserManager
from .cdp import CDPClient

__version__ = "0.1.0"
__all__ = [
    "mcp",
    "main",
    "browser_manager",
    "Browser",
    "BrowserManager",
    "CDPClient",
]
