"""Player action endpoints: /move, /look, /say, /do, /pickup."""
import asyncio
import json
import math
import time
import uuid
from pathlib import Path

_CLASSES: dict = json.loads((Path(__file__).parent.parent.parent / "data" / "classes.json").read_text())

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from server.broadcast.event_bus import EventBus
from server.broadcast.event_types import (
    PlayerTravelingEvent, PlayerArrivedEvent,
    PlayerSaidEvent, WorldStateChangeEvent,
    CombatRoundEvent, StatusEffectAppliedEvent,
)
from server.db import optimistic_lock
from server.db.batch_writer import BatchWriter, WriteOperation
from server.db.repositories import item_repo, npc_repo, place_repo, player_repo
from server.dependencies import get_batch_writer, get_event_bus, get_graph, get_item_master, get_redis
from server.dm import nonce_store, prompt_builder, signer
from server.dm.validator import RulingContext, validate_ruling
from server.engine import npc_ai, rules, player_skills
from server.engine.lifecycle import award_xp, _load_levels
from server.engine.rate_limiter import rate_limit
from server.engine.status_effects import make_effect

router = APIRouter(prefix="/player", tags=["player"])

# Reference speed — a player with SPD=BASE_SPD travels at base travel_time_seconds
BASE_SPD = 10


def _classify_action(action_text: str, action_rules: dict) -> tuple[str, bool]:
    """Keyword-based fast classifier. Returns (action_type, skip_dice)."""
    action_types = action_rules.get("action_types", {})
    scores: dict[str, int] = {}
    for type_name, type_info in action_types.items():
        if type_name == "other":
            continue
        keywords: list[str] = type_info.get("keywords", [])
        score = sum(1 for kw in keywords if kw in action_text)
        if score > 0:
            scores[type_name] = score
    if not scores:
        return "other", False
    best = max(scores, key=lambda t: scores[t])
    return best, bool(action_types[best].get("skip_dice", False))


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
    class_id: str | None = None


DEFAULT_SPAWN = "room_town_square"
DEFAULT_STATS = {
    # Resources
    "hp": 100, "max_hp": 100, "mp": 50, "max_mp": 50,
    # Combat derived stats (gear-modifiable)
    "atk": 10, "def": 8, "spd": 10,
    # Six core attributes (leveling point distribution)
    "str": 8, "dex": 8, "int": 8, "wis": 8, "cha": 8, "luk": 8,
    # Progression
    "level": 1, "xp": 0, "stat_points": 0, "classes": [],
}


