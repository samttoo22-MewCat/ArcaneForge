"""World seed script: populates FalkorDB with the sample world graph."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from server.db.connection import ensure_docker_running, create_falkordb_client, create_redis_client
from server.db.schema import init_schema
from server.db.repositories import place_repo, npc_repo, item_repo
from server.config import settings

_WORLD_DATA = Path(__file__).parent / "sample_world.json"
_NPC_TEMPLATES = Path(__file__).parent.parent / "npc_templates.json"


async def seed():
    print("[seed] Ensuring services are running...")
    await ensure_docker_running()

    client = create_falkordb_client()
    graph = client.select_graph(settings.game_graph_name)
    redis = create_redis_client()
    await redis.ping()

    await init_schema(graph)
    print("[seed] Schema ready.")

    world = json.loads(_WORLD_DATA.read_text(encoding="utf-8"))
    templates = json.loads(_NPC_TEMPLATES.read_text(encoding="utf-8"))

    # large places
    for lp in world["large_places"]:
        await graph.query(
            "MERGE (n:large_place {id: $id}) SET n += $props",
            {"id": lp["id"], "props": lp},
        )
    print(f"[seed] {len(world['large_places'])} large_place(s) created.")

    # middle places + BELONGS_TO edges
    for mp in world["middle_places"]:
        await graph.query(
            "MERGE (n:middle_place {id: $id}) SET n += $props",
            {"id": mp["id"], "props": mp},
        )
        await graph.query(
            "MATCH (m:middle_place {id: $mid}), (l:large_place {id: $lid}) "
            "MERGE (m)-[:BELONGS_TO]->(l)",
            {"mid": mp["id"], "lid": mp["parent_large_id"]},
        )
    print(f"[seed] {len(world['middle_places'])} middle_place(s) created.")

    # small places + BELONGS_TO edges
    for sp in world["small_places"]:
        await place_repo.create_small_place(graph, sp)
        await graph.query(
            "MATCH (s:small_place {id: $sid}), (m:middle_place {id: $mid}) "
            "MERGE (s)-[:BELONGS_TO]->(m)",
            {"sid": sp["id"], "mid": sp["parent_middle_id"]},
        )
    print(f"[seed] {len(world['small_places'])} small_place(s) created.")

    # connections
    for conn in world["connections"]:
        edge_props = {k: v for k, v in conn.items() if k not in ("from", "to")}
        await place_repo.create_connection(graph, conn["from"], conn["to"], edge_props)
    print(f"[seed] {len(world['connections'])} connection(s) created.")

    # NPCs
    for npc_def in world["initial_npcs"]:
        tpl = templates.get(npc_def["template"], {})
        props = {**tpl, "id": npc_def["id"], "current_place_id": npc_def["place_id"]}
        await npc_repo.create_npc(graph, props)
        # Update place npc_ids
        await graph.query(
            "MATCH (s:small_place {id: $pid}) "
            "WHERE NOT $nid IN s.npc_ids "
            "SET s.npc_ids = s.npc_ids + [$nid]",
            {"pid": npc_def["place_id"], "nid": npc_def["id"]},
        )
    print(f"[seed] {len(world['initial_npcs'])} NPC(s) created.")

    # Items
    for item_def in world["initial_items"]:
        props = {
            "instance_id": item_def["instance_id"],
            "item_id": item_def["item_id"],
            "durability": item_def.get("durability", 100),
            "quantity": item_def.get("quantity", 1),
            "location_type": "room",
            "location_id": item_def["place_id"],
        }
        await item_repo.create_item_instance(graph, props)
        await graph.query(
            "MATCH (i:item_instance {instance_id: $iid}), (s:small_place {id: $pid}) "
            "MERGE (i)-[:LOCATED_IN]->(s)",
            {"iid": item_def["instance_id"], "pid": item_def["place_id"]},
        )
        await graph.query(
            "MATCH (s:small_place {id: $pid}) "
            "WHERE NOT $iid IN s.item_instance_ids "
            "SET s.item_instance_ids = s.item_instance_ids + [$iid]",
            {"pid": item_def["place_id"], "iid": item_def["instance_id"]},
        )
    print(f"[seed] {len(world['initial_items'])} item(s) placed.")

    await redis.aclose()
    print("[seed] Done! World is ready.")


if __name__ == "__main__":
    asyncio.run(seed())
