"""
Chrome DevTools Protocol (CDP) client.

Provides async WebSocket communication with Chrome's debugging protocol.
Features:
- Async message handling
- Event subscriptions
- Automatic reconnection
- Proper error handling
"""

import asyncio
import json
import logging
from typing import Any, Callable, Optional
from collections.abc import Awaitable

import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)


class CDPError(Exception):
    """CDP command error."""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"CDP Error {code}: {message}")


class CDPClient:
    """
    Async CDP client using WebSockets.

    Handles:
    - Command/response matching via message IDs
    - Event subscriptions and dispatch
    - Connection lifecycle
    """

    def __init__(self):
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._callbacks: dict[int, asyncio.Future] = {}
        self._event_handlers: dict[str, list[Callable[[dict], Awaitable[None]]]] = {}
        self._id_counter = 0
        self._listen_task: Optional[asyncio.Task] = None
        self._connected = False
        self._ws_url: Optional[str] = None

    @property
    def connected(self) -> bool:
        """Check if connected to browser."""
        return self._connected and self.ws is not None and not self.ws.closed

    async def connect(self, ws_url: str) -> None:
        """Connect to the browser via WebSocket."""
        if self.connected:
            logger.warning("Already connected, closing existing connection")
            await self.close()

        logger.info(f"Connecting to CDP at {ws_url}")
        self._ws_url = ws_url

        try:
            self.ws = await websockets.connect(
                ws_url,
                max_size=None,  # No limit on message size (screenshots can be large)
                ping_interval=30,
                ping_timeout=10,
            )
            self._connected = True
            self._listen_task = asyncio.create_task(self._listen_loop())
            logger.info("CDP connection established")
        except Exception as e:
            logger.error(f"Failed to connect to CDP: {e}")
            raise

    async def _listen_loop(self) -> None:
        """Listen for incoming messages from the browser."""
        try:
            async for message in self.ws:
                await self._handle_message(message)
        except ConnectionClosed as e:
            logger.warning(f"CDP connection closed: {e}")
            self._connected = False
        except Exception as e:
            logger.error(f"CDP listen loop error: {e}")
            self._connected = False

    async def _handle_message(self, message: str) -> None:
        """Process an incoming CDP message."""
        try:
            data = json.loads(message)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse CDP message: {e}")
            return

        # Handle command responses (have "id" field)
        if "id" in data:
            msg_id = data["id"]
            if msg_id in self._callbacks:
                future = self._callbacks.pop(msg_id)
                if "error" in data:
                    error = data["error"]
                    future.set_exception(
                        CDPError(error.get("code", -1), error.get("message", "Unknown error"))
                    )
                else:
                    future.set_result(data.get("result", {}))

        # Handle events (have "method" field)
        if "method" in data:
            method = data["method"]
            params = data.get("params", {})

            if method in self._event_handlers:
                for handler in self._event_handlers[method]:
                    try:
                        asyncio.create_task(handler(params))
                    except Exception as e:
                        logger.error(f"Event handler error for {method}: {e}")

    async def send(
        self,
        method: str,
        params: Optional[dict] = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """
        Send a CDP command and wait for the result.

        Args:
            method: CDP method name (e.g., "Page.navigate")
            params: Optional parameters dict
            timeout: Timeout in seconds

        Returns:
            The result dict from the CDP response

        Raises:
            CDPError: If the command fails
            RuntimeError: If not connected
            asyncio.TimeoutError: If timeout exceeded
        """
        if not self.connected:
            raise RuntimeError("CDP client not connected")

        self._id_counter += 1
        msg_id = self._id_counter

        message = {
            "id": msg_id,
            "method": method,
            "params": params or {},
        }

        future: asyncio.Future[dict] = asyncio.Future()
        self._callbacks[msg_id] = future

        try:
            await self.ws.send(json.dumps(message))
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._callbacks.pop(msg_id, None)
            raise asyncio.TimeoutError(f"CDP command {method} timed out after {timeout}s")

    def on(self, event: str, handler: Callable[[dict], Awaitable[None]]) -> None:
        """
        Register an event handler.

        Args:
            event: CDP event name (e.g., "Page.loadEventFired")
            handler: Async callback function
        """
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def off(self, event: str, handler: Optional[Callable] = None) -> None:
        """
        Remove an event handler.

        Args:
            event: CDP event name
            handler: Specific handler to remove, or None to remove all
        """
        if event in self._event_handlers:
            if handler is None:
                del self._event_handlers[event]
            else:
                self._event_handlers[event] = [
                    h for h in self._event_handlers[event] if h != handler
                ]

    async def wait_for_event(
        self,
        event: str,
        predicate: Optional[Callable[[dict], bool]] = None,
        timeout: float = 30.0,
    ) -> dict:
        """
        Wait for a specific event to occur.

        Args:
            event: CDP event name to wait for
            predicate: Optional function to filter events
            timeout: Timeout in seconds

        Returns:
            The event params when the event fires
        """
        future: asyncio.Future[dict] = asyncio.Future()

        async def handler(params: dict) -> None:
            if predicate is None or predicate(params):
                if not future.done():
                    future.set_result(params)

        self.on(event, handler)
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            self.off(event, handler)

    async def close(self) -> None:
        """Close the CDP connection."""
        self._connected = False

        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None

        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None

        # Cancel any pending callbacks
        for future in self._callbacks.values():
            if not future.done():
                future.cancel()
        self._callbacks.clear()

        logger.info("CDP connection closed")
