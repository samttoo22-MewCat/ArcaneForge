"""Optimistic locking for small_place.player_ids[] array property.

FalkorDB does not support Redis WATCH, so we use Cypher conditional
updates (WHERE NOT … IN array) with exponential backoff retries.
"""
import asyncio


class ConcurrentWriteError(RuntimeError):
    pass


async def add_player_to_room(graph, place_id: str, player_id: str, max_retries: int = 3) -> None:
    for attempt in range(max_retries):
        result = await graph.query(
            "MATCH (s:small_place {id: $pid}) "
            "WHERE NOT $uid IN s.player_ids "
            "SET s.player_ids = s.player_ids + [$uid] "
            "RETURN s.id",
            {"pid": place_id, "uid": player_id},
        )
        if result.result_set:
            return
        # Either player already in list (idempotent) or concurrent write — check
        check = await graph.query(
            "MATCH (s:small_place {id: $pid}) RETURN $uid IN s.player_ids",
            {"pid": place_id, "uid": player_id},
        )
        if check.result_set and check.result_set[0][0]:
            return  # already present, idempotent success
        await asyncio.sleep(0.05 * (2**attempt))

    raise ConcurrentWriteError(f"Failed to add player {player_id} to room {place_id} after {max_retries} retries")


async def remove_player_from_room(graph, place_id: str, player_id: str) -> None:
    await graph.query(
        "MATCH (s:small_place {id: $pid}) "
        "SET s.player_ids = [x IN s.player_ids WHERE x <> $uid]",
        {"pid": place_id, "uid": player_id},
    )
