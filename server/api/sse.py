from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from server.broadcast.sse_manager import sse_stream
from server.broadcast.event_bus import EventBus
from server.dependencies import get_event_bus, get_graph
from server.db.repositories import player_repo, place_repo

router = APIRouter()


@router.get("/events")
async def events(
    request: Request,
    player_id: str = Query(...),
    graph=Depends(get_graph),
    bus: EventBus = Depends(get_event_bus),
):
    player = await player_repo.get_player(graph, player_id)
    if not player:
        from fastapi import HTTPException
        raise HTTPException(404, "Player not found")

    place_id = player["current_place_id"]
    place = await place_repo.get_small_place(graph, place_id)
    middle_id = place.get("parent_middle_id", "global") if place else "global"

    return await sse_stream(request, bus, player_id, place_id, middle_id)
