from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass

from engine.actions import ActionType

from agents.base import Agent


def _rng(state) -> random.Random:
    return random.Random(state.decision_seed + (state.seat_id * 10_000))


def _first(actions, action_type: ActionType):
    for action in actions:
        if action.type == action_type:
            return action
    return None


def _hand_strength(state) -> int:
    """Evaluate hand quality for the participation (die/play) decision.

    Scores based on:
    - Table matches (cards in hand whose month appears on the table)
    - High-value cards (bright, animal, ribbon)
    - Pairs/triples in hand (potential bombs, shakes, or self-matching)
    Typical range: 0 ~ 30+.  A score below ~6 indicates a weak hand.
    """
    score = 0
    table_months = {card.month for card in state.table_cards}
    for card in state.hand_cards:
        if card.month in table_months:
            score += 2
        if getattr(card, "bright", False):
            score += 3
        elif getattr(card, "animal", False):
            score += 2
        elif getattr(card, "ribbon", False):
            score += 1
    month_counts = Counter(card.month for card in state.hand_cards if card.month > 0)
    for count in month_counts.values():
        if count >= 3:
            score += 4  # bomb / shake candidate
        elif count >= 2:
            score += 1
    return score


def _best_match_action(state):
    table_by_id = {card.id: card for card in state.table_cards}

    def score(action):
        card = table_by_id.get(action.target_card_id)
        if card is None:
            return -99
        value = 0
        value += 6 if getattr(card, "bright", False) else 0
        value += 4 if getattr(card, "animal", False) else 0
        value += 3 if getattr(card, "ribbon", False) else 0
        value += getattr(card, "junk_value", 0)
        return value

    return max(state.legal_actions, key=score)


def _best_card_action(state, prefer_month_repeat: bool = False):
    actions = [a for a in state.legal_actions if a.type in {ActionType.PLAY_CARD, ActionType.DECLARE_SHAKE}]
    if not actions:
        return state.legal_actions[0]
    table_months = {card.month for card in state.table_cards}
    hand_by_id = {card.id: card for card in state.hand_cards}
    def score(action):
        card = hand_by_id.get(action.card_id)
        if card is None:
            return -99
        value = 0
        if card.month in table_months:
            value += 5
        if action.type == ActionType.DECLARE_SHAKE:
            value += 6
        if prefer_month_repeat:
            value += sum(1 for other in state.hand_cards if other.month == card.month)
        value += getattr(card, "junk_value", 0)
        return value
    return max(actions, key=score)


@dataclass(frozen=True, slots=True)
class RandomAgent(Agent):
    def select_action(self, state):
        return _rng(state).choice(list(state.legal_actions))


@dataclass(frozen=True, slots=True)
class RuleBasedAgent(Agent):
    stop_threshold: int = 4
    die_threshold: int = 7

    def select_action(self, state):
        if all(action.type == ActionType.CHOOSE_MATCH for action in state.legal_actions):
            return _best_match_action(state)
        if state.phase.name == "PARTICIPATION":
            die_action = _first(state.legal_actions, ActionType.DIE)
            if die_action and _hand_strength(state) < self.die_threshold:
                return die_action
        if state.phase.name == "SHOWDOWN_RESPONSE":
            return _first(state.legal_actions, ActionType.REJECT_SHOWDOWN) or state.legal_actions[0]
        if state.phase.name == "GO_STOP":
            my_score = state.scores_public[state.seat_id]
            if my_score >= self.stop_threshold:
                return next(action for action in state.legal_actions if action.choice == "stop")
            return next(action for action in state.legal_actions if action.choice == "go")
        bomb = _first(state.legal_actions, ActionType.DECLARE_BOMB)
        if bomb is not None:
            return bomb
        move = _first(state.legal_actions, ActionType.MOVE_GUKJIN)
        if move is not None and state.scores_public[state.seat_id] < 3:
            return move
        return _best_card_action(state)


@dataclass(frozen=True, slots=True)
class GreedyProfitAgent(Agent):
    stop_threshold: int = 6
    die_threshold: int = 5

    def select_action(self, state):
        if all(action.type == ActionType.CHOOSE_MATCH for action in state.legal_actions):
            return _best_match_action(state)
        if state.phase.name == "PARTICIPATION":
            die_action = _first(state.legal_actions, ActionType.DIE)
            if die_action and _hand_strength(state) < self.die_threshold:
                return die_action
        if state.phase.name == "SHOWDOWN_RESPONSE":
            return _first(state.legal_actions, ActionType.REJECT_SHOWDOWN) or state.legal_actions[0]
        if state.phase.name == "GO_STOP":
            if state.scores_public[state.seat_id] >= self.stop_threshold:
                return next(action for action in state.legal_actions if action.choice == "stop")
            return next(action for action in state.legal_actions if action.choice == "go")
        bomb = _first(state.legal_actions, ActionType.DECLARE_BOMB)
        if bomb is not None:
            return bomb
        showdown = _first(state.legal_actions, ActionType.PROPOSE_SHOWDOWN)
        if showdown is not None and state.scores_public[state.seat_id] <= 1:
            return showdown
        return _best_card_action(state, prefer_month_repeat=True)


@dataclass(frozen=True, slots=True)
class SurvivalAgent(Agent):
    stop_threshold: int = 3
    die_threshold: int = 9

    def select_action(self, state):
        if all(action.type == ActionType.CHOOSE_MATCH for action in state.legal_actions):
            return _best_match_action(state)
        if state.phase.name == "PARTICIPATION":
            die_action = _first(state.legal_actions, ActionType.DIE)
            if die_action and _hand_strength(state) < self.die_threshold:
                return die_action
        if state.phase.name == "SHOWDOWN_RESPONSE":
            return _first(state.legal_actions, ActionType.ACCEPT_SHOWDOWN) or state.legal_actions[0]
        if state.phase.name == "GO_STOP":
            if state.scores_public[state.seat_id] >= self.stop_threshold:
                return next(action for action in state.legal_actions if action.choice == "stop")
            return next(action for action in state.legal_actions if action.choice == "go")
        move = _first(state.legal_actions, ActionType.MOVE_GUKJIN)
        if move is not None:
            return move
        shake = _first(state.legal_actions, ActionType.DECLARE_SHAKE)
        if shake is not None and state.bankrolls_public[state.seat_id] > 0:
            return shake
        return _best_card_action(state)
