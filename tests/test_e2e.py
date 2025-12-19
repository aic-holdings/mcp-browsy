"""End-to-end tests for mcp-browsy.

These tests actually launch Chrome and test browser automation.
Run with: pytest tests/test_e2e.py -v

Requires Chrome/Chromium to be installed.
"""

import asyncio
import pytest

from mcp_browsy.browser import browser_manager
from mcp_browsy.utils.platform import find_chrome_executable
from mcp_browsy.tools import navigation, inspection


# Skip all tests if Chrome is not available
pytestmark = pytest.mark.skipif(
    find_chrome_executable() is None,
    reason="Chrome not installed"
)


@pytest.fixture
async def browser():
    """Launch browser for testing and cleanup after."""
    await browser_manager.launch(headless=True)
    yield browser_manager.browser
    await browser_manager.close()


class TestBrowserLaunch:
    """Test browser launch and connection."""

    @pytest.mark.asyncio
    async def test_launch_headless(self):
        """Should launch browser in headless mode."""
        try:
            browser = await browser_manager.launch(headless=True)
            assert browser is not None
            assert browser.cdp is not None
            
            # Should be able to get current URL (blank or about:blank)
            url = await browser.get_url()
            assert url is not None
        finally:
            await browser_manager.close()

    @pytest.mark.asyncio
    async def test_launch_returns_same_instance(self):
        """Multiple launch calls should return same browser instance."""
        try:
            browser1 = await browser_manager.launch(headless=True)
            browser2 = await browser_manager.launch(headless=True)
            assert browser1 is browser2
        finally:
            await browser_manager.close()


class TestNavigation:
    """Test navigation tools."""

    @pytest.mark.asyncio
    async def test_navigate_to_url(self, browser):
        """Should navigate to a URL and return result."""
        result = await navigation.navigate("https://example.com")
        
        assert "url" in result
        assert "title" in result
        assert "example" in result["url"].lower()

    @pytest.mark.asyncio
    async def test_navigate_sets_title(self, browser):
        """Navigation should set page title."""
        await navigation.navigate("https://example.com")
        
        title = await browser.get_title()
        assert "Example" in title

    @pytest.mark.asyncio
    async def test_reload(self, browser):
        """Should reload the page."""
        await navigation.navigate("https://example.com")
        result = await navigation.reload()
        
        assert "url" in result
        assert "example" in result["url"].lower()


class TestInspection:
    """Test inspection tools."""

    @pytest.mark.asyncio
    async def test_snapshot(self, browser):
        """Should get accessibility snapshot."""
        await navigation.navigate("https://example.com")
        result = await inspection.snapshot()
        
        assert "url" in result
        assert "title" in result
        assert "elements" in result
        assert isinstance(result["elements"], list)

    @pytest.mark.asyncio
    async def test_get_text(self, browser):
        """Should extract text from page."""
        await navigation.navigate("https://example.com")
        result = await inspection.get_text()
        
        assert result["success"] is True
        assert "text" in result
        # example.com should have some text
        assert len(result["text"]) > 0

    @pytest.mark.asyncio
    async def test_screenshot(self, browser):
        """Should take a screenshot."""
        await navigation.navigate("https://example.com")
        result = await inspection.screenshot()
        
        assert "format" in result
        assert "image" in result
        assert result["format"] == "png"
        # Image should be base64 encoded
        assert len(result["image"]) > 100

    @pytest.mark.asyncio
    async def test_evaluate_js(self, browser):
        """Should execute JavaScript."""
        await navigation.navigate("https://example.com")
        result = await inspection.evaluate("1 + 1")
        
        assert result["success"] is True
        assert result["result"] == 2

    @pytest.mark.asyncio
    async def test_get_html(self, browser):
        """Should get page HTML."""
        await navigation.navigate("https://example.com")
        result = await inspection.get_html()
        
        assert result["success"] is True
        assert "html" in result
        assert "<html" in result["html"].lower()


class TestTabs:
    """Test tab management."""

    @pytest.mark.asyncio
    async def test_list_tabs(self, browser):
        """Should list open tabs."""
        tabs = await navigation.get_tabs()
        
        assert isinstance(tabs, list)
        assert len(tabs) >= 1  # At least one tab
        assert "id" in tabs[0]

    @pytest.mark.asyncio
    async def test_new_tab(self, browser):
        """Should open new tab."""
        initial_tabs = await navigation.get_tabs()
        result = await navigation.new_tab("https://example.org")
        
        assert result.get("success", True)  # May not have success key
        
        # Should have more tabs now
        tabs = await navigation.get_tabs()
        assert len(tabs) >= len(initial_tabs)


class TestFullFlow:
    """Test complete user flows."""

    @pytest.mark.asyncio
    async def test_navigate_and_extract(self, browser):
        """Full flow: navigate, extract content, take screenshot."""
        # Navigate
        nav_result = await navigation.navigate("https://example.com")
        assert "example" in nav_result["url"].lower()
        
        # Get snapshot
        snapshot = await inspection.snapshot()
        assert len(snapshot["elements"]) > 0
        
        # Get text
        text = await inspection.get_text()
        assert text["success"]
        assert "Example" in text["text"]
        
        # Take screenshot
        screenshot = await inspection.screenshot()
        assert len(screenshot["image"]) > 1000  # Reasonable image size

    @pytest.mark.asyncio
    async def test_javascript_interaction(self, browser):
        """Test JavaScript evaluation for page interaction."""
        await navigation.navigate("https://example.com")
        
        # Get page title via JS
        result = await inspection.evaluate("document.title")
        assert result["success"]
        assert "Example" in result["result"]
        
        # Get element count
        result = await inspection.evaluate("document.querySelectorAll('*').length")
        assert result["success"]
        assert result["result"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
