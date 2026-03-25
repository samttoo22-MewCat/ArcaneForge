"""Repository for player nodes."""
import json
from typing import Optional


def _node_props(result_set) -> Optional[dict]:
    if not result_set:
        return None
    return result_set[0][0].properties


async def get_player(graph, player_id: str) -> Optional[dict]:
    r = await graph.query("MATCH (p:player {id: $id}) RETURN p", {"id": player_id})
    return _node_props(r.result_set)


async def create_player(graph, props: dict) -> None:
    props.setdefault("status_effects", [])
    props.setdefault("inventory_item_instance_ids", [])
    # FalkorDB only supports primitives — store dict as JSON string
    props.setdefault("equipped_slots", json.dumps({}))
    props.setdefault("is_in_combat", False)
    props.setdefault("combat_room_id", None)
    props.setdefault("is_traveling", False)
    props.setdefault("travel_destination_id", None)
    props.setdefault("travel_arrives_at", None)

    # Sanitize: convert any remaining dicts/lists-of-dicts to JSON strings
    sanitized = {}
    for k, v in props.items():
        if isinstance(v, dict):
            sanitized[k] = json.dumps(v)
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            sanitized[k] = json.dumps(v)
        else:
            sanitized[k] = v

    await graph.query(
        "MERGE (p:player {id: $id}) SET p += $props",
        {"id": sanitized["id"], "props": sanitized},
    )


async def update_player(graph, player_id: str, updates: dict) -> None:
    set_clause = ", ".join(f"p.{k} = ${k}" for k in updates)
    params = {"id": player_id, **updates}
    await graph.query(f"MATCH (p:player {{id: $id}}) SET {set_clause}", params)


async def update_player_location(graph, player_id: str, new_place_id: str) -> None:
    await graph.query(
        "MATCH (p:player {id: $id}) SET p.current_place_id = $place_id",
        {"id": player_id, "place_id": new_place_id},
    )


async def set_travel_state(
    graph,
    player_id: str,
    is_traveling: bool,
    destination_id: Optional[str] = None,
    arrives_at: Optional[float] = None,
) -> None:
    await graph.query(
        "MATCH (p:player {id: $id}) "
        "SET p.is_traveling = $traveling, "
        "    p.travel_destination_id = $dest, "
        "    p.travel_arrives_at = $eta",
        {"id": player_id, "traveling": is_traveling, "dest": destination_id, "eta": arrives_at},
    )


async def set_combat_state(graph, player_id: str, in_combat: bool, combat_room_id: Optional[str]) -> None:
    await graph.query(
        "MATCH (p:player {id: $id}) SET p.is_in_combat = $in_combat, p.combat_room_id = $room_id",
        {"id": player_id, "in_combat": in_combat, "room_id": combat_room_id},
    )
