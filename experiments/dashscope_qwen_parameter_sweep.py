from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from agents import DashScopeModelAgent
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

QWEN_FOUR_MODEL_PARAMETER_PANEL = (
    "qwen3-coder-30b-a3b-instruct",
    "qwen3.5-122b-a10b",
    "qwen3.5-397b-a17b",
    "qwen3-coder-480b-a35b-instruct",
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


def _active_param_size_b(model_id: str) -> float:
    match = re.search(r"-a(\d+(?:\.\d+)?)b(?:-|$)", model_id)
    if not match:
        return 0.0
    return float(match.group(1))


def model_metadata(model_ids: list[str]) -> list[dict[str, str | float]]:
    return [
        {
            "model_id": model_id,
            "parameter_size_b": parse_param_size_b(model_id),
            "active_parameter_size_b": _active_param_size_b(model_id),
        }
        for model_id in model_ids
    ]


def parse_models_arg(raw: str | None) -> list[str]:
    if not raw:
        return list(QWEN_FOUR_MODEL_PARAMETER_PANEL)
    models = []
    for item in raw.split(","):
        model_id = item.strip()
        if model_id:
            models.append(model_id)
    deduped = list(dict.fromkeys(models))
    if len(deduped) < 2:
        raise ValueError("At least two Qwen model ids are required")
    return deduped


def run_parameter_sweep(
    model_ids: list[str],
    *,
    base_seed: int,
    session_hands: int | None = 10,
    layout_repetitions: int = 1,
    remote_eval_hands: int = 10,
    max_carryover_multiplier: int = 64,
    initial_bankroll: int,
    stake_per_point: int,
    output_dir: str,
    prompt_template: str = DEFAULT_PROMPT_TEMPLATE,
    decoding: tuple[tuple[str, str], ...] = (),
) -> dict:
    model_ids = list(dict.fromkeys(model_ids))
    if len(model_ids) < 2:
        raise ValueError("At least two Qwen model ids are required")

    layouts = expand_layouts(canonical_lineups(model_ids))
    confirmatory_baseline = min(model_ids, key=lambda model_id: (parse_param_size_b(model_id), model_id))
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
            lambda mid=model_id: DashScopeModelAgent(
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
            "experiment": "dashscope_qwen_parameter_sweep",
            "family": "qwen",
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
    parser = argparse.ArgumentParser(description="Run same-family Qwen parameter-size sweep on DashScope.")
    parser.add_argument("--models", default="", help="Comma-separated Qwen model ids. Defaults to 30B/122B/397B/480B Qwen panel.")
    parser.add_argument("--base-seed", type=int, default=7)
    parser.add_argument("--session-hands", type=int, default=10)
    parser.add_argument("--layout-repetitions", type=int, default=1)
    parser.add_argument("--remote-eval-hands", type=int, default=10)
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
    output_dir = args.output_dir or _default_output_dir("dashscope_qwen_parameter")
    decoding = _parse_decoding(args.decoding)
    result = run_parameter_sweep(
        model_ids,
        base_seed=args.base_seed,
        session_hands=args.session_hands,
        layout_repetitions=args.layout_repetitions,
        remote_eval_hands=args.remote_eval_hands,
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
