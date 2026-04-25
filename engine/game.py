from __future__ import annotations

import copy
import random
from collections import defaultdict
from dataclasses import dataclass, field

from engine.actions import Action, ActionType
from engine.rules import (
    determine_shake_ready_months,
    has_chongtong,
    independent_triples,
    take_pi_from_captured,
)
from engine.scoring import apply_go_bonus, score_captured_cards
from engine.state import EventType, GameConfig, HandOutcome, Phase, PublicGameState, SeatState
from logs.recorder import LogRecorder


@dataclass(slots=True)
class HandContext:
    hand_id: int
    dealer_seat: int
    carryover_multiplier: int
    table_cards: list
    deck: list
    current_turn: int
    phase: Phase
    showdown_pending: bool = False
    showdown_proposer: int | None = None
    showdown_responses: dict[int, str] = field(default_factory=dict)
    exited_seat: int | None = None
    bomb_declared_by: int | None = None
    bomb_declared_seats: set[int] = field(default_factory=set)
    responsibility_source: int | None = None
    reason: str | None = None
    stop_candidate: int | None = None
    showdown_enabled: bool = True
    showdown_evaluations: list[dict] = field(default_factory=list)
    table_source_seats: dict[str, int] = field(default_factory=dict)
    pending_responsibility: dict | None = None
    showdown_attempted_seats: set[int] = field(default_factory=set)
    simulation_mode: bool = False
    simulation_remote_cache_miss: bool = False


@dataclass(slots=True)
class ResolutionInfo:
    source: str
    score_before: int
    score_after: int
    table_added: bool = False
    captured_any: bool = False
    used_choice: bool = False
    ttadak: bool = False
    panssuri: bool = False
    target_card_id: str | None = None
    target_source_seat: int | None = None


