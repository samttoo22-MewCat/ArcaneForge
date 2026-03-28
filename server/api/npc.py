"""NPC endpoints: shop inventory, NPC info, dialogue, memory, persuasion."""
import json
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from server.broadcast.event_bus import EventBus
from server.broadcast.event_types import NPCDialogueEvent, NPCPersuasionEvent
from server.db.repositories import npc_repo, player_repo
from server.db.repositories import memory_repo
from server.dependencies import get_graph, get_item_master, get_event_bus, get_redis
from server.dm import nonce_store, signer
from server.dm import prompt_builder
from server.engine import dice

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
    print(f"[say_response] npc={npc_id} player={req.player_id} line={req.line[:40]!r}")
    npc = await npc_repo.get_npc(graph, npc_id)
    if not npc:
        print(f"[say_response] ERROR: NPC {npc_id} not found")
        raise HTTPException(404, "NPC not found")

    player = await player_repo.get_player(graph, req.player_id)
    if not player:
        print(f"[say_response] ERROR: player {req.player_id} not found")
        raise HTTPException(404, "Player not found")

    if npc.get("current_place_id") != player.get("current_place_id"):
        print(f"[say_response] ERROR: NPC place={npc.get('current_place_id')} != player place={player.get('current_place_id')}")
        raise HTTPException(400, "NPC 不在同一地點。")

    if npc.get("behavior_state") == "dead":
        print(f"[say_response] ERROR: NPC {npc_id} is dead")
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
    print(f"[say_response] OK: broadcast to room {place_id}")
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


# ── Memory endpoints ───────────────────────────────────────────────────────────

class AddRoundRequest(BaseModel):
    player_id: str
    compressed_round: str  # 1 sentence summary of (player_msg + npc_response)


class UpdateSummaryRequest(BaseModel):
    player_id: str
    new_summary: str  # LLM-generated long-term impression


@router.get("/{npc_id}/memory")
async def get_npc_memory(
    npc_id: str,
    player_id: str,
    graph=Depends(get_graph),
    redis=Depends(get_redis),
):
    """Return combined memory context for (npc, player): recent rounds + long-term summary."""
    return await memory_repo.get_memory(graph, redis, npc_id, player_id)


@router.post("/{npc_id}/memory/add_round")
async def add_memory_round(
    npc_id: str,
    req: AddRoundRequest,
    redis=Depends(get_redis),
):
    """Append one compressed round. Returns overflow=True + rounds_for_summary when list hits MAX_ROUNDS."""
    result = await memory_repo.add_round(redis, npc_id, req.player_id, req.compressed_round)
    return result


@router.post("/{npc_id}/memory/update_summary")
async def update_memory_summary(
    npc_id: str,
    req: UpdateSummaryRequest,
    graph=Depends(get_graph),
    redis=Depends(get_redis),
):
    """Write new long-term summary to FalkorDB REMEMBERS edge."""
    await memory_repo.update_summary(graph, npc_id, req.player_id, req.new_summary)
    return {"success": True}


# ── Persuasion endpoints ───────────────────────────────────────────────────────

class PersuadeRequest(BaseModel):
    player_id: str
    player_message: str
    intent: str  # "persuade" | "threaten" | "bribe"


class PersuasionResultRequest(BaseModel):
    player_id: str
    nonce: str
    timestamp: float
    session_id: str
    signature: str
    ruling: dict


_TIER_DISPOSITION_DELTA: dict[str, int] = {
    "large_success": 3,
    "medium_success": 2,
    "small_success": 1,
    "small_failure": 0,
    "medium_failure": -1,
    "large_failure": -2,
}

_VALID_INTENTS = {"persuade", "threaten", "bribe"}


@router.post("/{npc_id}/persuade")
async def persuade_npc(
    npc_id: str,
    req: PersuadeRequest,
    graph=Depends(get_graph),
    redis=Depends(get_redis),
):
    """Step 1: build and sign a DM persuasion prompt packet for the client to resolve."""
    if req.intent not in _VALID_INTENTS:
        raise HTTPException(400, f"intent 必須是 persuade / threaten / bribe，收到：{req.intent}")

    npc = await npc_repo.get_npc(graph, npc_id)
    if not npc:
        raise HTTPException(404, "NPC not found")
    if npc.get("behavior_state") == "dead":
        raise HTTPException(400, "NPC 已死亡，無法互動。")

    player = await player_repo.get_player(graph, req.player_id)
    if not player:
        raise HTTPException(404, "Player not found")

    if npc.get("current_place_id") != player.get("current_place_id"):
        raise HTTPException(400, "你距離此 NPC 太遠，無法互動。")

    memory = await memory_repo.get_memory(graph, redis, npc_id, req.player_id)
    memory_summary = memory.get("summary", "") or ""

    payload = prompt_builder.build_npc_persuasion_prompt(
        player=player,
        npc=npc,
        player_message=req.player_message,
        intent=req.intent,
        memory_summary=memory_summary,
    )

    session_id = f"{req.player_id}_persuade_{uuid.uuid4().hex[:8]}"
    packet = signer.create_prompt_packet(payload, session_id)

    scene_snapshot = {
        "entity_ids": [npc_id, req.player_id],
        "item_instance_ids": [],
        "inventory_ids": [],
        "is_combat": False,
        "npc_id": npc_id,
        "intent": req.intent,
    }

    await nonce_store.store_pending_ruling(redis, packet["nonce"], {
        "player_id": req.player_id,
        "session_id": session_id,
        "scene_snapshot": scene_snapshot,
        "created_at": time.time(),
    })

    return {"dm_packet": packet, "npc_name": npc.get("name", npc_id), "intent": req.intent}


