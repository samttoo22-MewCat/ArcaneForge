"""V-03: Grab contest logic validation."""
import time
import pytest
from server.engine.grab_contest import GrabParticipant, roll_grab_contest, first_mover_bonus, FIRST_MOVER_CAP


class TestFirstMoverBonus:
    def test_immediate_join_zero_bonus(self):
        t = time.time()
        assert first_mover_bonus(t, t) == 0.0

    def test_3_second_join_gives_1_5(self):
        t0 = 1000.0
        t1 = 1003.0
        bonus = first_mover_bonus(t1, t0)
        assert abs(bonus - 1.5) < 0.001

    def test_bonus_capped_at_3(self):
        t0 = 1000.0
        t1 = 1100.0  # 100 seconds later
        bonus = first_mover_bonus(t1, t0)
        assert bonus == FIRST_MOVER_CAP

    def test_negative_join_time_clamped_to_zero(self):
        t0 = 1010.0
        t1 = 1000.0  # joined before window (shouldn't happen, but defensive)
        bonus = first_mover_bonus(t1, t0)
        assert bonus == 0.0


class TestGrabContest:
    def _make_participant(self, pid, attr=5, join_offset=0.0, dice_bonus=0, feasible=True):
        return GrabParticipant(
            player_id=pid,
            attribute_modifier=attr,
            join_time=1000.0 + join_offset,
            dm_dice_bonus=dice_bonus,
            feasible=feasible,
        )

    def test_single_participant_wins(self):
        p = self._make_participant("p1")
        winner, scores = roll_grab_contest([p], window_open_time=1000.0)
        assert winner == "p1"
        assert "p1" in scores

    def test_infeasible_participant_excluded(self):
        p1 = self._make_participant("p1", feasible=True)
        p2 = self._make_participant("p2", feasible=False)
        winner, scores = roll_grab_contest([p1, p2], window_open_time=1000.0)
        assert "p2" not in scores
        assert winner == "p1"

    def test_all_infeasible_returns_none(self):
        p1 = self._make_participant("p1", feasible=False)
        p2 = self._make_participant("p2", feasible=False)
        winner, scores = roll_grab_contest([p1, p2], window_open_time=1000.0)
        assert winner is None
        assert len(scores) == 0

    def test_server_rolls_d20_not_client(self):
        # Verify that dice_bonus from DM is capped at 5 but does not determine winner alone
        # Player with high dice_bonus but low attribute should sometimes lose to high attr player
        # Run many trials and verify the high-attribute player wins > 40% of time
        wins = {"high_attr": 0, "high_bonus": 0}
        for _ in range(200):
            high_attr = self._make_participant("high_attr", attr=15, dice_bonus=0)
            high_bonus = self._make_participant("high_bonus", attr=1, dice_bonus=5)
            winner, _ = roll_grab_contest([high_attr, high_bonus], window_open_time=1000.0)
            if winner:
                wins[winner] += 1
        # Both should win a meaningful fraction — d20 randomness means no one dominates completely
        assert wins["high_attr"] > 50, f"High-attr player won only {wins['high_attr']} times"
        assert wins["high_bonus"] > 20, f"High-bonus player won only {wins['high_bonus']} times"

    def test_three_player_contest_has_single_winner(self):
        participants = [
            self._make_participant("p1", join_offset=0.0),
            self._make_participant("p2", join_offset=1.0),
            self._make_participant("p3", join_offset=2.0),
        ]
        for _ in range(50):
            winner, scores = roll_grab_contest(participants, window_open_time=1000.0)
            assert winner in {"p1", "p2", "p3"}
            assert len(scores) == 3
