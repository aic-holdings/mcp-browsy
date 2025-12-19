"""
mcp-browsy MCP Server

World-class browser automation via direct CDP connection.
No extensions required - just launch and automate.
"""

import asyncio
import atexit
import logging
import signal
from typing import Optional

from fastmcp import FastMCP

from .browser import browser_manager
from .tools import navigation, input, inspection
from .hq_client import get_hq_client, is_hq_mode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create MCP server
mcp = FastMCP(
    "mcp-browsy",
    instructions="World-class browser automation MCP using direct CDP. No extension required.",
)


# =============================================================================
# Lifecycle Tools
# =============================================================================

@mcp.tool()
async def browsy_launch(headless: bool = False) -> str:
    """
    Launch browser and connect.

    This is called automatically by other tools, but you can call it
    explicitly to pre-launch the browser or configure headless mode.

    Args:
        headless: Run in headless mode (no visible window)
    """
    hq = get_hq_client()
    if hq:
        # HQ mode: create browser via browsy-hq
        session_id = await hq.create_browser(headless=headless)
        return f"Browser launched via browsy-hq. Session: {session_id}"
    else:
        # Local mode: launch Chrome directly
        await browser_manager.launch(headless=headless)
        browser = browser_manager.browser
        return f"Browser launched. Current page: {await browser.get_url()}"


@mcp.tool()
async def browsy_close() -> str:
    """Close the browser and cleanup."""
    hq = get_hq_client()
    if hq:
        await hq.close_browser()
        return "Browser closed (via browsy-hq)"
    else:
        await browser_manager.close()
        return "Browser closed"


# =============================================================================
# Navigation Tools
# =============================================================================

@mcp.tool()
async def browsy_navigate(url: str, wait_until: str = "load") -> dict:
    """
    Navigate to a URL.

    Args:
        url: The URL to navigate to
        wait_until: Wait condition - "load" or "domcontentloaded"
    """
    hq = get_hq_client()
    if hq:
        if not hq.session_id:
            await hq.create_browser()
        return await hq.navigate(url)
    else:
        return await navigation.navigate(url, wait_until)


@mcp.tool()
async def browsy_reload(ignore_cache: bool = False) -> dict:
    """
    Reload the current page.

    Args:
        ignore_cache: Bypass browser cache
    """
    return await navigation.reload(ignore_cache)


@mcp.tool()
async def browsy_back() -> dict:
    """Go back in browser history."""
    return await navigation.go_back()


@mcp.tool()
async def browsy_forward() -> dict:
    """Go forward in browser history."""
    return await navigation.go_forward()


@mcp.tool()
async def browsy_tabs() -> list[dict]:
    """List all open browser tabs."""
    return await navigation.get_tabs()


@mcp.tool()
async def browsy_tab_switch(tab_id: str) -> dict:
    """
    Switch to a different tab.

    Args:
        tab_id: ID of the tab to switch to (from browsy_tabs)
    """
    return await navigation.switch_tab(tab_id)


@mcp.tool()
async def browsy_tab_new(url: Optional[str] = None) -> dict:
    """
    Open a new browser tab.

    Args:
        url: Optional URL to navigate to in the new tab
    """
    return await navigation.new_tab(url)


@mcp.tool()
async def browsy_tab_close(tab_id: Optional[str] = None) -> dict:
    """
    Close a browser tab.

    Args:
        tab_id: ID of tab to close (current tab if not specified)
    """
    return await navigation.close_tab(tab_id)


# =============================================================================
# Input Tools
# =============================================================================

@mcp.tool()
async def browsy_click(
    selector: Optional[str] = None,
    x: Optional[float] = None,
    y: Optional[float] = None,
    button: str = "left",
    click_count: int = 1,
) -> dict:
    """
    Click on an element or coordinates.

    Args:
        selector: CSS selector of element to click
        x: X coordinate (if not using selector)
        y: Y coordinate (if not using selector)
        button: Mouse button - "left", "right", "middle"
        click_count: 1 for click, 2 for double-click
    """
    return await input.click(selector=selector, x=x, y=y, button=button, click_count=click_count)


