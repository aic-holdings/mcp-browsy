"""
DOM utilities for element interaction.

Provides helpers for:
- Resolving CSS selectors to node IDs
- Getting element coordinates
- Building element references for AI
"""

import logging
from typing import Optional

from .browser import browser_manager

logger = logging.getLogger(__name__)


class ElementNotFoundError(Exception):
    """Element could not be found."""
    pass


class ElementNotVisibleError(Exception):
    """Element exists but has no visible bounds."""
    pass


async def get_node_id(selector: str) -> int:
    """
    Resolve a CSS selector to a CDP node ID.

    Args:
        selector: CSS selector string

    Returns:
        CDP node ID

    Raises:
        ElementNotFoundError: If element not found
    """
    browser = browser_manager.browser
    if not browser:
        raise RuntimeError("Browser not connected")

    # Get document root
    doc = await browser.cdp.send("DOM.getDocument")
    root_id = doc["root"]["nodeId"]

    # Query for element
    result = await browser.cdp.send(
        "DOM.querySelector",
        {"nodeId": root_id, "selector": selector}
    )

    node_id = result.get("nodeId", 0)
    if node_id == 0:
        raise ElementNotFoundError(f"Element not found: {selector}")

    return node_id


async def get_element_center(node_id: int) -> tuple[float, float]:
    """
    Get the center coordinates of an element.

    Args:
        node_id: CDP node ID

    Returns:
        Tuple of (x, y) coordinates

    Raises:
        ElementNotVisibleError: If element has no visible bounds
    """
    browser = browser_manager.browser
    if not browser:
        raise RuntimeError("Browser not connected")

    try:
        model = await browser.cdp.send("DOM.getBoxModel", {"nodeId": node_id})
    except Exception as e:
        raise ElementNotVisibleError(f"Element has no box model: {e}")

    content = model["model"]["content"]
    # Content quad is [x1, y1, x2, y2, x3, y3, x4, y4]
    # Points: top-left, top-right, bottom-right, bottom-left
    x = (content[0] + content[2]) / 2
    y = (content[1] + content[5]) / 2

    return x, y


async def get_element_bounds(node_id: int) -> dict:
    """
    Get the bounding box of an element.

    Returns:
        Dict with x, y, width, height
    """
    browser = browser_manager.browser
    if not browser:
        raise RuntimeError("Browser not connected")

    model = await browser.cdp.send("DOM.getBoxModel", {"nodeId": node_id})
    content = model["model"]["content"]

    return {
        "x": content[0],
        "y": content[1],
        "width": content[2] - content[0],
        "height": content[5] - content[1],
    }


async def resolve_element(
    selector: Optional[str] = None,
    ref: Optional[str] = None,
    x: Optional[float] = None,
    y: Optional[float] = None,
) -> tuple[float, float]:
    """
    Resolve element reference to coordinates.

    Accepts multiple ways to specify an element:
    - selector: CSS selector string
    - ref: Element reference from snapshot (TODO: implement)
    - x, y: Direct coordinates

    Returns:
        Tuple of (x, y) coordinates
    """
    if x is not None and y is not None:
        return float(x), float(y)

    if selector:
        node_id = await get_node_id(selector)
        return await get_element_center(node_id)

    if ref:
        # TODO: Implement ref lookup from snapshot
        raise NotImplementedError("Element refs not yet implemented")

    raise ValueError("Must specify selector, ref, or x/y coordinates")


async def scroll_into_view(node_id: int) -> None:
    """Scroll element into view."""
    browser = browser_manager.browser
    if not browser:
        raise RuntimeError("Browser not connected")

    await browser.cdp.send(
        "DOM.scrollIntoViewIfNeeded",
        {"nodeId": node_id}
    )


async def focus_element(node_id: int) -> None:
    """Focus an element."""
    browser = browser_manager.browser
    if not browser:
        raise RuntimeError("Browser not connected")

    await browser.cdp.send("DOM.focus", {"nodeId": node_id})
