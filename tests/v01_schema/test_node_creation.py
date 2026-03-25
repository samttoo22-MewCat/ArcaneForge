"""V-01: FalkorDB schema validation (unit tests, no live DB required).

These tests validate the data structures and Cypher query patterns
without requiring a running FalkorDB instance.
Live integration tests should be run separately with docker compose.
"""
import pytest
from server.engine.rules import RuleError, can_move, can_attack, can_pickup, can_use_free_action, is_safe_zone


class TestRuleEngine:
    def test_can_move_dead_player_raises(self):
        player = {"hp": 0, "is_in_combat": False}
        with pytest.raises(RuleError):
            can_move(player, {}, {"is_locked": False, "is_hidden": False})

    def test_can_move_in_combat_raises(self):
        player = {"hp": 10, "is_in_combat": True}
        with pytest.raises(RuleError):
            can_move(player, {}, {"is_locked": False, "is_hidden": False})

    def test_can_move_locked_door_raises(self):
        player = {"hp": 10, "is_in_combat": False}
        with pytest.raises(RuleError):
            can_move(player, {}, {"is_locked": True, "is_hidden": False})

    def test_can_move_hidden_door_raises(self):
        player = {"hp": 10, "is_in_combat": False}
        with pytest.raises(RuleError):
            can_move(player, {}, {"is_locked": False, "is_hidden": True})

    def test_can_move_valid(self):
        player = {"hp": 10, "is_in_combat": False}
        # Should not raise
        can_move(player, {}, {"is_locked": False, "is_hidden": False})

    def test_can_attack_different_rooms_raises(self):
        attacker = {"hp": 10, "current_place_id": "room_A"}
        target = {"current_place_id": "room_B"}
        with pytest.raises(RuleError):
            can_attack(attacker, target, "room_A")

    def test_can_attack_same_room_valid(self):
        attacker = {"hp": 10, "current_place_id": "room_A"}
        target = {"current_place_id": "room_A"}
        can_attack(attacker, target, "room_A")

    def test_can_pickup_wrong_room_raises(self):
        player = {"hp": 10}
        item = {"location_type": "room", "location_id": "room_B"}
        with pytest.raises(RuleError):
            can_pickup(player, item, "room_A")

    def test_can_pickup_valid(self):
        player = {"hp": 10}
        item = {"location_type": "room", "location_id": "room_A"}
        can_pickup(player, item, "room_A")

    def test_is_safe_zone_true(self):
        place = {"is_safe_zone": True}
        assert is_safe_zone(place) is True

    def test_is_safe_zone_false(self):
        place = {"is_safe_zone": False}
        assert is_safe_zone(place) is False

    def test_can_use_free_action_stunned_raises(self):
        player = {"hp": 10, "status_effects": [{"effect_type": "stun", "duration": 1}]}
        with pytest.raises(RuleError):
            can_use_free_action(player)

    def test_can_use_free_action_valid(self):
        player = {"hp": 10, "status_effects": []}
        can_use_free_action(player)

    def test_can_move_while_traveling_raises(self):
        player = {"hp": 10, "is_in_combat": False, "is_traveling": True}
        with pytest.raises(RuleError, match="移動途中"):
            can_move(player, {}, {"is_locked": False, "is_hidden": False})

    def test_can_move_not_traveling_valid(self):
        player = {"hp": 10, "is_in_combat": False, "is_traveling": False}
        can_move(player, {}, {"is_locked": False, "is_hidden": False})
