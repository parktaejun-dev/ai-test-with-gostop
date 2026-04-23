from __future__ import annotations

import unittest

from agents import RandomAgent, ReplayPolicyAgent, RuleBasedAgent
from engine.actions import Action, ActionType
from engine.cards import build_deck
from engine.state import Phase, PublicGameState
from metrics.core import summarize_agent_results


class AgentMetricTests(unittest.TestCase):
    def _state(self):
        deck = build_deck()
        return PublicGameState(
            phase=Phase.TURN_START,
            hand_id=1,
            seat_id=0,
            dealer_seat=0,
            current_turn=0,
            alive_seats=(0, 1, 2),
            exited_seat=3,
            hand_cards=tuple(deck[:3]),
            table_cards=tuple(deck[3:5]),
            captured_cards_public={0: (), 1: (), 2: (), 3: ()},
            scores_public={0: 0, 1: 0, 2: 0, 3: 0},
            go_counts_public={0: 0, 1: 0, 2: 0, 3: 0},
            bankrolls_public={0: 1000, 1: 1000, 2: 1000, 3: 1000},
            carryover_multiplier=1,
            showdown_pending=False,
            showdown_proposer=None,
            showdown_responses={},
            legal_actions=(Action(ActionType.PLAY_CARD, card_id=deck[0].id), Action(ActionType.PLAY_CARD, card_id=deck[1].id)),
            decision_seed=11,
        )

    def test_random_agent_returns_legal_action(self):
        state = self._state()
        action = RandomAgent(name="r").select_action(state)
        self.assertIn(action, state.legal_actions)

    def test_replay_policy_reproducible(self):
        state = self._state()
        agent = ReplayPolicyAgent(name="p", policy=(1,))
        self.assertEqual(agent.select_action(state), state.legal_actions[1])

    def test_rule_based_returns_legal_action(self):
        state = self._state()
        action = RuleBasedAgent(name="rb").select_action(state)
        self.assertIn(action, state.legal_actions)

    def test_metrics_summary_contains_core_fields(self):
        fake_lineups = {
            ("A", "B", "C", "D"): {
                "session": {
                    "seats": {
                        0: type("S", (), {"bankroll": 1200})(),
                        1: type("S", (), {"bankroll": 800})(),
                        2: type("S", (), {"bankroll": 1000})(),
                        3: type("S", (), {"bankroll": 1000})(),
                    },
                    "hand_outcomes": [type("O", (), {"winner": 0})(), type("O", (), {"winner": 1})()],
                },
                "summary": {
                    "seat_to_name": {0: "A", 1: "B", 2: "C", 3: "D"},
                    "profit_by_seat": {0: 200, 1: -200, 2: 0, 3: 0},
                    "win_by_seat": {0: 1, 1: 1, 2: 0, 3: 0},
                    "showdown_events": 0,
                    "showdown_success_count": 0,
                    "showdown_proposals": {0: 1, 1: 0, 2: 0, 3: 0},
                    "showdown_accepts": {0: 0, 1: 1, 2: 1, 3: 0},
                    "showdown_rejects": {0: 0, 1: 0, 2: 0, 3: 0},
                    "showdown_ev_gains": {0: [5.0], 1: [], 2: [], 3: []},
                    "showdown_misplays": {0: [0.0], 1: [], 2: [], 3: []},
                    "forced_gwang_sell": {0: 0, 1: 0, 2: 1, 3: 0},
                    "early_exits": {0: 0, 1: 1, 2: 0, 3: 0},
                },
            }
        }
        summary = summarize_agent_results(fake_lineups)
        self.assertIn("A", summary)
        self.assertIn("mean_profit", summary["A"])
        self.assertIn("cvar_5", summary["A"])
        self.assertIn("sample_count", summary["A"])
        self.assertIn("cvar_5_effective_sample_size", summary["A"])
        self.assertEqual(summary["A"]["showdown_ev_gain"], 5.0)


if __name__ == "__main__":
    unittest.main()
