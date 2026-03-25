"""FastAPI application factory with lifespan management."""
import asyncio
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

    # Start NPC tick loop
    npc_task = asyncio.create_task(_npc_tick_loop(app))
    print("[startup] NPC tick loop started.")

    yield

    # --- Shutdown ---
    npc_task.cancel()
    try:
        await npc_task
    except asyncio.CancelledError:
        pass
    print("[shutdown] Flushing batch writer...")
    await batch_writer.stop()
    await redis_client.aclose()
    print("[shutdown] Connections closed.")


async def _npc_tick_loop(app: FastAPI) -> None:
    """Background task: process NPC behavior tree for all active rooms every tick."""
    from server.broadcast.event_types import CombatRoundEvent
    from server.db.repositories import npc_repo, player_repo
    from server.engine import npc_ai
    from server.engine.combat import calculate_damage
    from server.engine.lifecycle import handle_player_death

    while True:
        await asyncio.sleep(settings.npc_tick_interval_seconds)
        try:
            bus: EventBus = app.state.event_bus
            graph = app.state.graph
            redis = app.state.redis
            item_master: dict = app.state.item_master

            active_rooms = bus.active_room_ids
            if not active_rooms:
                continue

            for room_id in active_rooms:
                npcs = await npc_repo.get_npcs_in_place(graph, room_id)
                players = await player_repo.get_players_in_room(graph, room_id)

                for npc in npcs:
                    if npc.get("is_hibernating") or npc.get("behavior_state") == "dead":
                        continue

                    new_state = npc_ai.evaluate_npc_state(npc, players)

                    if new_state != npc.get("behavior_state"):
                        await npc_repo.update_npc(graph, npc["id"], {"behavior_state": new_state})

                    if new_state == "combat" and players:
                        target_id = npc_ai.pick_attack_target(npc, players)
                        if not target_id:
                            continue
                        target = next((p for p in players if p["id"] == target_id), None)
                        if not target:
                            continue

                        dmg = calculate_damage(
                            npc.get("atk", 5), target.get("def_", 2), 1.0, is_combat=True
                        )
                        new_hp = max(0, target.get("hp", 1) - dmg)
                        await player_repo.update_player(graph, target_id, {"hp": new_hp})

                        await bus.publish_room(room_id, CombatRoundEvent(
                            room_id=room_id,
                            actor_id=npc["id"],
                            target_id=target_id,
                            action="attack",
                            damage=dmg,
                            target_hp_remaining=new_hp,
                            narrative_hint=f"{npc.get('name', npc['id'])} 攻擊了 {target.get('name', target_id)}",
                        ).to_dict())

                        if new_hp <= 0:
                            await handle_player_death(
                                graph, redis, bus,
                                player_id=target_id,
                                player_name=target.get("name", target_id),
                                place_id=room_id,
                                killer_id=npc["id"],
                                killer_name=npc.get("name", ""),
                            )
        except Exception as exc:
            print(f"[npc_tick] Error: {exc}")


def create_app() -> FastAPI:
    app = FastAPI(
        title="ArcaneForge AI MUD",
        version="0.1.0",
        lifespan=lifespan,
    )

    from server.api import health, player, combat, grab, dm, sse, npc

    app.include_router(health.router)
    app.include_router(player.router, prefix="/api/v1")
    app.include_router(combat.router, prefix="/api/v1")
    app.include_router(grab.router, prefix="/api/v1")
    app.include_router(dm.router, prefix="/api/v1")
    app.include_router(npc.router, prefix="/api/v1")
    app.include_router(sse.router)

    # Print all registered routes on startup
    @app.on_event("startup")
    async def _print_routes():
        routes = [(r.methods, r.path) for r in app.routes if hasattr(r, "methods")]
        print("[routes] Registered endpoints:")
        for methods, path in sorted(routes, key=lambda x: x[1]):
            print(f"  {','.join(sorted(methods)):10s}  {path}")

    return app


app = create_app()
