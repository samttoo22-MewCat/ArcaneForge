"""Combat state stored in Redis (fast) and synced to FalkorDB on combat end."""
import json
from typing import Optional

import redis.asyncio as aioredis


COMBAT_TTL = 3600  # 1 hour — auto-cleanup if server crashes


def _combat_key(room_id: str) -> str:
    return f"combat:{room_id}"


async def init_combat(redis: aioredis.Redis, room_id: str, combatants: list[dict]) -> None:
    key = _combat_key(room_id)
    data = json.dumps({"room_id": room_id, "round": 0, "combatants": combatants, "active": True})
    await redis.set(key, data, ex=COMBAT_TTL)


async def get_combat(redis: aioredis.Redis, room_id: str) -> Optional[dict]:
    key = _combat_key(room_id)
    raw = await redis.get(key)
    return json.loads(raw) if raw else None


async def update_combat(redis: aioredis.Redis, room_id: str, updates: dict) -> None:
    state = await get_combat(redis, room_id)
    if state is None:
        return
    state.update(updates)
    await redis.set(_combat_key(room_id), json.dumps(state), ex=COMBAT_TTL)


async def end_combat(redis: aioredis.Redis, room_id: str) -> None:
    await redis.delete(_combat_key(room_id))


async def update_combatant_hp(redis: aioredis.Redis, room_id: str, combatant_id: str, new_hp: int) -> None:
    state = await get_combat(redis, room_id)
    if state is None:
        return
    for c in state["combatants"]:
        if c["id"] == combatant_id:
            c["hp"] = new_hp
            break
    await redis.set(_combat_key(room_id), json.dumps(state), ex=COMBAT_TTL)
