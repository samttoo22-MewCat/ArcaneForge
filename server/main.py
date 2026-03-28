"""FastAPI application factory with lifespan management."""
import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

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
    from server.broadcast.event_types import (
        CombatRoundEvent,
        NPCAlertEvent,
        NPCMovedEvent,
        StatusEffectAppliedEvent,
    )
    from server.db.repositories import npc_repo, player_repo
    from server.engine import npc_ai, global_events
    from server.engine.combat import calculate_damage
    from server.engine.lifecycle import handle_player_death
    from server.engine.status_effects import (
        ActiveEffect,
        StatusEffect,
        apply_effects,
        decrement_durations,
        make_effect,
    )

    while True:
        await asyncio.sleep(settings.npc_tick_interval_seconds)
        try:
            bus: EventBus = app.state.event_bus
            graph = app.state.graph
            redis = app.state.redis

            active_rooms = bus.active_room_ids

            # ── Process global server events (cross-zone NPC alerting) ──────
            extra_alert_rooms: set[str] = set()
            server_events = global_events.drain()
            for sevt in server_events:
                if sevt.event_type not in ("player_entered", "combat_started"):
                    continue
                hostile_npcs = await npc_repo.get_hostile_npcs_in_middle(graph, sevt.middle_id)
                alerted_any = False
                for npc in hostile_npcs:
                    npc_room = npc.get("current_place_id", "")
                    if npc_room == sevt.place_id:
                        continue  # same room — handled normally by tick
                    hostile_to = npc.get("hostile_to", [])
                    if isinstance(hostile_to, str):
                        import json as _json
                        hostile_to = _json.loads(hostile_to)
                    if "player" not in hostile_to:
                        continue
                    await npc_repo.update_npc(graph, npc["id"], {
                        "behavior_state": "alert",
                        "alert_ticks_remaining": 5,  # 10 s at 2 s/tick
                    })
                    extra_alert_rooms.add(npc_room)
                    alerted_any = True
                if alerted_any:
                    await bus.publish_middle(sevt.middle_id, NPCAlertEvent(
                        middle_id=sevt.middle_id,
                        place_id=sevt.place_id,
                        trigger=sevt.event_type,
                        message="敵人察覺到入侵者的氣息！",
                    ).to_dict())

            rooms_to_process = active_rooms | extra_alert_rooms
            if not rooms_to_process:
                continue

            for room_id in rooms_to_process:
                npcs = await npc_repo.get_npcs_in_place(graph, room_id)
                players = await player_repo.get_players_in_room(graph, room_id)

                # ── Tick player status effects (once per room per cycle) ──────
                for player in players:
                    raw_fx = player.get("status_effects", "[]") or "[]"
                    if isinstance(raw_fx, list):
                        effects_data = raw_fx
                    else:
                        try:
                            effects_data = json.loads(raw_fx)
                        except (json.JSONDecodeError, ValueError):
                            effects_data = []

                    if not effects_data:
                        continue

                    active_fx = [
                        ActiveEffect(
                            effect_type=StatusEffect(e["effect_type"]),
                            duration=e["duration"],
                            stacks=e.get("stacks", 1),
                            source_id=e.get("source_id"),
                        )
                        for e in effects_data
                        if e.get("effect_type") in [v.value for v in StatusEffect]
                    ]

                    dot_dmg, skip_action, _spd = apply_effects(active_fx, player.get("hp", 1))
                    active_fx = decrement_durations(active_fx)
                    updated_fx = [
                        {
                            "effect_type": e.effect_type.value,
                            "duration": e.duration,
                            "stacks": e.stacks,
                            "source_id": e.source_id,
                        }
                        for e in active_fx
                    ]
                    player_updates: dict = {"status_effects": json.dumps(updated_fx)}

                    if dot_dmg > 0:
                        new_hp = max(0, player.get("hp", 1) - dot_dmg)
                        player_updates["hp"] = new_hp
                        # Broadcast effect tick
                        for e in active_fx:
                            await bus.publish_room(room_id, StatusEffectAppliedEvent(
                                target_id=player["id"],
                                target_name=player.get("name", player["id"]),
                                effect_type=e.effect_type.value,
                                stacks=e.stacks,
                                source_id=e.source_id or "",
                                room_id=room_id,
                            ).to_dict())
                        # Check player death from DoT
                        if new_hp <= 0:
                            await player_repo.update_player(graph, player["id"], player_updates)
                            await handle_player_death(
                                graph, redis, bus,
                                player_id=player["id"],
                                player_name=player.get("name", player["id"]),
                                place_id=room_id,
                                killer_id="",
                                killer_name="狀態效果",
                            )
                            continue

                    await player_repo.update_player(graph, player["id"], player_updates)

                # ── Process each NPC ──────────────────────────────────────────
                for npc in npcs:
                    if npc.get("is_hibernating") or npc.get("behavior_state") == "dead":
                        continue

                    new_state = npc_ai.evaluate_npc_state(npc, players)

                    if new_state != npc.get("behavior_state"):
                        await npc_repo.update_npc(graph, npc["id"], {"behavior_state": new_state})

                    # ── Alert state: decrement timer, skip action ─────────────
                    if new_state == "alert":
                        remaining = max(0, npc.get("alert_ticks_remaining", 1) - 1)
                        await npc_repo.update_npc(graph, npc["id"], {"alert_ticks_remaining": remaining})
                        continue  # NPC is on guard but no players in room yet

                    # ── Patrol movement ───────────────────────────────────────
                    if new_state == "patrol":
                        patrol_route_raw = npc.get("patrol_route", "[]")
                        if isinstance(patrol_route_raw, str):
                            try:
                                patrol_route = json.loads(patrol_route_raw)
                            except (json.JSONDecodeError, ValueError):
                                patrol_route = []
                        else:
                            patrol_route = patrol_route_raw if isinstance(patrol_route_raw, list) else []

                        if patrol_route:
                            cooldown = npc.get("patrol_cooldown_ticks", 0)
                            if cooldown <= 0:
                                idx = npc.get("next_patrol_index", 0)
                                next_room = patrol_route[idx % len(patrol_route)]
                                old_room = npc.get("current_place_id", room_id)

                                if next_room != old_room:
                                    spd = max(1, npc.get("spd", 10))
                                    new_cooldown = max(1, 10 // spd)
                                    new_idx = (idx + 1) % len(patrol_route)
                                    await npc_repo.move_npc_to_place(
                                        graph, npc["id"], next_room, new_idx, new_cooldown
                                    )
                                    moved_event = NPCMovedEvent(
                                        npc_id=npc["id"],
                                        npc_name=npc.get("name", npc["id"]),
                                        from_place_id=old_room,
                                        to_place_id=next_room,
                                    ).to_dict()
                                    await bus.publish_room(old_room, moved_event)
                                    await bus.publish_room(next_room, moved_event)
                                else:
                                    # Already at target, advance index
                                    await npc_repo.update_npc(graph, npc["id"], {
                                        "next_patrol_index": (idx + 1) % len(patrol_route),
                                        "patrol_cooldown_ticks": max(1, 10 // max(1, npc.get("spd", 10))),
                                    })
                            else:
                                await npc_repo.update_npc(graph, npc["id"], {
                                    "patrol_cooldown_ticks": cooldown - 1
                                })
                        continue  # patrol NPCs don't attack this tick

                    # ── NPC status effect tick ────────────────────────────────
                    npc_fx_raw = npc.get("active_effects", "[]") or "[]"
                    if isinstance(npc_fx_raw, str):
                        try:
                            npc_fx_data = json.loads(npc_fx_raw)
                        except (json.JSONDecodeError, ValueError):
                            npc_fx_data = []
                    else:
                        npc_fx_data = npc_fx_raw if isinstance(npc_fx_raw, list) else []

                    npc_skip_action = False
                    if npc_fx_data:
                        npc_active_fx = [
                            ActiveEffect(
                                effect_type=StatusEffect(e["effect_type"]),
                                duration=e["duration"],
                                stacks=e.get("stacks", 1),
                                source_id=e.get("source_id"),
                            )
                            for e in npc_fx_data
                            if e.get("effect_type") in [v.value for v in StatusEffect]
                        ]
                        npc_dot_dmg, npc_skip_action, _ = apply_effects(npc_active_fx, npc.get("hp", 1))
                        npc_active_fx = decrement_durations(npc_active_fx)
                        updated_npc_fx = [
                            {
                                "effect_type": e.effect_type.value,
                                "duration": e.duration,
                                "stacks": e.stacks,
                                "source_id": e.source_id,
                            }
                            for e in npc_active_fx
                        ]
                        npc_updates: dict = {"active_effects": json.dumps(updated_npc_fx)}
                        if npc_dot_dmg > 0:
                            npc_new_hp = max(0, npc.get("hp", 1) - npc_dot_dmg)
                            npc_updates["hp"] = npc_new_hp
                            if npc_new_hp <= 0:
                                npc_updates["behavior_state"] = "dead"
                        await npc_repo.update_npc(graph, npc["id"], npc_updates)
                        if npc.get("hp", 1) - (npc_updates.get("hp", npc.get("hp", 1)) - npc.get("hp", 1)) <= 0:
                            continue  # NPC died from DoT

                    if npc_skip_action:
                        continue  # NPC is stunned this tick

                    # ── Combat action ─────────────────────────────────────────
                    if new_state == "combat" and players:
                        target_id = npc_ai.pick_attack_target(npc, players)
                        if not target_id:
                            continue
                        target = next((p for p in players if p["id"] == target_id), None)
                        if not target:
                            continue

                        # Choose skill or basic attack
                        chosen_skill = npc_ai.pick_skill(npc, target)
                        damage_mult = chosen_skill["damage_mult"] if chosen_skill else 1.0
                        skill_name = chosen_skill["name"] if chosen_skill else "攻擊"
                        applied_effect: str | None = None

                        # Deduct MP and reset skill cooldown; tick other cooldowns
                        if chosen_skill:
                            skills_raw = npc.get("skills", "[]")
                            if isinstance(skills_raw, str):
                                skills_list = json.loads(skills_raw)
                            else:
                                skills_list = skills_raw if isinstance(skills_raw, list) else []

                            new_mp = max(0, npc.get("mp", 0) - chosen_skill.get("mp_cost", 0))
                            for s in skills_list:
                                if s["id"] == chosen_skill["id"]:
                                    s["cooldown_remaining"] = s.get("cooldown_ticks", 3)
                                elif s.get("cooldown_remaining", 0) > 0:
                                    s["cooldown_remaining"] -= 1
                            await npc_repo.update_npc(graph, npc["id"], {
                                "mp": new_mp,
                                "skills": json.dumps(skills_list),
                            })
                        else:
                            # Tick all skill cooldowns even on basic attacks
                            skills_raw = npc.get("skills", "[]")
                            if isinstance(skills_raw, str):
                                try:
                                    skills_list = json.loads(skills_raw)
                                except (json.JSONDecodeError, ValueError):
                                    skills_list = []
                            else:
                                skills_list = skills_raw if isinstance(skills_raw, list) else []
                            if skills_list:
                                skills_list = npc_ai.tick_skill_cooldowns(skills_list)
                                await npc_repo.update_npc(graph, npc["id"], {
                                    "skills": json.dumps(skills_list),
                                })

                        dmg = calculate_damage(
                            npc.get("atk", 5), target.get("def_", 2), damage_mult, is_combat=True
                        )
                        new_hp = max(0, target.get("hp", 1) - dmg)
                        player_hp_updates: dict = {"hp": new_hp}

                        # Apply status effect if skill has one
                        if chosen_skill and chosen_skill.get("effect"):
                            effect_name = chosen_skill["effect"]
                            try:
                                new_effect = make_effect(effect_name, source_id=npc["id"])
                                target_fx_raw = target.get("status_effects", "[]") or "[]"
                                if isinstance(target_fx_raw, list):
                                    target_fx = target_fx_raw
                                else:
                                    try:
                                        target_fx = json.loads(target_fx_raw)
                                    except (json.JSONDecodeError, ValueError):
                                        target_fx = []

                                existing = next(
                                    (e for e in target_fx if e.get("effect_type") == effect_name), None
                                )
                                if existing:
                                    existing["stacks"] = min(existing.get("stacks", 1) + 1, 5)
                                    existing["duration"] = max(existing["duration"], new_effect.duration)
                                else:
                                    target_fx.append({
                                        "effect_type": new_effect.effect_type.value,
                                        "duration": new_effect.duration,
                                        "stacks": new_effect.stacks,
                                        "source_id": new_effect.source_id,
                                    })
                                player_hp_updates["status_effects"] = json.dumps(target_fx)
                                applied_effect = effect_name

                                await bus.publish_room(room_id, StatusEffectAppliedEvent(
                                    target_id=target_id,
                                    target_name=target.get("name", target_id),
                                    effect_type=effect_name,
                                    stacks=new_effect.stacks,
                                    source_id=npc["id"],
                                    room_id=room_id,
                                ).to_dict())
                            except (ValueError, KeyError):
                                pass  # Unknown effect type, skip

                        await player_repo.update_player(graph, target_id, player_hp_updates)

                        await bus.publish_room(room_id, CombatRoundEvent(
                            room_id=room_id,
                            actor_id=npc["id"],
                            target_id=target_id,
                            action="skill" if chosen_skill else "attack",
                            damage=dmg,
                            target_hp_remaining=new_hp,
                            status_applied=applied_effect,
                            narrative_hint=f"{npc.get('name', npc['id'])} 使用了【{skill_name}】，對 {target.get('name', target_id)} 造成 {dmg} 點傷害。",
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

    from server.api import health, player, combat, grab, dm, sse, npc, auth

    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(player.router, prefix="/api/v1")
    app.include_router(combat.router, prefix="/api/v1")
    app.include_router(grab.router, prefix="/api/v1")
    app.include_router(dm.router, prefix="/api/v1")
    app.include_router(npc.router, prefix="/api/v1")
    app.include_router(sse.router)

    # ── Global 429 handler ────────────────────────────────────────────────────
    from fastapi.exception_handlers import http_exception_handler
    from fastapi.exceptions import HTTPException as FastAPIHTTPException

    @app.exception_handler(FastAPIHTTPException)
    async def _http_exception_handler(request: Request, exc: FastAPIHTTPException):
        """Pass-through for all HTTP exceptions; adds Retry-After to 429 responses."""
        response = await http_exception_handler(request, exc)
        if exc.status_code == 429 and isinstance(exc.headers, dict):
            retry_after = exc.headers.get("Retry-After", "60")
            return JSONResponse(
                status_code=429,
                content={"detail": exc.detail},
                headers={
                    "Retry-After": retry_after,
                    "Access-Control-Expose-Headers": "Retry-After",
                },
            )
        return response

    # Print all registered routes on startup
    @app.on_event("startup")
    async def _print_routes():
        routes = [(r.methods, r.path) for r in app.routes if hasattr(r, "methods")]
        print("[routes] Registered endpoints:")
        for methods, path in sorted(routes, key=lambda x: x[1]):
            print(f"  {','.join(sorted(methods)):10s}  {path}")

    return app


app = create_app()
