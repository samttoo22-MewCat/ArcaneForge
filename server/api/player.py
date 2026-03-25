"""Player action endpoints: /move, /say, /do, /pickup."""
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from server.broadcast.event_bus import EventBus
from server.broadcast.event_types import PlayerMovedEvent, PlayerSaidEvent, WorldStateChangeEvent
from server.db import optimistic_lock
from server.db.batch_writer import BatchWriter, WriteOperation
from server.db.repositories import item_repo, place_repo, player_repo
from server.dependencies import get_batch_writer, get_event_bus, get_graph, get_item_master, get_redis
from server.dm import nonce_store, prompt_builder, signer
from server.dm.schemas import DMRulingSubmission
from server.dm.validator import RulingContext, validate_ruling
from server.engine import rules

router = APIRouter(prefix="/player", tags=["player"])


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


@router.post("/move")
async def move_player(
    req: MoveRequest,
    graph=Depends(get_graph),
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

    await optimistic_lock.remove_player_from_room(graph, old_place_id, req.player_id)
    await optimistic_lock.add_player_to_room(graph, new_place_id, req.player_id)

    writer.enqueue(WriteOperation("player", "id", {"id": req.player_id, "current_place_id": new_place_id}))

    event = PlayerMovedEvent(
        player_id=req.player_id,
        player_name=player.get("name", req.player_id),
        from_place_id=old_place_id,
        to_place_id=new_place_id,
        direction=req.direction,
    ).to_dict()
    await bus.publish_room(old_place_id, event)
    await bus.publish_room(new_place_id, event)

    new_place = await place_repo.get_small_place(graph, new_place_id)
    return {"success": True, "place": new_place}


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
