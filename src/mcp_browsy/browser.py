"""
Browser Manager - Launch and connect to Chrome.

Handles:
- Launching Chrome with CDP enabled
- Connecting to existing Chrome instances
- Tab/target management
- Graceful shutdown
"""

import asyncio
import logging
import subprocess
from typing import Optional

import httpx

from .cdp import CDPClient
from .utils.platform import (
    find_chrome_executable,
    find_default_profile_dir,
    is_profile_locked,
    get_temp_profile_dir,
)

logger = logging.getLogger(__name__)


class BrowserError(Exception):
    """Browser-related error."""
    pass


class Browser:
    """
    Represents a connected browser instance.

    Provides high-level operations and manages the CDP connection.
    """

    def __init__(self, cdp: CDPClient, target_id: str):
        self.cdp = cdp
        self.target_id = target_id
        self._enabled_domains: set[str] = set()

    async def enable_domain(self, domain: str) -> None:
        """Enable a CDP domain if not already enabled."""
        if domain not in self._enabled_domains:
            await self.cdp.send(f"{domain}.enable")
            self._enabled_domains.add(domain)

    async def navigate(self, url: str, wait_until: str = "load") -> dict:
        """
        Navigate to a URL and wait for it to load.

        Args:
            url: URL to navigate to
            wait_until: Wait condition - "load", "domcontentloaded", or "networkidle"

        Returns:
            Navigation result with frameId
        """
        await self.enable_domain("Page")

        # Set up event waiting based on condition
        if wait_until == "load":
            event_name = "Page.loadEventFired"
        elif wait_until == "domcontentloaded":
            event_name = "Page.domContentEventFired"
        else:
            event_name = "Page.loadEventFired"

        # Start navigation
        nav_result = await self.cdp.send("Page.navigate", {"url": url})

        # Wait for the load event
        try:
            await self.cdp.wait_for_event(event_name, timeout=30.0)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for {event_name}, continuing anyway")

        return nav_result

    async def get_url(self) -> str:
        """Get the current page URL."""
        await self.enable_domain("Runtime")
        result = await self.cdp.send(
            "Runtime.evaluate",
            {"expression": "window.location.href", "returnByValue": True}
        )
        return result.get("result", {}).get("value", "")

    async def get_title(self) -> str:
        """Get the current page title."""
        await self.enable_domain("Runtime")
        result = await self.cdp.send(
            "Runtime.evaluate",
            {"expression": "document.title", "returnByValue": True}
        )
        return result.get("result", {}).get("value", "")

    async def close(self) -> None:
        """Close the browser connection."""
        await self.cdp.close()


