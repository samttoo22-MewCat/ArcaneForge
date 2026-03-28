"""Player skill & spell system: unlock checks, effect resolution, cooldown helpers."""
import json
import time
from pathlib import Path

from server.engine import combat

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_SKILLS: dict = json.loads((_DATA_DIR / "skills.json").read_text(encoding="utf-8"))
_SPELLS: dict = json.loads((_DATA_DIR / "magic.json").read_text(encoding="utf-8"))


def load_skills() -> dict:
    return _SKILLS


def load_spells() -> dict:
    return _SPELLS


def check_ability_unlocked(player: dict, ability: dict) -> tuple[bool, str]:
    """Check if player meets required_classes / required_level / required_stats.

    Returns (True, "") if unlocked, or (False, reason_string) if locked.
    """
    # Class check
    required_classes: list[str] = ability.get("required_classes", [])
    if required_classes:
        player_classes: list[str] = player.get("classes", [])
        if isinstance(player_classes, str):
            try:
                player_classes = json.loads(player_classes)
            except (json.JSONDecodeError, ValueError):
                player_classes = []
        if not any(cls in player_classes for cls in required_classes):
            class_names = "、".join(required_classes)
            return False, f"需要職業：{class_names}"

    # Level check
    required_level: int = ability.get("required_level", 1)
    if player.get("level", 1) < required_level:
        return False, f"需要等級 {required_level}（目前 {player.get('level', 1)}）"

    # Stat checks
    required_stats: dict = ability.get("required_stats", {})
    for stat, min_val in required_stats.items():
        actual = player.get(stat, 0)
        if actual < min_val:
            return False, f"需要 {stat.upper()} ≥ {min_val}（目前 {actual}）"

    return True, ""


def get_cooldown_key(player_id: str, ability_id: str) -> str:
    return f"player:{player_id}:skill_cd:{ability_id}"


def get_cooldown_remaining(expires_at: float | None) -> float:
    if expires_at is None:
        return 0.0
    return max(0.0, expires_at - time.time())


def resolve_ability_effect(
    player: dict,
    ability: dict,
    target: dict | None,
    ability_type: str,
) -> dict:
    """Resolve the numeric effect of a skill or spell.

    Returns dict with keys: damage, heal, status_applied, narrative_hint.
    Raises ValueError for passive abilities (should be blocked before this call).
    """
    effect_type: str = ability.get("effect_type", "utility")
    name: str = ability.get("name", ability.get("id", "?"))
    target_name: str = target.get("name", "目標") if target else "自身"
    damage = 0
    heal = 0
    status_applied: str | None = None
    narrative_hint = ""

    if effect_type == "passive":
        raise ValueError("被動技能自動生效，無法主動使用。")

    elif effect_type == "heal":
        heal = ability.get("heal_amount", 15)
        # Cap to player's missing HP (self-heal)
        missing = player.get("max_hp", 100) - player.get("hp", 100)
        heal = min(heal, missing)
        narrative_hint = f"使用【{name}】，回復 {heal} 點 HP。"

    elif effect_type == "damage_modifier":
        if target is None:
            raise ValueError("此技能需要指定目標。")
        multiplier: float = ability.get("damage_multiplier", 1.0)
        attacker_tags: list[str] = ability.get("tags", [])
        if ability_type == "spell":
            element = ability.get("element", "arcane")
            attacker_tags = attacker_tags + [element]
        target_tags: list[str] = target.get("tags", [])
        damage = combat.calculate_damage(
            player.get("atk", 10),
            target.get("def", 2),
            multiplier,
            is_combat=True,
            attacker_tags=attacker_tags,
            target_tags=target_tags,
        )
        narrative_hint = f"使用【{name}】，對 {target_name} 造成 {damage} 點傷害。"

    elif effect_type == "status_apply":
        if target is None:
            raise ValueError("此技能需要指定目標。")
        status_applied = ability.get("status_apply")
        multiplier = ability.get("damage_multiplier", 0.5)
        if multiplier > 0:
            attacker_tags = ability.get("tags", [])
            if ability_type == "spell":
                element = ability.get("element", "arcane")
                attacker_tags = attacker_tags + [element]
            target_tags = target.get("tags", [])
            damage = combat.calculate_damage(
                player.get("atk", 10),
                target.get("def", 2),
                multiplier,
                is_combat=True,
                attacker_tags=attacker_tags,
                target_tags=target_tags,
            )
        status_label = status_applied or "未知"
        narrative_hint = (
            f"使用【{name}】，"
            + (f"對 {target_name} 造成 {damage} 點傷害，" if damage else "")
            + f"並施加【{status_label}】效果。"
        )

    else:
        # utility / social_outcome / environment_change
        narrative_hint = f"使用【{name}】。效果已生效。"

    return {
        "damage": damage,
        "heal": heal,
        "status_applied": status_applied,
        "narrative_hint": narrative_hint,
    }


def build_abilities_list(player: dict, cooldowns: dict[str, float]) -> list[dict]:
    """Build a combined list of all skills and spells with unlock + cooldown info."""
    result: list[dict] = []

    def _entry(ability_id: str, ability: dict, ability_type: str) -> dict:
        unlocked, locked_reason = check_ability_unlocked(player, ability)
        cd_remaining = cooldowns.get(ability_id, 0.0)
        is_passive = ability.get("effect_type") == "passive"
        entry: dict = {
            "id": ability_id,
            "name": ability.get("name", ability_id),
            "description": ability.get("description", ""),
            "mp_cost": ability.get("mp_cost", 0),
            "cooldown_turns": ability.get("cooldown_turns", 0),
            "cooldown_seconds_remaining": round(cd_remaining, 1),
            "is_unlocked": unlocked,
            "locked_reason": locked_reason,
            "effect_type": ability.get("effect_type", "utility"),
            "tags": ability.get("tags", []),
            "ability_type": ability_type,
            "is_passive": is_passive,
        }
        if ability_type == "spell":
            entry["element"] = ability.get("element", "arcane")
            entry["target"] = ability.get("target", "single")
        else:
            entry["target"] = _infer_target(ability)
        return entry

    def _infer_target(ability: dict) -> str:
        tags: list[str] = ability.get("tags", [])
        effect_type: str = ability.get("effect_type", "utility")
        if "self" in tags or effect_type == "heal":
            return "self"
        if "aoe" in tags:
            return "aoe"
        return "single"

    for skill_id, skill in _SKILLS.items():
        result.append(_entry(skill_id, skill, "skill"))
    for spell_id, spell in _SPELLS.items():
        result.append(_entry(spell_id, spell, "spell"))

    return result
