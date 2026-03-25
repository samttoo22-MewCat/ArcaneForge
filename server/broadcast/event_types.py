"""Typed event dataclasses for SSE broadcasts."""
import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class BaseEvent:
    event_type: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        import dataclasses
        return dataclasses.asdict(self)


@dataclass
class PlayerMovedEvent(BaseEvent):
    event_type: str = "player_moved"
    player_id: str = ""
    player_name: str = ""
    from_place_id: str = ""
    to_place_id: str = ""
    direction: str = ""


@dataclass
class CombatStartedEvent(BaseEvent):
    event_type: str = "combat_started"
    room_id: str = ""
    combatants: list[dict] = field(default_factory=list)


@dataclass
class CombatRoundEvent(BaseEvent):
    event_type: str = "combat_round"
    room_id: str = ""
    round_num: int = 0
    actor_id: str = ""
    target_id: str = ""
    action: str = ""
    damage: int = 0
    target_hp_remaining: int = 0
    status_applied: Optional[str] = None
    narrative_hint: str = ""


@dataclass
class CombatEndedEvent(BaseEvent):
    event_type: str = "combat_ended"
    room_id: str = ""
    winner_id: Optional[str] = None
    loot: list[dict] = field(default_factory=list)


@dataclass
class GrabContestOpenEvent(BaseEvent):
    event_type: str = "grab_contest_open"
    item_instance_id: str = ""
    item_name: str = ""
    window_closes_at: float = 0.0
    place_id: str = ""


@dataclass
class GrabContestResolvedEvent(BaseEvent):
    event_type: str = "grab_contest_resolved"
    item_instance_id: str = ""
    winner_id: Optional[str] = None
    scores: dict[str, float] = field(default_factory=dict)


@dataclass
class PlayerSaidEvent(BaseEvent):
    event_type: str = "player_said"
    player_id: str = ""
    player_name: str = ""
    message: str = ""
    place_id: str = ""


@dataclass
class NPCActionEvent(BaseEvent):
    event_type: str = "npc_action"
    npc_id: str = ""
    npc_name: str = ""
    action_type: str = ""
    target_id: Optional[str] = None
    narrative_hint: str = ""


@dataclass
class WorldStateChangeEvent(BaseEvent):
    event_type: str = "world_state_change"
    place_id: str = ""
    change_type: str = ""
    details: dict = field(default_factory=dict)


@dataclass
class SystemAnnouncementEvent(BaseEvent):
    event_type: str = "system_announcement"
    message: str = ""
