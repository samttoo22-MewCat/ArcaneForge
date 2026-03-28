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
    """Legacy instant-move event; kept for internal/admin use."""
    event_type: str = "player_moved"
    player_id: str = ""
    player_name: str = ""
    from_place_id: str = ""
    to_place_id: str = ""
    direction: str = ""


@dataclass
class PlayerTravelingEvent(BaseEvent):
    """Broadcast when a player starts moving through a passage."""
    event_type: str = "player_traveling"
    player_id: str = ""
    player_name: str = ""
    from_place_id: str = ""
    to_place_id: str = ""
    direction: str = ""
    travel_time_seconds: float = 0.0
    arrives_at: float = 0.0          # Unix timestamp of arrival
    transition_description: str = "" # Flavour text for the passage


@dataclass
class PlayerArrivedEvent(BaseEvent):
    """Broadcast when a player completes travel and arrives in a new room."""
    event_type: str = "player_arrived"
    player_id: str = ""
    player_name: str = ""
    from_place_id: str = ""
    to_place_id: str = ""
    to_place_name: str = ""  # 房間顯示名稱，供前端直接顯示
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
class PlayerDeathEvent(BaseEvent):
    event_type: str = "player_death"
    player_id: str = ""
    player_name: str = ""
    place_id: str = ""
    killer_id: str = ""
    killer_name: str = ""
    respawn_in_seconds: int = 60


@dataclass
class PlayerRespawnEvent(BaseEvent):
    event_type: str = "player_respawn"
    player_id: str = ""
    player_name: str = ""
    respawn_place_id: str = ""


@dataclass
class SystemAnnouncementEvent(BaseEvent):
    event_type: str = "system_announcement"
    message: str = ""


@dataclass
class DMRulingAppliedEvent(BaseEvent):
    """Broadcast after a DM ruling is validated and applied by the server."""
    event_type: str = "dm_ruling_applied"
    player_id: str = ""
    feasible: bool = True
    # Dice details (empty when not feasible)
    tier: str = ""          # "large_success" | ... | "large_failure" | ""
    raw_roll: int = 0       # raw d20 value (transparency / fairness)
    final_roll: int = 0     # raw_roll + stat_value + difficulty
    threshold: int = 0
    relevant_stat: str = ""
    stat_value: int = 0
    difficulty: int = 0
    # Effect applied
    effect_type: str = "no_effect"
    modifier: float = 1.0
    narrative_hint: str = ""
    status_applied: Optional[str] = None
    item_consumed: Optional[str] = None


@dataclass
class NPCDialogueEvent(BaseEvent):
    event_type: str = "npc_dialogue"
    npc_id: str = ""
    npc_name: str = ""
    npc_type: str = ""
    player_id: str = ""
    line: str = ""
    dialogue_key: str = ""
    place_id: str = ""


@dataclass
class NPCMovedEvent(BaseEvent):
    event_type: str = "npc_moved"
    npc_id: str = ""
    npc_name: str = ""
    from_place_id: str = ""
    to_place_id: str = ""


@dataclass
class StatusEffectAppliedEvent(BaseEvent):
    event_type: str = "status_effect_applied"
    target_id: str = ""
    target_name: str = ""
    effect_type: str = ""
    stacks: int = 1
    source_id: str = ""
    room_id: str = ""


@dataclass
class PlayerLeveledUpEvent(BaseEvent):
    event_type: str = "player_leveled_up"
    player_id: str = ""
    player_name: str = ""
    new_level: int = 0
    stat_points_gained: int = 3


@dataclass
class NPCAlertEvent(BaseEvent):
    """Broadcast to a middle_place when hostile NPCs detect an intruder in an adjacent room."""
    event_type: str = "npc_alert"
    middle_id: str = ""
    place_id: str = ""      # room that triggered the alert
    trigger: str = ""       # "player_entered" | "combat_started"
    message: str = ""       # display text for clients


@dataclass
class NPCPersuasionEvent(BaseEvent):
    """Broadcast after a persuade/threaten/bribe social action is resolved."""
    event_type: str = "npc_persuasion"
    npc_id: str = ""
    npc_name: str = ""
    player_id: str = ""
    player_name: str = ""
    intent: str = ""        # "persuade" | "threaten" | "bribe"
    tier: str = ""          # "large_success" | ... | "large_failure"
    narrative: str = ""     # DM-generated outcome description
    disposition: int = 0    # NPC's new disposition value toward this player
