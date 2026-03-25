"""Deterministic rule engine — no AI, no async, pure logic."""
from fastapi import HTTPException


class RuleError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=400, detail=detail)


def can_move(player: dict, target_place: dict, edge: dict) -> None:
    if player.get("hp", 0) <= 0:
        raise RuleError("你已經死亡，無法移動。")
    if player.get("is_in_combat"):
        raise RuleError("你正在戰鬥中，無法移動。")
    if edge.get("is_locked"):
        raise RuleError("通道已上鎖。")
    if edge.get("is_hidden"):
        raise RuleError("找不到那個出口。")


def can_attack(attacker: dict, target: dict, place_id: str) -> None:
    if attacker.get("hp", 0) <= 0:
        raise RuleError("你已經死亡。")
    if attacker.get("current_place_id") != place_id:
        raise RuleError("攻擊目標不在同一場所。")
    if target.get("current_place_id") != place_id:
        raise RuleError("目標不在同一場所。")


def can_pickup(player: dict, item: dict, place_id: str) -> None:
    if player.get("hp", 0) <= 0:
        raise RuleError("你已經死亡。")
    if item.get("location_type") != "room" or item.get("location_id") != place_id:
        raise RuleError("物品不在這個場所。")


def can_use_free_action(player: dict) -> None:
    if player.get("hp", 0) <= 0:
        raise RuleError("你已經死亡。")
    effects = player.get("status_effects", [])
    for e in effects:
        if isinstance(e, dict) and e.get("effect_type") == "stun":
            raise RuleError("你被暈眩，無法行動。")


def is_safe_zone(place: dict) -> bool:
    return bool(place.get("is_safe_zone", False))
