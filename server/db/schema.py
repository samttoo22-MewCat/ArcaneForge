"""FalkorDB schema initialisation: indexes and unique constraints."""

INDEX_QUERIES = [
    "CREATE INDEX FOR (n:large_place) ON (n.id)",
    "CREATE INDEX FOR (n:middle_place) ON (n.id)",
    "CREATE INDEX FOR (n:small_place) ON (n.id)",
    "CREATE INDEX FOR (n:player) ON (n.id)",
    "CREATE INDEX FOR (n:npc) ON (n.id)",
    "CREATE INDEX FOR (n:item_instance) ON (n.instance_id)",
]

# (label, property) pairs for unique node constraints via SDK method
UNIQUE_CONSTRAINTS = [
    ("player", "id"),
    ("small_place", "id"),
    ("item_instance", "instance_id"),
]


async def init_schema(graph) -> None:
    # Create indexes (idempotent)
    for query in INDEX_QUERIES:
        try:
            await graph.query(query)
        except Exception as e:
            msg = str(e).lower()
            if "already exists" in msg or "equivalent index" in msg or "already indexed" in msg:
                continue
            raise

    # Create unique constraints via SDK (uses GRAPH.CONSTRAINT internally)
    for label, prop in UNIQUE_CONSTRAINTS:
        try:
            await graph.create_node_unique_constraint(label, prop)
        except Exception as e:
            msg = str(e).lower()
            if "already exists" in msg or "equivalent" in msg or "constraint" in msg:
                continue
            raise
