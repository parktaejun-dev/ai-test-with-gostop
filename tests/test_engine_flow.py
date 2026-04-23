from __future__ import annotations

import unittest
from random import Random
from unittest.mock import patch

from agents.adapters import RemoteModelAgent
from engine import apply_go_bonus
from agents.baselines import RandomAgent
from engine.actions import Action, ActionType
from engine.cards import JOKERS, build_deck
from engine.game import GameEngine, HandContext, HandOutcome
from engine.rules import determine_shake_ready_months, take_pi_from_captured
from engine.state import GameConfig, Phase, SeatState


class _ChooseLastMatchAgent:
    name = "choose_last"

    def select_action(self, state):
        if all(action.type == ActionType.CHOOSE_MATCH for action in state.legal_actions):
            return state.legal_actions[-1]
        if any(action.type == ActionType.PROPOSE_SHOWDOWN for action in state.legal_actions):
            return next(action for action in state.legal_actions if action.type == ActionType.PROPOSE_SHOWDOWN)
        if any(action.type == ActionType.ACCEPT_SHOWDOWN for action in state.legal_actions):
            return next(action for action in state.legal_actions if action.type == ActionType.ACCEPT_SHOWDOWN)
        if any(action.type == ActionType.CHOOSE_GO_STOP for action in state.legal_actions):
            return next(action for action in state.legal_actions if action.choice == "stop")
        return state.legal_actions[0]


class _AcceptShowdownAgent(_ChooseLastMatchAgent):
    name = "accept_showdown"

    def select_action(self, state):
        if any(action.type == ActionType.ACCEPT_SHOWDOWN for action in state.legal_actions):
            return next(action for action in state.legal_actions if action.type == ActionType.ACCEPT_SHOWDOWN)
        return super().select_action(state)


class _RejectShowdownAgent(_ChooseLastMatchAgent):
    name = "reject_showdown"

    def select_action(self, state):
        if any(action.type == ActionType.REJECT_SHOWDOWN for action in state.legal_actions):
            return next(action for action in state.legal_actions if action.type == ActionType.REJECT_SHOWDOWN)
        return super().select_action(state)


class _AlwaysGoAgent(_ChooseLastMatchAgent):
    name = "always_go"

    def select_action(self, state):
        if any(action.type == ActionType.CHOOSE_GO_STOP for action in state.legal_actions):
            return next(action for action in state.legal_actions if action.choice == "go")
        return super().select_action(state)


