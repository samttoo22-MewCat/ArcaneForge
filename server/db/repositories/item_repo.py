"""Repository for item_instance nodes and their edges."""
from typing import Optional


def _node_props(result_set) -> Optional[dict]:
    if not result_set:
        return None
    return result_set[0][0].properties


async def get_item_instance(graph, instance_id: str) -> Optional[dict]:
    r = await graph.query(
        "MATCH (i:item_instance {instance_id: $id}) RETURN i",
        {"id": instance_id},
    )
    return _node_props(r.result_set)


async def get_items_in_place(graph, place_id: str) -> list[dict]:
    r = await graph.query(
        "MATCH (i:item_instance)-[:LOCATED_IN]->(s:small_place {id: $pid}) RETURN i",
        {"pid": place_id},
    )
    return [row[0].properties for row in r.result_set]


async def get_player_inventory(graph, player_id: str) -> list[dict]:
    r = await graph.query(
        "MATCH (i:item_instance)-[:OWNED_BY]->(p:player {id: $pid}) RETURN i",
        {"pid": player_id},
    )
    return [row[0].properties for row in r.result_set]


async def create_item_instance(graph, props: dict) -> None:
    await graph.query(
        "MERGE (i:item_instance {instance_id: $iid}) SET i += $props",
        {"iid": props["instance_id"], "props": props},
    )


async def place_item_in_room(graph, instance_id: str, place_id: str) -> None:
    await graph.query(
        "MATCH (i:item_instance {instance_id: $iid}), (s:small_place {id: $pid}) "
        "OPTIONAL MATCH (i)-[old:LOCATED_IN|OWNED_BY|EQUIPPED_BY]->() DELETE old "
        "CREATE (i)-[:LOCATED_IN]->(s) "
        "SET i.location_type = 'room', i.location_id = $pid",
        {"iid": instance_id, "pid": place_id},
    )


async def give_item_to_player(graph, instance_id: str, player_id: str) -> None:
    await graph.query(
        "MATCH (i:item_instance {instance_id: $iid}), (p:player {id: $pid}) "
        "OPTIONAL MATCH (i)-[old:LOCATED_IN|OWNED_BY|EQUIPPED_BY]->() DELETE old "
        "CREATE (i)-[:OWNED_BY]->(p) "
        "SET i.location_type = 'player_inventory', i.location_id = $pid",
        {"iid": instance_id, "pid": player_id},
    )


async def equip_item(graph, instance_id: str, player_id: str) -> None:
    await graph.query(
        "MATCH (i:item_instance {instance_id: $iid}), (p:player {id: $pid}) "
        "OPTIONAL MATCH (i)-[old:LOCATED_IN|OWNED_BY|EQUIPPED_BY]->() DELETE old "
        "CREATE (i)-[:EQUIPPED_BY]->(p) "
        "SET i.location_type = 'equipped', i.location_id = $pid",
        {"iid": instance_id, "pid": player_id},
    )


async def get_player_inventory_by_item_id(graph, player_id: str, item_id: str) -> list[dict]:
    """Get all instances of a specific item_id owned by player."""
    r = await graph.query(
        "MATCH (i:item_instance {item_id: $item_id})-[:OWNED_BY]->(p:player {id: $pid}) RETURN i",
        {"item_id": item_id, "pid": player_id},
    )
    return [row[0].properties for row in r.result_set]


async def consume_items_from_inventory(graph, player_id: str, item_id: str, amount: int) -> bool:
    """
    Consume `amount` units of `item_id` from player inventory (stack-aware).
    Returns True if successful, False if insufficient quantity.
    """
    instances = await get_player_inventory_by_item_id(graph, player_id, item_id)
    total = sum(i.get("quantity", 1) for i in instances)
    if total < amount:
        return False

    remaining = amount
    for inst in instances:
        if remaining <= 0:
            break
        qty = inst.get("quantity", 1)
        if qty <= remaining:
            await graph.query(
                "MATCH (i:item_instance {instance_id: $iid}) DETACH DELETE i",
                {"iid": inst["instance_id"]},
            )
            remaining -= qty
        else:
            await graph.query(
                "MATCH (i:item_instance {instance_id: $iid}) SET i.quantity = $qty",
                {"iid": inst["instance_id"], "qty": qty - remaining},
            )
            remaining = 0
    return True
