"""Combat engine: action bar, turn order, damage formula."""
from dataclasses import dataclass, field

from server.engine.dice import perturbation, damage_random
from server.config import settings

DOUBLE_ACTION_THRESHOLD = 0.30  # 30% SPD difference triggers double action


@dataclass
class Combatant:
    id: str
    spd: int
    hp: int
    hp_max: int
    atk: int
    def_: int
    charge: float = 0.0
    acted_twice_this_cycle: bool = False
    is_alive: bool = True

    def tick(self) -> None:
        self.charge += perturbation(float(self.spd), 0.1)

    def reset_charge(self) -> None:
        self.charge -= 100.0


def tick_to_ready(combatants: list[Combatant]) -> list[Combatant]:
    """Advance all charges until at least one reaches >= 100. Return ready list sorted by charge desc."""
    while not any(c.charge >= 100 for c in combatants if c.is_alive):
        for c in combatants:
            if c.is_alive:
                c.tick()
    ready = sorted([c for c in combatants if c.is_alive and c.charge >= 100], key=lambda c: -c.charge)
    return ready


def check_double_action(actor: Combatant, opponents: list[Combatant]) -> bool:
    """True if actor's SPD exceeds all alive opponents' SPD by > 30%."""
    alive_opponents = [o for o in opponents if o.is_alive and o.id != actor.id]
    if not alive_opponents:
        return False
    max_opp_spd = max(o.spd for o in alive_opponents)
    return actor.spd > max_opp_spd * (1 + DOUBLE_ACTION_THRESHOLD)


def calculate_damage(
    atk: int,
    def_: int,
    dm_modifier: float,
    is_combat: bool = True,
) -> int:
    cap = settings.dm_combat_modifier_cap if is_combat else settings.dm_modifier_cap
    modifier = min(float(dm_modifier), cap)
    raw = (atk - def_ * 0.5) * modifier * damage_random()
    return max(1, int(raw))


def apply_damage(target: Combatant, damage: int) -> int:
    """Apply damage, clamp hp to 0, return actual damage dealt."""
    actual = min(damage, target.hp)
    target.hp = max(0, target.hp - damage)
    if target.hp == 0:
        target.is_alive = False
    return actual
