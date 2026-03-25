"""NPC endpoints: shop inventory, NPC info."""
from fastapi import APIRouter, Depends, HTTPException

from server.db.repositories import npc_repo
from server.dependencies import get_graph, get_item_master

router = APIRouter(prefix="/npc", tags=["npc"])


@router.get("/{npc_id}")
async def get_npc(npc_id: str, graph=Depends(get_graph)):
    npc = await npc_repo.get_npc(graph, npc_id)
    if not npc:
        raise HTTPException(404, "NPC not found")
    return npc


@router.get("/{npc_id}/shop")
async def get_shop(
    npc_id: str,
    graph=Depends(get_graph),
    item_master: dict = Depends(get_item_master),
):
    npc = await npc_repo.get_npc(graph, npc_id)
    if not npc:
        raise HTTPException(404, "NPC not found")
    if npc.get("npc_type") != "merchant":
        raise HTTPException(400, "此 NPC 不是商人。")

    shop_items = await npc_repo.get_npc_shop(graph, npc_id)
    enriched = []
    for entry in shop_items:
        master = item_master.get(entry.get("item_id", ""), {})
        enriched.append({
            **entry,
            "name": master.get("name", entry.get("item_id", "")),
            "description": master.get("description", ""),
            "weight": master.get("weight", 0),
        })

    return {
        "npc_id": npc_id,
        "npc_name": npc.get("name", npc_id),
        "shop_inventory": enriched,
    }
