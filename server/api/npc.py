"""NPC endpoints: shop inventory, NPC info, dialogue."""
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from server.broadcast.event_bus import EventBus
from server.broadcast.event_types import NPCDialogueEvent
from server.db.repositories import npc_repo, player_repo
from server.dependencies import get_graph, get_item_master, get_event_bus

router = APIRouter(prefix="/npc", tags=["npc"])


@router.get("/{npc_id}")
async def get_npc(npc_id: str, graph=Depends(get_graph)):
    npc = await npc_repo.get_npc(graph, npc_id)
    if not npc:
        raise HTTPException(404, "NPC not found")
    return npc


@router.get("/{npc_id}/shop")
async def get_shop(
    npc_id: str,
    graph=Depends(get_graph),
    item_master: dict = Depends(get_item_master),
):
    npc = await npc_repo.get_npc(graph, npc_id)
    if not npc:
        raise HTTPException(404, "NPC not found")
    if npc.get("npc_type") != "merchant":
        raise HTTPException(400, "此 NPC 不是商人。")

    shop_items = await npc_repo.get_npc_shop(graph, npc_id)
    enriched = []
    for entry in shop_items:
        master = item_master.get(entry.get("item_id", ""), {})
        enriched.append({
            **entry,
            "name": master.get("name", entry.get("item_id", "")),
            "description": master.get("description", ""),
            "weight": master.get("weight", 0),
        })

    return {
        "npc_id": npc_id,
        "npc_name": npc.get("name", npc_id),
        "shop_inventory": enriched,
    }


class TalkRequest(BaseModel):
    player_id: str


class SayResponseRequest(BaseModel):
    player_id: str
    line: str  # LLM-generated NPC response from client


@router.post("/{npc_id}/say_response")
async def npc_say_response(
    npc_id: str,
    req: SayResponseRequest,
    graph=Depends(get_graph),
    bus: EventBus = Depends(get_event_bus),
):
    """Receive a client-generated NPC dialogue line and broadcast it to the room."""
    npc = await npc_repo.get_npc(graph, npc_id)
    if not npc:
        raise HTTPException(404, "NPC not found")

    player = await player_repo.get_player(graph, req.player_id)
    if not player:
        raise HTTPException(404, "Player not found")

    if npc.get("current_place_id") != player.get("current_place_id"):
        raise HTTPException(400, "NPC 不在同一地點。")

    if npc.get("behavior_state") == "dead":
        raise HTTPException(400, "NPC 已死亡，無法回應。")

    place_id = npc["current_place_id"]
    await bus.publish_room(place_id, NPCDialogueEvent(
        npc_id=npc_id,
        npc_name=npc.get("name", npc_id),
        npc_type=npc.get("npc_type", "monster"),
        player_id=req.player_id,
        line=req.line,
        dialogue_key="say_response",
        place_id=place_id,
    ).to_dict())
    return {"success": True}


@router.post("/{npc_id}/talk")
async def talk_to_npc(
    npc_id: str,
    req: TalkRequest,
    graph=Depends(get_graph),
    bus: EventBus = Depends(get_event_bus),
):
    npc = await npc_repo.get_npc(graph, npc_id)
    if not npc:
        raise HTTPException(404, "NPC not found")

    # Verify player is in the same room
    player = await player_repo.get_player(graph, req.player_id)
    if not player:
        raise HTTPException(404, "Player not found")

    npc_place = npc.get("current_place_id", "")
    player_place = player.get("current_place_id", "")
    if npc_place != player_place:
        raise HTTPException(400, "你距離此 NPC 太遠，無法對話。")

    # Parse dialogue tree
    dialogue_tree_raw = npc.get("dialogue_tree", "{}")
    if isinstance(dialogue_tree_raw, str):
        try:
            dialogue_tree = json.loads(dialogue_tree_raw)
        except (json.JSONDecodeError, ValueError):
            dialogue_tree = {}
    else:
        dialogue_tree = dialogue_tree_raw if isinstance(dialogue_tree_raw, dict) else {}

    npc_type = npc.get("npc_type", "monster")
    opens_shop = False

    # Select dialogue line based on NPC type and state
    if npc_type == "merchant":
        line = dialogue_tree.get("greeting", f"{npc.get('name', npc_id)} 看了你一眼。")
        opens_shop = True
        dialogue_key = "greeting"
    elif npc_type == "guard":
        line = dialogue_tree.get("greeting", "衛兵點點頭，示意你可以通過。")
        dialogue_key = "greeting"
    else:
        # Monster — taunt if hostile, otherwise flee_speech
        behavior = npc.get("behavior_state", "idle")
        if behavior in ("combat", "patrol", "idle"):
            line = dialogue_tree.get("taunt", f"{npc.get('name', npc_id)} 發出威脅的聲音。")
            dialogue_key = "taunt"
        else:
            line = dialogue_tree.get("flee_speech", f"{npc.get('name', npc_id)} 退到角落。")
            dialogue_key = "flee_speech"

    # Broadcast to room
    await bus.publish_room(npc_place, NPCDialogueEvent(
        npc_id=npc_id,
        npc_name=npc.get("name", npc_id),
        npc_type=npc_type,
        player_id=req.player_id,
        line=line,
        dialogue_key=dialogue_key,
        place_id=npc_place,
    ).to_dict())

    return {
        "dialogue": line,
        "opens_shop": opens_shop,
        "npc_id": npc_id,
        "npc_name": npc.get("name", npc_id),
        "npc_type": npc_type,
    }
