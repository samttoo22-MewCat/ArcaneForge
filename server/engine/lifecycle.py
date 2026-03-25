"""Player lifecycle events: death, respawn."""
import asyncio

from server.broadcast.event_bus import EventBus
from server.broadcast.event_types import PlayerDeathEvent, PlayerRespawnEvent
from server.config import settings
from server.db import optimistic_lock
from server.db.repositories import combat_repo, player_repo


async def handle_player_death(
    graph,
    redis,
    bus: EventBus,
    player_id: str,
    player_name: str,
    place_id: str,
    killer_id: str = "",
    killer_name: str = "",
) -> None:
    """Handle player death: clear combat state, broadcast event, schedule respawn."""
    player = await player_repo.get_player(graph, player_id)
    if not player:
        return

    room_id = player.get("combat_room_id")
    if room_id:
        await combat_repo.end_combat(redis, room_id)
    await player_repo.set_combat_state(graph, player_id, False, None)

    # Remove from room immediately (player is dead)
    await optimistic_lock.remove_player_from_room(graph, place_id, player_id)

    event = PlayerDeathEvent(
        player_id=player_id,
        player_name=player_name,
        place_id=place_id,
        killer_id=killer_id,
        killer_name=killer_name,
        respawn_in_seconds=settings.respawn_delay_seconds,
    ).to_dict()
    await bus.publish_room(place_id, event)

    asyncio.create_task(
        _do_respawn(graph, bus, player_id, player_name)
    )


async def _do_respawn(graph, bus: EventBus, player_id: str, player_name: str) -> None:
    await asyncio.sleep(settings.respawn_delay_seconds)

    player = await player_repo.get_player(graph, player_id)
    if not player:
        return

    hp_max = player.get("hp_max", player.get("max_hp", 100))
    mp_max = player.get("mp_max", player.get("max_mp", 50))
    spawn_id = settings.respawn_place_id

    await player_repo.respawn_player(graph, player_id, spawn_id, hp_max, mp_max)
    await optimistic_lock.add_player_to_room(graph, spawn_id, player_id)

    # Re-route SSE subscription to spawn room
    from server.db.repositories import place_repo
    spawn_place = await place_repo.get_small_place(graph, spawn_id)
    middle_id = (spawn_place or {}).get("parent_middle_id", "global")
    await bus.move_player(player_id, spawn_id, middle_id)

    event = PlayerRespawnEvent(
        player_id=player_id,
        player_name=player_name,
        respawn_place_id=spawn_id,
    ).to_dict()
    await bus.publish_room(spawn_id, event)
