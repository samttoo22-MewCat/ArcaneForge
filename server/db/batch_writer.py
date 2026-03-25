"""2-second batched UNWIND write loop for non-critical state updates."""
import asyncio
from dataclasses import dataclass, field
from typing import Any

from server.config import settings


@dataclass
class WriteOperation:
    label: str          # node label, e.g. "player"
    id_field: str       # primary key field name, e.g. "id"
    properties: dict[str, Any]


class BatchWriter:
    def __init__(self, graph, interval: float = None):
        self._graph = graph
        self._interval = interval or settings.batch_write_interval_seconds
        self._queue: asyncio.Queue[WriteOperation] = asyncio.Queue()
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._flush_loop(), name="batch_writer")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._flush()

    def enqueue(self, op: WriteOperation) -> None:
        self._queue.put_nowait(op)

    async def _flush_loop(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            await self._flush()

    async def _flush(self) -> None:
        if self._queue.empty():
            return

        # Drain queue and group by label
        ops: dict[str, list[dict]] = {}
        while not self._queue.empty():
            try:
                op = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            ops.setdefault(op.label, []).append((op.id_field, op.properties))

        for label, items in ops.items():
            # Build SET clause from all property keys seen
            all_keys: set[str] = set()
            for id_field, props in items:
                all_keys.update(props.keys())

            set_parts = ", ".join(f"n.{k} = row.{k}" for k in all_keys)
            rows = []
            for id_field, props in items:
                row = dict(props)
                rows.append(row)

            # We assume all items in a label batch share the same id_field
            first_id_field = items[0][0]
            cypher = (
                f"UNWIND $rows AS row "
                f"MATCH (n:{label} {{{first_id_field}: row.{first_id_field}}}) "
                f"SET {set_parts}"
            )
            try:
                await self._graph.query(cypher, {"rows": rows})
            except Exception as e:
                # Log but don't crash the flush loop
                print(f"[batch_writer] flush error for {label}: {e}")
