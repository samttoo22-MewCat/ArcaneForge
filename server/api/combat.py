"""Combat endpoints."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from server.broadcast.event_bus import EventBus
from server.broadcast.event_types import CombatStartedEvent, CombatRoundEvent, CombatEndedEvent
from server.db.repositories import player_repo, npc_repo, combat_repo
from server.dependencies import get_graph, get_redis, get_event_bus, get_batch_writer
from server.engine import rules
from server.engine.combat import Combatant, tick_to_ready, calculate_damage, apply_damage, check_double_action
from server.engine.state_machine import BattleStateMachine, BattleState

router = APIRouter(prefix="/combat", tags=["combat"])


class AttackRequest(BaseModel):
    player_id: str
    target_id: str
    target_type: str = "npc"  # "npc" | "player"
    dm_modifier: float = 1.0  # from prior DM ruling, default 1.0


class FleeRequest(BaseModel):
    player_id: str


@router.post("/attack")
async def attack(
    req: AttackRequest,
    graph=Depends(get_graph),
    redis=Depends(get_redis),
    bus: EventBus = Depends(get_event_bus),
    writer=Depends(get_batch_writer),
):
    player = await player_repo.get_player(graph, req.player_id)
    if not player:
        raise HTTPException(404, "Player not found")

    place_id = player["current_place_id"]

    # Load target
    if req.target_type == "npc":
        target = await npc_repo.get_npc(graph, req.target_id)
    else:
        target = await player_repo.get_player(graph, req.target_id)
    if not target:
        raise HTTPException(404, "Target not found")

    rules.can_attack(player, target, place_id)

    if rules.is_safe_zone(await _get_place(graph, place_id)):
        raise HTTPException(400, "安全區內無法發動戰鬥。")

    # Ensure combat state exists
    room_id = player.get("combat_room_id") or f"combat_{place_id}_{uuid.uuid4().hex[:6]}"
    combat_state = await combat_repo.get_combat(redis, room_id)
    if not combat_state:
        attacker_c = _to_combatant(player)
        target_c = _to_combatant(target)
        await combat_repo.init_combat(redis, room_id, [
            _combatant_to_dict(attacker_c),
            _combatant_to_dict(target_c),
        ])
        await player_repo.set_combat_state(graph, req.player_id, True, room_id)
        event = CombatStartedEvent(
            room_id=room_id,
            combatants=[{"id": player["id"], "name": player.get("name")},
                        {"id": target["id"], "name": target.get("name")}],
        ).to_dict()
        await bus.publish_room(place_id, event)

    # Calculate damage
    damage = calculate_damage(player.get("atk", 5), target.get("def_", 2), req.dm_modifier, is_combat=True)
    new_hp = max(0, target.get("hp", 1) - damage)

    await combat_repo.update_combatant_hp(redis, room_id, req.target_id, new_hp)

    round_event = CombatRoundEvent(
        room_id=room_id,
        round_num=combat_state["round"] if combat_state else 1,
        actor_id=req.player_id,
        target_id=req.target_id,
        action="attack",
        damage=damage,
        target_hp_remaining=new_hp,
    ).to_dict()
    await bus.publish_room(place_id, round_event)

    if new_hp <= 0:
        await combat_repo.end_combat(redis, room_id)
        await player_repo.set_combat_state(graph, req.player_id, False, None)
        ended_event = CombatEndedEvent(room_id=room_id, winner_id=req.player_id).to_dict()
        await bus.publish_room(place_id, ended_event)
        return {"success": True, "damage": damage, "target_defeated": True}

    return {"success": True, "damage": damage, "target_hp_remaining": new_hp}


@router.get("/status/{room_id}")
async def combat_status(room_id: str, redis=Depends(get_redis)):
    state = await combat_repo.get_combat(redis, room_id)
    if not state:
        raise HTTPException(404, "Combat room not found")
    return state


@router.post("/flee")
async def flee(req: FleeRequest, graph=Depends(get_graph), redis=Depends(get_redis), bus=Depends(get_event_bus)):
    player = await player_repo.get_player(graph, req.player_id)
    if not player or not player.get("is_in_combat"):
        raise HTTPException(400, "你不在戰鬥中。")
    room_id = player.get("combat_room_id")
    await combat_repo.end_combat(redis, room_id)
    await player_repo.set_combat_state(graph, req.player_id, False, None)
    return {"success": True, "fled": True}


# --- helpers ---

async def _get_place(graph, place_id: str) -> dict:
    from server.db.repositories import place_repo
    p = await place_repo.get_small_place(graph, place_id)
    return p or {}


def _to_combatant(entity: dict) -> Combatant:
    return Combatant(
        id=entity["id"],
        spd=entity.get("spd", 10),
        hp=entity.get("hp", 1),
        hp_max=entity.get("hp_max", entity.get("hp", 1)),
        atk=entity.get("atk", 5),
        def_=entity.get("def_", 2),
    )


def _combatant_to_dict(c: Combatant) -> dict:
    return {"id": c.id, "hp": c.hp, "hp_max": c.hp_max, "atk": c.atk, "def_": c.def_, "spd": c.spd, "charge": c.charge}
