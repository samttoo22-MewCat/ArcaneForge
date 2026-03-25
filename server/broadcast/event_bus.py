"""asyncio event bus: per-connection queues with room/middle/global routing."""
import asyncio
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional


QUEUE_MAX = 100  # backpressure cap per connection


@dataclass
class Subscription:
    queue: asyncio.Queue
    player_id: str
    room_id: str
    middle_id: str


class EventBus:
    def __init__(self):
        self._room_subs: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._middle_subs: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._global_subs: set[asyncio.Queue] = set()
        self._sub_index: dict[asyncio.Queue, Subscription] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, player_id: str, room_id: str, middle_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_MAX)
        sub = Subscription(queue=queue, player_id=player_id, room_id=room_id, middle_id=middle_id)
        async with self._lock:
            self._room_subs[room_id].add(queue)
            self._middle_subs[middle_id].add(queue)
            self._global_subs.add(queue)
            self._sub_index[queue] = sub
        return queue

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        async with self._lock:
            sub = self._sub_index.pop(queue, None)
            if sub is None:
                return
            self._room_subs[sub.room_id].discard(queue)
            self._middle_subs[sub.middle_id].discard(queue)
            self._global_subs.discard(queue)

    async def move_subscriber(self, queue: asyncio.Queue, new_room_id: str, new_middle_id: str) -> None:
        async with self._lock:
            sub = self._sub_index.get(queue)
            if sub is None:
                return
            self._room_subs[sub.room_id].discard(queue)
            self._middle_subs[sub.middle_id].discard(queue)
            sub.room_id = new_room_id
            sub.middle_id = new_middle_id
            self._room_subs[new_room_id].add(queue)
            self._middle_subs[new_middle_id].add(queue)

    async def publish_room(self, room_id: str, event: dict) -> None:
        await self._publish_to(self._room_subs.get(room_id, set()), event)

    async def publish_middle(self, middle_id: str, event: dict) -> None:
        await self._publish_to(self._middle_subs.get(middle_id, set()), event)

    async def publish_global(self, event: dict) -> None:
        await self._publish_to(self._global_subs, event)

    async def _publish_to(self, queues: set[asyncio.Queue], event: dict) -> None:
        dead: list[asyncio.Queue] = []
        for q in list(queues):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            await self.unsubscribe(q)

    @property
    def connection_count(self) -> int:
        return len(self._sub_index)
