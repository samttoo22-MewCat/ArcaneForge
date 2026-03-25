"""Status effect definitions and processor."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from server.engine.dice import roll_notation


class StatusEffect(str, Enum):
    BURNING = "burning"
    POISON = "poison"
    STUN = "stun"
    SLOW = "slow"
    BLEED = "bleed"


@dataclass
class ActiveEffect:
    effect_type: StatusEffect
    duration: int           # rounds remaining
    stacks: int = 1
    source_id: Optional[str] = None


@dataclass
class TickResult:
    damage: int = 0
    skips_action: bool = False
    spd_modifier: float = 1.0


def tick_effect(effect: ActiveEffect, target_hp: int) -> TickResult:
    result = TickResult()
    if effect.effect_type == StatusEffect.BURNING:
        result.damage = max(1, int(target_hp * 0.05)) * effect.stacks
    elif effect.effect_type == StatusEffect.POISON:
        result.damage = 3 * effect.stacks
    elif effect.effect_type == StatusEffect.STUN:
        result.skips_action = True
    elif effect.effect_type == StatusEffect.SLOW:
        result.spd_modifier = 0.5
    elif effect.effect_type == StatusEffect.BLEED:
        result.damage = roll_notation("1d4") * effect.stacks
    return result


def apply_effects(effects: list[ActiveEffect], target_hp: int) -> tuple[int, bool, float]:
    """Process all active effects. Returns (total_damage, skip_action, spd_multiplier)."""
    total_damage = 0
    skip_action = False
    spd_mult = 1.0
    for e in effects:
        result = tick_effect(e, target_hp)
        total_damage += result.damage
        skip_action = skip_action or result.skips_action
        spd_mult = min(spd_mult, result.spd_modifier)
    return total_damage, skip_action, spd_mult


def decrement_durations(effects: list[ActiveEffect]) -> list[ActiveEffect]:
    """Reduce duration by 1, remove expired effects."""
    updated = []
    for e in effects:
        e.duration -= 1
        if e.duration > 0:
            updated.append(e)
    return updated


EFFECT_DEFAULTS: dict[StatusEffect, dict] = {
    StatusEffect.BURNING: {"duration": 3},
    StatusEffect.POISON: {"duration": 5},
    StatusEffect.STUN: {"duration": 1},
    StatusEffect.SLOW: {"duration": 2},
    StatusEffect.BLEED: {"duration": 4},
}


def make_effect(effect_type: StatusEffect | str, stacks: int = 1, source_id: str = None) -> ActiveEffect:
    et = StatusEffect(effect_type)
    defaults = EFFECT_DEFAULTS[et]
    return ActiveEffect(effect_type=et, duration=defaults["duration"], stacks=stacks, source_id=source_id)
