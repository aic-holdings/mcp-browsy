"""Unit tests for mcp-browsy components.

Tests CDP client and BrowserManager initialization without requiring Chrome.
"""

import pytest

from mcp_browsy.cdp import CDPClient
from mcp_browsy.browser import Browser, BrowserManager
from mcp_browsy.dom import ElementNotFoundError, ElementNotVisibleError


class TestCDPClient:
    """Test CDP client initialization and state."""

    def test_init(self):
        """CDPClient should initialize without error."""
        client = CDPClient()
        assert client is not None
        assert client.ws is None  # Not connected yet

    def test_not_connected_by_default(self):
        """CDPClient should not be connected on init."""
        client = CDPClient()
        assert not hasattr(client, '_connected') or not client._connected


class TestBrowser:
    """Test Browser class initialization."""

    def test_init(self):
        """Browser should initialize with CDP client."""
        cdp = CDPClient()
        browser = Browser(cdp, "test-target-id")
        assert browser.cdp is cdp
        assert browser.target_id == "test-target-id"

    def test_enabled_domains_empty(self):
        """Browser should start with no domains enabled."""
        cdp = CDPClient()
        browser = Browser(cdp, "test-target-id")
        assert len(browser._enabled_domains) == 0


class TestBrowserManager:
    """Test BrowserManager singleton."""

    def test_init(self):
        """BrowserManager should initialize."""
        manager = BrowserManager()
        assert manager is not None
        assert manager.browser is None  # Not launched yet

    def test_singleton_pattern(self):
        """Module should export a singleton browser_manager."""
        from mcp_browsy.browser import browser_manager
        assert browser_manager is not None
        assert isinstance(browser_manager, BrowserManager)


class TestDOMExceptions:
    """Test DOM-related exceptions."""

    def test_element_not_found_error(self):
        """ElementNotFoundError should be raisable with message."""
        with pytest.raises(ElementNotFoundError) as exc_info:
            raise ElementNotFoundError("test selector")
        assert "test selector" in str(exc_info.value)

    def test_element_not_visible_error(self):
        """ElementNotVisibleError should be raisable with message."""
        with pytest.raises(ElementNotVisibleError) as exc_info:
            raise ElementNotVisibleError("element has no bounds")
        assert "element has no bounds" in str(exc_info.value)


class TestMCPServer:
    """Test MCP server registration."""

    def test_mcp_instance(self):
        """MCP server should be created."""
        from mcp_browsy import mcp
        assert mcp is not None
        assert mcp.name == "mcp-browsy"

    def test_tools_registered(self):
        """All expected tools should be registered."""
        from mcp_browsy import mcp
        
        tools = mcp._tool_manager._tools
        expected_tools = [
            "browsy_launch",
            "browsy_close",
            "browsy_navigate",
            "browsy_click",
            "browsy_type",
            "browsy_snapshot",
            "browsy_screenshot",
        ]
        
        for tool_name in expected_tools:
            assert tool_name in tools, f"Missing tool: {tool_name}"

    def test_tool_count(self):
        """Should have at least 20 tools registered."""
        from mcp_browsy import mcp
        
        tools = mcp._tool_manager._tools
        assert len(tools) >= 20, f"Expected 20+ tools, got {len(tools)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
