"""Player action endpoints: /move, /look, /say, /do, /pickup."""
import asyncio
import math
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from server.broadcast.event_bus import EventBus
from server.broadcast.event_types import (
    PlayerTravelingEvent, PlayerArrivedEvent,
    PlayerSaidEvent, WorldStateChangeEvent,
)
from server.db import optimistic_lock
from server.db.batch_writer import BatchWriter, WriteOperation
from server.db.repositories import item_repo, place_repo, player_repo
from server.dependencies import get_batch_writer, get_event_bus, get_graph, get_item_master, get_redis
from server.dm import nonce_store, prompt_builder, signer
from server.dm.validator import RulingContext, validate_ruling
from server.engine import rules

router = APIRouter(prefix="/player", tags=["player"])

# Reference speed — a player with SPD=BASE_SPD travels at base travel_time_seconds
BASE_SPD = 10


def _actual_travel_time(base_seconds: int, player_spd: int) -> float:
    """Scale travel time by player speed. Minimum 1 second."""
    spd = max(1, player_spd)
    return max(1.0, round(base_seconds * (BASE_SPD / spd), 1))


class MoveRequest(BaseModel):
    player_id: str
    direction: str


class SayRequest(BaseModel):
    player_id: str
    message: str


class DoRequest(BaseModel):
    player_id: str
    action: str


class PickupRequest(BaseModel):
    player_id: str
    item_instance_id: str


class CreatePlayerRequest(BaseModel):
    player_id: str
    name: str | None = None


DEFAULT_SPAWN = "room_town_square"
DEFAULT_STATS = {"hp": 100, "max_hp": 100, "mp": 50, "max_mp": 50, "atk": 10, "def": 8, "spd": 10}


@router.post("/create")
async def create_player(req: CreatePlayerRequest, graph=Depends(get_graph)):
    existing = await player_repo.get_player(graph, req.player_id)
    if existing:
        return {"created": False, "player_id": req.player_id}

    # Find first available small_place as spawn (fall back to hardcoded default)
    spawn_id = DEFAULT_SPAWN
    props = {
        "id": req.player_id,
        "name": req.name or req.player_id,
        "current_place_id": spawn_id,
        **DEFAULT_STATS,
    }
    await player_repo.create_player(graph, props)

    # Add player to spawn room's player_ids list
    await graph.query(
        "MATCH (s:small_place {id: $place_id}) "
        "SET s.player_ids = CASE WHEN $uid IN s.player_ids THEN s.player_ids ELSE s.player_ids + $uid END",
        {"place_id": spawn_id, "uid": req.player_id},
    )

    return {"created": True, "player_id": req.player_id, "spawn": spawn_id}


@router.post("/move")
async def move_player(
    req: MoveRequest,
    graph=Depends(get_graph),
    redis=Depends(get_redis),
    bus: EventBus = Depends(get_event_bus),
    writer: BatchWriter = Depends(get_batch_writer),
):
    player = await player_repo.get_player(graph, req.player_id)
    if not player:
        raise HTTPException(404, "Player not found")

    connections = await place_repo.get_connected_places(graph, player["current_place_id"])
    target = next((c for c in connections if c["_edge"]["direction"] == req.direction), None)
    if not target:
        raise HTTPException(400, "那個方向沒有出口。")

    edge = target["_edge"]
    rules.can_move(player, target, edge)

    old_place_id = player["current_place_id"]
    new_place_id = target["id"]
    travel_time = _actual_travel_time(edge["travel_time_seconds"], player.get("spd", BASE_SPD))
    arrives_at = time.time() + travel_time

    # 1. Remove player from current room (they've departed)
    await optimistic_lock.remove_player_from_room(graph, old_place_id, req.player_id)

    # 2. Mark player as traveling (position stays as old room until arrival)
    await player_repo.set_travel_state(graph, req.player_id, True, new_place_id, arrives_at)

    # 3. Broadcast departure to old room
    depart_event = PlayerTravelingEvent(
        player_id=req.player_id,
        player_name=player.get("name", req.player_id),
        from_place_id=old_place_id,
        to_place_id=new_place_id,
        direction=req.direction,
        travel_time_seconds=travel_time,
        arrives_at=arrives_at,
        transition_description=edge.get("transition_description", ""),
    ).to_dict()
    await bus.publish_room(old_place_id, depart_event)

    # 4. Schedule arrival
    asyncio.create_task(
        _arrive(
            graph=graph,
            redis=redis,
            bus=bus,
            writer=writer,
            player_id=req.player_id,
            player_name=player.get("name", req.player_id),
            old_place_id=old_place_id,
            new_place_id=new_place_id,
            direction=req.direction,
            delay=travel_time,
        )
    )

    return {
        "traveling": True,
        "direction": req.direction,
        "from_place_id": old_place_id,
        "to_place_id": new_place_id,
        "travel_time_seconds": travel_time,
        "arrives_at": arrives_at,
        "transition_description": edge.get("transition_description", ""),
    }


async def _arrive(
    graph,
    redis,
    bus: EventBus,
    writer: BatchWriter,
    player_id: str,
    player_name: str,
    old_place_id: str,
    new_place_id: str,
    direction: str,
    delay: float,
) -> None:
    await asyncio.sleep(delay)

    # Verify player still intends to arrive (not cancelled by admin etc.)
    player = await player_repo.get_player(graph, player_id)
    if not player or not player.get("is_traveling"):
        return
    if player.get("travel_destination_id") != new_place_id:
        return  # destination changed

    # Update position and clear travel state
    await optimistic_lock.add_player_to_room(graph, new_place_id, player_id)
    await player_repo.set_travel_state(graph, player_id, False, None, None)
    writer.enqueue(WriteOperation("player", "id", {
        "id": player_id,
        "current_place_id": new_place_id,
        "is_traveling": False,
        "travel_destination_id": None,
        "travel_arrives_at": None,
    }))

    # Update SSE subscription routing so the player receives events for the new room
    new_place = await place_repo.get_small_place(graph, new_place_id)
    new_middle_id = (new_place or {}).get("parent_middle_id", "global")
    await bus.move_player(player_id, new_place_id, new_middle_id)

    arrived_event = PlayerArrivedEvent(
        player_id=player_id,
        player_name=player_name,
        from_place_id=old_place_id,
        to_place_id=new_place_id,
        direction=direction,
    ).to_dict()
    await bus.publish_room(new_place_id, arrived_event)


