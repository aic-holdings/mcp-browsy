"""
Inspection tools for mcp-browsy.

Provides tools for:
- Accessibility snapshots
- Screenshots
- Text extraction
- Console logs
- JavaScript evaluation
"""

import base64
from typing import Optional

from ..browser import browser_manager


async def snapshot(include_hidden: bool = False) -> dict:
    """
    Get an accessibility tree snapshot of the page.

    This provides a structured view of the page that AI can use
    to understand and interact with elements.

    Args:
        include_hidden: Include hidden elements

    Returns:
        Dict with url, title, and elements list
    """
    browser = await browser_manager.launch()
    await browser.enable_domain("Accessibility")

    # Get full accessibility tree
    result = await browser.cdp.send("Accessibility.getFullAXTree")
    nodes = result.get("nodes", [])

    # Filter and transform nodes for AI consumption
    elements = []
    for node in nodes:
        role = node.get("role", {}).get("value", "")
        name = node.get("name", {}).get("value", "")

        # Skip generic/uninteresting nodes unless they have useful info
        if role in ("generic", "group", "none", "StaticText") and not name:
            if not include_hidden:
                continue

        # Skip ignored nodes
        if node.get("ignored", False) and not include_hidden:
            continue

        element = {
            "ref": node.get("nodeId", ""),
            "role": role,
            "name": name,
        }

        # Add value if present
        if "value" in node:
            value = node["value"].get("value", "")
            if value:
                element["value"] = value

        # Add description if present
        if "description" in node:
            desc = node["description"].get("value", "")
            if desc:
                element["description"] = desc

        # Add state indicators
        props = node.get("properties", [])
        for prop in props:
            prop_name = prop.get("name", "")
            prop_value = prop.get("value", {}).get("value")

            if prop_name == "focused" and prop_value:
                element["focused"] = True
            elif prop_name == "disabled" and prop_value:
                element["disabled"] = True
            elif prop_name == "checked":
                element["checked"] = prop_value
            elif prop_name == "selected" and prop_value:
                element["selected"] = True

        elements.append(element)

    return {
        "url": await browser.get_url(),
        "title": await browser.get_title(),
        "element_count": len(elements),
        "elements": elements[:100],  # Limit to avoid token overflow
    }


async def screenshot(
    selector: Optional[str] = None,
    full_page: bool = False,
    format: str = "png",
    quality: int = 80,
) -> dict:
    """
    Take a screenshot.

    Args:
        selector: CSS selector of element to capture (or full viewport)
        full_page: Capture full scrollable page
        format: Image format - "png", "jpeg", or "webp"
        quality: Quality for jpeg/webp (0-100)

    Returns:
        Dict with base64 encoded image
    """
    browser = await browser_manager.launch()
    await browser.enable_domain("Page")

    params = {
        "format": format,
    }

    if format in ("jpeg", "webp"):
        params["quality"] = quality

    if full_page:
        # Get full page dimensions
        await browser.enable_domain("Runtime")
        metrics = await browser.cdp.send("Runtime.evaluate", {
            "expression": "JSON.stringify({width: document.documentElement.scrollWidth, height: document.documentElement.scrollHeight})",
            "returnByValue": True,
        })
        dims = eval(metrics["result"]["value"])

        # Set viewport to full page size
        await browser.cdp.send("Emulation.setDeviceMetricsOverride", {
            "width": dims["width"],
            "height": dims["height"],
            "deviceScaleFactor": 1,
            "mobile": False,
        })

        params["captureBeyondViewport"] = True

    if selector:
        # Get element bounds
        from ..dom import get_node_id, get_element_bounds
        node_id = await get_node_id(selector)
        bounds = await get_element_bounds(node_id)
        params["clip"] = {
            "x": bounds["x"],
            "y": bounds["y"],
            "width": bounds["width"],
            "height": bounds["height"],
            "scale": 1,
        }

    result = await browser.cdp.send("Page.captureScreenshot", params)

    # Reset viewport if we changed it
    if full_page:
        await browser.cdp.send("Emulation.clearDeviceMetricsOverride")

    return {
        "format": format,
        "size_bytes": len(result["data"]) * 3 // 4,  # Approximate decoded size
        "image": result["data"],  # Base64 encoded
    }


