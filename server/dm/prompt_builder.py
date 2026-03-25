"""Build structured prompt payloads for DM LLM calls."""
import json
import os
from pathlib import Path

_WORLD_RULES_PATH = Path(__file__).parent.parent.parent / "data" / "world_rules.md"

_world_rules_cache: str | None = None


def _load_world_rules() -> str:
    global _world_rules_cache
    if _world_rules_cache is None:
        if _WORLD_RULES_PATH.exists():
            _world_rules_cache = _WORLD_RULES_PATH.read_text(encoding="utf-8")
        else:
            _world_rules_cache = "Standard fantasy TRPG rules apply. Be fair and consistent."
    return _world_rules_cache


def _trim_npc(npc: dict) -> dict:
    return {
        "id": npc.get("id"),
        "name": npc.get("name"),
        "hp": npc.get("hp"),
        "behavior_state": npc.get("behavior_state"),
        "faction": npc.get("faction"),
        "memory_summary": npc.get("memory_summary", ""),
    }


def _trim_item(item: dict, master: dict | None = None) -> dict:
    base = {"instance_id": item.get("instance_id"), "item_id": item.get("item_id")}
    if master:
        base["name"] = master.get("name")
        base["tags"] = master.get("tags", [])
    return base


def build_action_prompt(
    player: dict,
    scene: dict,
    action: str,
    npcs: list[dict],
    scene_items: list[dict],
    inventory_items: list[dict],
    item_master: dict[str, dict] | None = None,
    is_combat: bool = False,
) -> dict:
    """
    Build a structured DM prompt payload.
    Kept under ~1500 tokens by trimming context.
    """
    im = item_master or {}
    return {
        "world_rules": _load_world_rules()[:800],  # trim to ~800 chars
        "scene": {
            "id": scene.get("id"),
            "name": scene.get("name"),
            "description": scene.get("description_base", ""),
            "light": scene.get("light", "bright"),
            "weather": scene.get("weather", "clear"),
            "is_safe_zone": scene.get("is_safe_zone", False),
        },
        "player": {
            "id": player.get("id"),
            "name": player.get("name"),
            "hp": player.get("hp"),
            "hp_max": player.get("hp_max"),
            "atk": player.get("atk"),
            "def": player.get("def_"),
            "spd": player.get("spd"),
            "luk": player.get("luk"),
            "status_effects": player.get("status_effects", []),
            "equipped": player.get("equipped_slots", {}),
        },
        "npcs": [_trim_npc(n) for n in npcs[:5]],  # max 5 NPCs
        "scene_items": [_trim_item(i, im.get(i.get("item_id"))) for i in scene_items[:10]],
        "inventory": [_trim_item(i, im.get(i.get("item_id"))) for i in inventory_items[:10]],
        "action": action,
        "is_combat": is_combat,
        "output_schema": {
            "feasible": "bool",
            "reason": "string",
            "effect_type": "damage_modifier|heal|status_apply|environment_change|social_outcome|item_transform|no_effect",
            "modifier": "float 0.1-5.0 (max 3.0 in combat)",
            "status_to_apply": "string|null",
            "status_target": "entity_id|null",
            "item_consumed": "instance_id|null",
            "item_produced": "null (always)",
            "narrative_hint": "string max 200 chars",
            "dice_bonus": "int 0-5 (grab contests only)",
        },
    }
