"""SSE manager: connection registry, streaming response helpers."""
import asyncio
import json
from typing import Callable, Optional

from fastapi import Request
from fastapi.responses import StreamingResponse

from server.broadcast.event_bus import EventBus

HEARTBEAT_INTERVAL = 15.0  # seconds


async def sse_stream(
    request: Request,
    bus: EventBus,
    player_id: str,
    room_id: str,
    middle_id: str,
    on_disconnect: Optional[Callable] = None,
) -> StreamingResponse:
    queue = await bus.subscribe(player_id, room_id, middle_id)

    async def generator():
        try:
            # Initial connection ack
            yield f"data: {json.dumps({'type': 'connected', 'player_id': player_id})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_INTERVAL)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            await bus.unsubscribe(queue)
            if on_disconnect is not None:
                asyncio.create_task(on_disconnect())

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
