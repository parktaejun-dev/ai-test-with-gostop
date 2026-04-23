from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from engine.actions import Action


class Phase(str, Enum):
    DEAL = "deal"
    CHONGTONG = "chongtong"
    PARTICIPATION = "participation"
    TURN_START = "turn_start"
    MAIN_ACTION = "main_action"
    SHOWDOWN_RESPONSE = "showdown_response"
    GO_STOP = "go_stop"
    FINISHED = "finished"


class EventType(str, Enum):
    DEAL = "deal"
    FLOOR_JOKER = "floor_joker"
    REDEAL = "redeal"
    CHONGTONG = "chongtong"
    DIE = "die"
    FORCED_GWANG_SELL = "forced_gwang_sell"
    SHAKE = "shake"
    BOMB = "bomb"
    JABOMB = "jabomb"
    TTADAK = "ttadak"
    JJOK = "jjok"
    PANSSURI = "panssuri"
    SHOWDOWN_PROPOSED = "showdown_proposed"
    SHOWDOWN_ACCEPTED = "showdown_accepted"
    SHOWDOWN_REJECTED = "showdown_rejected"
    SHOWDOWN_EVAL = "showdown_eval"
    NAGARI = "nagari"
    STOP = "stop"
    GO = "go"
    RESPONSIBILITY_DOKBAK = "responsibility_dokbak"


@dataclass(slots=True)
class SeatState:
    seat: int
    agent_name: str
    bankroll: int = 0
    hand: list[Any] = field(default_factory=list)
    captured: list[Any] = field(default_factory=list)
    moved_gukjin: bool = False
    go_count: int = 0
    declared_shake_months: list[int] = field(default_factory=list)
    shake_ready_months: set[int] = field(default_factory=set)
    bomb_months: list[int] = field(default_factory=list)
    hidden_chongtong_months: set[int] = field(default_factory=set)
    exposed_cards: set[str] = field(default_factory=set)
    legal_actions: list[Action] = field(default_factory=list)
    alive: bool = True
    died_voluntarily: bool = False
    forced_gwang_sell: bool = False
    last_die_hand: int | None = None
    empty_turn: bool = False
    explanation: str | None = None
    last_go_score: int = 0


@dataclass(slots=True)
class HandOutcome:
    hand_id: int = 0
    winner: int | None = None
    base_points: int = 0
    final_points: int = 0
    payout_deltas: dict[int, int] = field(default_factory=dict)
    carryover_consumed: int = 1
    nagari: bool = False
    showdown_success: bool = False
    chongtong: bool = False
    redeal: bool = False
    stop_declared: bool = False
    bomb_declared_by: int | None = None
    responsibility_source: int | None = None
    bak_flags: dict[int, list[str]] = field(default_factory=dict)


@dataclass(slots=True)
class PublicGameState:
    phase: Phase
    hand_id: int
    seat_id: int
    dealer_seat: int
    current_turn: int
    alive_seats: tuple[int, ...]
    exited_seat: int | None
    hand_cards: tuple[Any, ...]
    table_cards: tuple[Any, ...]
    captured_cards_public: dict[int, tuple[Any, ...]]
    scores_public: dict[int, int]
    go_counts_public: dict[int, int]
    bankrolls_public: dict[int, int]
    carryover_multiplier: int
    showdown_pending: bool
    showdown_proposer: int | None
    showdown_responses: dict[int, str]
    legal_actions: tuple[Action, ...]
    decision_seed: int


@dataclass(slots=True)
class GameConfig:
    initial_bankroll: int = 100_000
    stake_per_point: int = 100
    session_hands: int | None = None
    bust_stop_count: int = 2
    max_session_hands: int = 10_000
    layout_repetitions: int = 10
    max_carryover_multiplier: int = 64
    min_eval_hands: int = 10_000
    gwang_sell_unit: int = 3
    showdown_requires_unanimous: bool = True
    remote_eval_hands: int = 300
