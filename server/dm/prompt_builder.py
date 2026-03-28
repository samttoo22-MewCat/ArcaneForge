"""Build structured prompt payloads for DM LLM calls."""
import json
from pathlib import Path

_DATA = Path(__file__).parent.parent.parent / "data"
_WORLD_RULES_PATH = _DATA / "world_rules.md"
_ACTION_RULES_PATH = _DATA / "action_rules.json"

_world_rules_cache: str | None = None
_action_rules_cache: dict | None = None


def _load_world_rules() -> str:
    global _world_rules_cache
    if _world_rules_cache is None:
        if _WORLD_RULES_PATH.exists():
            _world_rules_cache = _WORLD_RULES_PATH.read_text(encoding="utf-8")
        else:
            _world_rules_cache = "Standard fantasy TRPG rules apply. Be fair and consistent."
    return _world_rules_cache


def _load_action_rules() -> dict:
    global _action_rules_cache
    if _action_rules_cache is None:
        if _ACTION_RULES_PATH.exists():
            _action_rules_cache = json.loads(_ACTION_RULES_PATH.read_text(encoding="utf-8"))
        else:
            _action_rules_cache = {
                "action_types": {
                    "combat":  {"stats": ["atk", "spd"], "base_threshold": 12},
                    "social":  {"stats": ["luk"],        "base_threshold": 10},
                    "explore": {"stats": ["spd", "luk"], "base_threshold": 10},
                    "magic":   {"stats": ["luk"],        "base_threshold": 14},
                    "other":   {"stats": ["luk"],        "base_threshold": 12},
                },
                "tier_margins": [5, 2, 0, -2, -5],
            }
    return _action_rules_cache


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


def build_npc_persuasion_prompt(
    player: dict,
    npc: dict,
    player_message: str,
    intent: str,          # "persuade" | "threaten" | "bribe"
    memory_summary: str,
) -> dict:
    """
    Build a structured DM prompt for social actions (persuade/threaten/bribe) against an NPC.
    intent maps to relevant stat: persuade→cha, threaten→str, bribe→luk
    """
    action_rules = _load_action_rules()
    intent_stat = {"persuade": "cha", "threaten": "str", "bribe": "luk"}.get(intent, "cha")
    intent_zh = {"persuade": "說服", "threaten": "威脅", "bribe": "賄賂"}.get(intent, intent)

    return {
        "world_rules": _load_world_rules()[:800],
        "action_rules": action_rules,
        "npc": {
            "id": npc.get("id"),
            "name": npc.get("name"),
            "hp": npc.get("hp"),
            "behavior_state": npc.get("behavior_state"),
            "faction": npc.get("faction"),
            "npc_type": npc.get("npc_type"),
            "disposition": npc.get("disposition", 0),
            "memory_summary": memory_summary or "",
        },
        "player": {
            "id": player.get("id"),
            "name": player.get("name"),
            "level": player.get("level", 1),
            "classes": player.get("classes", []),
            "str": player.get("str", 8),
            "dex": player.get("dex", 8),
            "int": player.get("int", 8),
            "wis": player.get("wis", 8),
            "cha": player.get("cha", 8),
            "luk": player.get("luk", 8),
        },
        "player_message": player_message,
        "intent": intent,
        "intent_zh": intent_zh,
        "output_schema": {
            "feasible": "bool — false if the action is clearly impossible (e.g. dead NPC, NPC is mid-combat)",
            "violation_reason": "string — required when feasible is false",
            "action_type": "social",
            "relevant_stat": f"{intent_stat} — use {intent_stat} for {intent_zh} checks",
            "difficulty": "int -10 to +10 — modifier based on NPC disposition and context (positive=easier)",
            "threshold": "int 8-18 — DC based on difficulty of the request",
            "outcomes": {
                "large_success":  {"narrative": "string max 100 chars — NPC fully agrees or is deeply moved", "effect_type": "social_outcome", "status_to_apply": None, "status_target": None, "item_consumed": None},
                "medium_success": {"narrative": "string max 100 chars", "effect_type": "social_outcome", "status_to_apply": None, "status_target": None, "item_consumed": None},
                "small_success":  {"narrative": "string max 100 chars", "effect_type": "social_outcome", "status_to_apply": None, "status_target": None, "item_consumed": None},
                "small_failure":  {"narrative": "string max 100 chars", "effect_type": "social_outcome", "status_to_apply": None, "status_target": None, "item_consumed": None},
                "medium_failure": {"narrative": "string max 100 chars", "effect_type": "social_outcome", "status_to_apply": None, "status_target": None, "item_consumed": None},
                "large_failure":  {"narrative": "string max 100 chars — NPC is offended or becomes hostile", "effect_type": "social_outcome", "status_to_apply": None, "status_target": None, "item_consumed": None},
            },
            "_rules": [
                "You MUST return all six outcome keys.",
                "effect_type MUST be social_outcome for all outcomes.",
                "Narratives should reflect the NPC's memory_summary and current disposition.",
                "Do NOT include any damage numbers.",
            ],
        },
    }