@router.get("/look")
async def look(
    player_id: str,
    graph=Depends(get_graph),
):
    """Return current room description with visible exits (direction + description + travel time)."""
    player = await player_repo.get_player(graph, player_id)
    if not player:
        raise HTTPException(404, "Player not found")

    place_id = player.get("travel_destination_id") if player.get("is_traveling") else player["current_place_id"]
    place = await place_repo.get_small_place(graph, place_id)
    if not place:
        raise HTTPException(404, "Place not found")

    exits = await place_repo.get_exits(graph, place_id)
    npcs = await _get_npcs(graph, place_id)
    items = await item_repo.get_items_in_place(graph, place_id)

    return {
        "place": place,
        "exits": exits,
        "npcs": [{"id": n["id"], "name": n["name"], "behavior_state": n.get("behavior_state")} for n in npcs],
        "items": [{"instance_id": i["instance_id"], "item_id": i["item_id"], "quantity": i.get("quantity", 1)} for i in items],
        "player_traveling": player.get("is_traveling", False),
        "travel_arrives_at": player.get("travel_arrives_at"),
    }


async def _get_npcs(graph, place_id: str) -> list[dict]:
    from server.db.repositories import npc_repo
    return await npc_repo.get_npcs_in_place(graph, place_id)


@router.post("/say")
async def say(
    req: SayRequest,
    graph=Depends(get_graph),
    bus: EventBus = Depends(get_event_bus),
):
    player = await player_repo.get_player(graph, req.player_id)
    if not player:
        raise HTTPException(404, "Player not found")

    event = PlayerSaidEvent(
        player_id=req.player_id,
        player_name=player.get("name", req.player_id),
        message=req.message,
        place_id=player["current_place_id"],
    ).to_dict()
    await bus.publish_room(player["current_place_id"], event)
    return {"success": True}


@router.post("/do")
async def do_action(
    req: DoRequest,
    graph=Depends(get_graph),
    redis=Depends(get_redis),
    item_master: dict = Depends(get_item_master),
):
    """Step 1 of DM ruling flow: build and return signed prompt packet."""
    player = await player_repo.get_player(graph, req.player_id)
    if not player:
        raise HTTPException(404, "Player not found")

    rules.can_use_free_action(player)

    place = await place_repo.get_small_place(graph, player["current_place_id"])
    from server.db.repositories import npc_repo
    npcs = await npc_repo.get_npcs_in_place(graph, player["current_place_id"])
    scene_items = await item_repo.get_items_in_place(graph, player["current_place_id"])
    inventory = await item_repo.get_player_inventory(graph, req.player_id)

    payload = prompt_builder.build_action_prompt(
        player=player,
        scene=place,
        action=req.action,
        npcs=npcs,
        scene_items=scene_items,
        inventory_items=inventory,
        item_master=item_master,
        is_combat=player.get("is_in_combat", False),
    )

    session_id = f"{req.player_id}_action_{uuid.uuid4().hex[:8]}"
    packet = signer.create_prompt_packet(payload, session_id)

    # Store scene snapshot for later validation
    scene_snapshot = {
        "entity_ids": {p["id"] for p in [player] + npcs},
        "item_instance_ids": {i["instance_id"] for i in scene_items},
        "inventory_ids": {i["instance_id"] for i in inventory},
        "is_combat": player.get("is_in_combat", False),
    }
    # Convert sets to lists for JSON serialisation
    for k in ("entity_ids", "item_instance_ids", "inventory_ids"):
        scene_snapshot[k] = list(scene_snapshot[k])

    await nonce_store.store_pending_ruling(redis, packet["nonce"], {
        "player_id": req.player_id,
        "session_id": session_id,
        "scene_snapshot": scene_snapshot,
        "created_at": time.time(),
    })

    return {"dm_packet": packet, "requires_ruling": True}


@router.post("/pickup")
async def pickup(
    req: PickupRequest,
    graph=Depends(get_graph),
    bus: EventBus = Depends(get_event_bus),
    writer: BatchWriter = Depends(get_batch_writer),
):
    player = await player_repo.get_player(graph, req.player_id)
    if not player:
        raise HTTPException(404, "Player not found")

    item = await item_repo.get_item_instance(graph, req.item_instance_id)
    if not item:
        raise HTTPException(404, "Item not found")

    rules.can_pickup(player, item, player["current_place_id"])

    await item_repo.give_item_to_player(graph, req.item_instance_id, req.player_id)

    event = WorldStateChangeEvent(
        place_id=player["current_place_id"],
        change_type="item_picked_up",
        details={"player_id": req.player_id, "item_instance_id": req.item_instance_id},
    ).to_dict()
    await bus.publish_room(player["current_place_id"], event)
    return {"success": True}


# ── Must be LAST — wildcard catches any GET /player/{id} not matched above ──
@router.get("/{player_id}")
async def get_player(player_id: str, graph=Depends(get_graph)):
    player = await player_repo.get_player(graph, player_id)
    if not player:
        raise HTTPException(404, "Player not found")
    return player
