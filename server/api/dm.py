"""DM ruling submission endpoint — Step 2 of the DM ruling flow."""
import json
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from server.broadcast.event_bus import EventBus
from server.broadcast.event_types import DMRulingAppliedEvent
from server.db.repositories import item_repo, player_repo
from server.dependencies import get_batch_writer, get_event_bus, get_graph, get_redis
from server.dm import nonce_store, signer
from server.dm.schemas import DMRulingSubmission
from server.dm.validator import RulingContext, RulingValidationError, validate_ruling
from server.engine import dice

router = APIRouter(prefix="/dm", tags=["dm"])

_DATA = Path(__file__).parent.parent.parent / "data"

_action_rules_cache: dict | None = None
_outcome_fx_cache: dict | None = None


def _load_action_rules() -> dict:
    global _action_rules_cache
    if _action_rules_cache is None:
        p = _DATA / "action_rules.json"
        _action_rules_cache = json.loads(p.read_text()) if p.exists() else {}
    return _action_rules_cache


def _load_outcome_fx() -> dict:
    global _outcome_fx_cache
    if _outcome_fx_cache is None:
        p = _DATA / "outcome_effects.json"
        _outcome_fx_cache = json.loads(p.read_text()) if p.exists() else {}
    return _outcome_fx_cache


def _get_stat(player: dict, stat: str) -> int:
    """Safely retrieve a numeric stat from a player dict."""
    val = player.get(stat) or player.get(f"{stat}_") or 0
    return int(val) if val is not None else 0


async def _apply_outcome_effects(
    graph,
    player: dict,
    outcome,
    fx: dict,
    tier: str,
) -> tuple[str | None, str | None]:
    """
    Apply game-state effects for the resolved tier outcome.
    Returns (status_applied, item_consumed) for broadcast.
    """
    player_id = player["id"]
    status_applied: str | None = None
    item_consumed: str | None = None

    # ── Heal ──────────────────────────────────────────────────────────────────
    if outcome.effect_type == "heal":
        heal_mult = fx.get("heal_multiplier", 0.0)
        if heal_mult > 0:
            heal_amt = max(1, int(player.get("atk", 5) * heal_mult))
            new_hp = min(player.get("hp_max", 100), player.get("hp", 0) + heal_amt)
            await player_repo.update_player(graph, player_id, {"hp": new_hp})

    # ── Status apply ──────────────────────────────────────────────────────────
    elif outcome.effect_type == "status_apply" and outcome.status_to_apply:
        target_id = outcome.status_target or player_id
        target = player if target_id == player_id else None
        if target is None:
            # Try to load NPC (best-effort; NPC status is handled by npc_ai)
            pass
        else:
            effects: list = list(target.get("status_effects") or [])
            if outcome.status_to_apply not in effects:
                effects.append(outcome.status_to_apply)
            await player_repo.update_player(graph, target_id, {"status_effects": effects})
        status_applied = outcome.status_to_apply

    # ── Item consumed ─────────────────────────────────────────────────────────
    if outcome.item_consumed:
        await graph.query(
            "MATCH (i:item_instance {instance_id: $iid}) DETACH DELETE i",
            {"iid": outcome.item_consumed},
        )
        item_consumed = outcome.item_consumed

    # ── Penalty from outcome_effects.json ─────────────────────────────────────
    penalty = fx.get("penalty")
    if penalty == "skip_turn":
        effects = list(player.get("status_effects") or [])
        if "stun" not in effects:
            effects.append("stun")
        await player_repo.update_player(graph, player_id, {"status_effects": effects})
        if not status_applied:
            status_applied = "stun"

    elif penalty == "backfire_damage":
        backfire = max(1, int(player.get("atk", 5) * 0.3))
        new_hp = max(0, player.get("hp", 1) - backfire)
        await player_repo.update_player(graph, player_id, {"hp": new_hp})

    return status_applied, item_consumed


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
    snapshot = pending.get("scene_snapshot", {})
    if not signer.verify_payload(
        {**snapshot, "nonce": sub.nonce, "timestamp": sub.timestamp, "session_id": sub.session_id},
        sub.signature,
    ):
        raise HTTPException(403, "HMAC verification failed")

    # 4. Consume nonce (replay prevention)
    if not await nonce_store.consume_nonce(redis, sub.nonce):
        raise HTTPException(400, "Nonce already used (replay attack detected)")

    # 5. Build validation context
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

    await nonce_store.delete_pending_ruling(redis, sub.nonce)

    player = await player_repo.get_player(graph, pending["player_id"])
    if not player:
        raise HTTPException(404, "Player not found")

    place_id = player.get("current_place_id", "")

    # 7. Not feasible — broadcast rejection and return
    if not validated.feasible:
        event = DMRulingAppliedEvent(
            player_id=pending["player_id"],
            feasible=False,
            narrative_hint=validated.violation_reason or "行動不可行。",
        )
        await bus.publish_room(place_id, event.to_dict())
        return {
            "success": True,
            "feasible": False,
            "narrative_hint": event.narrative_hint,
        }

    # 8. Roll dice
    action_rules = _load_action_rules()
    outcome_fx = _load_outcome_fx()

    stat_val = _get_stat(player, validated.relevant_stat)
    raw_roll = dice.d20()
    final_roll = raw_roll + stat_val + validated.difficulty
    tier_margins = action_rules.get("tier_margins")
    tier = dice.calc_tier(final_roll, validated.threshold, tier_margins)

    # 9. Pick outcome for this tier
    outcome = validated.outcomes.get(tier)
    if not outcome:
        # Fallback (should not happen after validation)
        outcome = type("O", (), {"effect_type": "no_effect", "narrative": "",
                                  "status_to_apply": None, "status_target": None,
                                  "item_consumed": None})()

    fx = outcome_fx.get(tier, {})
    modifier = fx.get("damage_multiplier", 1.0) if outcome.effect_type == "damage_modifier" else 1.0

    # 10. Apply state effects
    status_applied, item_consumed = await _apply_outcome_effects(graph, player, outcome, fx, tier)

    # 11. Broadcast
    event = DMRulingAppliedEvent(
        player_id=pending["player_id"],
        feasible=True,
        tier=tier,
        raw_roll=raw_roll,
        final_roll=final_roll,
        threshold=validated.threshold,
        relevant_stat=validated.relevant_stat,
        stat_value=stat_val,
        difficulty=validated.difficulty,
        effect_type=outcome.effect_type,
        modifier=modifier,
        narrative_hint=outcome.narrative,
        status_applied=status_applied,
        item_consumed=item_consumed,
    )
    await bus.publish_room(place_id, event.to_dict())

    return {
        "success": True,
        "feasible": True,
        "tier": tier,
        "raw_roll": raw_roll,
        "final_roll": final_roll,
        "threshold": validated.threshold,
        "effect_type": outcome.effect_type,
        "modifier": modifier,
        "narrative_hint": outcome.narrative,
        "status_applied": status_applied,
    }
