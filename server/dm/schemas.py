"""Pydantic schemas for DM prompt packets and rulings."""
from typing import Literal, Optional
from pydantic import BaseModel, Field

EffectType = Literal[
    "damage_modifier",
    "heal",
    "status_apply",
    "environment_change",
    "social_outcome",
    "item_transform",
    "no_effect",
]

TierName = Literal[
    "large_success",
    "medium_success",
    "small_success",
    "small_failure",
    "medium_failure",
    "large_failure",
]

ALL_TIERS: tuple[str, ...] = (
    "large_success", "medium_success", "small_success",
    "small_failure", "medium_failure", "large_failure",
)


class OutcomeEntry(BaseModel):
    """DM-provided outcome for one tier. Narrative only — no numbers."""
    narrative: str = Field(default="", max_length=150)
    effect_type: EffectType = "no_effect"
    # Only populated when effect_type == "status_apply":
    status_to_apply: Optional[str] = None
    status_target: Optional[str] = None   # entity_id in scene
    # Only populated when effect_type == "item_transform":
    item_consumed: Optional[str] = None   # item instance_id


class DMRuling(BaseModel):
    feasible: bool
    violation_reason: str = ""
    action_type: Literal["combat", "social", "explore", "magic", "other"] = "other"
    relevant_stat: Literal["atk", "def", "spd", "str", "dex", "int", "wis", "cha", "luk"] = "luk"
    difficulty: int = Field(default=0, ge=-10, le=10)   # added to roll; negative = harder
    threshold: int = Field(default=12, ge=1, le=30)     # DC to beat
    outcomes: dict[TierName, OutcomeEntry] = Field(default_factory=dict)


class DMPromptPacket(BaseModel):
    payload: dict
    nonce: str
    timestamp: float
    session_id: str
    signature: str


class DMRulingSubmission(BaseModel):
    nonce: str
    timestamp: float
    session_id: str
    signature: str
    ruling: DMRuling
