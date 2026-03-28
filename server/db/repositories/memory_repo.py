"""NPC memory repository.

Two-layer storage:
  Redis  — recent compressed rounds (up to MAX_ROUNDS), fast retrieval
  FalkorDB — long-term REMEMBERS edge (attitude, summary, tags, count)
"""
from typing import Optional

MAX_ROUNDS = 10


def _key(npc_id: str, player_id: str) -> str:
    return f"npc_mem:{npc_id}:{player_id}"


# ── FalkorDB helpers ──────────────────────────────────────────────────────────

async def _ensure_remembers(graph, npc_id: str, player_id: str) -> dict:
    """Get existing REMEMBERS edge or create one with defaults."""
    r = await graph.query(
        "MATCH (n:npc {id: $nid})-[r:REMEMBERS]->(p:player {id: $pid}) RETURN r",
        {"nid": npc_id, "pid": player_id},
    )
    if r.result_set:
        return r.result_set[0][0].properties

    await graph.query(
        "MATCH (n:npc {id: $nid}), (p:player {id: $pid}) "
        "CREATE (n)-[:REMEMBERS {attitude: 0, summary: '', interaction_count: 0, tags: []}]->(p)",
        {"nid": npc_id, "pid": player_id},
    )
    return {"attitude": 0, "summary": "", "interaction_count": 0, "tags": []}


# ── Public API ─────────────────────────────────────────────────────────────────

async def get_memory(graph, redis, npc_id: str, player_id: str) -> dict:
    """Return combined memory for (npc, player) pair."""
    raw = await redis.lrange(_key(npc_id, player_id), 0, -1)
    rounds = [r.decode() if isinstance(r, bytes) else r for r in (raw or [])]

    edge = await _ensure_remembers(graph, npc_id, player_id)
    return {
        "attitude": edge.get("attitude", 0),
        "summary": edge.get("summary", "") or "",
        "interaction_count": edge.get("interaction_count", 0),
        "tags": list(edge.get("tags", []) or []),
        "recent_rounds": rounds,
    }


async def add_round(redis, npc_id: str, player_id: str, compressed_round: str) -> dict:
    """Append one compressed round. Returns overflow info when the list was full."""
    key = _key(npc_id, player_id)
    current_len: int = await redis.llen(key)

    overflow = current_len >= MAX_ROUNDS
    rounds_for_summary: list[str] = []

    if overflow:
        raw = await redis.lrange(key, 0, -1)
        rounds_for_summary = [r.decode() if isinstance(r, bytes) else r for r in (raw or [])]

    await redis.rpush(key, compressed_round)
    await redis.ltrim(key, -MAX_ROUNDS, -1)

    return {"overflow": overflow, "rounds_for_summary": rounds_for_summary}


async def update_summary(graph, npc_id: str, player_id: str, new_summary: str) -> None:
    """Write new long-term summary and increment interaction_count by MAX_ROUNDS."""
    await graph.query(
        "MATCH (n:npc {id: $nid}), (p:player {id: $pid}) "
        "MERGE (n)-[r:REMEMBERS]->(p) "
        "ON CREATE SET r.attitude = 0, r.tags = [], r.interaction_count = 0 "
        "SET r.summary = $summary, r.interaction_count = r.interaction_count + $inc",
        {"nid": npc_id, "pid": player_id, "summary": new_summary, "inc": MAX_ROUNDS},
    )


async def update_attitude(graph, npc_id: str, player_id: str, delta: int) -> int:
    """Clamp attitude by delta within [-100, 100]. Returns new value."""
    edge = await _ensure_remembers(graph, npc_id, player_id)
    new_val = max(-100, min(100, (edge.get("attitude") or 0) + delta))
    await graph.query(
        "MATCH (n:npc {id: $nid})-[r:REMEMBERS]->(p:player {id: $pid}) SET r.attitude = $val",
        {"nid": npc_id, "pid": player_id, "val": new_val},
    )
    return new_val


async def add_tag(graph, npc_id: str, player_id: str, tag: str) -> None:
    """Add a tag to the REMEMBERS edge (idempotent)."""
    edge = await _ensure_remembers(graph, npc_id, player_id)
    tags: list = list(edge.get("tags", []) or [])
    if tag in tags:
        return
    tags.append(tag)
    await graph.query(
        "MATCH (n:npc {id: $nid})-[r:REMEMBERS]->(p:player {id: $pid}) SET r.tags = $tags",
        {"nid": npc_id, "pid": player_id, "tags": tags},
    )
