"""
browsy-hq client for mcp-browsy.

When BROWSY_HQ_URL is set, mcp-browsy routes all browser operations
through browsy-hq instead of controlling Chrome locally.
"""

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class HQClient:
    """Client for browsy-hq API."""

    def __init__(self, hq_url: str, api_key: str):
        self.hq_url = hq_url.rstrip("/")
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None
        self.session_id: Optional[str] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={"X-API-Key": self.api_key}
            )
        return self._client

    async def create_browser(self, headless: bool = False) -> str:
        """Create a browser session via HQ, returns session_id."""
        client = await self._get_client()
        resp = await client.post(
            f"{self.hq_url}/browsers",
            json={"headless": headless, "owner": "mcp-browsy"}
        )
        resp.raise_for_status()
        data = resp.json()
        self.session_id = data["session_id"]
        logger.info(f"Created browser session: {self.session_id} on {data.get('daemon')}")
        return self.session_id

    async def close_browser(self) -> bool:
        """Close the current browser session."""
        if not self.session_id:
            return False
        client = await self._get_client()
        resp = await client.delete(f"{self.hq_url}/browsers/{self.session_id}")
        self.session_id = None
        return resp.status_code == 200

    async def navigate(self, url: str) -> dict:
        """Navigate to URL."""
        if not self.session_id:
            raise RuntimeError("No browser session")
        client = await self._get_client()
        resp = await client.post(
            f"{self.hq_url}/browsers/{self.session_id}/navigate",
            params={"url": url}
        )
        resp.raise_for_status()
        return resp.json()

    async def cdp(self, method: str, params: Optional[dict] = None) -> dict:
        """Send CDP command."""
        if not self.session_id:
            raise RuntimeError("No browser session")
        client = await self._get_client()
        resp = await client.post(
            f"{self.hq_url}/browsers/{self.session_id}/cdp",
            params={"method": method},
            json={"params": params} if params else None
        )
        resp.raise_for_status()
        return resp.json()

    async def screenshot(self) -> dict:
        """Get screenshot."""
        if not self.session_id:
            raise RuntimeError("No browser session")
        client = await self._get_client()
        resp = await client.get(f"{self.hq_url}/browsers/{self.session_id}/screenshot")
        resp.raise_for_status()
        return resp.json()

    async def snapshot(self) -> dict:
        """Get accessibility snapshot."""
        if not self.session_id:
            raise RuntimeError("No browser session")
        client = await self._get_client()
        resp = await client.get(f"{self.hq_url}/browsers/{self.session_id}/snapshot")
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        """Close client."""
        await self.close_browser()
        if self._client:
            await self._client.aclose()


# Global HQ client (set if BROWSY_HQ_URL is configured)
hq_client: Optional[HQClient] = None


def get_hq_client() -> Optional[HQClient]:
    """Get or create HQ client if configured."""
    global hq_client
    hq_url = os.environ.get("BROWSY_HQ_URL")
    api_key = os.environ.get("BROWSY_HQ_API_KEY")
    
    if hq_url and api_key:
        if hq_client is None:
            hq_client = HQClient(hq_url, api_key)
            logger.info(f"Using browsy-hq at {hq_url}")
        return hq_client
    return None


def is_hq_mode() -> bool:
    """Check if we're in HQ mode."""
    return os.environ.get("BROWSY_HQ_URL") is not None
