import asyncio
import subprocess
import time
from typing import Optional

import redis.asyncio as aioredis
from falkordb.asyncio import FalkorDB

from server.config import settings


async def _wait_for_falkordb(host: str, port: int, password: str, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            conn = aioredis.Redis(host=host, port=port, password=password or None)
            await conn.ping()
            await conn.aclose()
            return True
        except Exception:
            await asyncio.sleep(0.5)
    return False


async def ensure_docker_running() -> None:
    ok = await _wait_for_falkordb(
        settings.falkordb_host, settings.falkordb_port, settings.falkordb_password, timeout=2.0
    )
    if not ok:
        print("[startup] FalkorDB not reachable — starting docker compose...")
        subprocess.run(
            ["docker", "compose", "-f", "docker/docker-compose.yml", "up", "-d"],
            check=True,
        )
        reachable = await _wait_for_falkordb(
            settings.falkordb_host, settings.falkordb_port, settings.falkordb_password, timeout=10.0
        )
        if not reachable:
            raise RuntimeError("FalkorDB failed to start within 10 seconds")
        print("[startup] FalkorDB is up.")


def create_falkordb_client() -> FalkorDB:
    kwargs = {"host": settings.falkordb_host, "port": settings.falkordb_port}
    if settings.falkordb_password:
        kwargs["password"] = settings.falkordb_password
    return FalkorDB(**kwargs)


def create_redis_client() -> aioredis.Redis:
    kwargs = {"host": settings.redis_host, "port": settings.redis_port}
    if settings.redis_password:
        kwargs["password"] = settings.redis_password
    return aioredis.Redis(**kwargs, decode_responses=True)
