"""
Input tools for mcp-browsy.

Provides tools for:
- Mouse clicks
- Keyboard input
- Element interaction
- Drag and drop
"""

import asyncio
from typing import Optional

from ..browser import browser_manager
from ..dom import resolve_element, get_node_id, focus_element, scroll_into_view


# Key code mappings for special keys
KEY_CODES = {
    "Enter": {"key": "Enter", "code": "Enter", "keyCode": 13},
    "Tab": {"key": "Tab", "code": "Tab", "keyCode": 9},
    "Escape": {"key": "Escape", "code": "Escape", "keyCode": 27},
    "Backspace": {"key": "Backspace", "code": "Backspace", "keyCode": 8},
    "Delete": {"key": "Delete", "code": "Delete", "keyCode": 46},
    "ArrowUp": {"key": "ArrowUp", "code": "ArrowUp", "keyCode": 38},
    "ArrowDown": {"key": "ArrowDown", "code": "ArrowDown", "keyCode": 40},
    "ArrowLeft": {"key": "ArrowLeft", "code": "ArrowLeft", "keyCode": 37},
    "ArrowRight": {"key": "ArrowRight", "code": "ArrowRight", "keyCode": 39},
    "Home": {"key": "Home", "code": "Home", "keyCode": 36},
    "End": {"key": "End", "code": "End", "keyCode": 35},
    "PageUp": {"key": "PageUp", "code": "PageUp", "keyCode": 33},
    "PageDown": {"key": "PageDown", "code": "PageDown", "keyCode": 34},
    "Space": {"key": " ", "code": "Space", "keyCode": 32},
}


async def click(
    selector: Optional[str] = None,
    ref: Optional[str] = None,
    x: Optional[float] = None,
    y: Optional[float] = None,
    button: str = "left",
    click_count: int = 1,
) -> dict:
    """
    Click on an element or coordinates.

    Args:
        selector: CSS selector
        ref: Element reference from snapshot
        x, y: Coordinates (if not using selector/ref)
        button: "left", "right", or "middle"
        click_count: 1 for click, 2 for double-click

    Returns:
        Dict with click result
    """
    browser = await browser_manager.launch()

    try:
        click_x, click_y = await resolve_element(selector, ref, x, y)
    except Exception as e:
        return {"success": False, "error": str(e)}

    # If we have a selector, scroll element into view first
    if selector:
        try:
            node_id = await get_node_id(selector)
            await scroll_into_view(node_id)
            # Re-get coordinates after scroll
            click_x, click_y = await resolve_element(selector=selector)
        except Exception:
            pass

    # Mouse button mapping
    button_map = {"left": "left", "right": "right", "middle": "middle"}
    cdp_button = button_map.get(button, "left")

    # Send mouse events
    await browser.cdp.send("Input.dispatchMouseEvent", {
        "type": "mousePressed",
        "x": click_x,
        "y": click_y,
        "button": cdp_button,
        "clickCount": click_count,
    })

    await asyncio.sleep(0.05)

    await browser.cdp.send("Input.dispatchMouseEvent", {
        "type": "mouseReleased",
        "x": click_x,
        "y": click_y,
        "button": cdp_button,
        "clickCount": click_count,
    })

    return {
        "success": True,
        "x": int(click_x),
        "y": int(click_y),
        "selector": selector,
    }


async def type_text(
    text: str,
    selector: Optional[str] = None,
    ref: Optional[str] = None,
    delay: int = 0,
    clear: bool = False,
) -> dict:
    """
    Type text into an element.

    Args:
        text: Text to type
        selector: CSS selector of element to type into
        ref: Element reference from snapshot
        delay: Delay between keystrokes in ms
        clear: Clear existing content first

    Returns:
        Dict with type result
    """
    browser = await browser_manager.launch()

    # Focus element if specified
    if selector or ref:
        # Click to focus
        result = await click(selector=selector, ref=ref)
        if not result.get("success"):
            return result
        await asyncio.sleep(0.1)

    # Clear existing content if requested
    if clear:
        # Select all and delete
        await browser.cdp.send("Input.dispatchKeyEvent", {
            "type": "keyDown",
            "key": "a",
            "modifiers": 2,  # Ctrl/Cmd
        })
        await browser.cdp.send("Input.dispatchKeyEvent", {
            "type": "keyUp",
            "key": "a",
            "modifiers": 2,
        })
        await browser.cdp.send("Input.dispatchKeyEvent", {
            "type": "keyDown",
            "key": "Backspace",
            "keyCode": 8,
        })
        await browser.cdp.send("Input.dispatchKeyEvent", {
            "type": "keyUp",
            "key": "Backspace",
            "keyCode": 8,
        })
        await asyncio.sleep(0.05)

    # Type each character
    for char in text:
        await browser.cdp.send("Input.dispatchKeyEvent", {
            "type": "char",
            "text": char,
        })
        if delay > 0:
            await asyncio.sleep(delay / 1000)

    return {
        "success": True,
        "text": text,
        "selector": selector,
    }


