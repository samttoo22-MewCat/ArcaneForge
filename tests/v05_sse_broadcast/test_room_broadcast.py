"""V-05: SSE event bus broadcast tests."""
import asyncio
import pytest
from server.broadcast.event_bus import EventBus


@pytest.fixture
def bus():
    return EventBus()


async def test_room_broadcast_reaches_all_subscribers(bus):
    queues = []
    for i in range(5):
        q = await bus.subscribe(f"player_{i}", room_id="room_01", middle_id="mid_01")
        queues.append(q)

    event = {"event_type": "test", "data": "hello"}
    await bus.publish_room("room_01", event)

    for q in queues:
        received = q.get_nowait()
        assert received == event


async def test_global_broadcast_reaches_all(bus):
    queues = []
    for i in range(10):
        q = await bus.subscribe(f"p{i}", room_id=f"room_{i}", middle_id=f"mid_{i}")
        queues.append(q)

    event = {"event_type": "global_announcement", "message": "server restart"}
    await bus.publish_global(event)

    for q in queues:
        received = q.get_nowait()
        assert received == event


async def test_room_broadcast_doesnt_reach_other_room(bus):
    q_room1 = await bus.subscribe("p1", room_id="room_A", middle_id="mid_01")
    q_room2 = await bus.subscribe("p2", room_id="room_B", middle_id="mid_01")

    await bus.publish_room("room_A", {"msg": "room_a_event"})

    assert not q_room2.empty() is False  # room_B queue should be empty
    assert q_room1.get_nowait() == {"msg": "room_a_event"}


async def test_middle_broadcast_reaches_same_middle(bus):
    q1 = await bus.subscribe("p1", room_id="room_A1", middle_id="mid_X")
    q2 = await bus.subscribe("p2", room_id="room_A2", middle_id="mid_X")
    q3 = await bus.subscribe("p3", room_id="room_B1", middle_id="mid_Y")

    await bus.publish_middle("mid_X", {"event_type": "explosion_sound"})

    assert not q1.empty()
    assert not q2.empty()
    assert q3.empty()


async def test_disconnect_cleans_up(bus):
    q = await bus.subscribe("p1", room_id="room_01", middle_id="mid_01")
    assert bus.connection_count == 1

    await bus.unsubscribe(q)
    assert bus.connection_count == 0

    # Publishing should not raise
    await bus.publish_room("room_01", {"event": "ghost"})


async def test_full_queue_removes_dead_connection(bus):
    from server.broadcast.event_bus import QUEUE_MAX
    q = await bus.subscribe("p1", room_id="room_01", middle_id="mid_01")

    # Fill the queue to capacity
    for i in range(QUEUE_MAX):
        q.put_nowait({"i": i})

    assert bus.connection_count == 1

    # One more event should trigger dead queue cleanup
    await bus.publish_room("room_01", {"overflow": True})

    assert bus.connection_count == 0


async def test_move_player_by_id_updates_routing(bus):
    """move_player() looks up the queue by player_id and reroutes it."""
    q = await bus.subscribe("hero", room_id="room_A", middle_id="mid_01")

    await bus.move_player("hero", new_room_id="room_B", new_middle_id="mid_02")

    await bus.publish_room("room_B", {"event": "new_room_event"})
    assert not q.empty()
    assert q.get_nowait() == {"event": "new_room_event"}

    # Old room should no longer reach this player
    await bus.publish_room("room_A", {"event": "old_room_event"})
    assert q.empty()

    # New middle should reach this player
    await bus.publish_middle("mid_02", {"event": "mid_event"})
    assert not q.empty()

    # Old middle should no longer reach this player
    q.get_nowait()  # drain
    await bus.publish_middle("mid_01", {"event": "old_mid_event"})
    assert q.empty()


async def test_move_subscriber_updates_routing(bus):
    q = await bus.subscribe("p1", room_id="room_A", middle_id="mid_01")

    await bus.move_subscriber(q, new_room_id="room_B", new_middle_id="mid_02")

    # Should receive room_B events
    await bus.publish_room("room_B", {"event": "new_room"})
    assert not q.empty()

    # Should NOT receive room_A events
    await bus.publish_room("room_A", {"event": "old_room"})
    item = q.get_nowait()
    assert item == {"event": "new_room"}
    assert q.empty()