class GameEngine:
    def __init__(self, config: GameConfig, recorder: LogRecorder | None = None):
        self.config = config
        self.recorder = recorder or LogRecorder()

    def play_session(self, agents: dict[int, object], session_seed: int, num_hands: int | None = None) -> dict:
        from engine.cards import build_deck

        rng = random.Random(session_seed)
        hand_limit = num_hands if num_hands is not None else (self.config.session_hands or self.config.max_session_hands)
        seats = {
            seat: SeatState(
                seat=seat,
                agent_name=getattr(agent, "name", type(agent).__name__),
                bankroll=self.config.initial_bankroll,
            )
            for seat, agent in agents.items()
        }
        dealer = rng.randrange(4)
        carryover = 1
        session_logs = []
        hand_outcomes = []
        stopped_reason = "hand_limit"
        hand_id = 1
        while len(hand_outcomes) < hand_limit:
            deck = build_deck()
            rng.shuffle(deck)
            outcome, dealer, carryover, hand_logs = self._play_hand(
                rng=rng,
                hand_id=hand_id,
                deck=deck,
                dealer=dealer,
                carryover=carryover,
                seats=seats,
                agents=agents,
            )
            session_logs.extend(hand_logs)
            if outcome.redeal:
                continue
            hand_outcomes.append(outcome)
            hand_id += 1
            if self._bankrupt_count(seats) >= self.config.bust_stop_count:
                stopped_reason = "bust_stop"
                break
        return {
            "seats": seats,
            "hand_outcomes": hand_outcomes,
            "logs": session_logs,
            "initial_bankroll": self.config.initial_bankroll,
            "session_finished_reason": stopped_reason,
            "session_hands_played": len(hand_outcomes),
        }

    def _play_hand(
        self,
        rng: random.Random,
        hand_id: int,
        deck: list,
        dealer: int,
        carryover: int,
        seats: dict[int, SeatState],
        agents: dict[int, object],
    ):
        from engine.cards import JOKER_MONTH

        for seat in seats.values():
            seat.hand.clear()
            seat.captured.clear()
            seat.moved_gukjin = False
            seat.go_count = 0
            seat.declared_shake_months.clear()
            seat.shake_ready_months.clear()
            seat.bomb_months.clear()
            seat.hidden_chongtong_months.clear()
            seat.exposed_cards.clear()
            seat.legal_actions.clear()
            seat.alive = True
            seat.died_voluntarily = False
            seat.forced_gwang_sell = False
            seat.empty_turn = False
            seat.explanation = None
            seat.last_go_score = 0

        table_cards = [deck.pop() for _ in range(8)]
        for seat in range(4):
            seats[seat].hand.extend(deck.pop() for _ in range(7))

        logs: list[dict] = []
        floor_joker_count = self._resolve_floor_jokers(dealer, table_cards, deck, seats)
        if floor_joker_count:
            logs.append(self.recorder.event(hand_id, dealer, EventType.FLOOR_JOKER, {"count": floor_joker_count}))

        table_month_counts = defaultdict(int)
        for card in table_cards:
            table_month_counts[card.month] += 1
        if any(count >= 4 and month > 0 for month, count in table_month_counts.items()):
            logs.append(self.recorder.event(hand_id, dealer, EventType.REDEAL, {"reason": "table_four_of_month"}))
            return HandOutcome(hand_id=hand_id, nagari=False, redeal=True), dealer, carryover, logs

        chongtong_holders = {}
        for seat_id in range(4):
            months = has_chongtong(seats[seat_id].hand)
            if months:
                seats[seat_id].hidden_chongtong_months = set(months)
                chongtong_holders[seat_id] = months
        if len(chongtong_holders) > 1:
            logs.append(self.recorder.event(hand_id, dealer, EventType.REDEAL, {"reason": "multiple_chongtong"}))
            return HandOutcome(hand_id=hand_id, nagari=False, redeal=True), dealer, carryover, logs
        if len(chongtong_holders) == 1:
            winner = next(iter(chongtong_holders))
            payout = self._settle_simple_chongtong(seats, winner, carryover)
            outcome = HandOutcome(
                hand_id=hand_id,
                winner=winner,
                base_points=10,
                final_points=10,
                payout_deltas=payout,
                carryover_consumed=carryover,
                chongtong=True,
            )
            for seat_id, delta in payout.items():
                seats[seat_id].bankroll += delta
            logs.append(self.recorder.event(hand_id, winner, EventType.CHONGTONG, {"months": sorted(chongtong_holders[winner]), "payout_deltas": payout}))
            return outcome, winner, 1, logs

        participation_order = [((dealer + offset) % 4) for offset in range(1, 4)]
        voluntary_die = None
        for seat_id in participation_order[:2]:
            seat = seats[seat_id]
            if seat.last_die_hand == hand_id - 1:
                continue
            action = self._choose_action(
                agents[seat_id],
                seats=seats,
                seat_id=seat_id,
                phase=Phase.PARTICIPATION,
                dealer=dealer,
                hand_id=hand_id,
                current_turn=seat_id,
                table_cards=table_cards,
                carryover_multiplier=carryover,
                legal_actions=[Action(ActionType.DIE), Action(ActionType.PLAY_CARD)],
                decision_seed=rng.randrange(2**31),
                exited_seat=voluntary_die,
            )
            if action.type == ActionType.DIE:
                seat.alive = False
                seat.died_voluntarily = True
                seat.last_die_hand = hand_id
                voluntary_die = seat_id
                deck.extend(seat.hand)
                rng.shuffle(deck)
                seat.hand.clear()
                logs.append(self.recorder.event(hand_id, seat_id, EventType.DIE, {}))
                break

        if voluntary_die is None:
            forced = participation_order[2]
            seats[forced].alive = False
            seats[forced].forced_gwang_sell = True
            sell_count = self._gwang_sell_count(seats[forced].hand)
            shake_count = independent_triples(seats[forced].hand)
            payout = self.config.gwang_sell_unit * sell_count * (2**shake_count)
            payers = [seat_id for seat_id in range(4) if seat_id != forced]
            split = payout // len(payers) if payers else 0
            for payer in payers:
                seats[payer].bankroll -= split
                seats[forced].bankroll += split
            deck.extend(seats[forced].hand)
            rng.shuffle(deck)
            seats[forced].hand.clear()
            logs.append(
                self.recorder.event(
                    hand_id,
                    forced,
                    EventType.FORCED_GWANG_SELL,
                    {"sell_count": sell_count, "shake_count": shake_count, "payout": payout},
                )
            )
            voluntary_die = forced

        context = HandContext(
            hand_id=hand_id,
            dealer_seat=dealer,
            carryover_multiplier=carryover,
            table_cards=table_cards,
            deck=deck,
            current_turn=dealer,
            phase=Phase.TURN_START,
            showdown_responses={},
            exited_seat=voluntary_die,
        )
        outcome = self._run_context_until_done(rng, context, seats, agents, logs)
        self._emit_showdown_evaluations(context, outcome, logs)
        next_dealer = outcome.winner if outcome.winner is not None else dealer
        max_carryover = max(1, self.config.max_carryover_multiplier)
        next_carryover = 1 if outcome.winner is not None else min(carryover * 2, max_carryover)
        return outcome, next_dealer, next_carryover, logs

    def _run_context_until_done(self, rng, context: HandContext, seats, agents, logs: list[dict]) -> HandOutcome:
        max_turns = 400
        while max_turns > 0:
            max_turns -= 1
            alive_order = [seat_id for seat_id in range(4) if seats[seat_id].alive]
            if len(alive_order) <= 1:
                return self._resolve_nagari_by_score(context, seats, reason="only_one_alive")
            current = context.current_turn
            if not seats[current].alive:
                context.current_turn = self._next_alive(current, seats)
                continue
            self._refresh_shake_ready(seats[current], context.table_cards)
            turn_logs, done, outcome = self._play_turn(rng, context, seats, agents, current)
            logs.extend(turn_logs)
            if done:
                if outcome.hand_id == 0:
                    outcome.hand_id = context.hand_id
                return outcome
            if context.current_turn == current:
                context.current_turn = self._next_alive(current, seats)

        logs.append(self.recorder.event(context.hand_id, context.current_turn, EventType.NAGARI, {"reason": "turn_limit"}))
        return self._resolve_nagari_by_score(context, seats, reason="turn_limit")

    def _play_turn(self, rng, context: HandContext, seats, agents, current):
        logs = []
        seat = seats[current]
        alive = tuple(idx for idx, state in seats.items() if state.alive)
        score_now = score_captured_cards(seat.captured, seat.moved_gukjin)

        if context.showdown_pending:
            legal = [Action(ActionType.ACCEPT_SHOWDOWN), Action(ActionType.REJECT_SHOWDOWN)]
            action = self._choose_action(
                agents[current],
                seats,
                current,
                Phase.SHOWDOWN_RESPONSE,
                context.dealer_seat,
                context.hand_id,
                current,
                context.table_cards,
                context.carryover_multiplier,
                legal,
                rng.randrange(2**31),
                context.exited_seat,
                context,
            )
            if action.type == ActionType.ACCEPT_SHOWDOWN:
                context.showdown_responses[current] = "accept"
                logs.append(self.recorder.event(context.hand_id, current, EventType.SHOWDOWN_ACCEPTED, {}))
                responders = [seat_id for seat_id in alive if seat_id != context.showdown_proposer]
                if self.config.showdown_requires_unanimous:
                    success = all(context.showdown_responses.get(seat_id) == "accept" for seat_id in responders)
                else:
                    success = any(context.showdown_responses.get(seat_id) == "accept" for seat_id in responders)
                if success:
                    logs.append(self.recorder.event(context.hand_id, current, EventType.NAGARI, {"reason": "showdown_success"}))
                    outcome = self._resolve_nagari_by_score(context, seats, reason="showdown_success")
                    outcome.showdown_success = True
                    return logs, True, outcome
                return logs, False, None
            context.showdown_responses[current] = "reject"
            if self.config.showdown_requires_unanimous:
                responders = [seat_id for seat_id in alive if seat_id != context.showdown_proposer]
                remaining = [seat_id for seat_id in responders if seat_id not in context.showdown_responses]
                if len(remaining) == 1:
                    auto_accept = remaining[0]
                    context.showdown_responses[auto_accept] = "accept"
                    logs.append(self.recorder.event(context.hand_id, auto_accept, EventType.SHOWDOWN_ACCEPTED, {"auto": True}))
            else:
                responders = [seat_id for seat_id in alive if seat_id != context.showdown_proposer]
                if any(context.showdown_responses.get(seat_id) == "accept" for seat_id in responders):
                    return logs, False, None
                if any(seat_id not in context.showdown_responses for seat_id in responders):
                    return logs, False, None
            proposer = context.showdown_proposer
            context.showdown_pending = False
            context.showdown_proposer = None
            context.showdown_responses = {}
            if proposer is not None:
                context.current_turn = proposer
            logs.append(self.recorder.event(context.hand_id, current, EventType.SHOWDOWN_REJECTED, {}))
            return logs, False, None

        if seat.empty_turn or not seat.hand:
            if context.deck:
                self._draw_and_resolve(rng, seat, seats, agents, context, logs, source="empty_turn")
            else:
                logs.append(self.recorder.event(context.hand_id, current, EventType.NAGARI, {"reason": "empty_turn_no_deck"}))
                return logs, True, self._resolve_nagari_by_score(context, seats, reason="empty_turn_no_deck")
            score_after = score_captured_cards(seat.captured, seat.moved_gukjin)
            done, outcome = self._resolve_go_stop_decision(
                rng,
                context,
                seats,
                agents,
                current,
                score_after,
                logs,
                empty_turn=True,
            )
            if done:
                return logs, True, outcome
            if not context.deck:
                reason = self._empty_deck_reason(seats, alive)
                logs.append(self.recorder.event(context.hand_id, current, EventType.NAGARI, {"reason": reason}))
                context.pending_responsibility = None
                return logs, True, self._resolve_nagari_by_score(context, seats, reason=reason)
            return logs, False, None

        legal = self._legal_actions_for_turn(seat, context, seats, score_now)
        action = self._choose_action(
            agents[current],
            seats,
            current,
            Phase.TURN_START,
            context.dealer_seat,
            context.hand_id,
            current,
            context.table_cards,
            context.carryover_multiplier,
            legal,
            rng.randrange(2**31),
            context.exited_seat,
            context,
        )

        if action.type == ActionType.MOVE_GUKJIN:
            seat.moved_gukjin = True
            legal = [item for item in legal if item.type != ActionType.MOVE_GUKJIN]
            action = self._choose_action(
                agents[current],
                seats,
                current,
                Phase.MAIN_ACTION,
                context.dealer_seat,
                context.hand_id,
                current,
                context.table_cards,
                context.carryover_multiplier,
                legal,
                rng.randrange(2**31),
                context.exited_seat,
                context,
            )

        if action.type == ActionType.PROPOSE_SHOWDOWN:
            counterfactual = self._evaluate_showdown_counterfactual(rng, context, seats, agents, current)
            context.showdown_evaluations.append(counterfactual)
            context.showdown_attempted_seats.add(current)
            context.showdown_pending = True
            context.showdown_proposer = current
            context.showdown_responses = {current: "accept"}
            logs.append(self.recorder.event(context.hand_id, current, EventType.SHOWDOWN_PROPOSED, {"payload": action.showdown_payload}))
            return logs, False, None

        if action.type == ActionType.DECLARE_BOMB:
            bomb_type = "jabomb" if action.month in seat.hidden_chongtong_months else "bomb"
            self._resolve_bomb(rng, seat, seats, agents, context, action.month, logs, bomb_type)
            context.bomb_declared_by = current
            context.bomb_declared_seats.add(current)
        else:
            if action.type == ActionType.DECLARE_SHAKE:
                month = self._card_from_hand(seat, action.card_id).month
                if month not in seat.declared_shake_months:
                    seat.declared_shake_months.append(month)
                logs.append(self.recorder.event(context.hand_id, current, EventType.SHAKE, {"month": month}))
            if action.type in {ActionType.PLAY_CARD, ActionType.DECLARE_SHAKE}:
                self._resolve_play_card(rng, seat, seats, agents, context, action, logs)

        score_after = score_captured_cards(seat.captured, seat.moved_gukjin)
        done, outcome = self._resolve_go_stop_decision(
            rng,
            context,
            seats,
            agents,
            current,
            score_after,
            logs,
        )
        if done:
            return logs, True, outcome

        if not context.deck:
            reason = self._empty_deck_reason(seats, alive)
            logs.append(self.recorder.event(context.hand_id, current, EventType.NAGARI, {"reason": reason}))
            context.pending_responsibility = None
            return logs, True, self._resolve_nagari_by_score(context, seats, reason=reason)

        context.pending_responsibility = None
        return logs, False, None

    def _resolve_play_card(self, rng, seat, seats, agents, context, action, logs):
        card = self._remove_card_from_hand(seat, action.card_id)
        initial_month_matches = [table.id for table in context.table_cards if table.month == card.month and card.month > 0]
        hand_result = self._resolve_single_card(rng, seat, seats, context, agents, logs, card, source="hand")
        if hand_result.target_source_seat is not None and hand_result.score_before < 3 <= hand_result.score_after:
            source_seat = hand_result.target_source_seat
            if seat.seat == self._next_alive(source_seat, seats) and not hand_result.used_choice:
                context.pending_responsibility = {
                    "source": source_seat,
                    "winner": seat.seat,
                    "target_card_id": hand_result.target_card_id,
                    "qualifying_score": hand_result.score_after,
                }
        if context.deck:
            draw_result, invalidates = self._draw_and_resolve(rng, seat, seats, agents, context, logs, source="deck")
            if (
                len(initial_month_matches) == 2
                and hand_result.target_card_id in initial_month_matches
                and draw_result.target_card_id in initial_month_matches
                and draw_result.target_card_id != hand_result.target_card_id
            ):
                self._take_pi_from_opponents(seat.seat, seats, 1)
                logs.append(self.recorder.event(context.hand_id, seat.seat, EventType.JJOK, {"month": card.month}))
            if context.pending_responsibility:
                if invalidates:
                    context.pending_responsibility = None
                elif draw_result.captured_any or draw_result.used_choice or draw_result.ttadak or draw_result.panssuri:
                    context.pending_responsibility = None
                elif draw_result.score_after != context.pending_responsibility["qualifying_score"]:
                    context.pending_responsibility = None
        if not seat.hand:
            seat.empty_turn = True

    def _resolve_single_card(self, rng, seat, seats, context, agents, logs, card, source) -> ResolutionInfo:
        score_before = score_captured_cards(seat.captured, seat.moved_gukjin)
        month_matches = [table for table in context.table_cards if table.month == card.month and card.month > 0]
        if not month_matches:
            context.table_cards.append(card)
            if source == "hand":
                context.table_source_seats[card.id] = seat.seat
            return ResolutionInfo(source=source, score_before=score_before, score_after=score_before, table_added=True)
        if len(month_matches) == 3:
            for match in month_matches:
                context.table_cards.remove(match)
                context.table_source_seats.pop(match.id, None)
                seat.captured.append(match)
            seat.captured.append(card)
            self._take_pi_from_opponents(seat.seat, seats, 1)
            logs.append(self.recorder.event(context.hand_id, seat.seat, EventType.TTADAK, {"source": source, "month": card.month}))
            score_after = score_captured_cards(seat.captured, seat.moved_gukjin)
            return ResolutionInfo(
                source=source,
                score_before=score_before,
                score_after=score_after,
                captured_any=True,
                ttadak=True,
            )

        used_choice = len(month_matches) > 1
        if used_choice:
            legal = [Action(ActionType.CHOOSE_MATCH, target_card_id=match.id) for match in month_matches]
            chosen = self._choose_action(
                agents[seat.seat],
                seats,
                seat.seat,
                Phase.MAIN_ACTION,
                context.dealer_seat,
                context.hand_id,
                context.current_turn,
                context.table_cards,
                context.carryover_multiplier,
                legal,
                rng.randrange(2**31),
                context.exited_seat,
                context,
            )
            target = next((match for match in month_matches if match.id == chosen.target_card_id), month_matches[0])
        else:
            target = month_matches[0]
        target_source = context.table_source_seats.pop(target.id, None)
        context.table_cards.remove(target)
        seat.captured.extend([target, card])
        score_after = score_captured_cards(seat.captured, seat.moved_gukjin)
        result = ResolutionInfo(
            source=source,
            score_before=score_before,
            score_after=score_after,
            captured_any=True,
            used_choice=used_choice,
            target_card_id=target.id,
            target_source_seat=target_source,
        )
        if not context.table_cards:
            self._take_pi_from_opponents(seat.seat, seats, 1)
            logs.append(self.recorder.event(context.hand_id, seat.seat, EventType.PANSSURI, {"source": source}))
            result.panssuri = True
            result.score_after = score_captured_cards(seat.captured, seat.moved_gukjin)
        return result

    def _resolve_bomb(self, rng, seat, seats, agents, context, month, logs, bomb_type):
        hand_matches = [card for card in seat.hand if card.month == month]
        table_matches = [card for card in context.table_cards if card.month == month]
        needed_hand = 3
        for card in hand_matches[:needed_hand]:
            seat.hand.remove(card)
            seat.captured.append(card)
        for card in table_matches[:1]:
            context.table_cards.remove(card)
            context.table_source_seats.pop(card.id, None)
            seat.captured.append(card)
        seat.bomb_months.append(month)
        self._take_pi_from_opponents(seat.seat, seats, 2)
        logs.append(self.recorder.event(context.hand_id, seat.seat, EventType.JABOMB if bomb_type == "jabomb" else EventType.BOMB, {"month": month}))
        if context.deck:
            self._draw_and_resolve(rng, seat, seats, agents, context, logs, source="deck")
        if not seat.hand:
            seat.empty_turn = True

    def _take_pi_from_opponents(self, winner_seat: int, seats, count: int):
        from engine.cards import CARDS_BY_CODE

        for seat_id, state in seats.items():
            if seat_id == winner_seat or not state.alive:
                continue
            result = take_pi_from_captured(state.captured, count)
            for card_id in result.taken_ids:
                seats[winner_seat].captured.append(CARDS_BY_CODE[card_id])

    def _settle_hand(
        self,
        context: HandContext,
        seats: dict[int, SeatState],
        winner: int,
        logs: list[dict] | None = None,
        *,
        stop_declared: bool = True,
    ) -> HandOutcome:
        alive = [seat_id for seat_id, seat in seats.items() if seat.alive]
        winner_state = seats[winner]
        base_score = score_captured_cards(winner_state.captured, winner_state.moved_gukjin)
        winner_breakdown = score_captured_cards(winner_state.captured, winner_state.moved_gukjin, return_breakdown=True)
        final_points = apply_go_bonus(base_score, winner_state.go_count)
        if winner in context.bomb_declared_seats:
            final_points *= 2
        final_points *= 2 ** len(winner_state.declared_shake_months)
        payout_deltas = {seat_id: 0 for seat_id in seats}
        bak_flags = {}
        for seat_id in alive:
            if seat_id == winner:
                continue
            loser = seats[seat_id]
            multiplier = 1
            flags = []
            captured_score = score_captured_cards(loser.captured, loser.moved_gukjin, return_breakdown=True)
            if stop_declared and winner_breakdown["junk"] > 0 and captured_score["pi_count"] <= 5:
                multiplier *= 2
                flags.append("pi_bak")
            if stop_declared and winner_breakdown["bright"] > 0 and captured_score["bright_count"] == 0:
                multiplier *= 2
                flags.append("bright_bak")
            if stop_declared and loser.go_count > 0:
                multiplier *= 2
                flags.append("go_bak")
            loss = final_points * multiplier * self.config.stake_per_point * context.carryover_multiplier
            payout_deltas[seat_id] -= loss
            payout_deltas[winner] += loss
            bak_flags[seat_id] = flags
        if context.responsibility_source in alive and context.responsibility_source != winner:
            source = context.responsibility_source
            transferred = {}
            for seat_id in alive:
                if seat_id in {winner, source}:
                    continue
                transfer = -payout_deltas[seat_id]
                if transfer <= 0:
                    continue
                payout_deltas[seat_id] = 0
                payout_deltas[source] -= transfer
                transferred[seat_id] = transfer
            if transferred and logs is not None:
                logs.append(
                    self.recorder.event(
                        context.hand_id,
                        source,
                        EventType.RESPONSIBILITY_DOKBAK,
                        {"winner": winner, "transferred": transferred},
                    )
                )
        for seat_id, delta in payout_deltas.items():
            seats[seat_id].bankroll += delta
        return HandOutcome(
            hand_id=context.hand_id,
            winner=winner,
            base_points=base_score,
            final_points=final_points,
            payout_deltas=payout_deltas,
            carryover_consumed=context.carryover_multiplier,
            stop_declared=stop_declared,
            bomb_declared_by=winner if winner in context.bomb_declared_seats else None,
            responsibility_source=context.responsibility_source,
            bak_flags=bak_flags,
        )

    def _determine_nagari_winner(self, seats: dict[int, SeatState], alive_order: list[int]) -> int | None:
        if not alive_order:
            return None
        return max(
            alive_order,
            key=lambda seat_id: (
                score_captured_cards(seats[seat_id].captured, seats[seat_id].moved_gukjin),
                seats[seat_id].go_count,
                seat_id,
            ),
        )

    def _resolve_nagari_by_score(self, context: HandContext, seats: dict[int, SeatState], reason: str) -> HandOutcome:
        winner = self._determine_nagari_winner(seats, [seat_id for seat_id, state in seats.items() if state.alive])
        if winner is None:
            return HandOutcome(hand_id=context.hand_id, nagari=True)
        outcome = self._settle_hand(context, seats, winner, stop_declared=False)
        outcome.nagari = True
        return outcome

    def _settle_simple_chongtong(self, seats, winner, carryover_multiplier):
        payout = {seat_id: 0 for seat_id in seats}
        gain = 10 * self.config.stake_per_point * carryover_multiplier
        for seat_id in seats:
            if seat_id == winner:
                continue
            payout[seat_id] -= gain
            payout[winner] += gain
        return payout

    def _gwang_sell_count(self, hand) -> int:
        from engine.cards import JOKER_MONTH

        bright_cards = [card for card in hand if getattr(card, "bright", False)]
        bright_count = len(bright_cards)
        has_non_rain_bright = any(
            not getattr(card, "is_rain_bright", False) for card in bright_cards
        )
        if bright_count == 0 or not has_non_rain_bright:
            return 0
        sellable_extras = sum(
            1
            for card in hand
            if getattr(card, "is_double_pi", False) or card.month == JOKER_MONTH
        )
        return bright_count + sellable_extras

    def _bankrupt_count(self, seats: dict[int, SeatState]) -> int:
        return sum(1 for seat in seats.values() if seat.bankroll <= 0)

    def _resolve_floor_jokers(self, dealer: int, table_cards: list, deck: list, seats: dict[int, SeatState]) -> int:
        from engine.cards import JOKER_MONTH

        floor_jokers = [card for card in table_cards if card.month == JOKER_MONTH]
        resolved_count = 0
        for card in floor_jokers:
            table_cards.remove(card)
            seats[dealer].captured.append(card)
            resolved_count += 1
            while deck:
                replacement = deck.pop()
                if replacement.month == JOKER_MONTH:
                    seats[dealer].captured.append(replacement)
                    resolved_count += 1
                    continue
                table_cards.append(replacement)
                break
        return resolved_count

    def _next_alive(self, current, seats):
        seat = current
        while True:
            seat = (seat + 1) % 4
            if seats[seat].alive:
                return seat

    def _refresh_shake_ready(self, seat: SeatState, table_cards):
        seat.shake_ready_months.update(determine_shake_ready_months(seat.hand, table_cards))

    def _can_offer_go_stop(self, seat: SeatState, score_after: int) -> bool:
        return score_after >= 3 and score_after > seat.last_go_score

    def _empty_deck_reason(self, seats, alive) -> str:
        if any(score_captured_cards(seats[seat_id].captured, seats[seat_id].moved_gukjin) >= 3 and seats[seat_id].go_count > 0 for seat_id in alive):
            return "go_without_progress"
        return "deck_exhausted"

    def _resolve_go_stop_decision(self, rng, context, seats, agents, current, score_after: int, logs, *, empty_turn: bool = False):
        seat = seats[current]
        if not self._can_offer_go_stop(seat, score_after):
            return False, None
        stop_action = self._choose_action(
            agents[current],
            seats,
            current,
            Phase.GO_STOP,
            context.dealer_seat,
            context.hand_id,
            current,
            context.table_cards,
            context.carryover_multiplier,
            [Action(ActionType.CHOOSE_GO_STOP, choice="go"), Action(ActionType.CHOOSE_GO_STOP, choice="stop")],
            rng.randrange(2**31),
            context.exited_seat,
            context,
        )
        if stop_action.choice == "stop":
            if context.pending_responsibility and context.pending_responsibility.get("winner") == current:
                context.responsibility_source = context.pending_responsibility["source"]
            outcome = self._settle_hand(context, seats, current, logs)
            logs.append(
                self.recorder.event(
                    context.hand_id,
                    current,
                    EventType.STOP,
                    {
                        "score": score_after,
                        "empty_turn": empty_turn,
                        "payout_deltas": outcome.payout_deltas,
                        "final_points": outcome.final_points,
                        "bak_flags": outcome.bak_flags,
                        "carryover_consumed": outcome.carryover_consumed,
                    },
                )
            )
            return True, outcome
        seat.go_count += 1
        seat.last_go_score = score_after
        context.pending_responsibility = None
        logs.append(self.recorder.event(context.hand_id, current, EventType.GO, {"go_count": seat.go_count}))
        return False, None

    def _legal_actions_for_turn(self, seat: SeatState, context: HandContext, seats, score_now: int):
        from engine.cards import GUKJIN_CARD

        legal = []
        current_ready_months = determine_shake_ready_months(seat.hand, context.table_cards)
        if any(card.id == GUKJIN_CARD.id for card in seat.captured) and not seat.moved_gukjin:
            legal.append(Action(ActionType.MOVE_GUKJIN))
        for card in seat.hand:
            legal.append(Action(ActionType.PLAY_CARD, card_id=card.id))
            if card.month in current_ready_months and card.month not in seat.declared_shake_months:
                legal.append(Action(ActionType.DECLARE_SHAKE, card_id=card.id))
        for month in sorted({card.month for card in seat.hand if card.month > 0}):
            hand_count = sum(1 for card in seat.hand if card.month == month)
            table_count = sum(1 for card in context.table_cards if card.month == month)
            if hand_count >= 3 and table_count == 1:
                legal.append(Action(ActionType.DECLARE_BOMB, month=month))
            if month in seat.hidden_chongtong_months and hand_count >= 3 and table_count == 1:
                legal.append(Action(ActionType.DECLARE_BOMB, month=month))
        if self._showdown_is_eligible(context, seats, seat.seat):
            legal.append(Action(ActionType.PROPOSE_SHOWDOWN))
        return legal

    def _showdown_card_delta(self, seat_id: int, seats, context: HandContext, card) -> int:
        from engine.cards import JOKER_MONTH

        seat = seats[seat_id]
        before = score_captured_cards(seat.captured, seat.moved_gukjin)
        if card.month == JOKER_MONTH:
            after = score_captured_cards((*seat.captured, card), seat.moved_gukjin)
            return after - before
        month_matches = [table for table in context.table_cards if table.month == card.month and card.month > 0]
        if not month_matches:
            return 0
        if len(month_matches) == 3:
            sim_seats = copy.deepcopy(seats)
            sim_context = copy.deepcopy(context)
            sim_seat = sim_seats[seat_id]
            for match in [table for table in sim_context.table_cards if table.month == card.month]:
                sim_context.table_cards.remove(match)
                sim_seat.captured.append(match)
            sim_seat.captured.append(card)
            self._take_pi_from_opponents(seat_id, sim_seats, 1)
            after = score_captured_cards(sim_seat.captured, sim_seat.moved_gukjin)
            return after - before
        best_delta = 0
        for target in month_matches:
            sim_seats = copy.deepcopy(seats)
            sim_context = copy.deepcopy(context)
            sim_seat = sim_seats[seat_id]
            sim_target = next(table for table in sim_context.table_cards if table.id == target.id)
            sim_context.table_cards.remove(sim_target)
            sim_seat.captured.extend([sim_target, card])
            if not sim_context.table_cards:
                self._take_pi_from_opponents(seat_id, sim_seats, 1)
            after = score_captured_cards(sim_seat.captured, sim_seat.moved_gukjin)
            best_delta = max(best_delta, after - before)
        return best_delta

    def _showdown_is_eligible(self, context: HandContext, seats, current: int) -> bool:
        # Netmarble-style showdown only appears on the last two cards,
        # and each card must help a different opponent.
        if not context.showdown_enabled or len(context.deck) != 2:
            return False
        if current in context.showdown_attempted_seats:
            return False
        if len({card.month for card in context.deck}) != 2:
            return False
        alive = [seat_id for seat_id, state in seats.items() if state.alive]
        if len(alive) != 3 or current not in alive:
            return False
        opponents = [seat_id for seat_id in alive if seat_id != current]
        if len(opponents) != 2:
            return False
        cards = tuple(context.deck)
        card_deltas = [
            [self._showdown_card_delta(opponent, seats, context, card) > 0 for opponent in opponents]
            for card in cards
        ]
        return (card_deltas[0][0] and card_deltas[1][1]) or (card_deltas[0][1] and card_deltas[1][0])

    def _choose_action(
        self,
        agent,
        seats,
        seat_id,
        phase,
        dealer,
        hand_id,
        current_turn,
        table_cards,
        carryover_multiplier,
        legal_actions,
        decision_seed,
        exited_seat,
        context=None,
    ):
        seat = seats[seat_id]
        seat.legal_actions = legal_actions
        public = PublicGameState(
            phase=phase,
            hand_id=hand_id,
            seat_id=seat_id,
            dealer_seat=dealer,
            current_turn=current_turn,
            alive_seats=tuple(idx for idx, state in seats.items() if state.alive),
            exited_seat=exited_seat,
            hand_cards=tuple(sorted(seat.hand, key=lambda c: (c.month, c.id))),
            table_cards=tuple(sorted(table_cards, key=lambda c: (c.month, c.id))),
            captured_cards_public={idx: tuple(state.captured) for idx, state in seats.items()},
            scores_public={idx: score_captured_cards(state.captured, state.moved_gukjin) for idx, state in seats.items()},
            go_counts_public={idx: state.go_count for idx, state in seats.items()},
            bankrolls_public={idx: state.bankroll for idx, state in seats.items()},
            carryover_multiplier=carryover_multiplier,
            showdown_pending=context.showdown_pending if context else False,
            showdown_proposer=context.showdown_proposer if context else None,
            showdown_responses=dict(context.showdown_responses or {}) if context else {},
            legal_actions=tuple(legal_actions),
            decision_seed=decision_seed,
        )
        if self._is_remote_agent(agent):
            if context and context.simulation_mode:
                cached_action = self._cached_remote_action(agent, public)
                if cached_action is not None:
                    return cached_action
                context.simulation_remote_cache_miss = True
                return legal_actions[0]
            if isinstance(self.config.remote_eval_hands, int) and self.config.remote_eval_hands >= 0:
                if public.hand_id > self.config.remote_eval_hands:
                    return legal_actions[0]
        action = agent.select_action(public)
        if action not in legal_actions:
            return legal_actions[0]
        return action

    def _is_remote_agent(self, agent) -> bool:
        return type(agent).__name__ in {
            "RemoteModelAgent",
            "OpenRouterModelAgent",
            "DashScopeModelAgent",
            "NvidiaModelAgent",
        }

    def _cached_remote_action(self, agent, public_state):
        cache = getattr(agent, "_cache", None)
        if not isinstance(cache, dict):
            return None
        from agents.adapters import _state_key

        choice_index = cache.get(_state_key(public_state))
        if isinstance(choice_index, int) and 0 <= choice_index < len(public_state.legal_actions):
            return public_state.legal_actions[choice_index]
        return None

    def _determine_stop_candidate(self, seats, alive_order):
        best_seat = None
        best_score = -1
        for seat_id in alive_order:
            score = score_captured_cards(seats[seat_id].captured, seats[seat_id].moved_gukjin)
            if score >= 3 and score > best_score:
                best_seat = seat_id
                best_score = score
        return best_seat

    def _card_from_hand(self, seat: SeatState, card_id: str):
        for card in seat.hand:
            if card.id == card_id:
                return card
        raise ValueError(f"Card {card_id} not in hand")

    def _remove_card_from_hand(self, seat: SeatState, card_id: str):
        card = self._card_from_hand(seat, card_id)
        seat.hand.remove(card)
        return card

    def _draw_and_resolve(self, rng, seat, seats, agents, context, logs, source):
        from engine.cards import JOKER_MONTH

        if not context.deck:
            return ResolutionInfo(source=source, score_before=score_captured_cards(seat.captured, seat.moved_gukjin), score_after=score_captured_cards(seat.captured, seat.moved_gukjin)), False
        draw = context.deck.pop()
        invalidates = False
        while draw.month == JOKER_MONTH:
            seat.captured.append(draw)
            invalidates = True
            if not context.deck:
                score = score_captured_cards(seat.captured, seat.moved_gukjin)
                return ResolutionInfo(source=source, score_before=score, score_after=score), invalidates
            draw = context.deck.pop()
        result = self._resolve_single_card(rng, seat, seats, context, agents, logs, draw, source=source)
        return result, invalidates

    def _evaluate_showdown_counterfactual(self, rng, context: HandContext, seats, agents, proposer: int) -> dict:
        sim_rng = random.Random()
        sim_rng.setstate(rng.getstate())
        sim_context = copy.deepcopy(context)
        sim_context.showdown_enabled = False
        sim_context.showdown_pending = False
        sim_context.showdown_proposer = None
        sim_context.showdown_responses = {}
        sim_context.pending_responsibility = None
        sim_context.simulation_mode = True
        sim_seats = copy.deepcopy(seats)
        sim_logs: list[dict] = []
        outcome = self._run_context_until_done(sim_rng, sim_context, sim_seats, agents, sim_logs)
        if sim_context.simulation_remote_cache_miss:
            return {"seat": proposer, "counterfactual_payout": None, "available": False}
        return {"seat": proposer, "counterfactual_payout": outcome.payout_deltas.get(proposer, 0), "available": True}

    def _emit_showdown_evaluations(self, context: HandContext, outcome: HandOutcome, logs: list[dict]) -> None:
        for evaluation in context.showdown_evaluations:
            if not evaluation.get("available", True):
                continue
            seat = evaluation["seat"]
            actual = outcome.payout_deltas.get(seat, 0)
            counterfactual = evaluation["counterfactual_payout"]
            if counterfactual is None:
                continue
            ev_gain = actual - counterfactual
            logs.append(
                self.recorder.event(
                    context.hand_id,
                    seat,
                    EventType.SHOWDOWN_EVAL,
                    {
                        "actual_payout": actual,
                        "counterfactual_payout": counterfactual,
                        "ev_gain": ev_gain,
                        "misplay": int(ev_gain < 0),
                    },
                )
            )
