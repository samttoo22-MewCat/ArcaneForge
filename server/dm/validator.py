"""Server-side DM ruling validator — the primary anti-cheat enforcement point."""
from dataclasses import dataclass, field
from typing import Optional

from server.config import settings
from server.dm.schemas import DMRuling
from server.engine.status_effects import StatusEffect


class RulingValidationError(ValueError):
    pass


@dataclass
class RulingContext:
    player_id: str
    is_combat: bool
    scene_entity_ids: set[str]          # player/npc ids currently in scene
    scene_item_instance_ids: set[str]   # item instances in scene or player inventory
    player_inventory_ids: set[str]
    suspect_flags: int = 0              # running suspicious flag count for this player


@dataclass
class SuspicionTracker:
    """In-memory tracker for suspicious patterns. Reset on server restart (acceptable for open MUD)."""
    _records: dict[str, dict] = field(default_factory=dict)

    def record(self, player_id: str, modifier: float, is_combat: bool, response_time_ms: float) -> int:
        cap = settings.dm_combat_modifier_cap if is_combat else settings.dm_modifier_cap
        rec = self._records.setdefault(player_id, {"near_cap_count": 0, "fast_response_count": 0, "flags": 0})
        if modifier >= cap * 0.9:
            rec["near_cap_count"] += 1
        if response_time_ms < 2000:
            rec["fast_response_count"] += 1
        if rec["near_cap_count"] >= 20 or rec["fast_response_count"] >= 10:
            rec["flags"] += 1
            rec["near_cap_count"] = 0
            rec["fast_response_count"] = 0
        return rec["flags"]


_suspicion = SuspicionTracker()


def validate_ruling(ruling: DMRuling, context: RulingContext, response_time_ms: float = 9999) -> DMRuling:
    """
    Validate and sanitise a DM ruling.
    Raises RulingValidationError for hard rejections.
    Clamps modifier and records suspicion flags silently.
    """
    # 1. Clamp modifier
    cap = settings.dm_combat_modifier_cap if context.is_combat else settings.dm_modifier_cap
    if ruling.modifier > cap:
        ruling = ruling.model_copy(update={"modifier": cap})

    # 2. If not feasible, zero out effects
    if not ruling.feasible:
        ruling = ruling.model_copy(update={
            "modifier": 1.0,
            "status_to_apply": None,
            "item_consumed": None,
            "item_produced": None,
            "dice_bonus": 0,
        })
        return ruling

    # 3. Validate status_to_apply is a real status
    if ruling.status_to_apply:
        try:
            StatusEffect(ruling.status_to_apply)
        except ValueError:
            raise RulingValidationError(f"Unknown status effect: {ruling.status_to_apply!r}")

    # 4. Validate status_target is in scene
    if ruling.status_target and ruling.status_target not in context.scene_entity_ids:
        raise RulingValidationError(f"Target {ruling.status_target!r} not in scene")

    # 5. Validate item_consumed exists in scene or inventory
    if ruling.item_consumed:
        valid = context.scene_item_instance_ids | context.player_inventory_ids
        if ruling.item_consumed not in valid:
            raise RulingValidationError(f"Item {ruling.item_consumed!r} not accessible")

    # 6. item_produced must be null (DM cannot create items — master table only)
    if ruling.item_produced is not None:
        raise RulingValidationError("DM cannot produce items (item_produced must be null)")

    # 7. Record suspicion
    flags = _suspicion.record(context.player_id, ruling.modifier, context.is_combat, response_time_ms)
    if flags > 0:
        # Log for manual review — don't ban automatically
        print(f"[SUSPECT] player {context.player_id} has {flags} suspicion flag(s)")

    return ruling
