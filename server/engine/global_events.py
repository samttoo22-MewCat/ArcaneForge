"""Server-side internal event queue for cross-zone NPC coordination.

Separate from the SSE EventBus (which is client-facing).
This queue lets game logic (player arrival, combat start) wake up
NPC AI in adjacent rooms within the same middle_place.
"""
import asyncio
from dataclasses import dataclass, field


@dataclass
class ServerEvent:
    event_type: str       # "player_entered" | "combat_started"
    place_id: str         # room where the trigger happened
    middle_id: str        # zone (middle_place) of the trigger
    data: dict = field(default_factory=dict)


_queue: asyncio.Queue[ServerEvent] = asyncio.Queue(maxsize=500)


def emit_nowait(event: ServerEvent) -> None:
    """Non-blocking emit. Drops silently if queue is full (backpressure)."""
    try:
        _queue.put_nowait(event)
    except asyncio.QueueFull:
        pass


def drain() -> list[ServerEvent]:
    """Drain all pending events synchronously. Called once per NPC tick."""
    events: list[ServerEvent] = []
    while not _queue.empty():
        try:
            events.append(_queue.get_nowait())
        except asyncio.QueueEmpty:
            break
    return events
