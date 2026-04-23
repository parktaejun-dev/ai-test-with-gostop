from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ActionType(str, Enum):
    DIE = "die"
    DECLARE_CHONGTONG = "declare_chongtong"
    PLAY_CARD = "play_card"
    DECLARE_SHAKE = "declare_shake"
    CHOOSE_MATCH = "choose_match"
    DECLARE_BOMB = "declare_bomb"
    CHOOSE_GO_STOP = "choose_go_stop"
    MOVE_GUKJIN = "move_gukjin"
    PROPOSE_SHOWDOWN = "propose_showdown"
    ACCEPT_SHOWDOWN = "accept_showdown"
    REJECT_SHOWDOWN = "reject_showdown"


@dataclass(frozen=True, slots=True)
class Action:
    type: ActionType
    card_id: str | None = None
    month: int | None = None
    target_card_id: str | None = None
    revealed_card_ids: tuple[str, ...] = field(default_factory=tuple)
    showdown_payload: tuple[tuple[str, int], ...] = field(default_factory=tuple)
    choice: str | None = None

