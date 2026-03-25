"""Grab contest engine: competition window, dice resolution."""
from dataclasses import dataclass, field

from server.engine.dice import d20
from server.config import settings

FIRST_MOVER_RATE = 0.5   # +0.5 per second
FIRST_MOVER_CAP = 3.0    # max +3


@dataclass
class GrabParticipant:
    player_id: str
    attribute_modifier: int   # higher of SPD or LUK
    join_time: float          # Unix timestamp when they joined the contest
    dm_dice_bonus: int = 0    # from DM ruling dice_bonus field
    feasible: bool = True     # if DM ruled feasible=False, excluded from rolls


def first_mover_bonus(join_time: float, window_open_time: float) -> float:
    elapsed = join_time - window_open_time
    bonus = elapsed * FIRST_MOVER_RATE
    return min(FIRST_MOVER_CAP, max(0.0, bonus))


def roll_grab_contest(
    participants: list[GrabParticipant],
    window_open_time: float,
) -> tuple[str | None, dict[str, float]]:
    """
    Returns (winner_player_id, scores_dict).
    Server rolls d20 — DM provides only dice_bonus.
    Participants with feasible=False are excluded.
    """
    eligible = [p for p in participants if p.feasible]
    if not eligible:
        return None, {}

    scores: dict[str, float] = {}
    for p in eligible:
        roll = d20()
        fmb = first_mover_bonus(p.join_time, window_open_time)
        score = roll + p.attribute_modifier + fmb + p.dm_dice_bonus
        scores[p.player_id] = score

    max_score = max(scores.values())
    winners = [pid for pid, s in scores.items() if s == max_score]

    if len(winners) == 1:
        return winners[0], scores

    # Tiebreaker: re-roll among tied players
    tiebreak_scores: dict[str, int] = {pid: d20() for pid in winners}
    winner = max(tiebreak_scores, key=lambda k: tiebreak_scores[k])
    return winner, scores