class BrowserManager:
    """
    Manages browser lifecycle and connections.

    Supports:
    - Launching new Chrome instances
    - Connecting to existing instances
    - Hybrid mode (try connect, then launch)
    """

    def __init__(self, port: int = 9222):
        self.port = port
        self.process: Optional[subprocess.Popen] = None
        self.browser: Optional[Browser] = None
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=5.0)
        return self._http_client

    async def _get_targets(self) -> list[dict]:
        """Get list of available CDP targets."""
        client = await self._get_http_client()
        try:
            response = await client.get(f"http://localhost:{self.port}/json/list")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.debug(f"Failed to get targets: {e}")
            return []

    async def _get_page_target(self) -> Optional[dict]:
        """Find the first 'page' type target."""
        targets = await self._get_targets()
        for target in targets:
            if target.get("type") == "page":
                return target
        return None

    async def _try_connect(self) -> bool:
        """Attempt to connect to an existing Chrome instance."""
        target = await self._get_page_target()
        if not target:
            return False

        ws_url = target.get("webSocketDebuggerUrl")
        if not ws_url:
            return False

        try:
            cdp = CDPClient()
            await cdp.connect(ws_url)
            self.browser = Browser(cdp, target["id"])
            logger.info(f"Connected to existing browser: {target.get('title', 'Unknown')}")
            return True
        except Exception as e:
            logger.debug(f"Failed to connect to existing browser: {e}")
            return False

    async def launch(
        self,
        headless: bool = False,
        use_profile: bool = True,
        timeout: float = 30.0,
    ) -> Browser:
        """
        Launch Chrome or connect to an existing instance.

        Uses hybrid approach:
        1. Try to connect to existing Chrome with CDP on specified port
        2. If not available, launch new Chrome instance

        Args:
            headless: Run in headless mode
            use_profile: Use default Chrome profile (for logged-in sessions)
            timeout: Timeout for connection

        Returns:
            Browser instance

        Raises:
            BrowserError: If Chrome cannot be found or launched
        """
        if self.browser and self.browser.cdp.connected:
            logger.debug("Already connected, reusing existing browser")
            return self.browser

        # Try connecting first
        if await self._try_connect():
            return self.browser

        # Find Chrome executable
        chrome_path = find_chrome_executable()
        if not chrome_path:
            raise BrowserError(
                "Chrome executable not found. Please install Chrome or Chromium."
            )

        # Build launch arguments
        args = [
            chrome_path,
            f"--remote-debugging-port={self.port}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            "--disable-default-apps",
            "--disable-extensions",
            "--disable-sync",
            "--disable-translate",
            "--metrics-recording-only",
            "--mute-audio",
            "--safebrowsing-disable-auto-update",
        ]

        if headless:
            args.extend(["--headless=new", "--disable-gpu"])

        # Handle user profile
        if use_profile:
            profile_dir = find_default_profile_dir()
            if profile_dir:
                if is_profile_locked(profile_dir):
                    logger.warning(
                        "Default profile is locked (Chrome is running). "
                        "Using temporary profile. For logged-in sessions, "
                        "close Chrome or launch it with --remote-debugging-port."
                    )
                    args.append(f"--user-data-dir={get_temp_profile_dir()}")
                else:
                    args.append(f"--user-data-dir={profile_dir}")
            else:
                logger.info("No default profile found, using temporary profile")
                args.append(f"--user-data-dir={get_temp_profile_dir()}")
        else:
            args.append(f"--user-data-dir={get_temp_profile_dir()}")

        logger.info(f"Launching Chrome: {chrome_path}")
        logger.debug(f"Chrome args: {' '.join(args)}")

        # Launch process
        try:
            self.process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            raise BrowserError(f"Failed to launch Chrome: {e}")

        # Wait for CDP to become available
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            if await self._try_connect():
                logger.info("Chrome launched and connected successfully")
                return self.browser
            await asyncio.sleep(0.5)

        # Cleanup on failure
        if self.process:
            self.process.terminate()
            self.process = None

        raise BrowserError(
            f"Failed to connect to Chrome after {timeout}s. "
            "Check if the port is available or Chrome can start."
        )

    async def get_tabs(self) -> list[dict]:
        """Get list of open tabs."""
        targets = await self._get_targets()
        tabs = []
        for target in targets:
            if target.get("type") == "page":
                tabs.append({
                    "id": target["id"],
                    "url": target.get("url", ""),
                    "title": target.get("title", ""),
                    "active": target["id"] == (self.browser.target_id if self.browser else None),
                })
        return tabs

    async def switch_tab(self, tab_id: str) -> bool:
        """Switch to a different tab."""
        targets = await self._get_targets()
        target = next((t for t in targets if t["id"] == tab_id), None)

        if not target or "webSocketDebuggerUrl" not in target:
            return False

        # Close current connection and connect to new target
        if self.browser:
            await self.browser.cdp.close()

        cdp = CDPClient()
        await cdp.connect(target["webSocketDebuggerUrl"])
        self.browser = Browser(cdp, tab_id)

        # Bring tab to front
        await cdp.send("Page.bringToFront")
        return True

    async def new_tab(self, url: Optional[str] = None) -> dict:
        """Open a new tab."""
        client = await self._get_http_client()

        # Create new target via PUT request
        create_url = f"http://localhost:{self.port}/json/new"
        if url:
            create_url += f"?{url}"

        response = await client.put(create_url)
        response.raise_for_status()
        target = response.json()

        return {
            "id": target["id"],
            "url": target.get("url", ""),
            "title": target.get("title", ""),
        }

    async def close_tab(self, tab_id: str) -> bool:
        """Close a tab by ID."""
        client = await self._get_http_client()

        try:
            response = await client.get(f"http://localhost:{self.port}/json/close/{tab_id}")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        """Close browser and cleanup."""
        if self.browser:
            await self.browser.close()
            self.browser = None

        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

        logger.info("Browser manager closed")


# Singleton instance for use across tools
browser_manager = BrowserManager()