def build_action_prompt(
    player: dict,
    scene: dict,
    action: str,
    npcs: list[dict],
    scene_items: list[dict],
    inventory_items: list[dict],
    item_master: dict[str, dict] | None = None,
    is_combat: bool = False,
    detected_action_type: str | None = None,
) -> dict:
    """
    Build a structured DM prompt payload.
    Kept under ~1500 tokens by trimming context.
    """
    im = item_master or {}
    action_rules = _load_action_rules()

    return {
        "world_rules": _load_world_rules()[:800],
        "action_rules": action_rules,
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
            "level": player.get("level", 1),
            "classes": player.get("classes", []),
            "hp": player.get("hp"),
            "hp_max": player.get("max_hp"),
            "mp": player.get("mp"),
            "mp_max": player.get("max_mp"),
            # Combat derived
            "atk": player.get("atk"),
            "def": player.get("def"),
            "spd": player.get("spd"),
            # Six core attributes
            "str": player.get("str", 8),
            "dex": player.get("dex", 8),
            "int": player.get("int", 8),
            "wis": player.get("wis", 8),
            "cha": player.get("cha", 8),
            "luk": player.get("luk", 8),
            "status_effects": player.get("status_effects", []),
            "equipped": player.get("equipped_slots", {}),
        },
        "npcs": [_trim_npc(n) for n in npcs[:5]],
        "scene_items": [_trim_item(i, im.get(i.get("item_id"))) for i in scene_items[:10]],
        "inventory": [_trim_item(i, im.get(i.get("item_id"))) for i in inventory_items[:10]],
        "action": action,
        "is_combat": is_combat,
        "action_type_hint": detected_action_type or "other",
        "output_schema": {
            "feasible": "bool — false if the action violates world rules",
            "violation_reason": "string — required when feasible is false",
            "action_type": "combat | social | explore | magic | other",
            "relevant_stat": "atk | def | spd | str | dex | int | wis | cha | luk — single stat used for the roll",
            "difficulty": "int -10 to +10 — modifier added to roll (negative=harder, positive=easier)",
            "threshold": "int 1-30 — DC to beat; see action_rules.action_types[action_type].base_threshold",
            "outcomes": {
                "large_success":  {
                    "narrative": "string max 100 chars",
                    "effect_type": "damage_modifier|heal|status_apply|environment_change|social_outcome|item_transform|no_effect",
                    "status_to_apply": "string|null",
                    "status_target": "entity_id|null",
                    "item_consumed": "instance_id|null",
                },
                "medium_success": {"narrative": "string max 100 chars", "effect_type": "..."},
                "small_success":  {"narrative": "string max 100 chars", "effect_type": "..."},
                "small_failure":  {"narrative": "string max 100 chars", "effect_type": "..."},
                "medium_failure": {"narrative": "string max 100 chars", "effect_type": "..."},
                "large_failure":  {"narrative": "string max 100 chars", "effect_type": "..."},
            },
            "_rules": [
                "You MUST return all six outcome keys.",
                "Do NOT include any damage numbers or HP values — the server calculates all numbers.",
                "item_produced is always null — you cannot create items outside the master table.",
            ],
        },
    }
