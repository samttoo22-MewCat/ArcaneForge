"""FastAPI application factory with lifespan management."""
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from server.broadcast.event_bus import EventBus
from server.config import settings
from server.db.batch_writer import BatchWriter
from server.db.connection import create_falkordb_client, create_redis_client, ensure_docker_running
from server.db.schema import init_schema

_ITEMS_PATH = Path(__file__).parent.parent / "data" / "items.json"


def _load_item_master() -> dict:
    if _ITEMS_PATH.exists():
        items = json.loads(_ITEMS_PATH.read_text(encoding="utf-8"))
        return {item["item_id"]: item for item in items}
    return {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    print("[startup] Ensuring FalkorDB is running...")
    await ensure_docker_running()

    falkordb_client = create_falkordb_client()
    graph = falkordb_client.select_graph(settings.game_graph_name)
    redis_client = create_redis_client()

    # Verify Redis connection
    await redis_client.ping()
    print("[startup] Redis connected.")

    # Initialise schema (idempotent)
    await init_schema(graph)
    print("[startup] Schema initialised.")

    # Start batch writer background task
    batch_writer = BatchWriter(graph)
    batch_writer.start()
    print("[startup] Batch writer started.")

    # SSE event bus
    event_bus = EventBus()
    print("[startup] Event bus ready.")

    # Load static item master table
    item_master = _load_item_master()
    print(f"[startup] Loaded {len(item_master)} items from master table.")

    # Attach to app state
    app.state.graph = graph
    app.state.redis = redis_client
    app.state.batch_writer = batch_writer
    app.state.event_bus = event_bus
    app.state.item_master = item_master
    app.state.falkordb_client = falkordb_client

    yield

    # --- Shutdown ---
    print("[shutdown] Flushing batch writer...")
    await batch_writer.stop()
    await redis_client.aclose()
    print("[shutdown] Connections closed.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="ArcaneForge AI MUD",
        version="0.1.0",
        lifespan=lifespan,
    )

    from server.api import health, player, combat, grab, dm, sse

    app.include_router(health.router)
    app.include_router(player.router, prefix="/api/v1")
    app.include_router(combat.router, prefix="/api/v1")
    app.include_router(grab.router, prefix="/api/v1")
    app.include_router(dm.router, prefix="/api/v1")
    app.include_router(sse.router)

    return app


app = create_app()