async def press_key(
    key: str,
    modifiers: Optional[list[str]] = None,
) -> dict:
    """
    Press a keyboard key.

    Args:
        key: Key name (e.g., "Enter", "Tab", "a", "1")
        modifiers: List of modifier keys ["Control", "Shift", "Alt", "Meta"]

    Returns:
        Dict with key press result
    """
    browser = await browser_manager.launch()

    # Calculate modifier flags
    modifier_flags = 0
    if modifiers:
        if "Alt" in modifiers:
            modifier_flags |= 1
        if "Control" in modifiers:
            modifier_flags |= 2
        if "Meta" in modifiers:
            modifier_flags |= 4
        if "Shift" in modifiers:
            modifier_flags |= 8

    # Get key definition
    if key in KEY_CODES:
        key_def = KEY_CODES[key]
    else:
        key_def = {
            "key": key,
            "code": f"Key{key.upper()}" if len(key) == 1 else key,
            "keyCode": ord(key.upper()) if len(key) == 1 else 0,
        }

    # Key down
    await browser.cdp.send("Input.dispatchKeyEvent", {
        "type": "keyDown",
        "modifiers": modifier_flags,
        **key_def,
    })

    # For printable characters, also send char event
    if len(key) == 1:
        await browser.cdp.send("Input.dispatchKeyEvent", {
            "type": "char",
            "text": key,
            "modifiers": modifier_flags,
        })

    # Key up
    await browser.cdp.send("Input.dispatchKeyEvent", {
        "type": "keyUp",
        "modifiers": modifier_flags,
        **key_def,
    })

    return {
        "success": True,
        "key": key,
        "modifiers": modifiers or [],
    }


async def hover(
    selector: Optional[str] = None,
    ref: Optional[str] = None,
    x: Optional[float] = None,
    y: Optional[float] = None,
) -> dict:
    """
    Hover over an element.

    Args:
        selector: CSS selector
        ref: Element reference
        x, y: Coordinates

    Returns:
        Dict with hover result
    """
    browser = await browser_manager.launch()

    try:
        hover_x, hover_y = await resolve_element(selector, ref, x, y)
    except Exception as e:
        return {"success": False, "error": str(e)}

    await browser.cdp.send("Input.dispatchMouseEvent", {
        "type": "mouseMoved",
        "x": hover_x,
        "y": hover_y,
    })

    return {
        "success": True,
        "x": int(hover_x),
        "y": int(hover_y),
    }


async def scroll(
    selector: Optional[str] = None,
    x: int = 0,
    y: int = 0,
) -> dict:
    """
    Scroll the page or an element.

    Args:
        selector: CSS selector of scrollable element (or page if None)
        x: Horizontal scroll amount (positive = right)
        y: Vertical scroll amount (positive = down)

    Returns:
        Dict with scroll result
    """
    browser = await browser_manager.launch()
    await browser.enable_domain("Runtime")

    if selector:
        # Scroll within element
        script = f"""
            const el = document.querySelector('{selector}');
            if (el) {{
                el.scrollBy({x}, {y});
                true;
            }} else {{
                false;
            }}
        """
    else:
        # Scroll page
        script = f"window.scrollBy({x}, {y}); true;"

    result = await browser.cdp.send("Runtime.evaluate", {
        "expression": script,
        "returnByValue": True,
    })

    success = result.get("result", {}).get("value", False)
    return {"success": success, "x": x, "y": y}


async def select_option(
    selector: str,
    values: list[str],
) -> dict:
    """
    Select options in a dropdown.

    Args:
        selector: CSS selector of select element
        values: List of option values to select

    Returns:
        Dict with selection result
    """
    browser = await browser_manager.launch()
    await browser.enable_domain("Runtime")

    values_json = str(values).replace("'", '"')
    script = f"""
        const select = document.querySelector('{selector}');
        if (select && select.tagName === 'SELECT') {{
            const values = {values_json};
            for (const option of select.options) {{
                option.selected = values.includes(option.value);
            }}
            select.dispatchEvent(new Event('change', {{ bubbles: true }}));
            true;
        }} else {{
            false;
        }}
    """

    result = await browser.cdp.send("Runtime.evaluate", {
        "expression": script,
        "returnByValue": True,
    })

    success = result.get("result", {}).get("value", False)
    return {"success": success, "selector": selector, "values": values}