@router.post("/{npc_id}/persuasion_result")
async def persuasion_result(
    npc_id: str,
    req: PersuasionResultRequest,
    graph=Depends(get_graph),
    redis=Depends(get_redis),
    bus: EventBus = Depends(get_event_bus),
):
    """Step 2: validate the DM ruling, apply disposition change, update memory, broadcast."""
    # 1. Timestamp check
    if not signer.is_timestamp_valid(req.timestamp):
        raise HTTPException(400, "Prompt packet expired or invalid timestamp")

    # 2. Retrieve pending ruling
    pending = await nonce_store.get_pending_ruling(redis, req.nonce)
    if not pending:
        raise HTTPException(400, "Unknown or expired nonce")

    # 3. HMAC verification
    snapshot = pending.get("scene_snapshot", {})
    if not signer.verify_payload(
        {**snapshot, "nonce": req.nonce, "timestamp": req.timestamp, "session_id": req.session_id},
        req.signature,
    ):
        raise HTTPException(403, "HMAC verification failed")

    # 4. Consume nonce (replay prevention)
    if not await nonce_store.consume_nonce(redis, req.nonce):
        raise HTTPException(400, "Nonce already used (replay attack detected)")
    await nonce_store.delete_pending_ruling(redis, req.nonce)

    # 5. Load entities
    npc = await npc_repo.get_npc(graph, npc_id)
    if not npc:
        raise HTTPException(404, "NPC not found")
    player = await player_repo.get_player(graph, req.player_id)
    if not player:
        raise HTTPException(404, "Player not found")

    # 6. Validate ruling structure (basic)
    ruling = req.ruling
    if not isinstance(ruling, dict):
        raise HTTPException(422, "ruling must be a dict")
    if not ruling.get("feasible", True):
        place_id = player.get("current_place_id", "")
        await bus.publish_room(place_id, NPCPersuasionEvent(
            npc_id=npc_id,
            npc_name=npc.get("name", npc_id),
            player_id=req.player_id,
            player_name=player.get("name", req.player_id),
            intent=snapshot.get("intent", "persuade"),
            tier="large_failure",
            narrative=ruling.get("violation_reason", "行動不可行。"),
            disposition=npc.get("disposition", 0),
        ).to_dict())
        return {"success": True, "feasible": False, "narrative": ruling.get("violation_reason", "")}

    outcomes = ruling.get("outcomes", {})
    relevant_stat = ruling.get("relevant_stat", "cha")
    difficulty = int(ruling.get("difficulty", 0))
    threshold = int(ruling.get("threshold", 12))

    # 7. Roll dice
    stat_val = int(player.get(relevant_stat) or 0)
    raw_roll = dice.d20()
    final_roll = raw_roll + stat_val + difficulty

    # 8. Determine tier
    margins = [5, 2, 0, -2, -5]
    tiers = ["large_success", "medium_success", "small_success", "small_failure", "medium_failure", "large_failure"]
    diff = final_roll - threshold
    tier = tiers[-1]
    for i, margin in enumerate(margins):
        if diff >= margin:
            tier = tiers[i]
            break

    # 9. Get narrative from DM outcome
    outcome = outcomes.get(tier, {})
    if isinstance(outcome, dict):
        narrative = outcome.get("narrative", "")
    else:
        narrative = ""

    # 10. Update NPC disposition (clamped -5 to +5)
    delta = _TIER_DISPOSITION_DELTA.get(tier, 0)
    current_disposition = int(npc.get("disposition", 0))
    new_disposition = max(-5, min(5, current_disposition + delta))
    if new_disposition != current_disposition:
        await npc_repo.update_npc(graph, npc_id, {"disposition": new_disposition})

    # 11. Store outcome as memory round
    intent_zh = {"persuade": "說服", "threaten": "威脅", "bribe": "賄賂"}.get(
        snapshot.get("intent", "persuade"), "互動"
    )
    compressed = f"{player.get('name', req.player_id)}嘗試{intent_zh}：{narrative}"
    await memory_repo.add_round(redis, npc_id, req.player_id, compressed)

    # 12. Broadcast
    place_id = player.get("current_place_id", "")
    await bus.publish_room(place_id, NPCPersuasionEvent(
        npc_id=npc_id,
        npc_name=npc.get("name", npc_id),
        player_id=req.player_id,
        player_name=player.get("name", req.player_id),
        intent=snapshot.get("intent", "persuade"),
        tier=tier,
        narrative=narrative,
        disposition=new_disposition,
    ).to_dict())

    return {
        "success": True,
        "feasible": True,
        "tier": tier,
        "raw_roll": raw_roll,
        "final_roll": final_roll,
        "threshold": threshold,
        "disposition": new_disposition,
        "narrative": narrative,
    }
