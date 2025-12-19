"""
Navigation tools for mcp-browsy.

Provides tools for:
- URL navigation
- History navigation (back/forward)
- Tab management
- Page reload
"""

from ..browser import browser_manager


async def navigate(url: str, wait_until: str = "load") -> dict:
    """
    Navigate to a URL.

    Args:
        url: The URL to navigate to
        wait_until: Wait condition - "load", "domcontentloaded"

    Returns:
        Dict with url, title, status
    """
    browser = await browser_manager.launch()
    result = await browser.navigate(url, wait_until)

    return {
        "url": await browser.get_url(),
        "title": await browser.get_title(),
        "frame_id": result.get("frameId"),
    }


async def reload(ignore_cache: bool = False) -> dict:
    """
    Reload the current page.

    Args:
        ignore_cache: If True, bypass cache

    Returns:
        Dict with success status
    """
    browser = await browser_manager.launch()
    await browser.enable_domain("Page")

    await browser.cdp.send("Page.reload", {"ignoreCache": ignore_cache})

    # Wait for load
    try:
        await browser.cdp.wait_for_event("Page.loadEventFired", timeout=30.0)
    except Exception:
        pass

    return {
        "url": await browser.get_url(),
        "title": await browser.get_title(),
    }


async def go_back() -> dict:
    """
    Go back in browser history.

    Returns:
        Dict with navigation result or error
    """
    browser = await browser_manager.launch()
    await browser.enable_domain("Page")

    history = await browser.cdp.send("Page.getNavigationHistory")
    current_idx = history.get("currentIndex", 0)

    if current_idx <= 0:
        return {"success": False, "error": "Cannot go back - at beginning of history"}

    entries = history.get("entries", [])
    prev_entry = entries[current_idx - 1]

    await browser.cdp.send(
        "Page.navigateToHistoryEntry",
        {"entryId": prev_entry["id"]}
    )

    return {
        "success": True,
        "url": prev_entry.get("url"),
        "title": prev_entry.get("title"),
    }


async def go_forward() -> dict:
    """
    Go forward in browser history.

    Returns:
        Dict with navigation result or error
    """
    browser = await browser_manager.launch()
    await browser.enable_domain("Page")

    history = await browser.cdp.send("Page.getNavigationHistory")
    current_idx = history.get("currentIndex", 0)
    entries = history.get("entries", [])

    if current_idx >= len(entries) - 1:
        return {"success": False, "error": "Cannot go forward - at end of history"}

    next_entry = entries[current_idx + 1]

    await browser.cdp.send(
        "Page.navigateToHistoryEntry",
        {"entryId": next_entry["id"]}
    )

    return {
        "success": True,
        "url": next_entry.get("url"),
        "title": next_entry.get("title"),
    }


async def get_tabs() -> list[dict]:
    """
    List all open tabs.

    Returns:
        List of tab dicts with id, url, title, active
    """
    await browser_manager.launch()
    return await browser_manager.get_tabs()


async def switch_tab(tab_id: str) -> dict:
    """
    Switch to a different tab.

    Args:
        tab_id: ID of the tab to switch to

    Returns:
        Dict with success status
    """
    await browser_manager.launch()
    success = await browser_manager.switch_tab(tab_id)

    if success:
        browser = browser_manager.browser
        return {
            "success": True,
            "url": await browser.get_url(),
            "title": await browser.get_title(),
        }
    return {"success": False, "error": f"Tab not found: {tab_id}"}


async def new_tab(url: str = None) -> dict:
    """
    Open a new tab.

    Args:
        url: Optional URL to navigate to

    Returns:
        Dict with new tab info
    """
    await browser_manager.launch()
    return await browser_manager.new_tab(url)


async def close_tab(tab_id: str = None) -> dict:
    """
    Close a tab.

    Args:
        tab_id: ID of tab to close, or current tab if None

    Returns:
        Dict with success status
    """
    await browser_manager.launch()

    if tab_id is None:
        tab_id = browser_manager.browser.target_id

    success = await browser_manager.close_tab(tab_id)
    return {"success": success}
