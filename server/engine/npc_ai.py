"""NPC behavior tree: rule-based decision making, no AI calls."""
from typing import Optional


def evaluate_npc_state(npc: dict, players_in_room: list[dict]) -> str:
    """Determine new behavior_state based on current conditions."""
    # Flee if HP < 25%
    hp = npc.get("hp", npc.get("hp_max", 1))
    hp_max = npc.get("hp_max", 1)
    if hp_max > 0 and hp / hp_max < 0.25:
        return "flee"

    # Enter combat if hostile players are present
    hostile_to = npc.get("hostile_to", [])
    if isinstance(hostile_to, str):
        import json
        hostile_to = json.loads(hostile_to)
    if "player" in hostile_to and players_in_room:
        return "combat"

    # Return to default state
    current = npc.get("behavior_state", "idle")
    if current in ("patrol", "idle", "sleep"):
        return current
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
        import json
        hostile_ids = json.loads(hostile_ids)

    for pid in hostile_ids:
        if any(p["id"] == pid for p in players_in_room):
            return pid

    # Default: attack player with lowest HP
    return min(players_in_room, key=lambda p: p.get("hp", 999))["id"]


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