class EngineFlowTest(unittest.TestCase):
    def test_deck_size(self):
        deck = build_deck()
        self.assertEqual(len(deck), 50)

    def test_shake_ready_detects_three_in_hand(self):
        deck = build_deck()
        jan_cards = [card for card in deck if card.month == 1][:3]
        ready = determine_shake_ready_months(jan_cards, [])
        self.assertEqual(ready, {1})

    def test_shake_is_optional_when_month_is_ready(self):
        deck = build_deck()
        jan_cards = [card for card in deck if card.month == 1][:3]
        engine = GameEngine(GameConfig(session_hands=1))
        seat = SeatState(seat=0, agent_name="A", hand=jan_cards, alive=True)
        context = HandContext(
            hand_id=1,
            dealer_seat=0,
            carryover_multiplier=1,
            table_cards=[],
            deck=[],
            current_turn=0,
            phase=Phase.TURN_START,
        )

        legal = engine._legal_actions_for_turn(seat, context, {0: seat}, 0)

        self.assertTrue(any(action.type == ActionType.PLAY_CARD and action.card_id == jan_cards[0].id for action in legal))
        self.assertTrue(any(action.type == ActionType.DECLARE_SHAKE and action.card_id == jan_cards[0].id for action in legal))

    def test_take_pi_prefers_normal_then_double(self):
        deck = build_deck()
        pi_cards = [card for card in deck if card.is_pi and not card.is_double_pi][:1]
        double_cards = [card for card in deck if card.is_double_pi][:2]
        captured = pi_cards + double_cards
        result = take_pi_from_captured(captured, 2)
        self.assertEqual(len(result.taken_ids), 2)
        self.assertEqual(result.total_pi_value, 3)

    def test_session_runs(self):
        agents = {seat: RandomAgent(name=f"a{seat}") for seat in range(4)}
        result = GameEngine(GameConfig(session_hands=3)).play_session(agents, session_seed=7, num_hands=3)
        self.assertEqual(len(result["hand_outcomes"]), 3)

    def test_session_uses_configured_session_hands(self):
        agents = {seat: RandomAgent(name=f"a{seat}") for seat in range(4)}
        result = GameEngine(GameConfig(session_hands=2)).play_session(agents, session_seed=7)
        self.assertEqual(len(result["hand_outcomes"]), 2)

    def test_redeal_does_not_count_toward_session_hands(self):
        engine = GameEngine(GameConfig(session_hands=2))
        agents = {seat: RandomAgent(name=f"a{seat}") for seat in range(4)}
        outcomes = iter(
            [
                (HandOutcome(hand_id=1, redeal=True), 0, 1, []),
                (HandOutcome(hand_id=1, winner=0), 0, 1, []),
                (HandOutcome(hand_id=2, winner=1), 1, 1, []),
            ]
        )

        def fake_play_hand(*args, **kwargs):
            return next(outcomes)

        with patch.object(GameEngine, "_play_hand", side_effect=fake_play_hand):
            result = engine.play_session(agents, session_seed=7)

        self.assertEqual(len(result["hand_outcomes"]), 2)
        self.assertEqual(result["session_hands_played"], 2)

    def test_initial_table_uses_eight_cards(self):
        deck = build_deck()
        chosen = []
        used_ids = set()
        for month in range(1, 9):
            card = next(
                item for item in deck if item.month == month and not item.joker and item.id not in used_ids
            )
            chosen.append(card)
            used_ids.add(card.id)
        ordered_deck = [card for card in deck if card.id not in used_ids] + chosen
        engine = GameEngine(GameConfig(session_hands=1))
        seats = {
            seat: SeatState(seat=seat, agent_name=f"A{seat}", bankroll=100_000, alive=True)
            for seat in range(4)
        }
        agents = {seat: RandomAgent(name=f"a{seat}") for seat in range(4)}
        captured = {}

        def spy(self, rng, context, seats_arg, agents_arg, logs):
            captured["table_len"] = len(context.table_cards)
            return HandOutcome(hand_id=context.hand_id, nagari=True)

        with patch("engine.game.has_chongtong", return_value=set()), patch.object(GameEngine, "_run_context_until_done", spy):
            engine._play_hand(Random(1), 1, ordered_deck, dealer=0, carryover=1, seats=seats, agents=agents)

        self.assertEqual(captured["table_len"], 8)

    def test_floor_joker_replacement_draws_until_non_joker(self):
        deck = build_deck()
        replacement = next(card for card in deck if not card.joker and card.id not in {JOKERS[0].id, JOKERS[1].id})
        engine = GameEngine(GameConfig(session_hands=1))
        seats = {
            0: SeatState(seat=0, agent_name="A", alive=True),
            1: SeatState(seat=1, agent_name="B", alive=True),
            2: SeatState(seat=2, agent_name="C", alive=True),
            3: SeatState(seat=3, agent_name="D", alive=False),
        }
        table_cards = [JOKERS[0]]
        draw_deck = [replacement, JOKERS[1]]

        resolved = engine._resolve_floor_jokers(0, table_cards, draw_deck, seats)

        self.assertEqual(resolved, 2)
        self.assertEqual(table_cards, [replacement])
        self.assertEqual({card.id for card in seats[0].captured}, {JOKERS[0].id, JOKERS[1].id})

    def test_showdown_eligibility_matches_netmarble_rule(self):
        deck = build_deck()
        engine = GameEngine(GameConfig(session_hands=1))
        last_junk = next(card for card in deck if card.month == 1 and card.junk)
        last_bright = next(card for card in deck if card.bright and card.month == 11)
        same_month_alt = next(card for card in deck if card.month == 1 and card.ribbon)
        same_opponent_junk = next(card for card in deck if card.month == 2 and card.junk)
        table_month1 = next(card for card in deck if card.month == 1 and card.id not in {last_junk.id, same_month_alt.id})
        table_month11 = next(card for card in deck if card.month == 11 and card.id != last_bright.id)
        seat1_captured = [card for card in deck if card.junk and card.month not in {1, 11} and card.id != same_opponent_junk.id][:9]
        seat2_captured = [card for card in deck if card.bright and card.month in {3, 8}][:2]
        used_ids = {last_junk.id, last_bright.id, same_month_alt.id, same_opponent_junk.id, table_month1.id, table_month11.id}
        used_ids.update(card.id for card in seat1_captured)
        used_ids.update(card.id for card in seat2_captured)
        seat0_hand = [next(card for card in deck if card.id not in used_ids)]
        seats = {
            0: SeatState(seat=0, agent_name="A", hand=seat0_hand, alive=True),
            1: SeatState(seat=1, agent_name="B", captured=seat1_captured, alive=True),
            2: SeatState(seat=2, agent_name="C", captured=seat2_captured, alive=True),
            3: SeatState(seat=3, agent_name="D", alive=False),
        }
        context = HandContext(
            hand_id=1,
            dealer_seat=0,
            carryover_multiplier=1,
            table_cards=[table_month1, table_month11],
            deck=[last_junk, last_bright],
            current_turn=0,
            phase=Phase.TURN_START,
            exited_seat=3,
        )

        legal = engine._legal_actions_for_turn(seats[0], context, seats, 0)
        self.assertTrue(any(action.type == ActionType.PROPOSE_SHOWDOWN for action in legal))

        context.deck = [last_junk, same_month_alt]
        legal = engine._legal_actions_for_turn(seats[0], context, seats, 0)
        self.assertFalse(any(action.type == ActionType.PROPOSE_SHOWDOWN for action in legal))

        context.deck = [last_junk, same_opponent_junk]
        legal = engine._legal_actions_for_turn(seats[0], context, seats, 0)
        self.assertFalse(any(action.type == ActionType.PROPOSE_SHOWDOWN for action in legal))

        context.deck = [last_junk, last_bright, same_month_alt]
        legal = engine._legal_actions_for_turn(seats[0], context, seats, 0)
        self.assertFalse(any(action.type == ActionType.PROPOSE_SHOWDOWN for action in legal))

    def test_showdown_eligibility_uses_actual_draw_resolution(self):
        deck = build_deck()
        engine = GameEngine(GameConfig(session_hands=1))
        last_junk = next(card for card in deck if card.month == 1 and card.junk)
        last_bright = next(card for card in deck if card.bright and card.month == 11)
        seat1_captured = [card for card in deck if card.junk and card.month not in {1, 11}][:9]
        seat2_captured = [card for card in deck if card.bright and card.month in {3, 8}][:2]
        used_ids = {last_junk.id, last_bright.id}
        used_ids.update(card.id for card in seat1_captured)
        used_ids.update(card.id for card in seat2_captured)
        seat0_hand = [next(card for card in deck if card.id not in used_ids)]
        seats = {
            0: SeatState(seat=0, agent_name="A", hand=seat0_hand, alive=True),
            1: SeatState(seat=1, agent_name="B", captured=seat1_captured, alive=True),
            2: SeatState(seat=2, agent_name="C", captured=seat2_captured, alive=True),
            3: SeatState(seat=3, agent_name="D", alive=False),
        }
        context = HandContext(
            hand_id=1,
            dealer_seat=0,
            carryover_multiplier=1,
            table_cards=[],
            deck=[last_junk, last_bright],
            current_turn=0,
            phase=Phase.TURN_START,
            exited_seat=3,
        )

        legal = engine._legal_actions_for_turn(seats[0], context, seats, 0)
        self.assertFalse(any(action.type == ActionType.PROPOSE_SHOWDOWN for action in legal))

    def test_choose_match_uses_explicit_target(self):
        deck = build_deck()
        jan_junks = [card for card in deck if card.month == 1 and card.junk][:2]
        jan_ribbon = next(card for card in deck if card.month == 1 and card.ribbon)
        other = next(card for card in deck if card.month == 2 and card.id not in {jan_junks[0].id, jan_junks[1].id, jan_ribbon.id})
        engine = GameEngine(GameConfig(session_hands=1))
        seats = {
            0: SeatState(seat=0, agent_name="A", hand=[jan_ribbon], alive=True),
            1: SeatState(seat=1, agent_name="B", alive=True),
            2: SeatState(seat=2, agent_name="C", alive=True),
            3: SeatState(seat=3, agent_name="D", alive=False),
        }

        context = HandContext(
            hand_id=1,
            dealer_seat=0,
            carryover_multiplier=1,
            table_cards=[jan_junks[0], jan_junks[1]],
            deck=[other],
            current_turn=0,
            phase=Phase.TURN_START,
            exited_seat=3,
        )
        agents = {0: _ChooseLastMatchAgent(), 1: _ChooseLastMatchAgent(), 2: _ChooseLastMatchAgent(), 3: _ChooseLastMatchAgent()}
        engine._resolve_play_card(
            Random(1),
            seats[0],
            seats,
            agents,
            context,
            Action(ActionType.PLAY_CARD, card_id=jan_ribbon.id),
            [],
        )
        captured_ids = {card.id for card in seats[0].captured}
        self.assertIn(jan_junks[1].id, captured_ids)
        self.assertNotIn(jan_junks[0].id, captured_ids)
        self.assertIn(jan_junks[0], context.table_cards)

    def test_declare_bomb_available_with_three_in_hand_and_one_on_table(self):
        deck = build_deck()
        month_cards = [card for card in deck if card.month == 1][:4]
        engine = GameEngine(GameConfig(session_hands=1))
        seat = SeatState(seat=0, agent_name="A", hand=month_cards[:3], alive=True)
        context = HandContext(
            hand_id=1,
            dealer_seat=0,
            carryover_multiplier=1,
            table_cards=[month_cards[3]],
            deck=[],
            current_turn=0,
            phase=Phase.TURN_START,
        )

        legal = engine._legal_actions_for_turn(seat, context, {0: seat}, 0)

        self.assertTrue(any(action.type == ActionType.DECLARE_BOMB and action.month == 1 for action in legal))

    def test_normal_bomb_consumes_three_hand_cards(self):
        deck = build_deck()
        month_cards = [card for card in deck if card.month == 1][:4]
        engine = GameEngine(GameConfig(session_hands=1))
        seat = SeatState(seat=0, agent_name="A", hand=month_cards[:3], alive=True)
        seats = {
            0: seat,
            1: SeatState(seat=1, agent_name="B", alive=True),
            2: SeatState(seat=2, agent_name="C", alive=False),
            3: SeatState(seat=3, agent_name="D", alive=False),
        }
        context = HandContext(
            hand_id=1,
            dealer_seat=0,
            carryover_multiplier=1,
            table_cards=[month_cards[3]],
            deck=[],
            current_turn=0,
            phase=Phase.TURN_START,
        )

        engine._resolve_bomb(Random(9), seat, seats, {idx: _ChooseLastMatchAgent() for idx in seats}, context, 1, [], "bomb")

        self.assertEqual(len(seat.hand), 0)
        self.assertEqual(sum(1 for card in seat.captured if card.month == 1), 4)

    def test_jjok_logs_and_takes_extra_pi(self):
        deck = build_deck()
        jan_junks = [card for card in deck if card.month == 1 and card.junk][:2]
        jan_ribbon = next(card for card in deck if card.month == 1 and card.ribbon)
        jan_draw = next(card for card in deck if card.month == 1 and card.id not in {jan_junks[0].id, jan_junks[1].id, jan_ribbon.id})
        opponent_pi = next(card for card in deck if card.junk and card.month != 1 and card.id != jan_draw.id)
        engine = GameEngine(GameConfig(session_hands=1))
        seats = {
            0: SeatState(seat=0, agent_name="A", hand=[jan_ribbon], alive=True),
            1: SeatState(seat=1, agent_name="B", captured=[opponent_pi], alive=True),
            2: SeatState(seat=2, agent_name="C", alive=False),
            3: SeatState(seat=3, agent_name="D", alive=False),
        }
        context = HandContext(
            hand_id=1,
            dealer_seat=0,
            carryover_multiplier=1,
            table_cards=[jan_junks[0], jan_junks[1]],
            deck=[jan_draw],
            current_turn=0,
            phase=Phase.TURN_START,
            exited_seat=2,
        )
        agents = {seat: _ChooseLastMatchAgent() for seat in range(4)}
        logs = []

        engine._resolve_play_card(
            Random(8),
            seats[0],
            seats,
            agents,
            context,
            Action(ActionType.PLAY_CARD, card_id=jan_ribbon.id),
            logs,
        )

        self.assertTrue(any("JJOK" in str(entry["event"]) for entry in logs))
        self.assertEqual(seats[1].captured, [])
        self.assertIn(opponent_pi.id, {card.id for card in seats[0].captured})

    def test_settle_hand_uses_go_bonus_helper(self):
        deck = build_deck()
        engine = GameEngine(GameConfig(session_hands=1, stake_per_point=1))
        godori = [card for card in deck if card.animal_tag == "godori"]
        seats = {
            0: SeatState(seat=0, agent_name="A", captured=godori, alive=True, go_count=3),
            1: SeatState(seat=1, agent_name="B", alive=True),
            2: SeatState(seat=2, agent_name="C", alive=True),
            3: SeatState(seat=3, agent_name="D", alive=False),
        }
        context = HandContext(
            hand_id=1,
            dealer_seat=0,
            carryover_multiplier=1,
            table_cards=[],
            deck=[],
            current_turn=0,
            phase=Phase.TURN_START,
            exited_seat=None,
        )
        outcome = engine._settle_hand(context, seats, 0, [])
        self.assertEqual(outcome.base_points, 5)
        self.assertEqual(outcome.final_points, apply_go_bonus(5, 3))

    def test_winner_bomb_double_persists_even_if_another_player_bombs_later(self):
        deck = build_deck()
        engine = GameEngine(GameConfig(session_hands=1, stake_per_point=1))
        godori = [card for card in deck if card.animal_tag == "godori"]
        seats = {
            0: SeatState(seat=0, agent_name="A", captured=godori, alive=True),
            1: SeatState(seat=1, agent_name="B", alive=True),
            2: SeatState(seat=2, agent_name="C", alive=True),
            3: SeatState(seat=3, agent_name="D", alive=False),
        }
        context = HandContext(
            hand_id=1,
            dealer_seat=0,
            carryover_multiplier=1,
            table_cards=[],
            deck=[],
            current_turn=0,
            phase=Phase.TURN_START,
            bomb_declared_by=1,
            bomb_declared_seats={0, 1},
        )

        outcome = engine._settle_hand(context, seats, 0, [])
        self.assertEqual(outcome.final_points, apply_go_bonus(5, 0) * 2)
        self.assertEqual(outcome.bomb_declared_by, 0)

    def test_bomb_resolution_does_not_add_shake_multiplier(self):
        deck = build_deck()
        engine = GameEngine(GameConfig(session_hands=1, stake_per_point=1))
        bomb_month = 1
        month_cards = [card for card in deck if card.month == bomb_month][:4]
        godori = [card for card in deck if card.animal_tag == "godori"]
        seats = {
            0: SeatState(seat=0, agent_name="A", hand=month_cards[:3], captured=list(godori), alive=True),
            1: SeatState(seat=1, agent_name="B", alive=True),
            2: SeatState(seat=2, agent_name="C", alive=True),
            3: SeatState(seat=3, agent_name="D", alive=False),
        }
        context = HandContext(
            hand_id=1,
            dealer_seat=0,
            carryover_multiplier=1,
            table_cards=[month_cards[3]],
            deck=[],
            current_turn=0,
            phase=Phase.TURN_START,
            bomb_declared_seats={0},
        )

        engine._resolve_bomb(Random(0), seats[0], seats, {}, context, bomb_month, [], "bomb")
        outcome = engine._settle_hand(context, seats, 0, [])

        self.assertEqual(seats[0].declared_shake_months, [])
        self.assertIn(bomb_month, seats[0].bomb_months)
        self.assertEqual(outcome.final_points, apply_go_bonus(5, 0) * 2)

    def test_can_offer_go_stop_requires_score_increase_after_go(self):
        engine = GameEngine(GameConfig(session_hands=1))
        seat = SeatState(seat=0, agent_name="A", go_count=1, last_go_score=3)
        self.assertFalse(engine._can_offer_go_stop(seat, 3))
        self.assertFalse(engine._can_offer_go_stop(seat, 2))
        self.assertTrue(engine._can_offer_go_stop(seat, 4))

    def test_gwang_sell_requires_bright(self):
        engine = GameEngine(GameConfig(session_hands=1))
        rain_bright = next(card for card in build_deck() if card.rain_bright)
        double_pi = next(card for card in build_deck() if card.is_double_pi)
        self.assertEqual(engine._gwang_sell_count([rain_bright, JOKERS[0]]), 0)
        self.assertEqual(engine._gwang_sell_count([rain_bright, double_pi, JOKERS[0]]), 0)

    def test_gwang_sell_counts_bright_with_extras(self):
        engine = GameEngine(GameConfig(session_hands=1))
        bright = next(card for card in build_deck() if card.bright and not card.is_rain_bright)
        double_pi = next(card for card in build_deck() if card.is_double_pi)
        self.assertEqual(engine._gwang_sell_count([bright]), 1)
        self.assertEqual(engine._gwang_sell_count([bright, double_pi]), 2)

    def test_responsibility_dokbak_transfers_third_party_loss(self):
        deck = build_deck()
        jan_junks = [card for card in deck if card.month == 1 and card.junk][:2]
        normal_pi = [card for card in deck if card.junk and card.id not in {jan_junks[0].id, jan_junks[1].id}]
        unrelated = next(card for card in deck if card.month == 12 and card.id not in {item.id for item in jan_junks + normal_pi[:11]})
        engine = GameEngine(GameConfig(session_hands=1, stake_per_point=1))
        seats = {
            0: SeatState(seat=0, agent_name="A", captured=normal_pi[:2], alive=True),
            1: SeatState(seat=1, agent_name="B", hand=[jan_junks[1]], captured=normal_pi[:11], alive=True),
            2: SeatState(seat=2, agent_name="C", captured=normal_pi[2:6], alive=True),
            3: SeatState(seat=3, agent_name="D", alive=False),
        }

        context = HandContext(
            hand_id=1,
            dealer_seat=0,
            carryover_multiplier=1,
            table_cards=[jan_junks[0]],
            deck=[unrelated],
            current_turn=1,
            phase=Phase.TURN_START,
            exited_seat=3,
            table_source_seats={jan_junks[0].id: 0},
        )
        agents = {seat: _ChooseLastMatchAgent() for seat in range(4)}
        engine._resolve_play_card(
            Random(2),
            seats[1],
            seats,
            agents,
            context,
            Action(ActionType.PLAY_CARD, card_id=jan_junks[1].id),
            [],
        )
        self.assertIsNotNone(context.pending_responsibility)
        self.assertEqual(context.pending_responsibility["source"], 0)
        context.responsibility_source = context.pending_responsibility["source"]
        logs = []
        outcome = engine._settle_hand(context, seats, 1, logs)
        self.assertEqual(outcome.payout_deltas[2], 0)
        self.assertLess(outcome.payout_deltas[0], 0)
        self.assertTrue(any("RESPONSIBILITY_DOKBAK" in str(entry["event"]) for entry in logs))

    def test_showdown_eval_is_logged_from_counterfactual(self):
        deck = build_deck()
        engine = GameEngine(GameConfig(session_hands=1))
        last_junk = next(card for card in deck if card.month == 1 and card.junk)
        last_bright = next(card for card in deck if card.bright and card.month == 11)
        seat1_captured = [card for card in deck if card.junk and card.month not in {1, 11}][:9]
        seat2_captured = [card for card in deck if card.bright and card.month in {3, 8}][:2]
        table_month1 = next(card for card in deck if card.month == 1 and card.id != last_junk.id)
        table_month11 = next(card for card in deck if card.month == 11 and card.id != last_bright.id)
        used_ids = {last_junk.id, last_bright.id, table_month1.id, table_month11.id}
        used_ids.update(card.id for card in seat1_captured)
        used_ids.update(card.id for card in seat2_captured)
        seat1_hand = [next(card for card in deck if card.id not in used_ids)]
        used_ids.update(card.id for card in seat1_hand)
        seat2_hand = [next(card for card in deck if card.id not in used_ids)]
        used_ids.update(card.id for card in seat2_hand)
        seat0_hand = [next(card for card in deck if card.id not in used_ids)]
        seats = {
            0: SeatState(seat=0, agent_name="A", hand=seat0_hand, alive=True),
            1: SeatState(seat=1, agent_name="B", hand=seat1_hand, captured=seat1_captured, alive=True),
            2: SeatState(seat=2, agent_name="C", hand=seat2_hand, captured=seat2_captured, alive=True),
            3: SeatState(seat=3, agent_name="D", alive=False),
        }

        context = HandContext(
            hand_id=1,
            dealer_seat=0,
            carryover_multiplier=1,
            table_cards=[table_month1, table_month11],
            deck=[last_junk, last_bright],
            current_turn=0,
            phase=Phase.TURN_START,
            exited_seat=3,
        )
        agents = {0: _ChooseLastMatchAgent(), 1: _AcceptShowdownAgent(), 2: _AcceptShowdownAgent(), 3: _AcceptShowdownAgent()}
        legal = engine._legal_actions_for_turn(seats[0], context, seats, 0)
        self.assertTrue(any(action.type == ActionType.PROPOSE_SHOWDOWN for action in legal))
        logs = []
        turn_logs, done, outcome = engine._play_turn(Random(3), context, seats, agents, 0)
        logs.extend(turn_logs)
        self.assertFalse(done)
        context.current_turn = 1
        turn_logs, done, _ = engine._play_turn(Random(4), context, seats, agents, 1)
        logs.extend(turn_logs)
        self.assertFalse(done)
        context.current_turn = 2
        turn_logs, done, outcome = engine._play_turn(Random(5), context, seats, agents, 2)
        logs.extend(turn_logs)
        self.assertTrue(done)
        self.assertTrue(outcome.showdown_success)
        engine._emit_showdown_evaluations(context, outcome, logs)
        eval_logs = [entry for entry in logs if "SHOWDOWN_EVAL" in str(entry["event"])]
        self.assertEqual(len(eval_logs), 1)
        self.assertIn("ev_gain", eval_logs[0])

    def test_showdown_counterfactual_does_not_call_remote_agents(self):
        deck = build_deck()
        engine = GameEngine(GameConfig(session_hands=1))
        last_junk = next(card for card in deck if card.month == 1 and card.junk)
        last_bright = next(card for card in deck if card.bright and card.month == 11)
        seat1_captured = [card for card in deck if card.junk and card.month not in {1, 11}][:9]
        seat2_captured = [card for card in deck if card.bright and card.month in {3, 8}][:2]
        table_month1 = next(card for card in deck if card.month == 1 and card.id != last_junk.id)
        table_month11 = next(card for card in deck if card.month == 11 and card.id != last_bright.id)
        used_ids = {last_junk.id, last_bright.id, table_month1.id, table_month11.id}
        used_ids.update(card.id for card in seat1_captured)
        used_ids.update(card.id for card in seat2_captured)
        seat1_hand = [next(card for card in deck if card.id not in used_ids)]
        used_ids.update(card.id for card in seat1_hand)
        seat2_hand = [next(card for card in deck if card.id not in used_ids)]
        used_ids.update(card.id for card in seat2_hand)
        seat0_hand = [next(card for card in deck if card.id not in used_ids)]
        seats = {
            0: SeatState(seat=0, agent_name="A", hand=seat0_hand, alive=True),
            1: SeatState(seat=1, agent_name="B", hand=seat1_hand, captured=seat1_captured, alive=True),
            2: SeatState(seat=2, agent_name="C", hand=seat2_hand, captured=seat2_captured, alive=True),
            3: SeatState(seat=3, agent_name="D", alive=False),
        }
        context = HandContext(
            hand_id=1,
            dealer_seat=0,
            carryover_multiplier=1,
            table_cards=[table_month1, table_month11],
            deck=[last_junk, last_bright],
            current_turn=0,
            phase=Phase.TURN_START,
            exited_seat=3,
        )
        failing_remote = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("remote responder must not run in showdown simulation"))
        agents = {
            0: _ChooseLastMatchAgent(),
            1: RemoteModelAgent(name="remote1", model_id="gpt-4o-mini", prompt_template="Choose", responder=failing_remote),
            2: RemoteModelAgent(name="remote2", model_id="gpt-4o-mini", prompt_template="Choose", responder=failing_remote),
            3: _ChooseLastMatchAgent(),
        }

        turn_logs, done, outcome = engine._play_turn(Random(3), context, seats, agents, 0)
        self.assertFalse(done)
        self.assertIsNone(outcome)
        self.assertTrue(any("SHOWDOWN_PROPOSED" in str(entry["event"]) for entry in turn_logs))
        evaluation = engine._evaluate_showdown_counterfactual(Random(3), context, seats, agents, 0)
        self.assertFalse(evaluation["available"])
        self.assertIsNone(evaluation["counterfactual_payout"])

    def test_showdown_success_settles_payouts(self):
        deck = build_deck()
        engine = GameEngine(GameConfig(session_hands=1, stake_per_point=1))
        last_junk = next(card for card in deck if card.month == 1 and card.junk)
        last_bright = next(card for card in deck if card.bright and card.month == 11)
        seat1_captured = [card for card in deck if card.junk and card.month not in {1, 11}][:10]
        seat2_captured = [card for card in deck if card.bright and card.month in {3, 8}][:2]
        table_month1 = next(card for card in deck if card.month == 1 and card.id != last_junk.id)
        table_month11 = next(card for card in deck if card.month == 11 and card.id != last_bright.id)
        used_ids = {last_junk.id, last_bright.id, table_month1.id, table_month11.id}
        used_ids.update(card.id for card in seat1_captured)
        used_ids.update(card.id for card in seat2_captured)
        seat1_hand = [next(card for card in deck if card.id not in used_ids)]
        used_ids.update(card.id for card in seat1_hand)
        seat2_hand = [next(card for card in deck if card.id not in used_ids)]
        used_ids.update(card.id for card in seat2_hand)
        seat0_hand = [next(card for card in deck if card.id not in used_ids)]
        seats = {
            0: SeatState(seat=0, agent_name="A", hand=seat0_hand, alive=True),
            1: SeatState(seat=1, agent_name="B", hand=seat1_hand, captured=seat1_captured, alive=True),
            2: SeatState(seat=2, agent_name="C", hand=seat2_hand, captured=seat2_captured, alive=True),
            3: SeatState(seat=3, agent_name="D", alive=False),
        }
        context = HandContext(
            hand_id=1,
            dealer_seat=0,
            carryover_multiplier=1,
            table_cards=[table_month1, table_month11],
            deck=[last_junk, last_bright],
            current_turn=0,
            phase=Phase.TURN_START,
            exited_seat=3,
        )
        agents = {0: _ChooseLastMatchAgent(), 1: _AcceptShowdownAgent(), 2: _AcceptShowdownAgent(), 3: _AcceptShowdownAgent()}

        turn_logs, done, _ = engine._play_turn(Random(3), context, seats, agents, 0)
        self.assertFalse(done)
        self.assertTrue(any("SHOWDOWN_PROPOSED" in str(entry["event"]) for entry in turn_logs))

        context.current_turn = 1
        turn_logs, done, _ = engine._play_turn(Random(4), context, seats, agents, 1)
        self.assertFalse(done)

        context.current_turn = 2
        _, done, outcome = engine._play_turn(Random(5), context, seats, agents, 2)
        self.assertTrue(done)
        self.assertTrue(outcome.showdown_success)
        self.assertEqual(outcome.winner, 1)
        self.assertGreater(outcome.final_points, 0)
        self.assertGreater(outcome.payout_deltas[1], 0)
        self.assertLess(outcome.payout_deltas[0], 0)
        self.assertLess(outcome.payout_deltas[2], 0)

    def test_deck_exhausted_nagari_settles_by_score(self):
        deck = build_deck()
        scoring_pile = [card for card in deck if card.junk][:10]
        used_ids = {card.id for card in scoring_pile}
        seat0_card = next(card for card in deck if card.id not in used_ids)
        engine = GameEngine(GameConfig(session_hands=1, stake_per_point=1))
        seats = {
            0: SeatState(seat=0, agent_name="A", hand=[seat0_card], alive=True),
            1: SeatState(seat=1, agent_name="B", captured=scoring_pile, alive=True),
            2: SeatState(seat=2, agent_name="C", alive=True),
            3: SeatState(seat=3, agent_name="D", alive=False),
        }
        context = HandContext(
            hand_id=1,
            dealer_seat=0,
            carryover_multiplier=1,
            table_cards=[],
            deck=[],
            current_turn=0,
            phase=Phase.TURN_START,
            exited_seat=3,
        )
        agents = {seat: _ChooseLastMatchAgent() for seat in range(4)}

        _, done, outcome = engine._play_turn(Random(6), context, seats, agents, 0)
        self.assertTrue(done)
        self.assertTrue(outcome.nagari)
        self.assertEqual(outcome.winner, 1)
        self.assertGreater(outcome.payout_deltas[1], 0)
        self.assertLess(outcome.payout_deltas[0], 0)
        self.assertLess(outcome.payout_deltas[2], 0)
        self.assertEqual(outcome.bak_flags[0], [])
        self.assertEqual(outcome.bak_flags[2], [])

    def test_empty_turn_offers_go_stop_instead_of_forced_stop(self):
        deck = build_deck()
        scoring_pile = [card for card in deck if card.junk][:12]
        used_ids = {card.id for card in scoring_pile}
        draw_cards = [card for card in deck if card.junk and card.id not in used_ids][:2]
        engine = GameEngine(GameConfig(session_hands=1, stake_per_point=1))
        seats = {
            0: SeatState(seat=0, agent_name="A", captured=scoring_pile, alive=True, empty_turn=True),
            1: SeatState(seat=1, agent_name="B", alive=True),
            2: SeatState(seat=2, agent_name="C", alive=True),
            3: SeatState(seat=3, agent_name="D", alive=False),
        }
        context = HandContext(
            hand_id=1,
            dealer_seat=0,
            carryover_multiplier=1,
            table_cards=[],
            deck=list(draw_cards),
            current_turn=0,
            phase=Phase.TURN_START,
            exited_seat=3,
        )
        agents = {0: _AlwaysGoAgent(), 1: _ChooseLastMatchAgent(), 2: _ChooseLastMatchAgent(), 3: _ChooseLastMatchAgent()}

        logs, done, outcome = engine._play_turn(Random(7), context, seats, agents, 0)
        self.assertFalse(done)
        self.assertIsNone(outcome)
        self.assertEqual(seats[0].go_count, 1)
        self.assertEqual(seats[0].last_go_score, 3)
        self.assertTrue(any("GO" in str(entry["event"]) for entry in logs))

    def test_bak_flags_require_matching_winner_score_type(self):
        deck = build_deck()
        godori = [card for card in deck if card.animal_tag == "godori"]
        loser_pi = [card for card in deck if card.junk and card.id not in {card.id for card in godori}][:5]
        engine = GameEngine(GameConfig(session_hands=1, stake_per_point=1))
        seats = {
            0: SeatState(seat=0, agent_name="A", captured=godori, alive=True),
            1: SeatState(seat=1, agent_name="B", captured=loser_pi, alive=True, go_count=1),
            2: SeatState(seat=2, agent_name="C", alive=True),
            3: SeatState(seat=3, agent_name="D", alive=False),
        }
        context = HandContext(
            hand_id=1,
            dealer_seat=0,
            carryover_multiplier=1,
            table_cards=[],
            deck=[],
            current_turn=0,
            phase=Phase.TURN_START,
            exited_seat=3,
        )

        outcome = engine._settle_hand(context, seats, 0, [], stop_declared=True)
        self.assertEqual(outcome.bak_flags[1], ["go_bak"])

    def test_showdown_first_reject_auto_accepts_remaining_player(self):
        deck = build_deck()
        engine = GameEngine(GameConfig(session_hands=1))
        last_junk = next(card for card in deck if card.month == 1 and card.junk)
        last_bright = next(card for card in deck if card.bright and card.month == 11)
        seat1_captured = [card for card in deck if card.junk and card.month not in {1, 11}][:9]
        seat2_captured = [card for card in deck if card.bright and card.month in {3, 8}][:2]
        table_month1 = next(card for card in deck if card.month == 1 and card.id != last_junk.id)
        table_month11 = next(card for card in deck if card.month == 11 and card.id != last_bright.id)
        used_ids = {last_junk.id, last_bright.id, table_month1.id, table_month11.id}
        used_ids.update(card.id for card in seat1_captured)
        used_ids.update(card.id for card in seat2_captured)
        seat1_hand = [next(card for card in deck if card.id not in used_ids)]
        used_ids.update(card.id for card in seat1_hand)
        seat2_hand = [next(card for card in deck if card.id not in used_ids)]
        used_ids.update(card.id for card in seat2_hand)
        seat0_hand = [next(card for card in deck if card.id not in used_ids)]
        seats = {
            0: SeatState(seat=0, agent_name="A", hand=seat0_hand, alive=True),
            1: SeatState(seat=1, agent_name="B", hand=seat1_hand, captured=seat1_captured, alive=True),
            2: SeatState(seat=2, agent_name="C", hand=seat2_hand, captured=seat2_captured, alive=True),
            3: SeatState(seat=3, agent_name="D", alive=False),
        }

        context = HandContext(
            hand_id=1,
            dealer_seat=0,
            carryover_multiplier=1,
            table_cards=[table_month1, table_month11],
            deck=[last_junk, last_bright],
            current_turn=0,
            phase=Phase.TURN_START,
            exited_seat=3,
        )
        agents = {0: _ChooseLastMatchAgent(), 1: _RejectShowdownAgent(), 2: _AcceptShowdownAgent(), 3: _AcceptShowdownAgent()}

        turn_logs, done, _ = engine._play_turn(Random(3), context, seats, agents, 0)
        self.assertFalse(done)
        self.assertTrue(any("SHOWDOWN_PROPOSED" in str(entry["event"]) for entry in turn_logs))

        context.current_turn = 1
        turn_logs, done, _ = engine._play_turn(Random(4), context, seats, agents, 1)
        self.assertFalse(done)
        self.assertTrue(any("SHOWDOWN_ACCEPTED" in str(entry["event"]) and entry.get("auto") for entry in turn_logs))
        self.assertTrue(any("SHOWDOWN_REJECTED" in str(entry["event"]) for entry in turn_logs))
        self.assertEqual(context.current_turn, 0)
        legal = engine._legal_actions_for_turn(seats[0], context, seats, 0)
        self.assertFalse(any(action.type == ActionType.PROPOSE_SHOWDOWN for action in legal))

    def test_showdown_non_unanimous_succeeds_after_single_accept(self):
        deck = build_deck()
        engine = GameEngine(GameConfig(session_hands=1, showdown_requires_unanimous=False))
        last_junk = next(card for card in deck if card.month == 1 and card.junk)
        last_bright = next(card for card in deck if card.bright and card.month == 11)
        table_month1 = next(card for card in deck if card.month == 1 and card.id != last_junk.id)
        table_month11 = next(card for card in deck if card.month == 11 and card.id != last_bright.id)
        seat1_captured = [card for card in deck if card.junk and card.month not in {1, 11}][:9]
        seat2_captured = [card for card in deck if card.bright and card.month in {3, 8}][:2]
        used_ids = {last_junk.id, last_bright.id, table_month1.id, table_month11.id}
        used_ids.update(card.id for card in seat1_captured)
        used_ids.update(card.id for card in seat2_captured)
        seat1_hand = [next(card for card in deck if card.id not in used_ids)]
        used_ids.update(card.id for card in seat1_hand)
        seat2_hand = [next(card for card in deck if card.id not in used_ids)]
        used_ids.update(card.id for card in seat2_hand)
        seat0_hand = [next(card for card in deck if card.id not in used_ids)]
        seats = {
            0: SeatState(seat=0, agent_name="A", hand=seat0_hand, alive=True),
            1: SeatState(seat=1, agent_name="B", hand=seat1_hand, captured=seat1_captured, alive=True),
            2: SeatState(seat=2, agent_name="C", hand=seat2_hand, captured=seat2_captured, alive=True),
            3: SeatState(seat=3, agent_name="D", alive=False),
        }
        context = HandContext(
            hand_id=1,
            dealer_seat=0,
            carryover_multiplier=1,
            table_cards=[table_month1, table_month11],
            deck=[last_junk, last_bright],
            current_turn=0,
            phase=Phase.TURN_START,
            exited_seat=3,
        )
        agents = {0: _ChooseLastMatchAgent(), 1: _AcceptShowdownAgent(), 2: _RejectShowdownAgent(), 3: _AcceptShowdownAgent()}

        turn_logs, done, _ = engine._play_turn(Random(10), context, seats, agents, 0)
        self.assertFalse(done)
        self.assertTrue(any("SHOWDOWN_PROPOSED" in str(entry["event"]) for entry in turn_logs))

        context.current_turn = 1
        _, done, outcome = engine._play_turn(Random(11), context, seats, agents, 1)
        self.assertTrue(done)
        self.assertTrue(outcome.showdown_success)

    def test_showdown_non_unanimous_reject_waits_for_remaining_response(self):
        deck = build_deck()
        engine = GameEngine(GameConfig(session_hands=1, showdown_requires_unanimous=False))
        last_junk = next(card for card in deck if card.month == 1 and card.junk)
        last_bright = next(card for card in deck if card.bright and card.month == 11)
        table_month1 = next(card for card in deck if card.month == 1 and card.id != last_junk.id)
        table_month11 = next(card for card in deck if card.month == 11 and card.id != last_bright.id)
        seat1_captured = [card for card in deck if card.junk and card.month not in {1, 11}][:9]
        seat2_captured = [card for card in deck if card.bright and card.month in {3, 8}][:2]
        used_ids = {last_junk.id, last_bright.id, table_month1.id, table_month11.id}
        used_ids.update(card.id for card in seat1_captured)
        used_ids.update(card.id for card in seat2_captured)
        seat1_hand = [next(card for card in deck if card.id not in used_ids)]
        used_ids.update(card.id for card in seat1_hand)
        seat2_hand = [next(card for card in deck if card.id not in used_ids)]
        used_ids.update(card.id for card in seat2_hand)
        seat0_hand = [next(card for card in deck if card.id not in used_ids)]
        seats = {
            0: SeatState(seat=0, agent_name="A", hand=seat0_hand, alive=True),
            1: SeatState(seat=1, agent_name="B", hand=seat1_hand, captured=seat1_captured, alive=True),
            2: SeatState(seat=2, agent_name="C", hand=seat2_hand, captured=seat2_captured, alive=True),
            3: SeatState(seat=3, agent_name="D", alive=False),
        }
        context = HandContext(
            hand_id=1,
            dealer_seat=0,
            carryover_multiplier=1,
            table_cards=[table_month1, table_month11],
            deck=[last_junk, last_bright],
            current_turn=0,
            phase=Phase.TURN_START,
            exited_seat=3,
        )
        agents = {0: _ChooseLastMatchAgent(), 1: _RejectShowdownAgent(), 2: _RejectShowdownAgent(), 3: _AcceptShowdownAgent()}

        turn_logs, done, _ = engine._play_turn(Random(12), context, seats, agents, 0)
        self.assertFalse(done)
        self.assertTrue(any("SHOWDOWN_PROPOSED" in str(entry["event"]) for entry in turn_logs))

        context.current_turn = 1
        turn_logs, done, outcome = engine._play_turn(Random(13), context, seats, agents, 1)
        self.assertFalse(done)
        self.assertIsNone(outcome)
        self.assertTrue(context.showdown_pending)
        self.assertEqual(context.current_turn, 1)


if __name__ == "__main__":
    unittest.main()
