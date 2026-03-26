"""Server-side DM ruling validator — the primary anti-cheat enforcement point."""
from dataclasses import dataclass, field

from server.dm.schemas import ALL_TIERS, DMRuling
from server.engine.status_effects import StatusEffect


class RulingValidationError(ValueError):
    pass


@dataclass
class RulingContext:
    player_id: str
    is_combat: bool
    scene_entity_ids: set[str]          # player/npc ids currently in scene
    scene_item_instance_ids: set[str]   # item instances on ground
    player_inventory_ids: set[str]
    suspect_flags: int = 0


@dataclass
class SuspicionTracker:
    """In-memory tracker for suspicious patterns. Reset on server restart (acceptable)."""
    _records: dict[str, dict] = field(default_factory=dict)

    def record(self, player_id: str, response_time_ms: float) -> int:
        rec = self._records.setdefault(player_id, {"fast_response_count": 0, "flags": 0})
        if response_time_ms < 2000:
            rec["fast_response_count"] += 1
        if rec["fast_response_count"] >= 10:
            rec["flags"] += 1
            rec["fast_response_count"] = 0
        return rec["flags"]


_suspicion = SuspicionTracker()


def validate_ruling(ruling: DMRuling, context: RulingContext, response_time_ms: float = 9999) -> DMRuling:
    """
    Validate a DM ruling.
    Raises RulingValidationError for hard rejections.
    Records suspicion flags silently for soft anomalies.
    """
    # 1. If not feasible — strip outcomes and return (valid rejection)
    if not ruling.feasible:
        return ruling.model_copy(update={"outcomes": {}})

    # 2. All six tier keys must be present
    missing = set(ALL_TIERS) - set(ruling.outcomes.keys())
    if missing:
        raise RulingValidationError(f"DM ruling missing outcome tiers: {missing}")

    # 3. Validate each outcome entry
    valid_item_ids = context.scene_item_instance_ids | context.player_inventory_ids
    for tier_name, outcome in ruling.outcomes.items():
        # status_to_apply must be a real status
        if outcome.status_to_apply:
            try:
                StatusEffect(outcome.status_to_apply)
            except ValueError:
                raise RulingValidationError(
                    f"[{tier_name}] Unknown status effect: {outcome.status_to_apply!r}"
                )

        # status_target must be in scene
        if outcome.status_target and outcome.status_target not in context.scene_entity_ids:
            raise RulingValidationError(
                f"[{tier_name}] Target {outcome.status_target!r} not in scene"
            )

        # item_consumed must be accessible
        if outcome.item_consumed and outcome.item_consumed not in valid_item_ids:
            raise RulingValidationError(
                f"[{tier_name}] Item {outcome.item_consumed!r} not accessible"
            )

    # 4. Record suspicion (fast LLM responses may indicate local forging)
    flags = _suspicion.record(context.player_id, response_time_ms)
    if flags > 0:
        print(f"[SUSPECT] player {context.player_id} has {flags} suspicion flag(s)")

    return ruling
