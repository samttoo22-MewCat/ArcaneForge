"""Repository for player nodes."""
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
    props.setdefault("equipped_slots", {})
    props.setdefault("is_in_combat", False)
    props.setdefault("combat_room_id", None)
    await graph.query(
        "MERGE (p:player {id: $id}) SET p += $props",
        {"id": props["id"], "props": props},
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


async def set_combat_state(graph, player_id: str, in_combat: bool, combat_room_id: Optional[str]) -> None:
    await graph.query(
        "MATCH (p:player {id: $id}) SET p.is_in_combat = $in_combat, p.combat_room_id = $room_id",
        {"id": player_id, "in_combat": in_combat, "room_id": combat_room_id},
    )
