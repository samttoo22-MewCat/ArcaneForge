import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from server.broadcast.event_bus import EventBus
from server.broadcast.sse_manager import sse_stream
from server.config import settings
from server.db.repositories import combat_repo, player_repo, place_repo
from server.dependencies import get_event_bus, get_graph, get_redis

router = APIRouter()


@router.get("/events")
async def events(
    request: Request,
    player_id: str = Query(...),
    graph=Depends(get_graph),
    redis=Depends(get_redis),
    bus: EventBus = Depends(get_event_bus),
):
    player = await player_repo.get_player(graph, player_id)
    if not player:
        raise HTTPException(404, "Player not found")

    place_id = player["current_place_id"]
    place = await place_repo.get_small_place(graph, place_id)
    middle_id = place.get("parent_middle_id", "global") if place else "global"

    async def handle_disconnect():
        await asyncio.sleep(settings.disconnect_grace_seconds)
        if bus.is_player_connected(player_id):
            return  # Reconnected, do nothing
        p = await player_repo.get_player(graph, player_id)
        if not p:
            return
        if p.get("is_in_combat"):
            room_id = p.get("combat_room_id")
            if room_id:
                await combat_repo.end_combat(redis, room_id)
            await player_repo.set_combat_state(graph, player_id, False, None)
        if p.get("is_traveling"):
            await player_repo.set_travel_state(graph, player_id, False, None, None)

    return await sse_stream(request, bus, player_id, place_id, middle_id, on_disconnect=handle_disconnect)
