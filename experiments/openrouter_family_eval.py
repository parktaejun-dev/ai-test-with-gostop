from __future__ import annotations

import argparse
import json
import re
import hashlib
from dataclasses import asdict
from datetime import datetime
from itertools import combinations, permutations
from pathlib import Path
from urllib import error, parse, request

from agents import OpenRouterModelAgent
from analysis import build_report, export_experiment_bundle
from engine.state import GameConfig
from simulator.runner import run_layouts


DEFAULT_PROMPT_TEMPLATE = (
    "You are a fixed Go-Stop evaluation policy. "
    "Choose one legal action index only. "
    "Optimize long-run profit with risk control. "
    "Do not explain."
)

FAMILY_FALLBACKS = {
    "gemma": [
        "google/gemma-3n-e2b-it:free",
        "google/gemma-3n-e4b-it:free",
        "google/gemma-4-26b-a4b-it:free",
        "google/gemma-4-31b-it:free",
    ],
    "gemma-4": [
        "google/gemma-4-26b-a4b-it:free",
        "google/gemma-4-31b-it:free",
    ],
    "gemma-3": [
        "google/gemma-3-4b-it:free",
        "google/gemma-3-12b-it:free",
        "google/gemma-3-27b-it:free",
    ],
}


def _parse_decoding(raw_values: list[str] | None) -> tuple[tuple[str, str], ...]:
    decoded = []
    for item in raw_values or []:
        if "=" not in item:
            raise ValueError(f"Invalid decoding entry '{item}': expected key=value")
        key, value = item.split("=", 1)
        decoded.append((key.strip(), value.strip()))
    return tuple(decoded)


