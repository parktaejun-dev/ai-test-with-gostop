from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from urllib import error, request

from experiments.openrouter_family_eval import merge_model_lists, normalize_selector_models, parse_param_size_b


PROMPT_DIR = Path(__file__).resolve().parent / "prompts" / "factorial"
FIXED_MODEL_PANEL_ID = "openrouter_cross_vendor_panel_v1"
FIXED_MODEL_PANEL = (
    "google/gemma-3-27b-it:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
)
SELECTOR_MODEL_PANEL_ID = "openrouter_cross_vendor_panel_selector_v1"
STRATEGY_REGISTRY = (
    ("balanced", "Balanced", "balanced.txt"),
    ("analytic", "Analytic", "analytic.txt"),
    ("conservative", "Conservative", "conservative.txt"),
    ("aggressive", "Aggressive", "aggressive.txt"),
)


def _prompt_signature(prompt: str) -> dict[str, str]:
    return {"sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(), "length": str(len(prompt))}


@dataclass(frozen=True, slots=True)
class StrategyPrompt:
    strategy_id: str
    label: str
    path: str
    text: str
    signature: dict[str, str]

    def to_manifest(self) -> dict[str, str]:
        return {
            "strategy_id": self.strategy_id,
            "label": self.label,
            "path": self.path,
            "prompt_sha256": self.signature["sha256"],
            "prompt_length": self.signature["length"],
        }


@dataclass(frozen=True, slots=True)
class ResolvedFactorialPanel:
    panel_id: str
    source: str
    model_ids: tuple[str, ...]


def _selector_models() -> list[str]:
    try:
        from os import environ

        selector_url = environ.get("OPENROUTER_SELECTOR_URL")
        selector_token = environ.get("OPENROUTER_SELECTOR_TOKEN")
    except Exception:
        selector_url = None
        selector_token = None
    if not selector_url:
        return []
    body = {
        "free_only": True,
        "same_family_only": False,
        "strategy": "fixed_factorial_panel",
    }
    headers = {"Content-Type": "application/json"}
    if selector_token:
        headers["Authorization"] = f"Bearer {selector_token}"
    req = request.Request(
        selector_url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Selector request failed: {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Selector request failed: {exc.reason}") from exc
    return normalize_selector_models(payload)


def resolve_fixed_model_panel() -> ResolvedFactorialPanel:
    selector_models = _selector_models()
    if selector_models:
        merged = merge_model_lists(selector_models, list(FIXED_MODEL_PANEL))
        if len(merged) >= 4:
            return ResolvedFactorialPanel(
                panel_id=SELECTOR_MODEL_PANEL_ID,
                source="selector",
                model_ids=tuple(merged[:4]),
            )
    if len(FIXED_MODEL_PANEL) < 4:
        raise RuntimeError("Factorial model panel requires at least four models")
    return ResolvedFactorialPanel(
        panel_id=FIXED_MODEL_PANEL_ID,
        source="fallback",
        model_ids=tuple(FIXED_MODEL_PANEL[:4]),
    )


def fixed_model_panel_metadata(model_panel: tuple[str, ...] | None = None) -> list[dict[str, str | float]]:
    panel = tuple(model_panel or FIXED_MODEL_PANEL)
    return [
        {
            "model_id": model_id,
            "parameter_size_b": parse_param_size_b(model_id),
        }
        for model_id in panel
    ]


def fixed_model_panel_signature(model_panel: tuple[str, ...] | None = None) -> str:
    panel = tuple(model_panel or FIXED_MODEL_PANEL)
    payload = json.dumps(list(panel), ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_factorial_strategies() -> tuple[StrategyPrompt, ...]:
    prompts = []
    for strategy_id, label, filename in STRATEGY_REGISTRY:
        path = PROMPT_DIR / filename
        text = path.read_text(encoding="utf-8").strip()
        prompts.append(
            StrategyPrompt(
                strategy_id=strategy_id,
                label=label,
                path=str(path),
                text=text,
                signature=_prompt_signature(text),
            )
        )
    return tuple(prompts)