@router.post("/create")
async def create_player(req: CreatePlayerRequest, graph=Depends(get_graph)):
    existing = await player_repo.get_player(graph, req.player_id)
    if existing:
        return {"created": False, "player_id": req.player_id}

    # Find first available small_place as spawn (fall back to hardcoded default)
    spawn_id = DEFAULT_SPAWN
    stats = {**DEFAULT_STATS}
    if req.class_id and req.class_id in _CLASSES:
        cls = _CLASSES[req.class_id]
        stats["classes"] = [req.class_id]
        for stat in cls.get("primary_stats", []):
            if stat in stats:
                stats[stat] += 3
    props = {
        "id": req.player_id,
        "name": req.name or req.player_id,
        "current_place_id": spawn_id,
        **stats,
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
    _rl: None = Depends(rate_limit("move")),
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

    # Hibernate NPCs if no more players remain in the room
    remaining = await player_repo.get_players_in_room(graph, old_place_id)
    if not remaining:
        await npc_repo.hibernate_npcs_in_place(graph, old_place_id)

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
    # 必須立即更新 current_place_id（直接寫 DB），不能用 BatchWriter 的非同步佇列，
    # 否則廣播 player_arrived 後前端 /look 可能仍讀到舊位置
    await player_repo.update_player_location(graph, player_id, new_place_id)
    await player_repo.set_travel_state(graph, player_id, False, None, None)

    # Wake hibernating NPCs in the new room and run delayed simulation
    hibernated = await npc_repo.wake_npcs_in_place(graph, new_place_id)
    for npc in hibernated:
        if npc.get("frozen_at"):
            elapsed = time.time() - npc["frozen_at"]
            updates = npc_ai.simulate_npc_elapsed_time(npc, elapsed)
            if updates:
                await npc_repo.update_npc(graph, npc["id"], updates)

    # Update SSE subscription routing so the player receives events for the new room
    new_place = await place_repo.get_small_place(graph, new_place_id)
    new_middle_id = (new_place or {}).get("parent_middle_id", "global")
    await bus.move_player(player_id, new_place_id, new_middle_id)

    # Notify global event system so adjacent hostile NPCs in the same zone get alerted
    from server.engine import global_events as _gevt
    _gevt.emit_nowait(_gevt.ServerEvent(
        event_type="player_entered",
        place_id=new_place_id,
        middle_id=new_middle_id,
        data={"player_id": player_id},
    ))

    arrived_event = PlayerArrivedEvent(
        player_id=player_id,
        player_name=player_name,
        from_place_id=old_place_id,
        to_place_id=new_place_id,
        to_place_name=(new_place or {}).get("name", ""),  # 帶入房間顯示名稱
        direction=direction,
    ).to_dict()
    await bus.publish_room(new_place_id, arrived_event)


@router.get("/look")
async def look(
    player_id: str,
    graph=Depends(get_graph),
    item_master: dict = Depends(get_item_master),
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

    # --- Hierarchical map context ---
    middle_id = place.get("parent_middle_id")
    middle_context = None
    large_context = None
    if middle_id:
        middle_rooms, middle_conns, middle_place = await asyncio.gather(
            place_repo.get_small_places_in_middle(graph, middle_id),
            place_repo.get_connections_in_middle(graph, middle_id),
            place_repo.get_middle_place(graph, middle_id),
        )
        middle_context = {
            "middle_id": middle_id,
            "middle_name": (middle_place or {}).get("name", middle_id),
            "rooms": [
                {
                    "id": r["id"],
                    "name": r.get("name", r["id"]),
                    "x_pos": r.get("x_pos", 0),
                    "y_pos": r.get("y_pos", 0),
                    "is_safe_zone": r.get("is_safe_zone", False),
                    "parent_middle_id": r.get("parent_middle_id", middle_id),
                }
                for r in middle_rooms
            ],
            "connections": middle_conns,
        }
        large_id = (middle_place or {}).get("parent_large_id") if middle_place else None
        if large_id:
            large_districts, large_place = await asyncio.gather(
                place_repo.get_middle_places_in_large(graph, large_id),
                place_repo.get_large_place(graph, large_id),
            )
            large_context = {
                "large_id": large_id,
                "large_name": (large_place or {}).get("name", large_id),
                "current_middle_id": middle_id,
                "districts": [
                    {
                        "id": d["id"],
                        "name": d.get("name", d["id"]),
                        "x_pos": d.get("x_pos", 0),
                        "y_pos": d.get("y_pos", 0),
                        "type": d.get("type", ""),
                        "parent_large_id": d.get("parent_large_id", large_id),
                    }
                    for d in large_districts
                ],
            }

    return {
        "place": place,
        "exits": exits,
        "npcs": [{"id": n["id"], "name": n["name"], "npc_type": n.get("npc_type", ""), "behavior_state": n.get("behavior_state")} for n in npcs],
        "items": [
            {
                "instance_id": i["instance_id"],
                "item_id": i["item_id"],
                "name": item_master.get(i["item_id"], {}).get("name", i["item_id"]),  # 中文顯示名
                "quantity": i.get("quantity", 1),
            }
            for i in items
        ],
        "player_traveling": player.get("is_traveling", False),
        "travel_arrives_at": player.get("travel_arrives_at"),
        "middle_context": middle_context,
        "large_context": large_context,
    }


async def _get_npcs(graph, place_id: str) -> list[dict]:
    return await npc_repo.get_npcs_in_place(graph, place_id)


@router.post("/say")
async def say(
    req: SayRequest,
    graph=Depends(get_graph),
    bus: EventBus = Depends(get_event_bus),
    _rl: None = Depends(rate_limit("say")),
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
    bus: EventBus = Depends(get_event_bus),
    _rl: None = Depends(rate_limit("do")),
):
    """Step 1 of DM ruling flow: build and return signed prompt packet."""
    player = await player_repo.get_player(graph, req.player_id)
    if not player:
        raise HTTPException(404, "Player not found")

    rules.can_use_free_action(player)

    # Fast-path: keyword classify before touching LLM
    from server.dm.prompt_builder import _load_action_rules as _load_ar
    _action_rules = _load_ar()
    detected_type, skip_dice = _classify_action(req.action, _action_rules)

    if skip_dice:
        # Chat / zero-cost action — broadcast as speech and skip DM entirely
        event = PlayerSaidEvent(
            player_id=req.player_id,
            player_name=player.get("name", req.player_id),
            message=req.action,
            place_id=player["current_place_id"],
        ).to_dict()
        await bus.publish_room(player["current_place_id"], event)
        return {"requires_ruling": False, "message": req.action}

    place = await place_repo.get_small_place(graph, player["current_place_id"])
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
        detected_action_type=detected_type,
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
    _rl: None = Depends(rate_limit("pickup")),
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


@router.get("/{player_id}/inventory")
async def get_inventory(
    player_id: str,
    graph=Depends(get_graph),
    item_master=Depends(get_item_master),
):
    player = await player_repo.get_player(graph, player_id)
    if not player:
        raise HTTPException(404, "Player not found")
    raw = await item_repo.get_player_inventory(graph, player_id)
    result = []
    for inst in raw:
        master = item_master.get(inst.get("item_id", ""), {})
        result.append({
            **inst,
            "name": master.get("name", inst.get("item_id", "")),
            "description": master.get("description", ""),
            "category": master.get("category", ""),
            "weight": master.get("weight", 0),
        })
    return {"items": result}


@router.get("/{player_id}/craftable")
async def get_craftable_items(
    player_id: str,
    graph=Depends(get_graph),
    item_master: dict = Depends(get_item_master),
):
    """Return all craftable items enriched with per-ingredient availability."""
    player = await player_repo.get_player(graph, player_id)
    if not player:
        raise HTTPException(404, "Player not found")

    result = []
    for item_id, master in item_master.items():
        if not master.get("is_craftable"):
            continue
        recipe: dict = master.get("craft_recipe") or {}
        ingredients = []
        can_craft = True
        for ing_id, needed in recipe.items():
            instances = await item_repo.get_player_inventory_by_item_id(graph, player_id, ing_id)
            have = sum(i.get("quantity", 1) for i in instances)
            ing_name = item_master.get(ing_id, {}).get("name", ing_id)
            if have < needed:
                can_craft = False
            ingredients.append({
                "item_id": ing_id,
                "name": ing_name,
                "needed": needed,
                "have": have,
                "sufficient": have >= needed,
            })
        result.append({
            "item_id": item_id,
            "name": master.get("name", item_id),
            "description": master.get("description", ""),
            "category": master.get("category", ""),
            "can_craft": can_craft,
            "ingredients": ingredients,
        })
    return {"craftable": result}


class CraftRequest(BaseModel):
    player_id: str
    item_id: str  # must have is_craftable: true in item master


@router.post("/craft")
async def craft(
    req: CraftRequest,
    graph=Depends(get_graph),
    bus: EventBus = Depends(get_event_bus),
    item_master: dict = Depends(get_item_master),
    _rl: None = Depends(rate_limit("craft")),
):
    master = item_master.get(req.item_id)
    if not master or not master.get("is_craftable"):
        raise HTTPException(400, "此物品無法製作。")

    recipe: dict = master.get("craft_recipe") or {}
    if not recipe:
        raise HTTPException(400, "此物品沒有製作配方。")

    player = await player_repo.get_player(graph, req.player_id)
    if not player:
        raise HTTPException(404, "Player not found")

    # Verify all ingredients
    for ingredient_id, amount in recipe.items():
        instances = await item_repo.get_player_inventory_by_item_id(graph, req.player_id, ingredient_id)
        total = sum(i.get("quantity", 1) for i in instances)
        if total < amount:
            name = item_master.get(ingredient_id, {}).get("name", ingredient_id)
            raise HTTPException(400, f"材料不足：需要 {name} ×{amount}，但只有 ×{total}。")

    # Consume ingredients
    for ingredient_id, amount in recipe.items():
        await item_repo.consume_items_from_inventory(graph, req.player_id, ingredient_id, amount)

    # Create crafted item
    instance_id = f"craft_{uuid.uuid4().hex[:8]}"
    props = {
        "instance_id": instance_id,
        "item_id": req.item_id,
        "durability": master.get("durability_max", 100),
        "quantity": 1,
        "location_type": "player_inventory",
        "location_id": req.player_id,
    }
    await item_repo.create_item_instance(graph, props)
    await graph.query(
        "MATCH (i:item_instance {instance_id: $iid}), (p:player {id: $pid}) "
        "MERGE (i)-[:OWNED_BY]->(p)",
        {"iid": instance_id, "pid": req.player_id},
    )

    event = WorldStateChangeEvent(
        place_id=player["current_place_id"],
        change_type="item_crafted",
        details={"player_id": req.player_id, "item_id": req.item_id, "instance_id": instance_id},
    ).to_dict()
    await bus.publish_room(player["current_place_id"], event)
    return {"success": True, "crafted": req.item_id, "instance_id": instance_id}


class BuyRequest(BaseModel):
    player_id: str
    npc_id: str
    item_id: str
    quantity: int = 1


class SellRequest(BaseModel):
    player_id: str
    npc_id: str
    item_instance_id: str


@router.post("/buy")
async def buy_item(
    req: BuyRequest,
    graph=Depends(get_graph),
    item_master: dict = Depends(get_item_master),
    _rl: None = Depends(rate_limit("buy")),
):
    import json as _json

    player = await player_repo.get_player(graph, req.player_id)
    if not player:
        raise HTTPException(404, "Player not found")

    npc = await npc_repo.get_npc(graph, req.npc_id)
    if not npc or npc.get("npc_type") != "merchant":
        raise HTTPException(400, "目標不是商人或不存在。")
    if npc.get("current_place_id") != player["current_place_id"]:
        raise HTTPException(400, "商人不在同一個地點。")

    shop_inv = npc.get("shop_inventory", [])
    if isinstance(shop_inv, str):
        shop_inv = _json.loads(shop_inv)

    shop_item = next((s for s in shop_inv if s["item_id"] == req.item_id), None)
    if not shop_item:
        raise HTTPException(400, "商人沒有此物品。")
    if shop_item.get("stock", 0) < req.quantity:
        raise HTTPException(400, f"庫存不足，只剩 {shop_item.get('stock', 0)} 個。")

    total_price = shop_item["price"] * req.quantity
    coin_instances = await item_repo.get_player_inventory_by_item_id(graph, req.player_id, "coin_copper")
    total_coins = sum(i.get("quantity", 1) for i in coin_instances)
    if total_coins < total_price:
        raise HTTPException(400, f"銅幣不足。需要 {total_price} 個，你只有 {total_coins} 個。")

    await item_repo.consume_items_from_inventory(graph, req.player_id, "coin_copper", total_price)

    instance_id = f"buy_{uuid.uuid4().hex[:8]}"
    master = item_master.get(req.item_id, {})
    props = {
        "instance_id": instance_id,
        "item_id": req.item_id,
        "durability": master.get("durability_max", 100),
        "quantity": req.quantity,
        "location_type": "player_inventory",
        "location_id": req.player_id,
    }
    await item_repo.create_item_instance(graph, props)
    await graph.query(
        "MATCH (i:item_instance {instance_id: $iid}), (p:player {id: $pid}) "
        "MERGE (i)-[:OWNED_BY]->(p)",
        {"iid": instance_id, "pid": req.player_id},
    )

    for s in shop_inv:
        if s["item_id"] == req.item_id:
            s["stock"] -= req.quantity
            break
    await npc_repo.update_npc(graph, req.npc_id, {"shop_inventory": _json.dumps(shop_inv, ensure_ascii=False)})

    return {"success": True, "item_id": req.item_id, "quantity": req.quantity, "cost": total_price}


@router.post("/sell")
async def sell_item(
    req: SellRequest,
    graph=Depends(get_graph),
    item_master: dict = Depends(get_item_master),
    _rl: None = Depends(rate_limit("sell")),
):
    player = await player_repo.get_player(graph, req.player_id)
    if not player:
        raise HTTPException(404, "Player not found")

    npc = await npc_repo.get_npc(graph, req.npc_id)
    if not npc or npc.get("npc_type") != "merchant":
        raise HTTPException(400, "目標不是商人或不存在。")
    if npc.get("current_place_id") != player["current_place_id"]:
        raise HTTPException(400, "商人不在同一個地點。")

    inst = await item_repo.get_item_instance(graph, req.item_instance_id)
    if not inst or inst.get("location_id") != req.player_id:
        raise HTTPException(400, "你沒有這個物品，或物品不在背包中。")
    if inst.get("item_id") == "coin_copper":
        raise HTTPException(400, "無法直接出售銅幣。")

    master = item_master.get(inst.get("item_id", ""), {})
    qty = inst.get("quantity", 1)
    atk = master.get("base_atk", 0)
    def_ = master.get("base_def", 0)
    sell_price = max(1, (atk + def_ + 1) * qty)

    await graph.query(
        "MATCH (i:item_instance {instance_id: $iid}) DETACH DELETE i",
        {"iid": req.item_instance_id},
    )

    coin_id = f"coin_{uuid.uuid4().hex[:8]}"
    await item_repo.create_item_instance(graph, {
        "instance_id": coin_id,
        "item_id": "coin_copper",
        "durability": 999,
        "quantity": sell_price,
        "location_type": "player_inventory",
        "location_id": req.player_id,
    })
    await graph.query(
        "MATCH (i:item_instance {instance_id: $iid}), (p:player {id: $pid}) "
        "MERGE (i)-[:OWNED_BY]->(p)",
        {"iid": coin_id, "pid": req.player_id},
    )

    return {"success": True, "sold_instance_id": req.item_instance_id, "received_coins": sell_price}


class UseSkillRequest(BaseModel):
    player_id: str
    ability_id: str
    ability_type: str = "skill"  # "skill" | "spell"
    target_id: str | None = None


@router.get("/{player_id}/abilities")
async def get_player_abilities(
    player_id: str,
    graph=Depends(get_graph),
    redis=Depends(get_redis),
):
    """Return all skills/spells with unlock status and cooldown info for this player."""
    player = await player_repo.get_player(graph, player_id)
    if not player:
        raise HTTPException(404, "Player not found")

    all_ids = list(player_skills.load_skills().keys()) + list(player_skills.load_spells().keys())
    cooldowns: dict[str, float] = {}
    for ability_id in all_ids:
        raw = await redis.get(player_skills.get_cooldown_key(player_id, ability_id))
        if raw is not None:
            try:
                expires_at = float(raw)
                cooldowns[ability_id] = player_skills.get_cooldown_remaining(expires_at)
            except (ValueError, TypeError):
                pass

    return {"abilities": player_skills.build_abilities_list(player, cooldowns)}


@router.post("/use_skill")
async def use_skill(
    req: UseSkillRequest,
    graph=Depends(get_graph),
    redis=Depends(get_redis),
    bus: EventBus = Depends(get_event_bus),
    _rl: None = Depends(rate_limit("use_skill")),
):
    """Use a skill or spell. Validates unlock, MP, and cooldown; applies effect."""
    player = await player_repo.get_player(graph, req.player_id)
    if not player:
        raise HTTPException(404, "Player not found")

    # Load ability definition
    if req.ability_type == "spell":
        ability_dict = player_skills.load_spells()
    else:
        ability_dict = player_skills.load_skills()
    ability = ability_dict.get(req.ability_id)
    if not ability:
        raise HTTPException(400, f"技能/法術「{req.ability_id}」不存在。")

    # Unlock check
    unlocked, locked_reason = player_skills.check_ability_unlocked(player, ability)
    if not unlocked:
        raise HTTPException(400, locked_reason)

    # Passive guard
    if ability.get("effect_type") == "passive":
        raise HTTPException(400, "被動技能自動生效，無法主動使用。")

    # MP check
    mp_cost: int = ability.get("mp_cost", 0)
    if player.get("mp", 0) < mp_cost:
        raise HTTPException(400, f"魔力不足。需要 {mp_cost} MP，目前只有 {player.get('mp', 0)} MP。")

    # Cooldown check
    cd_key = player_skills.get_cooldown_key(req.player_id, req.ability_id)
    raw_cd = await redis.get(cd_key)
    if raw_cd is not None:
        try:
            remaining = player_skills.get_cooldown_remaining(float(raw_cd))
            if remaining > 0:
                raise HTTPException(400, f"技能冷卻中，還需 {remaining:.1f} 秒。")
        except (ValueError, TypeError):
            pass

    # Target resolution
    target: dict | None = None
    if req.target_id:
        target = await npc_repo.get_npc(graph, req.target_id)
        if not target:
            raise HTTPException(400, "目標 NPC 不存在。")
        if target.get("current_place_id") != player.get("current_place_id"):
            raise HTTPException(400, "目標不在同一個地點。")

    # Resolve effect
    try:
        result = player_skills.resolve_ability_effect(player, ability, target, req.ability_type)
    except ValueError as e:
        raise HTTPException(400, str(e))

    damage: int = result["damage"]
    heal: int = result["heal"]
    status_applied: str | None = result["status_applied"]
    narrative_hint: str = result["narrative_hint"]

    # Deduct MP
    new_mp = max(0, player.get("mp", 0) - mp_cost)
    await player_repo.update_player(graph, req.player_id, {"mp": new_mp})

    # Set cooldown in Redis
    cd_turns: int = ability.get("cooldown_turns", 0)
    if cd_turns > 0:
        cd_seconds = cd_turns * 2.0
        await redis.set(cd_key, str(time.time() + cd_seconds), ex=int(cd_seconds) + 5)

    # Apply heal to player
    if heal > 0:
        new_hp = min(player.get("max_hp", 100), player.get("hp", 100) + heal)
        await player_repo.update_player(graph, req.player_id, {"hp": new_hp})

    # Apply damage / status to target NPC
    new_target_hp: int | None = None
    target_defeated = False
    if target and damage > 0:
        new_target_hp = max(0, target.get("hp", 1) - damage)
        await npc_repo.update_npc_hp(graph, req.target_id, new_target_hp)
        if new_target_hp == 0:
            await npc_repo.update_npc(graph, req.target_id, {"behavior_state": "dead"})
            target_defeated = True
            xp_reward = max(5, target.get("hp_max", 10) // 2 + target.get("atk", 5))
            await award_xp(graph, bus, req.player_id, xp_reward)

    if target and status_applied:
        try:
            new_effect = make_effect(status_applied, source_id=req.player_id)
            target_fx_raw = target.get("status_effects", "[]") or "[]"
            if isinstance(target_fx_raw, list):
                target_fx = target_fx_raw
            else:
                try:
                    target_fx = json.loads(target_fx_raw)
                except (json.JSONDecodeError, ValueError):
                    target_fx = []
            existing = next((e for e in target_fx if e.get("effect_type") == status_applied), None)
            if existing:
                existing["stacks"] = min(existing.get("stacks", 1) + 1, 5)
                existing["duration"] = max(existing["duration"], new_effect.duration)
            else:
                target_fx.append({
                    "effect_type": new_effect.effect_type.value,
                    "duration": new_effect.duration,
                    "stacks": new_effect.stacks,
                    "source_id": new_effect.source_id,
                })
            await npc_repo.update_npc(graph, req.target_id, {"status_effects": json.dumps(target_fx)})
            room_id = player.get("current_place_id", "")
            await bus.publish_room(room_id, StatusEffectAppliedEvent(
                target_id=req.target_id,
                target_name=target.get("name", req.target_id),
                effect_type=status_applied,
                stacks=new_effect.stacks,
                source_id=req.player_id,
                room_id=room_id,
            ).to_dict())
        except (ValueError, KeyError):
            pass  # Unknown effect type, skip

    # Broadcast combat round event
    room_id = player.get("current_place_id", "")
    await bus.publish_room(room_id, CombatRoundEvent(
        room_id=room_id,
        actor_id=req.player_id,
        target_id=req.target_id or "",
        action=ability.get("name", req.ability_id),
        damage=damage,
        target_hp_remaining=new_target_hp if new_target_hp is not None else 0,
        status_applied=status_applied,
        narrative_hint=narrative_hint,
    ).to_dict())

    return {
        "success": True,
        "ability_id": req.ability_id,
        "ability_name": ability.get("name", req.ability_id),
        "mp_remaining": new_mp,
        "damage": damage,
        "heal": heal,
        "status_applied": status_applied,
        "narrative_hint": narrative_hint,
        "target_hp_remaining": new_target_hp,
        "target_defeated": target_defeated,
    }


_VALID_STATS = {"str", "dex", "int", "wis", "cha", "luk"}


class AllocateStatRequest(BaseModel):
    player_id: str
    stat: str  # "str" | "dex" | "int" | "wis" | "cha" | "luk"


@router.post("/allocate_stat")
async def allocate_stat(
    req: AllocateStatRequest,
    graph=Depends(get_graph),
    _rl: None = Depends(rate_limit("allocate_stat")),
):
    """Spend one unallocated stat point to raise a core attribute by 1."""
    if req.stat not in _VALID_STATS:
        raise HTTPException(400, f"無效屬性：{req.stat}。有效值：{', '.join(sorted(_VALID_STATS))}")

    player = await player_repo.get_player(graph, req.player_id)
    if not player:
        raise HTTPException(404, "Player not found")

    if (player.get("stat_points") or 0) <= 0:
        raise HTTPException(400, "沒有可分配的屬性點數。")

    new_val = (player.get(req.stat) or 8) + 1
    updates: dict = {req.stat: new_val, "stat_points": (player.get("stat_points") or 0) - 1}

    # Update derived combat stats when relevant core attributes change
    if req.stat == "str":
        updates["atk"] = (player.get("atk") or 10) + 1
    elif req.stat == "dex":
        updates["spd"] = (player.get("spd") or 10) + 1

    await player_repo.update_player(graph, req.player_id, updates)
    return {"success": True, "stat": req.stat, "new_value": new_val, "stat_points": updates["stat_points"]}


# ── Must be LAST — wildcard catches any GET /player/{id} not matched above ──
@router.get("/{player_id}")
async def get_player(player_id: str, graph=Depends(get_graph)):
    player = await player_repo.get_player(graph, player_id)
    if not player:
        raise HTTPException(404, "Player not found")
    levels = _load_levels()
    xp_table: list[int] = levels["xp_table"]
    max_level: int = levels["max_level"]
    current_level: int = player.get("level", 1)
    player["xp_next_level"] = xp_table[current_level] if current_level < max_level else None
    return player
