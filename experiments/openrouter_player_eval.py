from __future__ import annotations

import argparse
import json
import hashlib
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

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


def parse_seat_models_arg(raw: str) -> list[str]:
    models = []
    for item in raw.split(","):
        model_id = item.strip()
        if model_id:
            models.append(model_id)
    if len(models) != 4:
        raise ValueError("Exactly four seat model ids are required")
    return models


def _seat_names(seat_models: list[str]) -> list[str]:
    return [f"seat{index + 1}:{model}" for index, model in enumerate(seat_models)]


def run_player_eval(
    seat_models: list[str],
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
    if len(seat_models) != 4:
        raise ValueError("Exactly four seat model ids are required")

    seat_names = _seat_names(seat_models)
    layout = tuple(seat_names)
    config = GameConfig(
        session_hands=session_hands,
        layout_repetitions=layout_repetitions,
        max_carryover_multiplier=max_carryover_multiplier,
        initial_bankroll=initial_bankroll,
        stake_per_point=stake_per_point,
    )
    factories = {
        seat_name: (
            lambda mid=model_id, seat=seat_name: OpenRouterModelAgent(
                name=seat,
                model_id=mid,
                prompt_template=prompt_template,
                decoding=decoding,
            )
        )
        for seat_name, model_id in zip(seat_names, seat_models, strict=True)
    }
    result = run_layouts(
        [layout],
        agent_factories=factories,
        config=config,
        base_seed=base_seed,
        layout_repetitions=config.layout_repetitions,
    )
    report = build_report(result)
    bundle = export_experiment_bundle(
        output_dir,
        config={
            "experiment": "openrouter_player_eval",
            "seat_models": seat_models,
            "seat_names": seat_names,
            "base_seed": base_seed,
            "prompt_signature": _prompt_signature(prompt_template),
            "decoding": decoding,
            **asdict(config),
        },
        report=report,
        cross_play_result=result,
    )
    return {
        "seat_models": seat_models,
        "seat_names": seat_names,
        "layouts": [layout],
        "report": report,
        "bundle": bundle,
    }


def _parse_args():
    parser = argparse.ArgumentParser(description="Run a fixed 4-seat OpenRouter lineup.")
    parser.add_argument("--seat-models", required=True, help="Comma-separated OpenRouter model ids for 4 seats.")
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
    seat_models = parse_seat_models_arg(args.seat_models)
    output_dir = args.output_dir or _default_output_dir("openrouter_player")
    prompt = DEFAULT_PROMPT_TEMPLATE
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    decoding = _parse_decoding(args.decoding)
    result = run_player_eval(
        seat_models,
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
                "seat_models": result["seat_models"],
                "seat_names": result["seat_names"],
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
