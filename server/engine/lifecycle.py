"""Player lifecycle events: death, respawn, XP/leveling."""
import asyncio
import json
from pathlib import Path

from server.broadcast.event_bus import EventBus
from server.broadcast.event_types import PlayerDeathEvent, PlayerLeveledUpEvent, PlayerRespawnEvent
from server.config import settings
from server.db import optimistic_lock
from server.db.repositories import combat_repo, player_repo

_LEVELS_PATH = Path(__file__).parent.parent.parent / "data" / "levels.json"
_CLASSES_PATH = Path(__file__).parent.parent.parent / "data" / "classes.json"
_levels_cache: dict = {}
_classes_cache: dict = {}


def _load_levels() -> dict:
    global _levels_cache
    if not _levels_cache:
        _levels_cache = json.loads(_LEVELS_PATH.read_text(encoding="utf-8"))
    return _levels_cache


def _load_classes() -> dict:
    global _classes_cache
    if not _classes_cache:
        _classes_cache = json.loads(_CLASSES_PATH.read_text(encoding="utf-8"))
    return _classes_cache


async def award_xp(graph, bus: EventBus, player_id: str, xp_amount: int) -> None:
    """Award XP to a player and trigger level-up if threshold crossed."""
    player = await player_repo.get_player(graph, player_id)
    if not player:
        return

    levels = _load_levels()
    classes = _load_classes()
    xp_table: list[int] = levels["xp_table"]
    max_level: int = levels["max_level"]
    sp_per_level: int = levels.get("stat_points_per_level", 3)

    current_xp: int = player.get("xp", 0) + xp_amount
    current_level: int = player.get("level", 1)

    # Find new level
    new_level = current_level
    while new_level < max_level and current_xp >= xp_table[new_level]:
        new_level += 1

    updates: dict = {"xp": current_xp}
    levels_gained = new_level - current_level

    if levels_gained > 0:
        updates["level"] = new_level
        updates["stat_points"] = player.get("stat_points", 0) + sp_per_level * levels_gained
        primary_class = (player.get("classes") or [])[0] if player.get("classes") else None
        if primary_class and primary_class in classes:
            cls = classes[primary_class]
            updates["max_hp"] = player.get("max_hp", 100) + cls.get("hp_bonus_per_level", 0) * levels_gained
            updates["max_mp"] = player.get("max_mp", 50) + cls.get("mp_bonus_per_level", 0) * levels_gained

    await player_repo.update_player(graph, player_id, updates)

    if levels_gained > 0:
        event = PlayerLeveledUpEvent(
            player_id=player_id,
            player_name=player.get("name", player_id),
            new_level=new_level,
            stat_points_gained=sp_per_level * levels_gained,
        ).to_dict()
        await bus.publish_global(event)


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