@mcp.tool()
async def browsy_type(
    text: str,
    selector: Optional[str] = None,
    delay: int = 0,
    clear: bool = False,
) -> dict:
    """
    Type text into an element.

    Args:
        text: Text to type
        selector: CSS selector of element (types into focused element if not specified)
        delay: Delay between keystrokes in milliseconds
        clear: Clear existing content first
    """
    return await input.type_text(text, selector=selector, delay=delay, clear=clear)


@mcp.tool()
async def browsy_press(
    key: str,
    modifiers: Optional[list[str]] = None,
) -> dict:
    """
    Press a keyboard key.

    Args:
        key: Key name (e.g., "Enter", "Tab", "Escape", "a", "1")
        modifiers: Modifier keys ["Control", "Shift", "Alt", "Meta"]
    """
    return await input.press_key(key, modifiers)


@mcp.tool()
async def browsy_hover(
    selector: Optional[str] = None,
    x: Optional[float] = None,
    y: Optional[float] = None,
) -> dict:
    """
    Hover over an element or coordinates.

    Args:
        selector: CSS selector of element
        x: X coordinate
        y: Y coordinate
    """
    return await input.hover(selector=selector, x=x, y=y)


@mcp.tool()
async def browsy_scroll(
    selector: Optional[str] = None,
    x: int = 0,
    y: int = 0,
) -> dict:
    """
    Scroll the page or an element.

    Args:
        selector: CSS selector of scrollable element (page if not specified)
        x: Horizontal scroll amount (positive = right)
        y: Vertical scroll amount (positive = down)
    """
    return await input.scroll(selector=selector, x=x, y=y)


@mcp.tool()
async def browsy_select(
    selector: str,
    values: list[str],
) -> dict:
    """
    Select options in a dropdown.

    Args:
        selector: CSS selector of select element
        values: List of option values to select
    """
    return await input.select_option(selector, values)


# =============================================================================
# Inspection Tools
# =============================================================================

@mcp.tool()
async def browsy_snapshot(include_hidden: bool = False) -> dict:
    """
    Get accessibility snapshot of the page.

    Returns a structured view of page elements that AI can use
    to understand and interact with the page.

    Args:
        include_hidden: Include hidden elements
    """
    hq = get_hq_client()
    if hq and hq.session_id:
        return await hq.snapshot()
    else:
        return await inspection.snapshot(include_hidden)


@mcp.tool()
async def browsy_screenshot(
    selector: Optional[str] = None,
    full_page: bool = False,
    format: str = "png",
) -> dict:
    """
    Take a screenshot.

    Args:
        selector: CSS selector of element to capture (viewport if not specified)
        full_page: Capture entire scrollable page
        format: Image format - "png", "jpeg", "webp"
    """
    hq = get_hq_client()
    if hq and hq.session_id:
        return await hq.screenshot()
    else:
        return await inspection.screenshot(selector=selector, full_page=full_page, format=format)


@mcp.tool()
async def browsy_get_text(selector: Optional[str] = None) -> dict:
    """
    Get text content from page or element.

    Args:
        selector: CSS selector (entire page if not specified)
    """
    return await inspection.get_text(selector)


@mcp.tool()
async def browsy_get_html(
    selector: Optional[str] = None,
    outer: bool = True,
) -> dict:
    """
    Get HTML content from page or element.

    Args:
        selector: CSS selector (entire page if not specified)
        outer: Get outerHTML (True) or innerHTML (False)
    """
    return await inspection.get_html(selector=selector, outer=outer)


@mcp.tool()
async def browsy_evaluate(expression: str) -> dict:
    """
    Execute JavaScript in the page.

    Args:
        expression: JavaScript expression to evaluate
    """
    return await inspection.evaluate(expression)


@mcp.tool()
async def browsy_cookies(domain: Optional[str] = None) -> dict:
    """
    Get browser cookies.

    Args:
        domain: Filter by domain (optional)
    """
    return await inspection.get_cookies(domain)


# =============================================================================
# Server Lifecycle
# =============================================================================

async def cleanup():
    """Cleanup on shutdown."""
    logger.info("Shutting down mcp-browsy...")
    await browser_manager.close()


def main():
    """Entry point for the MCP server."""
    # Register cleanup
    atexit.register(lambda: asyncio.run(cleanup()))

    # Handle signals
    def signal_handler(sig, frame):
        asyncio.run(cleanup())
        exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run MCP server
    logger.info("Starting mcp-browsy MCP server...")
    mcp.run()


if __name__ == "__main__":
    main()