def _prompt_signature(prompt: str) -> dict[str, str]:
    return {"sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(), "length": str(len(prompt))}


def parse_param_size_b(model_id: str) -> float:
    patterns = [
        r"-(\d+(?:\.\d+)?)b(?:-|$)",
        r"e(\d+(?:\.\d+)?)b(?:-|$)",
        r"/(\d+(?:\.\d+)?)b(?:-|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, model_id)
        if match:
            return float(match.group(1))
    return 0.0


def sort_unique_models(model_ids: list[str]) -> list[str]:
    return sorted(set(model_ids), key=parse_param_size_b)


def merge_model_lists(primary: list[str], fallback: list[str]) -> list[str]:
    merged: list[str] = []
    for model_id in [*primary, *fallback]:
        if model_id not in merged:
            merged.append(model_id)
    return merged


def normalize_selector_models(payload) -> list[str]:
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get("models") or payload.get("model_ids") or payload.get("items") or []
    else:
        items = []
    model_ids = []
    for item in items:
        if isinstance(item, str):
            model_ids.append(item)
            continue
        if isinstance(item, dict):
            model_id = item.get("id") or item.get("model_id") or item.get("name")
            if model_id:
                model_ids.append(model_id)
    return model_ids


def resolve_family_models(family: str) -> list[str]:
    selector_url = None
    try:
        from os import environ

        selector_url = environ.get("OPENROUTER_SELECTOR_URL")
        selector_token = environ.get("OPENROUTER_SELECTOR_TOKEN")
    except Exception:
        selector_url = None
        selector_token = None
    if selector_url:
        body = {
            "family": family,
            "free_only": True,
            "same_family_only": True,
            "strategy": "parameter_sweep",
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
        model_ids = normalize_selector_models(payload)
        if model_ids:
            fallback = FAMILY_FALLBACKS.get(family, [])
            merged = merge_model_lists(model_ids, fallback)
            return sort_unique_models(merged)
    fallback = FAMILY_FALLBACKS.get(family)
    if not fallback:
        raise RuntimeError(f"No selector result and no fallback configured for family '{family}'")
    return sort_unique_models(list(fallback))


def canonical_lineups(model_ids: list[str]) -> list[tuple[str, ...]]:
    if not model_ids:
        raise ValueError("At least one model is required")
    unique = list(dict.fromkeys(model_ids))
    if len(unique) >= 4:
        return [tuple(combo) for combo in combinations(unique, 4)]
    if len(unique) == 3:
        a, b, c = unique
        return [
            (a, b, c, a),
            (a, b, c, b),
            (a, b, c, c),
        ]
    if len(unique) == 2:
        a, b = unique
        return [(a, a, b, b)]
    return [(unique[0], unique[0], unique[0], unique[0])]


def expand_layouts(lineups: list[tuple[str, ...]]) -> list[tuple[str, ...]]:
    layouts = set()
    for lineup in lineups:
        layouts.update(set(permutations(lineup, 4)))
    return sorted(layouts)


def model_label(model_id: str) -> str:
    return model_id.replace("/", "__").replace(":", "__")


def model_metadata(model_ids: list[str]) -> list[dict[str, str | float]]:
    return [
        {
            "model_id": model_id,
            "parameter_size_b": parse_param_size_b(model_id),
        }
        for model_id in model_ids
    ]


def select_reference_model(model_ids: list[str]) -> str:
    unique = list(dict.fromkeys(model_ids))
    if not unique:
        raise ValueError("At least one model is required")
    positive_sizes = [model_id for model_id in unique if parse_param_size_b(model_id) > 0]
    if positive_sizes:
        return min(positive_sizes, key=lambda model_id: (parse_param_size_b(model_id), model_id))
    return unique[0]


def run_family_eval(
    family: str,
    *,
    base_seed: int,
    session_hands: int | None = None,
    layout_repetitions: int = 10,
    max_carryover_multiplier: int = 64,
    initial_bankroll: int,
    stake_per_point: int,
    output_dir: str,
    prompt_template: str = DEFAULT_PROMPT_TEMPLATE,
    decoding: tuple[tuple[str, str], ...] = (),
) -> dict:
    model_ids = resolve_family_models(family)
    layouts = expand_layouts(canonical_lineups(model_ids))
    confirmatory_baseline = select_reference_model(model_ids)
    config = GameConfig(
        session_hands=session_hands,
        layout_repetitions=layout_repetitions,
        max_carryover_multiplier=max_carryover_multiplier,
        initial_bankroll=initial_bankroll,
        stake_per_point=stake_per_point,
    )
    factories = {
        model_id: (
            lambda mid=model_id: OpenRouterModelAgent(
                name=model_label(mid),
                model_id=mid,
                prompt_template=prompt_template,
                decoding=decoding,
            )
        )
        for model_id in model_ids
    }
    result = run_layouts(
        layouts,
        agent_factories=factories,
        config=config,
        base_seed=base_seed,
        layout_repetitions=config.layout_repetitions,
    )
    report = build_report(result, confirmatory_baseline=confirmatory_baseline)
    bundle = export_experiment_bundle(
        output_dir,
        config={
            "experiment": "openrouter_family_eval",
            "family": family,
            "resolved_models": model_ids,
            "resolved_model_metadata": model_metadata(model_ids),
            "confirmatory_baseline": confirmatory_baseline,
            "base_seed": base_seed,
            "prompt_template": prompt_template,
            "prompt_signature": _prompt_signature(prompt_template),
            "decoding": decoding,
            **asdict(config),
        },
        report=report,
        cross_play_result=result,
    )
    return {
        "models": model_ids,
        "layouts": layouts,
        "confirmatory_baseline": confirmatory_baseline,
        "report": report,
        "bundle": bundle,
        "cross_play_result": result,
    }


def _parse_args():
    parser = argparse.ArgumentParser(description="Run same-family OpenRouter free-model parameter sweep.")
    parser.add_argument("--family", default="gemma")
    parser.add_argument("--base-seed", type=int, default=7)
    parser.add_argument("--session-hands", type=int, default=None)
    parser.add_argument("--layout-repetitions", type=int, default=10)
    parser.add_argument("--max-carryover", type=int, default=64)
    parser.add_argument("--initial-bankroll", type=int, default=100_000)
    parser.add_argument("--stake-per-point", type=int, default=100)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--prompt-file", default="")
    parser.add_argument("--decoding", action="append", default=None)
    return parser.parse_args()


def _default_output_dir(prefix: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"results/{prefix}_{stamp}"


def main() -> None:
    args = _parse_args()
    prompt = DEFAULT_PROMPT_TEMPLATE
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    output_dir = args.output_dir or _default_output_dir("openrouter_family")
    decoding = _parse_decoding(args.decoding)
    result = run_family_eval(
        args.family,
        base_seed=args.base_seed,
        session_hands=args.session_hands,
        layout_repetitions=args.layout_repetitions,
        max_carryover_multiplier=args.max_carryover,
        initial_bankroll=args.initial_bankroll,
        stake_per_point=args.stake_per_point,
        output_dir=output_dir,
        prompt_template=prompt,
        decoding=decoding,
    )
    print(
        json.dumps(
            {
                "confirmatory_baseline": result["confirmatory_baseline"],
                "models": result["models"],
                "layout_count": len(result["layouts"]),
                "bundle": result["bundle"],
                "ranking": result["report"]["ranking"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
