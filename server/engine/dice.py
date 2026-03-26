"""Server-side dice system using SystemRandom for unpredictability."""
import random
import re

_rng = random.SystemRandom()


def roll(sides: int, count: int = 1, modifier: int = 0) -> int:
    total = sum(_rng.randint(1, sides) for _ in range(count))
    return total + modifier


def d20(modifier: int = 0) -> int:
    return roll(20, modifier=modifier)


def d6(count: int = 1, modifier: int = 0) -> int:
    return roll(6, count=count, modifier=modifier)


def perturbation(base: float, percent: float = 0.1) -> float:
    """Return base ± (base * percent) random offset."""
    delta = base * percent
    return base + _rng.uniform(-delta, delta)


def damage_random() -> float:
    """Random multiplier in [0.85, 1.15] for damage variance."""
    return _rng.uniform(0.85, 1.15)


def parse_notation(notation: str) -> tuple[int, int, int]:
    """Parse dice notation like '2d6+3' -> (count, sides, modifier)."""
    pattern = re.compile(r"^(\d+)d(\d+)([+-]\d+)?$", re.IGNORECASE)
    m = pattern.match(notation.strip())
    if not m:
        raise ValueError(f"Invalid dice notation: {notation!r}")
    count = int(m.group(1))
    sides = int(m.group(2))
    modifier = int(m.group(3)) if m.group(3) else 0
    return count, sides, modifier


def roll_notation(notation: str) -> int:
    count, sides, modifier = parse_notation(notation)
    return roll(sides, count=count, modifier=modifier)


def calc_tier(roll_result: int, threshold: int, margins: list[int] | None = None) -> str:
    """
    Map a roll result against a threshold to one of six outcome tiers.

    margins: 5 boundary values [large, medium, small_success, small_fail, medium_fail].
    Default [5, 2, 0, -2, -5]:
      delta >= 5  → large_success
      delta >= 2  → medium_success
      delta >= 0  → small_success
      delta >= -2 → small_failure
      delta >= -5 → medium_failure
      otherwise   → large_failure
    """
    m = margins if margins is not None else [5, 2, 0, -2, -5]
    delta = roll_result - threshold
    if delta >= m[0]:
        return "large_success"
    if delta >= m[1]:
        return "medium_success"
    if delta >= m[2]:
        return "small_success"
    if delta >= m[3]:
        return "small_failure"
    if delta >= m[4]:
        return "medium_failure"
    return "large_failure"
