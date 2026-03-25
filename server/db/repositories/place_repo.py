"""Repository for large_place, middle_place, small_place nodes."""
from typing import Optional


def _node_props(result_set, index=0) -> Optional[dict]:
    if not result_set:
        return None
    return result_set[0][index].properties


async def get_large_place(graph, place_id: str) -> Optional[dict]:
    r = await graph.query("MATCH (n:large_place {id: $id}) RETURN n", {"id": place_id})
    return _node_props(r.result_set)


async def get_middle_place(graph, place_id: str) -> Optional[dict]:
    r = await graph.query("MATCH (n:middle_place {id: $id}) RETURN n", {"id": place_id})
    return _node_props(r.result_set)


async def get_small_place(graph, place_id: str) -> Optional[dict]:
    r = await graph.query("MATCH (n:small_place {id: $id}) RETURN n", {"id": place_id})
    return _node_props(r.result_set)


async def get_connected_places(graph, place_id: str) -> list[dict]:
    r = await graph.query(
        "MATCH (s:small_place {id: $id})-[e:CONNECTS_TO]->(t:small_place) "
        "RETURN t, e.direction, e.is_locked, e.requires_key_id, e.is_hidden",
        {"id": place_id},
    )
    results = []
    for row in r.result_set:
        place = row[0].properties
        place["_edge"] = {
            "direction": row[1],
            "is_locked": row[2],
            "requires_key_id": row[3],
            "is_hidden": row[4],
        }
        results.append(place)
    return results


async def create_small_place(graph, props: dict) -> None:
    props.setdefault("player_ids", [])
    props.setdefault("npc_ids", [])
    props.setdefault("item_instance_ids", [])
    await graph.query(
        "MERGE (s:small_place {id: $id}) SET s += $props",
        {"id": props["id"], "props": props},
    )


async def create_connection(graph, from_id: str, to_id: str, edge_props: dict) -> None:
    await graph.query(
        "MATCH (a:small_place {id: $from_id}), (b:small_place {id: $to_id}) "
        "MERGE (a)-[e:CONNECTS_TO {direction: $dir}]->(b) SET e += $props",
        {"from_id": from_id, "to_id": to_id, "dir": edge_props.get("direction"), "props": edge_props},
    )
