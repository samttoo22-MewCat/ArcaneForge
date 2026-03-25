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


class DMRuling(BaseModel):
    feasible: bool
    reason: str = ""
    effect_type: EffectType = "no_effect"
    modifier: float = Field(default=1.0, ge=0.1, le=10.0)
    status_to_apply: Optional[str] = None
    status_target: Optional[str] = None
    item_consumed: Optional[str] = None
    item_produced: Optional[str] = None
    environment_change: Optional[str] = None
    narrative_hint: str = ""
    dice_bonus: int = Field(default=0, ge=0, le=5)


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
