"""V-02: DM ruling validator — modifier clamping, feasibility, item checks."""
import pytest
from server.dm.schemas import DMRuling
from server.dm.validator import RulingContext, validate_ruling, RulingValidationError


def make_context(is_combat=False, entity_ids=None, item_ids=None, inventory_ids=None) -> RulingContext:
    return RulingContext(
        player_id="player_01",
        is_combat=is_combat,
        scene_entity_ids=set(entity_ids or ["player_01", "npc_01"]),
        scene_item_instance_ids=set(item_ids or ["item_01"]),
        player_inventory_ids=set(inventory_ids or []),
    )


class TestModifierClamping:
    def test_modifier_clamped_in_combat(self):
        ruling = DMRuling(feasible=True, effect_type="damage_modifier", modifier=6.0)
        ctx = make_context(is_combat=True)
        result = validate_ruling(ruling, ctx)
        assert result.modifier <= 3.0

    def test_modifier_clamped_outside_combat(self):
        ruling = DMRuling(feasible=True, effect_type="damage_modifier", modifier=9.0)
        ctx = make_context(is_combat=False)
        result = validate_ruling(ruling, ctx)
        assert result.modifier <= 5.0

    def test_modifier_within_limit_unchanged(self):
        ruling = DMRuling(feasible=True, effect_type="damage_modifier", modifier=2.0)
        ctx = make_context(is_combat=True)
        result = validate_ruling(ruling, ctx)
        assert result.modifier == 2.0

    def test_not_feasible_zeroes_modifier(self):
        ruling = DMRuling(feasible=False, reason="impossible", modifier=3.0)
        ctx = make_context()
        result = validate_ruling(ruling, ctx)
        assert result.modifier == 1.0
        assert result.status_to_apply is None
        assert result.dice_bonus == 0


class TestFeasibilityChecks:
    def test_unknown_status_effect_raises(self):
        ruling = DMRuling(feasible=True, effect_type="status_apply", status_to_apply="flying", status_target="npc_01")
        ctx = make_context()
        with pytest.raises(RulingValidationError):
            validate_ruling(ruling, ctx)

    def test_valid_status_effect_passes(self):
        ruling = DMRuling(feasible=True, effect_type="status_apply", status_to_apply="burning", status_target="npc_01")
        ctx = make_context()
        result = validate_ruling(ruling, ctx)
        assert result.status_to_apply == "burning"

    def test_target_not_in_scene_raises(self):
        ruling = DMRuling(feasible=True, effect_type="status_apply", status_to_apply="stun", status_target="npc_unknown")
        ctx = make_context()
        with pytest.raises(RulingValidationError):
            validate_ruling(ruling, ctx)

    def test_item_not_in_scene_raises(self):
        ruling = DMRuling(feasible=True, effect_type="item_transform", item_consumed="nonexistent_item")
        ctx = make_context()
        with pytest.raises(RulingValidationError):
            validate_ruling(ruling, ctx)

    def test_item_in_inventory_passes(self):
        ruling = DMRuling(feasible=True, effect_type="item_transform", item_consumed="inv_item_01")
        ctx = make_context(inventory_ids=["inv_item_01"])
        result = validate_ruling(ruling, ctx)
        assert result.item_consumed == "inv_item_01"

    def test_item_in_scene_passes(self):
        ruling = DMRuling(feasible=True, effect_type="item_transform", item_consumed="item_01")
        ctx = make_context(item_ids=["item_01"])
        result = validate_ruling(ruling, ctx)
        assert result.item_consumed == "item_01"

    def test_item_produced_always_rejected(self):
        ruling = DMRuling(feasible=True, effect_type="item_transform", item_produced="magic_sword_legendary")
        ctx = make_context()
        with pytest.raises(RulingValidationError, match="item_produced"):
            validate_ruling(ruling, ctx)
