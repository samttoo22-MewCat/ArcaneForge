"""Grab contest endpoints."""
import asyncio
import json
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from server.broadcast.event_bus import EventBus
from server.broadcast.event_types import GrabContestOpenEvent, GrabContestResolvedEvent
from server.dependencies import get_graph, get_redis, get_event_bus
from server.db.repositories import item_repo, player_repo
from server.engine.grab_contest import GrabParticipant, roll_grab_contest
from server.config import settings

router = APIRouter(prefix="/grab", tags=["grab"])


class StartGrabRequest(BaseModel):
    player_id: str
    item_instance_id: str


class JoinGrabRequest(BaseModel):
    player_id: str
    contest_id: str


class GrabRulingRequest(BaseModel):
    player_id: str
    contest_id: str
    dice_bonus: int = 0
    feasible: bool = True


def _contest_key(contest_id: str) -> str:
    return f"grab_contest:{contest_id}"


@router.post("/start")
async def start_grab(
    req: StartGrabRequest,
    graph=Depends(get_graph),
    redis=Depends(get_redis),
    bus: EventBus = Depends(get_event_bus),
):
    player = await player_repo.get_player(graph, req.player_id)
    if not player:
        raise HTTPException(404, "Player not found")

    item = await item_repo.get_item_instance(graph, req.item_instance_id)
    if not item:
        raise HTTPException(404, "Item not found")

    place_id = player["current_place_id"]
    if item.get("location_id") != place_id:
        raise HTTPException(400, "物品不在你所在的場所。")

    contest_id = uuid.uuid4().hex
    window_open_time = time.time()
    window_closes_at = window_open_time + settings.grab_contest_window_seconds

    contest_state = {
        "contest_id": contest_id,
        "item_instance_id": req.item_instance_id,
        "place_id": place_id,
        "window_open_time": window_open_time,
        "window_closes_at": window_closes_at,
        "participants": [{
            "player_id": req.player_id,
            "join_time": window_open_time,
            "attribute_modifier": max(player.get("spd", 10), player.get("luk", 5)),
            "dice_bonus": 0,
            "feasible": True,
        }],
        "resolved": False,
    }
    await redis.set(_contest_key(contest_id), json.dumps(contest_state), ex=60)

    # Schedule resolution after window closes
    asyncio.create_task(_resolve_after_window(contest_id, redis, graph, bus, window_closes_at))

    event = GrabContestOpenEvent(
        item_instance_id=req.item_instance_id,
        item_name=item.get("item_id", ""),
        window_closes_at=window_closes_at,
        place_id=place_id,
    ).to_dict()
    await bus.publish_room(place_id, event)

    return {"contest_id": contest_id, "window_closes_at": window_closes_at}


@router.post("/join")
async def join_grab(
    req: JoinGrabRequest,
    graph=Depends(get_graph),
    redis=Depends(get_redis),
):
    raw = await redis.get(_contest_key(req.contest_id))
    if not raw:
        raise HTTPException(404, "Contest not found or expired")

    state = json.loads(raw)
    if state["resolved"]:
        raise HTTPException(400, "Contest already resolved")
    if time.time() > state["window_closes_at"]:
        raise HTTPException(400, "Contest window has closed")

    player = await player_repo.get_player(graph, req.player_id)
    if not player:
        raise HTTPException(404, "Player not found")

    # Check player is in same room
    if player["current_place_id"] != state["place_id"]:
        raise HTTPException(400, "你不在爭奪場所。")

    # Add participant if not already in
    existing_ids = {p["player_id"] for p in state["participants"]}
    if req.player_id not in existing_ids:
        state["participants"].append({
            "player_id": req.player_id,
            "join_time": time.time(),
            "attribute_modifier": max(player.get("spd", 10), player.get("luk", 5)),
            "dice_bonus": 0,
            "feasible": True,
        })
        await redis.set(_contest_key(req.contest_id), json.dumps(state), ex=60)

    return {"joined": True, "contest_id": req.contest_id}


@router.post("/ruling")
async def submit_grab_ruling(req: GrabRulingRequest, redis=Depends(get_redis)):
    raw = await redis.get(_contest_key(req.contest_id))
    if not raw:
        raise HTTPException(404, "Contest not found")

    state = json.loads(raw)
    bonus = min(5, max(0, req.dice_bonus))

    for p in state["participants"]:
        if p["player_id"] == req.player_id:
            p["dice_bonus"] = bonus
            p["feasible"] = req.feasible
            break

    await redis.set(_contest_key(req.contest_id), json.dumps(state), ex=60)
    return {"accepted": True}


async def _resolve_after_window(contest_id: str, redis, graph, bus, closes_at: float):
    wait = closes_at - time.time()
    if wait > 0:
        await asyncio.sleep(wait)

    raw = await redis.get(_contest_key(contest_id))
    if not raw:
        return
    state = json.loads(raw)
    if state["resolved"]:
        return

    participants = [
        GrabParticipant(
            player_id=p["player_id"],
            attribute_modifier=p["attribute_modifier"],
            join_time=p["join_time"],
            dm_dice_bonus=p["dice_bonus"],
            feasible=p["feasible"],
        )
        for p in state["participants"]
    ]

    winner_id, scores = roll_grab_contest(participants, state["window_open_time"])

    if winner_id:
        await item_repo.give_item_to_player(graph, state["item_instance_id"], winner_id)

    state["resolved"] = True
    await redis.set(_contest_key(contest_id), json.dumps(state), ex=30)

    event = GrabContestResolvedEvent(
        item_instance_id=state["item_instance_id"],
        winner_id=winner_id,
        scores=scores,
    ).to_dict()
    await bus.publish_room(state["place_id"], event)
