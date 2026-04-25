from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from agents import NvidiaModelAgent
from analysis import build_report, export_experiment_bundle
from engine.state import GameConfig
from experiments.openrouter_family_eval import canonical_lineups, expand_layouts, model_label, parse_param_size_b
from simulator.runner import run_layouts


DEFAULT_PROMPT_TEMPLATE = (
    "You are a fixed Go-Stop evaluation policy. "
    "Choose one legal action index only. "
    "Optimize long-run profit with risk control. "
    "Do not explain."
)

NVIDIA_120B_CROSS_FAMILY_PANEL = (
    "qwen/qwen3.5-122b-a10b",
    "mistralai/mistral-small-4-119b-2603",
    "nvidia/nemotron-3-super-120b-a12b",
    "stockmark/stockmark-2-100b-instruct",
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


def parse_models_arg(raw: str | None) -> list[str]:
    if not raw:
        return list(NVIDIA_120B_CROSS_FAMILY_PANEL)
    models = []
    for item in raw.split(","):
        model_id = item.strip()
        if model_id:
            models.append(model_id)
    deduped = list(dict.fromkeys(models))
    if len(deduped) < 2:
        raise ValueError("At least two NVIDIA model ids are required")
    return deduped


def model_metadata(model_ids: list[str]) -> list[dict[str, str | float]]:
    return [
        {
            "model_id": model_id,
            "family": model_id.split("/", 1)[0] if "/" in model_id else model_id,
            "parameter_size_b": parse_param_size_b(model_id),
        }
        for model_id in model_ids
    ]


def run_same_size_family_eval(
    model_ids: list[str],
    *,
    base_seed: int,
    session_hands: int | None = 10,
    layout_repetitions: int = 1,
    remote_eval_hands: int = 10,
    max_remote_calls_per_agent: int | None = None,
    max_carryover_multiplier: int = 64,
    initial_bankroll: int,
    stake_per_point: int,
    output_dir: str,
    prompt_template: str = DEFAULT_PROMPT_TEMPLATE,
    decoding: tuple[tuple[str, str], ...] = (),
) -> dict:
    model_ids = list(dict.fromkeys(model_ids))
    if len(model_ids) < 2:
        raise ValueError("At least two NVIDIA model ids are required")

    layouts = expand_layouts(canonical_lineups(model_ids))
    confirmatory_baseline = model_ids[0]
    config = GameConfig(
        session_hands=session_hands,
        layout_repetitions=layout_repetitions,
        remote_eval_hands=remote_eval_hands,
        max_carryover_multiplier=max_carryover_multiplier,
        initial_bankroll=initial_bankroll,
        stake_per_point=stake_per_point,
    )
    factories = {
        model_id: (
            lambda mid=model_id: NvidiaModelAgent(
                name=model_label(mid),
                model_id=mid,
                prompt_template=prompt_template,
                decoding=decoding,
                max_calls=max_remote_calls_per_agent,
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
            "experiment": "nvidia_same_size_family_eval",
            "parameter_size_target_b": 120.0,
            "max_remote_calls_per_agent": max_remote_calls_per_agent,
            "resolved_models": model_ids,
            "resolved_model_metadata": model_metadata(model_ids),
            "confirmatory_baseline": confirmatory_baseline,
            "base_seed": base_seed,
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
    parser = argparse.ArgumentParser(description="Run same-size cross-family evaluation on NVIDIA Build NIM.")
    parser.add_argument("--models", default="", help="Comma-separated NVIDIA model ids. Defaults to 120B-ish cross-family panel.")
    parser.add_argument("--base-seed", type=int, default=7)
    parser.add_argument("--session-hands", type=int, default=10)
    parser.add_argument("--layout-repetitions", type=int, default=1)
    parser.add_argument("--remote-eval-hands", type=int, default=10)
    parser.add_argument("--max-remote-calls-per-agent", type=int, default=None)
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
    model_ids = parse_models_arg(args.models)
    prompt = DEFAULT_PROMPT_TEMPLATE
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    output_dir = args.output_dir or _default_output_dir("nvidia_120b_family")
    decoding = _parse_decoding(args.decoding)
    result = run_same_size_family_eval(
        model_ids,
        base_seed=args.base_seed,
        session_hands=args.session_hands,
        layout_repetitions=args.layout_repetitions,
        remote_eval_hands=args.remote_eval_hands,
        max_remote_calls_per_agent=args.max_remote_calls_per_agent,
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