async def get_text(selector: Optional[str] = None) -> dict:
    """
    Get text content from page or element.

    Args:
        selector: CSS selector (or entire page if None)

    Returns:
        Dict with text content
    """
    browser = await browser_manager.launch()
    await browser.enable_domain("Runtime")

    if selector:
        script = f"""
            const el = document.querySelector('{selector}');
            el ? el.innerText : null;
        """
    else:
        script = "document.body.innerText"

    result = await browser.cdp.send("Runtime.evaluate", {
        "expression": script,
        "returnByValue": True,
    })

    text = result.get("result", {}).get("value")
    if text is None:
        return {"success": False, "error": f"Element not found: {selector}"}

    return {
        "success": True,
        "text": text,
        "length": len(text),
    }


async def get_html(
    selector: Optional[str] = None,
    outer: bool = True,
) -> dict:
    """
    Get HTML content from page or element.

    Args:
        selector: CSS selector (or entire page if None)
        outer: Get outerHTML (True) or innerHTML (False)

    Returns:
        Dict with HTML content
    """
    browser = await browser_manager.launch()
    await browser.enable_domain("Runtime")

    prop = "outerHTML" if outer else "innerHTML"

    if selector:
        script = f"""
            const el = document.querySelector('{selector}');
            el ? el.{prop} : null;
        """
    else:
        script = f"document.documentElement.{prop}"

    result = await browser.cdp.send("Runtime.evaluate", {
        "expression": script,
        "returnByValue": True,
    })

    html = result.get("result", {}).get("value")
    if html is None:
        return {"success": False, "error": f"Element not found: {selector}"}

    return {
        "success": True,
        "html": html,
        "length": len(html),
    }


async def get_console_logs(
    level: Optional[str] = None,
    clear: bool = False,
) -> dict:
    """
    Get browser console logs.

    Note: This captures logs from when the Console domain was enabled.
    Call this early if you want to capture all logs.

    Args:
        level: Filter by level - "log", "warning", "error", "info"
        clear: Clear logs after retrieval

    Returns:
        Dict with log entries
    """
    browser = await browser_manager.launch()

    # We need to have been collecting logs - enable console domain
    await browser.enable_domain("Console")

    # Note: CDP doesn't have a "get all logs" command.
    # We'd need to have been collecting them via events.
    # For now, return a message about this limitation.

    return {
        "success": True,
        "message": "Console log collection requires event subscription. Use browsy_evaluate to check console.",
        "logs": [],
    }


async def evaluate(expression: str) -> dict:
    """
    Execute JavaScript in the page context.

    Args:
        expression: JavaScript expression to evaluate

    Returns:
        Dict with result or error
    """
    browser = await browser_manager.launch()
    await browser.enable_domain("Runtime")

    result = await browser.cdp.send("Runtime.evaluate", {
        "expression": expression,
        "returnByValue": True,
        "awaitPromise": True,  # Wait for promises
    })

    if "exceptionDetails" in result:
        exception = result["exceptionDetails"]
        return {
            "success": False,
            "error": exception.get("text", "Unknown error"),
            "exception": exception,
        }

    value = result.get("result", {}).get("value")
    return {
        "success": True,
        "result": value,
        "type": result.get("result", {}).get("type"),
    }


async def get_cookies(domain: Optional[str] = None) -> dict:
    """
    Get browser cookies.

    Args:
        domain: Filter by domain (optional)

    Returns:
        Dict with cookies list
    """
    browser = await browser_manager.launch()
    await browser.enable_domain("Network")

    result = await browser.cdp.send("Network.getCookies")
    cookies = result.get("cookies", [])

    if domain:
        cookies = [c for c in cookies if domain in c.get("domain", "")]

    # Simplify cookie data for output
    simple_cookies = []
    for c in cookies:
        simple_cookies.append({
            "name": c.get("name"),
            "value": c.get("value"),
            "domain": c.get("domain"),
            "path": c.get("path"),
            "expires": c.get("expires"),
            "secure": c.get("secure"),
            "httpOnly": c.get("httpOnly"),
        })

    return {
        "success": True,
        "count": len(simple_cookies),
        "cookies": simple_cookies,
    }
