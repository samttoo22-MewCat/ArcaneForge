"""FalkorDB schema initialisation: indexes and constraints."""

SCHEMA_QUERIES = [
    # Indexes for fast MATCH by id
    "CREATE INDEX FOR (n:large_place) ON (n.id)",
    "CREATE INDEX FOR (n:middle_place) ON (n.id)",
    "CREATE INDEX FOR (n:small_place) ON (n.id)",
    "CREATE INDEX FOR (n:player) ON (n.id)",
    "CREATE INDEX FOR (n:npc) ON (n.id)",
    "CREATE INDEX FOR (n:item_instance) ON (n.instance_id)",
    # Unique constraints
    "CREATE CONSTRAINT ON (n:player) ASSERT n.id IS UNIQUE",
    "CREATE CONSTRAINT ON (n:small_place) ASSERT n.id IS UNIQUE",
    "CREATE CONSTRAINT ON (n:item_instance) ASSERT n.instance_id IS UNIQUE",
]


async def init_schema(graph) -> None:
    for query in SCHEMA_QUERIES:
        try:
            await graph.query(query)
        except Exception as e:
            # Ignore "already exists" errors from idempotent runs
            msg = str(e).lower()
            if "already exists" in msg or "equivalent index" in msg:
                continue
            raise
