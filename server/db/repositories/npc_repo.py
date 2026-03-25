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
