"""DM ruling submission endpoint — Step 2 of the DM ruling flow."""
import time

from fastapi import APIRouter, Depends, HTTPException

from server.dependencies import get_graph, get_redis, get_event_bus, get_batch_writer
from server.dm import nonce_store, signer
from server.dm.schemas import DMRulingSubmission
from server.dm.validator import RulingContext, validate_ruling, RulingValidationError
from server.broadcast.event_bus import EventBus
from server.broadcast.event_types import WorldStateChangeEvent
from server.db.repositories import player_repo

router = APIRouter(prefix="/dm", tags=["dm"])


@router.post("/ruling")
async def submit_ruling(
    sub: DMRulingSubmission,
    graph=Depends(get_graph),
    redis=Depends(get_redis),
    bus: EventBus = Depends(get_event_bus),
    writer=Depends(get_batch_writer),
):
    received_at = time.time()

    # 1. Timestamp validity
    if not signer.is_timestamp_valid(sub.timestamp):
        raise HTTPException(400, "Prompt packet expired or invalid timestamp")

    # 2. Retrieve pending ruling context
    pending = await nonce_store.get_pending_ruling(redis, sub.nonce)
    if not pending:
        raise HTTPException(400, "Unknown or expired nonce")

    # 3. HMAC verification
    payload = sub.model_dump()["ruling"]  # partial check; verify full packet payload
    reconstructed_payload = {**pending.get("scene_snapshot", {})}
    # Verify signature against the stored session_id (the full packet was signed with it)
    if not signer.verify_payload(
        {**reconstructed_payload, "nonce": sub.nonce, "timestamp": sub.timestamp, "session_id": sub.session_id},
        sub.signature,
    ):
        raise HTTPException(403, "HMAC verification failed")

    # 4. Consume nonce (replay prevention)
    if not await nonce_store.consume_nonce(redis, sub.nonce):
        raise HTTPException(400, "Nonce already used (replay attack detected)")

    # 5. Build validation context from scene snapshot
    snapshot = pending.get("scene_snapshot", {})
    ctx = RulingContext(
        player_id=pending["player_id"],
        is_combat=snapshot.get("is_combat", False),
        scene_entity_ids=set(snapshot.get("entity_ids", [])),
        scene_item_instance_ids=set(snapshot.get("item_instance_ids", [])),
        player_inventory_ids=set(snapshot.get("inventory_ids", [])),
    )

    response_time_ms = (received_at - pending["created_at"]) * 1000

    # 6. Validate ruling
    try:
        validated = validate_ruling(sub.ruling, ctx, response_time_ms)
    except RulingValidationError as e:
        await nonce_store.delete_pending_ruling(redis, sub.nonce)
        raise HTTPException(422, str(e))

    # 7. Clean up pending state
    await nonce_store.delete_pending_ruling(redis, sub.nonce)

    # 8. Apply effects (delegated to game state — simplified here)
    event = WorldStateChangeEvent(
        place_id="",
        change_type="dm_ruling_applied",
        details={
            "player_id": pending["player_id"],
            "feasible": validated.feasible,
            "effect_type": validated.effect_type,
            "modifier": validated.modifier,
            "narrative_hint": validated.narrative_hint,
        },
    )
    player = await player_repo.get_player(graph, pending["player_id"])
    if player:
        event.place_id = player.get("current_place_id", "")
        await bus.publish_room(event.place_id, event.to_dict())

    return {
        "success": True,
        "feasible": validated.feasible,
        "effect_type": validated.effect_type,
        "modifier": validated.modifier,
        "narrative_hint": validated.narrative_hint,
    }
