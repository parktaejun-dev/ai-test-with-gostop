from __future__ import annotations

import hashlib
import socket
import json
import os
import time
from http.client import IncompleteRead
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib import error, request

from agents.base import Agent


RESPONSES_RESERVED_DECODING_FIELDS = frozenset({"model", "input", "text"})
OPENROUTER_RESERVED_DECODING_FIELDS = frozenset({"model", "messages", "response_format"})


def _state_key(state) -> str:
    payload = {
        "phase": str(state.phase),
        "hand_id": state.hand_id,
        "seat_id": state.seat_id,
        "dealer_seat": state.dealer_seat,
        "current_turn": state.current_turn,
        "alive_seats": state.alive_seats,
        "exited_seat": state.exited_seat,
        "hand_cards": [card.id for card in state.hand_cards],
        "table_cards": [card.id for card in state.table_cards],
        "captured_cards_public": {
            seat: [card.id for card in cards]
            for seat, cards in state.captured_cards_public.items()
        },
        "scores_public": state.scores_public,
        "go_counts_public": state.go_counts_public,
        "bankrolls_public": state.bankrolls_public,
        "carryover_multiplier": state.carryover_multiplier,
        "showdown_pending": state.showdown_pending,
        "showdown_proposer": state.showdown_proposer,
        "showdown_responses": state.showdown_responses,
        "legal_actions": [str(action) for action in state.legal_actions],
        "decision_seed": state.decision_seed,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def _serialize_state(state) -> str:
    payload = {
        "phase": str(state.phase),
        "hand_id": state.hand_id,
        "seat_id": state.seat_id,
        "dealer_seat": state.dealer_seat,
        "current_turn": state.current_turn,
        "alive_seats": list(state.alive_seats),
        "exited_seat": state.exited_seat,
        "hand_cards": [
            {
                "id": card.id,
                "month": card.month,
                "bright": getattr(card, "bright", False),
                "animal": getattr(card, "animal", False),
                "ribbon": getattr(card, "ribbon", False),
                "junk_value": getattr(card, "junk_value", 0),
            }
            for card in state.hand_cards
        ],
        "table_cards": [
            {
                "id": card.id,
                "month": card.month,
                "bright": getattr(card, "bright", False),
                "animal": getattr(card, "animal", False),
                "ribbon": getattr(card, "ribbon", False),
                "junk_value": getattr(card, "junk_value", 0),
            }
            for card in state.table_cards
        ],
        "captured_cards_public": {
            seat: [
                {
                    "id": card.id,
                    "month": card.month,
                    "bright": getattr(card, "bright", False),
                    "animal": getattr(card, "animal", False),
                    "ribbon": getattr(card, "ribbon", False),
                    "junk_value": getattr(card, "junk_value", 0),
                }
                for card in cards
            ]
            for seat, cards in state.captured_cards_public.items()
        },
        "scores_public": state.scores_public,
        "go_counts_public": state.go_counts_public,
        "bankrolls_public": state.bankrolls_public,
        "carryover_multiplier": state.carryover_multiplier,
        "showdown_pending": state.showdown_pending,
        "showdown_proposer": state.showdown_proposer,
        "showdown_responses": state.showdown_responses,
        "legal_actions": [
            {
                "index": index,
                "type": action.type.value,
                "card_id": action.card_id,
                "month": action.month,
                "target_card_id": action.target_card_id,
                "choice": action.choice,
                "showdown_payload": list(action.showdown_payload),
            }
            for index, action in enumerate(state.legal_actions)
        ],
        "decision_seed": state.decision_seed,
    }
    return json.dumps(payload, ensure_ascii=True, sort_keys=True)


def _coerce_to_choice(raw: Any) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float) and raw.is_integer():
        return int(raw)
    if isinstance(raw, str):
        stripped = raw.strip()
        if not stripped:
            return None
        if stripped.isdigit() or (stripped.startswith("-") and stripped[1:].isdigit()):
            try:
                return int(stripped)
            except ValueError:
                pass
        try:
            parsed = json.loads(stripped)
            nested = _coerce_to_choice(parsed)
            if nested is not None:
                return nested
        except Exception:
            pass
        return None
    if isinstance(raw, dict):
        if "choice_index" in raw:
            value = _coerce_to_choice(raw.get("choice_index"))
            if value is not None:
                return value
        for key in ("choice", "index", "action", "action_index"):
            if key in raw:
                value = _coerce_to_choice(raw.get(key))
                if value is not None:
                    return value
        for key in ("data", "payload"):
            nested = _coerce_to_choice(raw.get(key))
            if nested is not None:
                return nested
        for value in raw.values():
            nested = _coerce_to_choice(value)
            if nested is not None:
                return nested
    if isinstance(raw, (list, tuple)):
        for item in raw:
            nested = _coerce_to_choice(item)
            if nested is not None:
                return nested
    return None


