"""Redis-backed nonce store for replay-attack prevention."""
import redis.asyncio as aioredis

from server.config import settings


async def consume_nonce(redis: aioredis.Redis, nonce: str) -> bool:
    """
    Atomically mark nonce as used.
    Returns True if nonce was fresh (not seen before), False if replay.
    """
    key = f"nonce:{nonce}"
    result = await redis.set(key, "1", ex=settings.nonce_ttl_seconds, nx=True)
    return result is not None


async def is_nonce_used(redis: aioredis.Redis, nonce: str) -> bool:
    key = f"nonce:{nonce}"
    return await redis.exists(key) == 1


async def store_pending_ruling(redis: aioredis.Redis, nonce: str, data: dict) -> None:
    import json
    key = f"pending_ruling:{nonce}"
    await redis.set(key, json.dumps(data), ex=120)  # 2-minute TTL


async def get_pending_ruling(redis: aioredis.Redis, nonce: str) -> dict | None:
    import json
    key = f"pending_ruling:{nonce}"
    raw = await redis.get(key)
    return json.loads(raw) if raw else None


async def delete_pending_ruling(redis: aioredis.Redis, nonce: str) -> None:
    await redis.delete(f"pending_ruling:{nonce}")
