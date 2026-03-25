from fastapi import APIRouter, Depends
from server.dependencies import get_graph, get_redis

router = APIRouter()


@router.get("/health")
async def health(graph=Depends(get_graph), redis=Depends(get_redis)):
    try:
        await redis.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    try:
        await graph.query("RETURN 1")
        db_ok = True
    except Exception:
        db_ok = False

    status = "ok" if (redis_ok and db_ok) else "degraded"
    return {"status": status, "falkordb": db_ok, "redis": redis_ok}
