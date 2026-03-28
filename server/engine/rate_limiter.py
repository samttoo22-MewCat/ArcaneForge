"""Redis-based fixed-window rate limiter for player action endpoints.

Usage:
    from server.engine.rate_limiter import rate_limit

    @router.post("/do")
    async def do_action(
        req: DoRequest,
        _rl: None = Depends(rate_limit("do", max_requests=10, window_seconds=60)),
        ...
    ):
        ...

Keys:  rl:{player_id}:{endpoint}:{window_bucket}
       where window_bucket = int(time.time() // window_seconds)
TTL:   window_seconds + 10 seconds (grace)
"""
import time

from fastapi import Depends, HTTPException, Request

from server.dependencies import get_redis

# ── Default limits per endpoint ──────────────────────────────────────────────
# These can be overridden when calling rate_limit().

DEFAULTS: dict[str, tuple[int, int]] = {
    # endpoint_name: (max_requests, window_seconds)
    "do":        (10,  60),   # LLM-driven actions — most expensive
    "use_skill": (20,  60),   # Skill/spell use
    "say":       (30,  60),   # Chat
    "move":      (60,  60),   # Movement
    "craft":     (20,  60),   # Crafting
    "buy":       (20,  60),   # Trade: buy
    "sell":      (20,  60),   # Trade: sell
    "pickup":      (30,  60),   # Item pickup
    "allocate_stat": (30, 60),  # Stat point allocation
}


def rate_limit(
    endpoint: str,
    max_requests: int | None = None,
    window_seconds: int | None = None,
):
    """Return a FastAPI dependency that enforces a fixed-window rate limit.

    player_id is extracted from the JSON request body automatically.
    Falls back to IP address if the body cannot be parsed or has no player_id.
    """
    _max, _window = DEFAULTS.get(endpoint, (30, 60))
    if max_requests is not None:
        _max = max_requests
    if window_seconds is not None:
        _window = window_seconds

    async def _check(
        request: Request,
        redis=Depends(get_redis),
    ) -> None:
        # Extract player_id from JSON body (body is cached by Starlette)
        try:
            body = await request.json()
            player_id: str = body.get("player_id") or ""
        except Exception:
            player_id = ""

        if not player_id:
            # Fall back to client IP
            player_id = request.client.host if request.client else "unknown"

        window_bucket = int(time.time() // _window)
        key = f"rl:{player_id}:{endpoint}:{window_bucket}"

        count: int = await redis.incr(key)
        if count == 1:
            # First hit in this window — set TTL
            await redis.expire(key, _window + 10)

        if count > _max:
            retry_after = _window - (int(time.time()) % _window)
            raise HTTPException(
                status_code=429,
                detail=(
                    f"請求過於頻繁，請稍後再試。"
                    f"（{retry_after} 秒後重試，"
                    f"此端點限制 {_max} 次/{_window} 秒）"
                ),
                headers={"Retry-After": str(retry_after)},
            )

    return _check
