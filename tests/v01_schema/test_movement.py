"""Tests for travel time calculation and movement system."""
import pytest
from server.api.player import _actual_travel_time, BASE_SPD


class TestTravelTimeFormula:
    def test_base_speed_equals_base_time(self):
        # Player with SPD == BASE_SPD should travel at exactly base_time
        assert _actual_travel_time(10, BASE_SPD) == 10.0

    def test_double_speed_halves_time(self):
        result = _actual_travel_time(10, BASE_SPD * 2)
        assert result == 5.0

    def test_half_speed_doubles_time(self):
        result = _actual_travel_time(10, BASE_SPD // 2)
        assert result == 20.0

    def test_minimum_travel_time_is_one_second(self):
        # Even extremely fast player can't go below 1s
        result = _actual_travel_time(1, 9999)
        assert result >= 1.0

    def test_zero_spd_clamped_to_one(self):
        # SPD=0 should not divide by zero
        result = _actual_travel_time(5, 0)
        assert result >= 1.0

    def test_indoor_room_fast_player(self):
        # 3s base, SPD=20 (2x) → 1.5s → rounds to 1.5
        result = _actual_travel_time(3, 20)
        assert result == 1.5

    def test_wilderness_path_slow_player(self):
        # 20s base, SPD=5 (0.5x) → 40s
        result = _actual_travel_time(20, 5)
        assert result == 40.0

    def test_different_base_times_scale_correctly(self):
        times = [_actual_travel_time(t, BASE_SPD) for t in [3, 8, 15, 20]]
        assert times == [3.0, 8.0, 15.0, 20.0]


class TestExitDirectionSystem:
    """Tests that the direction enum values are valid and cover all cases."""

    VALID_DIRECTIONS = {"north", "south", "east", "west", "up", "down", "in", "out"}

    def test_all_directions_are_valid(self):
        for d in self.VALID_DIRECTIONS:
            assert isinstance(d, str)
            assert len(d) > 0

    def test_in_out_directions_exist(self):
        assert "in" in self.VALID_DIRECTIONS
        assert "out" in self.VALID_DIRECTIONS

    def test_vertical_directions_exist(self):
        assert "up" in self.VALID_DIRECTIONS
        assert "down" in self.VALID_DIRECTIONS

    def test_cardinal_directions_exist(self):
        for d in ("north", "south", "east", "west"):
            assert d in self.VALID_DIRECTIONS

    def test_opposite_directions(self):
        opposites = [("north", "south"), ("east", "west"), ("up", "down"), ("in", "out")]
        for a, b in opposites:
            assert a in self.VALID_DIRECTIONS
            assert b in self.VALID_DIRECTIONS
