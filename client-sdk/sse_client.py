"""Async SSE client that connects to /events and dispatches events."""
import asyncio
import json
from typing import Callable, Awaitable

import httpx


EventHandler = Callable[[dict], Awaitable[None]]


class SSEClient:
    def __init__(self, server_url: str, player_id: str):
        self.server_url = server_url.rstrip("/")
        self.player_id = player_id
        self._handlers: dict[str, list[EventHandler]] = {}
        self._running = False

    def on(self, event_type: str, handler: EventHandler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def on_any(self, handler: EventHandler) -> None:
        self._handlers.setdefault("*", []).append(handler)

    async def connect(self) -> None:
        self._running = True
        url = f"{self.server_url}/events?player_id={self.player_id}"
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not self._running:
                        break
                    if line.startswith("data:"):
                        raw = line[5:].strip()
                        if not raw:
                            continue
                        try:
                            event = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        await self._dispatch(event)

    async def disconnect(self) -> None:
        self._running = False

    async def _dispatch(self, event: dict) -> None:
        event_type = event.get("event_type", event.get("type", "unknown"))
        handlers = self._handlers.get(event_type, []) + self._handlers.get("*", [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                print(f"[sse_client] handler error for {event_type}: {e}")
