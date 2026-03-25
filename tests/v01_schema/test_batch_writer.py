"""V-01: Batch writer logic tests (no live DB required)."""
import asyncio
import pytest
from server.db.batch_writer import BatchWriter, WriteOperation


class MockGraph:
    def __init__(self):
        self.queries = []

    async def query(self, cypher: str, params: dict = None):
        self.queries.append((cypher, params))


async def test_batch_writer_flushes_queue():
    graph = MockGraph()
    writer = BatchWriter(graph, interval=0.05)
    writer.enqueue(WriteOperation("player", "id", {"id": "p1", "hp": 90}))
    writer.enqueue(WriteOperation("player", "id", {"id": "p2", "hp": 80}))

    writer.start()
    await asyncio.sleep(0.15)  # wait for at least one flush
    await writer.stop()

    assert len(graph.queries) >= 1
    # Both player operations should have been batched together
    combined_query = " ".join(q for q, _ in graph.queries)
    assert "player" in combined_query


async def test_empty_queue_no_query():
    graph = MockGraph()
    writer = BatchWriter(graph, interval=0.05)
    writer.start()
    await asyncio.sleep(0.15)
    await writer.stop()
    assert len(graph.queries) == 0


async def test_stop_flushes_remaining():
    graph = MockGraph()
    writer = BatchWriter(graph, interval=9999)  # interval too long to auto-flush
    writer.enqueue(WriteOperation("player", "id", {"id": "p1", "hp": 50}))

    writer.start()
    await writer.stop()  # stop should flush immediately

    assert len(graph.queries) >= 1