def _extract_choice_index(response_payload: Any) -> int:
    candidates = []
    if isinstance(response_payload, dict):
        output_text = response_payload.get("output_text")
        if output_text:
            candidates.append(output_text)
        output = response_payload.get("output", [])
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict):
                    candidates.append(item)
                    continue
                content = item.get("content", [])
                if isinstance(content, str):
                    candidates.append(content)
                elif isinstance(content, list):
                    for content_item in content:
                        if isinstance(content_item, str):
                            candidates.append(content_item)
                        elif isinstance(content_item, dict):
                            candidates.append(content_item.get("text"))
                            candidates.append(content_item.get("value"))
                            candidates.append(content_item)
                candidates.append(item.get("text"))
        candidates.append(response_payload.get("choice_index"))
        choices = response_payload.get("choices", [])
        if isinstance(choices, list):
            for choice in choices:
                if not isinstance(choice, dict):
                    candidates.append(choice)
                    continue
                message = choice.get("message", {})
                if isinstance(message, dict):
                    candidates.append(message.get("content"))
                else:
                    candidates.append(message)
    elif isinstance(response_payload, (str, int, float, dict, list)):
        candidates.append(response_payload)

    for candidate in candidates:
        value = _coerce_to_choice(candidate)
        if value is not None:
            return value
    raise RuntimeError("No parsable choice_index found in API response")


def _validated_choice_index(choice_index: int, action_count: int) -> int:
    if not 0 <= choice_index < action_count:
        raise RuntimeError(f"choice_index out of range: {choice_index}")
    return choice_index


def _post_with_retries(url: str, payload: bytes, headers: dict[str, str], *, max_attempts: int = 3, timeout: int = 60) -> str:
    for attempt in range(1, max_attempts + 1):
        req = request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=timeout) as response:
                return response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if attempt >= max_attempts or exc.code not in {408, 429, 500, 502, 503, 504}:
                raise RuntimeError(f"API request failed: {exc.code} {detail}") from exc
            backoff = 2 ** (attempt - 1) * 0.5
            time.sleep(backoff)
        except (error.URLError, TimeoutError, socket.timeout, IncompleteRead) as exc:
            if attempt >= max_attempts:
                reason = getattr(exc, "reason", str(exc))
                raise RuntimeError(f"API request failed: {reason}") from exc
            backoff = 2 ** (attempt - 1) * 0.5
            time.sleep(backoff)
    raise RuntimeError("API request exhausted retry budget")


def _coerce_decoding(decoding: dict) -> dict:
    coerced = {}
    for key, value in decoding.items():
        if isinstance(value, str):
            lowered = value.lower()
            if lowered in {"true", "false"}:
                coerced[key] = lowered == "true"
                continue
            try:
                coerced[key] = int(value)
                continue
            except ValueError:
                try:
                    coerced[key] = float(value)
                    continue
                except ValueError:
                    coerced[key] = value
                    continue
        coerced[key] = value
    return coerced


def _validate_decoding_keys(decoding: dict, reserved_fields: frozenset[str]) -> None:
    blocked = sorted(set(decoding) & set(reserved_fields))
    if blocked:
        names = ", ".join(blocked)
        raise ValueError(f"decoding cannot override reserved request fields: {names}")


