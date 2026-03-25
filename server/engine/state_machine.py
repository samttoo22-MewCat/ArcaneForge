"""Battle state machine."""
from enum import Enum


class BattleState(str, Enum):
    IDLE = "idle"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    ROUND_RESOLVING = "round_resolving"
    ENDED = "ended"


VALID_TRANSITIONS: dict[BattleState, set[BattleState]] = {
    BattleState.IDLE: {BattleState.INITIALIZING},
    BattleState.INITIALIZING: {BattleState.ACTIVE, BattleState.IDLE},
    BattleState.ACTIVE: {BattleState.ROUND_RESOLVING, BattleState.ENDED},
    BattleState.ROUND_RESOLVING: {BattleState.ACTIVE, BattleState.ENDED},
    BattleState.ENDED: set(),
}


class BattleStateMachine:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.state = BattleState.IDLE

    def transition(self, new_state: BattleState) -> None:
        allowed = VALID_TRANSITIONS.get(self.state, set())
        if new_state not in allowed:
            raise ValueError(
                f"[{self.room_id}] Invalid transition {self.state} -> {new_state}"
            )
        self.state = new_state

    def is_active(self) -> bool:
        return self.state in (BattleState.ACTIVE, BattleState.ROUND_RESOLVING)
