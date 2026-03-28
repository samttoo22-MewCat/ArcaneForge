"""NPC behavior tree: rule-based decision making, no AI calls."""
import json
from typing import Optional


def evaluate_npc_state(npc: dict, players_in_room: list[dict]) -> str:
    """Determine new behavior_state based on current conditions (uses personality for flee threshold)."""
    hp = npc.get("hp", npc.get("hp_max", 1))
    hp_max = npc.get("hp_max", 1)
    personality = npc.get("personality", "aggressive")

    # Personality-based flee threshold
    if personality == "berserker":
        flee_threshold = 0.0      # never flees
    elif personality == "evasive":
        flee_threshold = 0.5      # flees early at 50% HP
    elif personality == "defensive":
        flee_threshold = 0.3      # slightly more cautious
    else:
        flee_threshold = 0.25     # default

    if hp_max > 0 and hp / hp_max < flee_threshold:
        return "flee"

    # Enter combat if hostile players are present (also exits alert state immediately)
    hostile_to = npc.get("hostile_to", [])
    if isinstance(hostile_to, str):
        hostile_to = json.loads(hostile_to)
    if "player" in hostile_to and players_in_room:
        return "combat"

    # Stay alert if an intruder was detected in an adjacent room (no players here yet)
    if npc.get("alert_ticks_remaining", 0) > 0:
        return "alert"

    # Return to default state
    current = npc.get("behavior_state", "idle")
    if current in ("patrol", "idle", "sleep", "alert"):
        return current if current != "alert" else "patrol"
    if current == "combat":
        # No more players — return to patrol
        return "patrol"
    return "idle"


def pick_attack_target(npc: dict, players_in_room: list[dict]) -> Optional[str]:
    """Pick a target player. Prioritises players already tracked as hostile."""
    if not players_in_room:
        return None

    hostile_ids = npc.get("hostility_toward", [])
    if isinstance(hostile_ids, str):
        hostile_ids = json.loads(hostile_ids)

    for pid in hostile_ids:
        if any(p["id"] == pid for p in players_in_room):
            return pid

    # Default: attack player with lowest HP
    return min(players_in_room, key=lambda p: p.get("hp", 999))["id"]


def pick_skill(npc: dict, target: dict) -> Optional[dict]:
    """
    Select a skill to use based on personality, available MP, and cooldowns.
    Returns the chosen skill dict, or None to use a basic attack.
    """
    skills_raw = npc.get("skills", "[]")
    if isinstance(skills_raw, str):
        try:
            skills = json.loads(skills_raw)
        except (json.JSONDecodeError, ValueError):
            skills = []
    else:
        skills = skills_raw if isinstance(skills_raw, list) else []

    if not skills:
        return None

    personality = npc.get("personality", "aggressive")
    hp = npc.get("hp", 1)
    hp_max = npc.get("hp_max", 1)
    hp_pct = hp / max(1, hp_max)
    mp = npc.get("mp", 0)

    # Filter to skills that are off cooldown and have enough MP
    available = [
        s for s in skills
        if s.get("cooldown_remaining", 0) <= 0 and s.get("mp_cost", 0) <= mp
    ]
    if not available:
        return None

    if personality == "aggressive":
        # Always use highest damage skill
        return max(available, key=lambda s: s.get("damage_mult", 1.0))

    elif personality == "defensive":
        # Use self-heal/buff if HP < 50%, otherwise highest damage
        if hp_pct < 0.5:
            self_skills = [s for s in available if s.get("target") == "self"]
            if self_skills:
                return self_skills[0]
        return max(available, key=lambda s: s.get("damage_mult", 1.0))

    elif personality == "evasive":
        # Prefer free (zero MP cost) skills to conserve resources
        free_skills = [s for s in available if s.get("mp_cost", 0) == 0]
        if free_skills:
            return free_skills[0]
        return available[0]

    elif personality == "berserker":
        # Damage multiplier scales up as HP drops
        return max(available, key=lambda s: s.get("damage_mult", 1.0) * (2.0 - hp_pct))

    # neutral / unknown: use first available skill
    return available[0]


def tick_skill_cooldowns(skills: list[dict]) -> list[dict]:
    """Decrement all skill cooldowns by 1 (minimum 0)."""
    for s in skills:
        if s.get("cooldown_remaining", 0) > 0:
            s["cooldown_remaining"] -= 1
    return skills


def simulate_npc_elapsed_time(npc: dict, elapsed_seconds: float) -> dict:
    """
    Calculate state updates for an NPC that has been hibernating.
    Returns a dict of property updates to apply (may be empty).
    """
    updates: dict = {}
    state = npc.get("behavior_state", "idle")

    # Idle/patrol monsters slowly regenerate HP
    if state in ("idle", "patrol"):
        hp = npc.get("hp", npc.get("hp_max", 1))
        hp_max = npc.get("hp_max", 1)
        if hp < hp_max:
            regen = int(elapsed_seconds / 10)  # 1 HP per 10 seconds
            updates["hp"] = min(hp_max, hp + regen)

    # If they were in combat with nobody around, reset to patrol
    if state == "combat":
        updates["behavior_state"] = "patrol"
        updates["hostility_toward"] = []

    return updates
