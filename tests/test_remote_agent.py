from __future__ import annotations

import io
import json
import os
import socket
import unittest
from unittest.mock import patch
from urllib import error

from agents.adapters import OpenRouterModelAgent, RemoteModelAgent, _serialize_state, _state_key
from engine.game import GameEngine
from engine.actions import Action, ActionType
from engine.cards import build_deck
from engine.state import GameConfig, Phase, PublicGameState, SeatState


class _FakeHTTPResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _TimeoutingHTTPResponse:
    def read(self):
        raise socket.timeout("timed out")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class RemoteAgentTests(unittest.TestCase):
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
            legal_actions=(
                Action(ActionType.PLAY_CARD, card_id=deck[0].id),
                Action(ActionType.PLAY_CARD, card_id=deck[1].id),
            ),
            decision_seed=17,
        )

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False)
    @patch("agents.adapters.request.urlopen")
    def test_remote_agent_uses_responses_api(self, mock_urlopen):
        mock_urlopen.return_value = _FakeHTTPResponse({"output_text": "{\"choice_index\": 1}"})
        agent = RemoteModelAgent(name="remote", model_id="gpt-4o-mini", prompt_template="Choose best action.")
        action = agent.select_action(self._state())
        self.assertEqual(action, self._state().legal_actions[1])
        request_obj = mock_urlopen.call_args.args[0]
        self.assertTrue(request_obj.full_url.endswith("/responses"))
        body = json.loads(request_obj.data.decode("utf-8"))
        self.assertEqual(body["model"], "gpt-4o-mini")
        self.assertEqual(body["text"]["format"]["type"], "json_schema")

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}, clear=False)
    @patch("agents.adapters.request.urlopen")
    def test_openrouter_agent_uses_chat_completions(self, mock_urlopen):
        mock_urlopen.return_value = _FakeHTTPResponse(
            {"choices": [{"message": {"content": "{\"choice_index\": 0}"}}]}
        )
        agent = OpenRouterModelAgent(
            name="openrouter",
            model_id="google/gemma-3-4b-it:free",
            prompt_template="Choose best action.",
        )
        action = agent.select_action(self._state())
        self.assertEqual(action, self._state().legal_actions[0])
        request_obj = mock_urlopen.call_args.args[0]
        self.assertTrue(request_obj.full_url.endswith("/chat/completions"))
        body = json.loads(request_obj.data.decode("utf-8"))
        self.assertEqual(body["model"], "google/gemma-3-4b-it:free")
        self.assertEqual(body["response_format"]["type"], "json_object")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False)
    @patch("agents.adapters.request.urlopen")
    def test_remote_agent_falls_back_to_first_action_on_malformed_response(self, mock_urlopen):
        mock_urlopen.return_value = _FakeHTTPResponse({"output_text": "not-json"})
        agent = RemoteModelAgent(name="remote", model_id="gpt-4o-mini", prompt_template="Choose best action.")
        action = agent.select_action(self._state())
        self.assertEqual(action, self._state().legal_actions[0])
        mock_urlopen.return_value = _FakeHTTPResponse({"output_text": "{\"choice_index\": 1}"})
        action = agent.select_action(self._state())
        self.assertEqual(action, self._state().legal_actions[1])

    def test_remote_agent_accepts_parseable_string_responder(self):
        agent = RemoteModelAgent(
            name="remote",
            model_id="gpt-4o-mini",
            prompt_template="Choose best action.",
            responder=lambda *args, **kwargs: "{\"choice_index\": 1}",
        )
        action = agent.select_action(self._state())
        self.assertEqual(action, self._state().legal_actions[1])

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False)
    @patch("agents.adapters.time.sleep")
    @patch("agents.adapters.request.urlopen")
    def test_remote_agent_retries_transient_http_error(self, mock_urlopen, mock_sleep):
        mock_urlopen.side_effect = [
            error.HTTPError(
                url="https://api.openai.com/v1/responses",
                code=500,
                msg="server error",
                hdrs=None,
                fp=io.BytesIO(b"temporary failure"),
            ),
            _FakeHTTPResponse({"output_text": "{\"choice_index\": 1}"}),
        ]
        agent = RemoteModelAgent(name="remote", model_id="gpt-4o-mini", prompt_template="Choose best action.")
        action = agent.select_action(self._state())
        self.assertEqual(action, self._state().legal_actions[1])
        self.assertEqual(mock_urlopen.call_count, 2)
        mock_sleep.assert_called_once()

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False)
    @patch("agents.adapters.time.sleep")
    @patch("agents.adapters.request.urlopen")
    def test_remote_agent_retries_request_timeout_http_error(self, mock_urlopen, mock_sleep):
        mock_urlopen.side_effect = [
            error.HTTPError(
                url="https://api.openai.com/v1/responses",
                code=408,
                msg="request timeout",
                hdrs=None,
                fp=io.BytesIO(b"timeout"),
            ),
            _FakeHTTPResponse({"output_text": "{\"choice_index\": 1}"}),
        ]
        agent = RemoteModelAgent(name="remote", model_id="gpt-4o-mini", prompt_template="Choose best action.")
        action = agent.select_action(self._state())
        self.assertEqual(action, self._state().legal_actions[1])
        self.assertEqual(mock_urlopen.call_count, 2)
        mock_sleep.assert_called_once()

    def test_remote_eval_hands_caps_engine_calls(self):
        deck = build_deck()
        legal_actions = [Action(ActionType.PLAY_CARD, card_id=deck[0].id)]
        seats = {
            0: SeatState(seat=0, agent_name="A", hand=[deck[0]], alive=True),
            1: SeatState(seat=1, agent_name="B", alive=True),
            2: SeatState(seat=2, agent_name="C", alive=True),
            3: SeatState(seat=3, agent_name="D", alive=False),
        }
        engine = GameEngine(GameConfig(session_hands=1, remote_eval_hands=0))
        agent = RemoteModelAgent(
            name="remote",
            model_id="gpt-4o-mini",
            prompt_template="Choose best action.",
            responder=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("responder should not be called")),
        )

        action = engine._choose_action(
            agent=agent,
            seats=seats,
            seat_id=0,
            phase=Phase.TURN_START,
            dealer=0,
            hand_id=1,
            current_turn=0,
            table_cards=[],
            carryover_multiplier=1,
            legal_actions=legal_actions,
            decision_seed=11,
            exited_seat=3,
        )

        self.assertEqual(action, legal_actions[0])

    def test_remote_agent_rejects_reserved_decoding_keys(self):
        with self.assertRaises(ValueError):
            RemoteModelAgent(
                name="remote",
                model_id="gpt-4o-mini",
                prompt_template="Choose best action.",
                decoding=(("model", "override"),),
            )

    def test_openrouter_agent_rejects_reserved_decoding_keys(self):
        with self.assertRaises(ValueError):
            OpenRouterModelAgent(
                name="openrouter",
                model_id="google/gemma-3-4b-it:free",
                prompt_template="Choose best action.",
                decoding=(("response_format", "override"),),
            )

    def test_serialize_state_includes_captured_cards_public(self):
        state = self._state()
        serialized = _serialize_state(state)
        self.assertIn("captured_cards_public", serialized)
        self.assertIn("\"hand_id\": 1", serialized)

    def test_state_key_changes_with_exited_and_showdown_state(self):
        state = self._state()
        other = PublicGameState(
            phase=state.phase,
            hand_id=state.hand_id + 1,
            seat_id=state.seat_id,
            dealer_seat=state.dealer_seat,
            current_turn=state.current_turn,
            alive_seats=state.alive_seats,
            exited_seat=None,
            hand_cards=state.hand_cards,
            table_cards=state.table_cards,
            captured_cards_public=state.captured_cards_public,
            scores_public=state.scores_public,
            go_counts_public=state.go_counts_public,
            bankrolls_public=state.bankrolls_public,
            carryover_multiplier=state.carryover_multiplier,
            showdown_pending=True,
            showdown_proposer=1,
            showdown_responses={1: "accept"},
            legal_actions=state.legal_actions,
            decision_seed=state.decision_seed,
        )

        self.assertNotEqual(_state_key(state), _state_key(other))

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}, clear=False)
    @patch("agents.adapters.request.urlopen")
    def test_openrouter_invalid_choice_index_falls_back_without_modulo(self, mock_urlopen):
        mock_urlopen.return_value = _FakeHTTPResponse(
            {"choices": [{"message": {"content": "{\"choice_index\": -1}"}}]}
        )
        agent = OpenRouterModelAgent(
            name="openrouter",
            model_id="google/gemma-3-4b-it:free",
            prompt_template="Choose best action.",
        )
        action = agent.select_action(self._state())
        self.assertEqual(action, self._state().legal_actions[0])
        mock_urlopen.return_value = _FakeHTTPResponse(
            {"choices": [{"message": {"content": "{\"choice_index\": 1}"}}]}
        )
        action = agent.select_action(self._state())
        self.assertEqual(action, self._state().legal_actions[1])

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}, clear=False)
    @patch("agents.adapters.request.urlopen")
    def test_openrouter_parses_array_message_content(self, mock_urlopen):
        mock_urlopen.return_value = _FakeHTTPResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": [
                                {"type": "text", "text": "{\"choice_index\": 1}"}
                            ]
                        }
                    }
                ]
            }
        )
        agent = OpenRouterModelAgent(
            name="openrouter",
            model_id="google/gemma-3-4b-it:free",
            prompt_template="Choose best action.",
        )
        action = agent.select_action(self._state())
        self.assertEqual(action, self._state().legal_actions[1])

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}, clear=False)
    @patch("agents.adapters.request.urlopen")
    def test_openrouter_falls_back_on_system_role_compatibility_error(self, mock_urlopen):
        mock_urlopen.side_effect = [
            error.HTTPError(
                url="https://openrouter.ai/api/v1/chat/completions",
                code=400,
                msg="bad request",
                hdrs=None,
                fp=io.BytesIO(b'{"error":{"message":"Unsupported value for messages[0].role: system"}}'),
            ),
            _FakeHTTPResponse({"choices": [{"message": {"content": "{\"choice_index\": 1}"}}]}),
        ]
        agent = OpenRouterModelAgent(
            name="openrouter",
            model_id="google/gemma-3-4b-it:free",
            prompt_template="Choose best action.",
        )
        action = agent.select_action(self._state())
        self.assertEqual(action, self._state().legal_actions[1])
        self.assertEqual(mock_urlopen.call_count, 2)
        fallback_body = json.loads(mock_urlopen.call_args_list[1].args[0].data.decode("utf-8"))
        self.assertEqual(len(fallback_body["messages"]), 1)
        self.assertEqual(fallback_body["messages"][0]["role"], "user")

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}, clear=False)
    @patch("agents.adapters.request.urlopen")
    def test_openrouter_falls_back_without_json_mode_when_unsupported(self, mock_urlopen):
        mock_urlopen.side_effect = [
            error.HTTPError(
                url="https://openrouter.ai/api/v1/chat/completions",
                code=400,
                msg="bad request",
                hdrs=None,
                fp=io.BytesIO(b'{"error":{"message":"response_format json_object is not supported for this model"}}'),
            ),
            _FakeHTTPResponse({"choices": [{"message": {"content": "{\"choice_index\": 1}"}}]}),
        ]
        agent = OpenRouterModelAgent(
            name="openrouter",
            model_id="google/gemma-3-4b-it:free",
            prompt_template="Choose best action.",
        )
        action = agent.select_action(self._state())
        self.assertEqual(action, self._state().legal_actions[1])
        self.assertEqual(mock_urlopen.call_count, 2)
        fallback_body = json.loads(mock_urlopen.call_args_list[1].args[0].data.decode("utf-8"))
        self.assertEqual([message["role"] for message in fallback_body["messages"]], ["system", "user"])
        self.assertNotIn("response_format", fallback_body)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False)
    @patch("agents.adapters.time.sleep")
    @patch("agents.adapters.request.urlopen")
    def test_remote_agent_retries_response_read_timeout(self, mock_urlopen, mock_sleep):
        mock_urlopen.side_effect = [
            _TimeoutingHTTPResponse(),
            _FakeHTTPResponse({"output_text": "{\"choice_index\": 1}"}),
        ]
        agent = RemoteModelAgent(name="remote", model_id="gpt-4o-mini", prompt_template="Choose best action.")
        action = agent.select_action(self._state())
        self.assertEqual(action, self._state().legal_actions[1])
        self.assertEqual(mock_urlopen.call_count, 2)
        mock_sleep.assert_called_once()


if __name__ == "__main__":
    unittest.main()
