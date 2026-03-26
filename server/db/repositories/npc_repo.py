"""Repository for NPC nodes."""
import json
import time
from typing import Optional


def _sanitize_props(props: dict) -> dict:
    """
    FalkorDB only supports primitive types and arrays of primitives.
    Serialize any list-of-dicts or nested-dict values as JSON strings.
    """
    clean = {}
    for k, v in props.items():
        if isinstance(v, list) and v and isinstance(v[0], dict):
            clean[k] = json.dumps(v, ensure_ascii=False)
        elif isinstance(v, dict):
            clean[k] = json.dumps(v, ensure_ascii=False)
        else:
            clean[k] = v
    return clean


def _node_props(result_set) -> Optional[dict]:
    if not result_set:
        return None
    return result_set[0][0].properties


async def get_npc(graph, npc_id: str) -> Optional[dict]:
    r = await graph.query("MATCH (n:npc {id: $id}) RETURN n", {"id": npc_id})
    return _node_props(r.result_set)


async def get_npcs_in_place(graph, place_id: str) -> list[dict]:
    r = await graph.query(
        "MATCH (n:npc {current_place_id: $pid}) RETURN n",
        {"pid": place_id},
    )
    return [row[0].properties for row in r.result_set]


async def create_npc(graph, props: dict) -> None:
    props.setdefault("status_effects", [])
    props.setdefault("hostility_toward", [])
    props.setdefault("is_hibernating", False)
    props.setdefault("frozen_at", None)
    props.setdefault("memory_summary", "")
    # New NPC feature defaults
    props.setdefault("personality", "aggressive")
    props.setdefault("patrol_route", json.dumps([]))
    props.setdefault("next_patrol_index", 0)
    props.setdefault("patrol_cooldown_ticks", 0)
    props.setdefault("mp", 0)
    props.setdefault("mp_max", 0)
    props.setdefault("skills", json.dumps([]))
    props.setdefault("active_effects", json.dumps([]))
    props.setdefault("dialogue_tree", json.dumps({}))
    safe_props = _sanitize_props(props)
    await graph.query(
        "MERGE (n:npc {id: $id}) SET n += $props",
        {"id": safe_props["id"], "props": safe_props},
    )


async def hibernate_npcs_in_place(graph, place_id: str) -> None:
    now = time.time()
    await graph.query(
        "MATCH (n:npc {current_place_id: $pid}) SET n.is_hibernating = true, n.frozen_at = $now",
        {"pid": place_id, "now": now},
    )


async def wake_npcs_in_place(graph, place_id: str) -> list[dict]:
    """Wake hibernating NPCs and return them for delayed-simulation processing."""
    r = await graph.query(
        "MATCH (n:npc {current_place_id: $pid, is_hibernating: true}) "
        "SET n.is_hibernating = false "
        "RETURN n",
        {"pid": place_id},
    )
    return [row[0].properties for row in r.result_set]


async def update_npc_memory(graph, npc_id: str, memory_summary: str) -> None:
    await graph.query(
        "MATCH (n:npc {id: $id}) SET n.memory_summary = $mem",
        {"id": npc_id, "mem": memory_summary},
    )


async def update_npc(graph, npc_id: str, updates: dict) -> None:
    if not updates:
        return
    safe = _sanitize_props(updates)
    set_clause = ", ".join(f"n.{k} = ${k}" for k in safe)
    params = {"id": npc_id, **safe}
    await graph.query(f"MATCH (n:npc {{id: $id}}) SET {set_clause}", params)


async def update_npc_hp(graph, npc_id: str, new_hp: int) -> None:
    await graph.query(
        "MATCH (n:npc {id: $id}) SET n.hp = $hp",
        {"id": npc_id, "hp": new_hp},
    )


async def move_npc_to_place(
    graph, npc_id: str, new_place_id: str, next_index: int, cooldown: int
) -> None:
    """Move a patrolling NPC to a new room and reset its patrol cooldown."""
    await graph.query(
        "MATCH (n:npc {id: $id}) "
        "SET n.current_place_id = $place, "
        "    n.next_patrol_index = $idx, "
        "    n.patrol_cooldown_ticks = $cd",
        {"id": npc_id, "place": new_place_id, "idx": next_index, "cd": cooldown},
    )


async def get_npc_shop(graph, npc_id: str) -> list[dict]:
    """Return parsed shop_inventory for a merchant NPC."""
    import json
    npc = await get_npc(graph, npc_id)
    if not npc:
        return []
    raw = npc.get("shop_inventory", "[]")
    if isinstance(raw, str):
        return json.loads(raw)
    return raw if isinstance(raw, list) else []