def _responses_api_responder(prompt_template: str, state, model_id: str, decoding: dict) -> dict:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    decoding_options = _coerce_decoding(decoding)
    _validate_decoding_keys(decoding_options, RESPONSES_RESERVED_DECODING_FIELDS)
    body = {
        "model": model_id,
        "input": [
            {
                "role": "developer",
                "content": [{"type": "input_text", "text": prompt_template}],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Return JSON only. Choose exactly one legal action by its integer index.\n"
                            f"{_serialize_state(state)}"
                        ),
                    }
                ],
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "action_choice",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "choice_index": {"type": "integer", "minimum": 0},
                    },
                    "required": ["choice_index"],
                    "additionalProperties": False,
                },
            }
        },
    }
    body.update(decoding_options)
    payload = json.dumps(body).encode("utf-8")
    raw = _post_with_retries(
        f"{base_url}/responses",
        payload=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    parsed = json.loads(raw)
    return {"choice_index": _extract_choice_index(parsed)}


def _chat_choice_index(response_payload: dict) -> int:
    return _extract_choice_index(response_payload)


def _should_fallback_openrouter_role(detail: str) -> bool:
    lowered = detail.lower()
    if "developer instruction is not enabled" in lowered:
        return True
    if "messages[0].role" in lowered and any(role in lowered for role in ("system", "developer")):
        return True
    if "unsupported role" in lowered and any(role in lowered for role in ("system", "developer")):
        return True
    if "invalid role" in lowered and any(role in lowered for role in ("system", "developer")):
        return True
    if "not supported" in lowered and any(token in lowered for token in ("system message", "developer message", "system role", "developer role")):
        return True
    if "unsupported value" in lowered and any(role in lowered for role in ("system", "developer")):
        return True
    return False


def _should_fallback_openrouter_json_mode(detail: str) -> bool:
    lowered = detail.lower()
    if "response_format" in lowered and any(token in lowered for token in ("not supported", "unsupported", "invalid", "must be")):
        return True
    if "json_object" in lowered and any(token in lowered for token in ("not supported", "unsupported", "invalid")):
        return True
    if "json mode" in lowered and any(token in lowered for token in ("not supported", "unsupported", "invalid")):
        return True
    return False


def _openrouter_api_responder(prompt_template: str, state, model_id: str, decoding: dict) -> dict:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
    decoding_options = _coerce_decoding(decoding)
    _validate_decoding_keys(decoding_options, OPENROUTER_RESERVED_DECODING_FIELDS)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    http_referer = os.environ.get("OPENROUTER_HTTP_REFERER")
    app_title = os.environ.get("OPENROUTER_APP_TITLE")
    if http_referer:
        headers["HTTP-Referer"] = http_referer
    if app_title:
        headers["X-Title"] = app_title

    def _request_with_messages(messages: list[dict[str, str]], *, response_format_mode: str | None) -> str:
        body = {
            "model": model_id,
            "messages": messages,
        }
        if response_format_mode == "json_object":
            body["response_format"] = {"type": "json_object"}
        elif response_format_mode == "json_schema":
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "action_choice",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "choice_index": {"type": "integer", "minimum": 0},
                        },
                        "required": ["choice_index"],
                        "additionalProperties": False,
                    },
                },
            }
        body.update(decoding_options)
        return _post_with_retries(
            f"{base_url}/chat/completions",
            payload=json.dumps(body).encode("utf-8"),
            headers=headers,
        )

    primary_messages = [
        {
            "role": "system",
            "content": (
                f"{prompt_template}\n"
                "Return JSON only with exactly one key: choice_index."
            ),
        },
        {
            "role": "user",
            "content": _serialize_state(state),
        },
    ]

    fallback_messages = [
        {
            "role": "user",
            "content": (
                f"{prompt_template}\n"
                "Return JSON only with exactly one key: choice_index.\n\n"
                f"{_serialize_state(state)}"
            ),
        }
    ]

    variants = [(primary_messages, "json_object")]
    attempted = set()
    last_exc: RuntimeError | None = None
    while variants:
        messages, response_format_mode = variants.pop(0)
        variant_key = (tuple(message["role"] for message in messages), response_format_mode)
        if variant_key in attempted:
            continue
        attempted.add(variant_key)
        try:
            raw = _request_with_messages(messages, response_format_mode=response_format_mode)
            break
        except RuntimeError as exc:
            last_exc = exc
            detail = str(exc)
            if _should_fallback_openrouter_role(detail):
                variants.append((fallback_messages, response_format_mode))
            if _should_fallback_openrouter_json_mode(detail):
                variants.append((messages, "json_schema"))
                variants.append((messages, None))
    else:
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("OpenRouter request failed without a specific exception")

    parsed = json.loads(raw)
    return {"choice_index": _chat_choice_index(parsed)}


@dataclass(frozen=True, slots=True)
class ReplayPolicyAgent(Agent):
    policy: tuple[int, ...] = ()

    def select_action(self, state):
        if not self.policy:
            return state.legal_actions[0]
        index = self.policy[(state.hand_id - 1) % len(self.policy)] % len(state.legal_actions)
        return state.legal_actions[index]


@dataclass(frozen=True, slots=True)
class RemoteModelAgent(Agent):
    model_id: str
    prompt_template: str
    decoding: tuple[tuple[str, str], ...] = ()
    responder: Callable | None = None
    _cache: dict[str, int] = field(default_factory=dict, init=False, repr=False, compare=False)

    def __post_init__(self):
        _validate_decoding_keys(dict(self.decoding), RESPONSES_RESERVED_DECODING_FIELDS)

    def select_action(self, state):
        key = _state_key(state)
        cache = object.__getattribute__(self, "_cache")
        if key in cache:
            return state.legal_actions[cache[key]]
        responder = self.responder or _responses_api_responder
        try:
            response = responder(self.prompt_template, state, self.model_id, dict(self.decoding))
            choice_index = _extract_choice_index(response)
            choice_index = _validated_choice_index(choice_index, len(state.legal_actions))
        except Exception:
            return state.legal_actions[0]
        cache[key] = choice_index
        return state.legal_actions[choice_index]


@dataclass(frozen=True, slots=True)
class OpenRouterModelAgent(Agent):
    model_id: str
    prompt_template: str
    decoding: tuple[tuple[str, str], ...] = ()
    responder: Callable | None = None
    _cache: dict[str, int] = field(default_factory=dict, init=False, repr=False, compare=False)

    def __post_init__(self):
        _validate_decoding_keys(dict(self.decoding), OPENROUTER_RESERVED_DECODING_FIELDS)

    def select_action(self, state):
        key = _state_key(state)
        cache = object.__getattribute__(self, "_cache")
        if key in cache:
            return state.legal_actions[cache[key]]
        responder = self.responder or _openrouter_api_responder
        try:
            response = responder(self.prompt_template, state, self.model_id, dict(self.decoding))
            choice_index = _extract_choice_index(response)
            choice_index = _validated_choice_index(choice_index, len(state.legal_actions))
        except Exception:
            return state.legal_actions[0]
        cache[key] = choice_index
        return state.legal_actions[choice_index]
