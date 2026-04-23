from __future__ import annotations

import argparse
import json
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agents import OpenRouterModelAgent
from analysis import build_report, export_experiment_bundle
from engine.state import GameConfig
from experiments.openrouter_family_eval import (
    DEFAULT_PROMPT_TEMPLATE,
    _parse_decoding,
    _prompt_signature,
    canonical_lineups,
    expand_layouts,
    model_label,
    model_metadata,
    resolve_family_models,
    select_reference_model,
)
from metrics.core import summarize_agent_results
from simulator.runner import run_layouts


def _parse_base_seeds(raw: str) -> list[int]:
    seeds = []
    for item in raw.split(","):
        item = item.strip()
        if item:
            seeds.append(int(item))
    if not seeds:
        raise ValueError("At least one base seed is required")
    return seeds


def _default_output_dir(prefix: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"results/{prefix}_{stamp}"


def _aggregate_results(results_by_seed: list[tuple[int, dict]]) -> dict:
    aggregate = {"lineups": {}, "agent_summary": {}}
    global_session_id = 0
    global_layout_id = 0
    for base_seed, result in results_by_seed:
        for lineup_key, payload in result.get("lineups", {}).items():
            session_payload = deepcopy(payload["session"])
            session_logs = []
            for entry in session_payload.get("logs", []):
                annotated = dict(entry)
                annotated["base_seed"] = base_seed
                annotated["layout_id"] = global_layout_id
                annotated["session_id"] = global_session_id
                session_logs.append(annotated)
            session_payload["logs"] = session_logs
            aggregate["lineups"][(base_seed, lineup_key)] = {
                "session": session_payload,
                "summary": payload["summary"],
            }
            global_session_id += 1
            global_layout_id += 1
    aggregate["agent_summary"] = summarize_agent_results(aggregate["lineups"])
    return aggregate


def run_family_study(
    family: str,
    *,
    base_seeds: list[int],
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
    baseline_model = select_reference_model(model_ids)
    layouts = expand_layouts(canonical_lineups(model_ids))
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
    results_by_seed = []
    for base_seed in base_seeds:
        results_by_seed.append(
            (
                base_seed,
                run_layouts(
                    layouts,
                    agent_factories=factories,
                    config=config,
                    base_seed=base_seed,
                    layout_repetitions=config.layout_repetitions,
                ),
            )
        )
    aggregate_result = _aggregate_results(results_by_seed)
    report = build_report(aggregate_result, confirmatory_baseline=baseline_model)
    bundle = export_experiment_bundle(
        output_dir,
        config={
            "experiment": "openrouter_family_study",
            "family": family,
            "resolved_models": model_ids,
            "resolved_model_metadata": model_metadata(model_ids),
            "confirmatory_baseline": baseline_model,
            "base_seeds": base_seeds,
            "layout_count": len(layouts),
            "seed_count": len(base_seeds),
            "prompt_template": prompt_template,
            "prompt_signature": _prompt_signature(prompt_template),
            "decoding": decoding,
            **asdict(config),
        },
        report=report,
        cross_play_result=aggregate_result,
    )
    return {
        "models": model_ids,
        "baseline_model": baseline_model,
        "layouts": layouts,
        "base_seeds": base_seeds,
        "report": report,
        "bundle": bundle,
        "cross_play_result": aggregate_result,
    }


def _parse_args():
    parser = argparse.ArgumentParser(description="Run a multi-seed same-family OpenRouter parameter sweep.")
    parser.add_argument("--family", default="gemma")
    parser.add_argument("--base-seeds", default="7,11,13,17,19")
    parser.add_argument("--session-hands", type=int, default=None)
    parser.add_argument("--layout-repetitions", type=int, default=10)
    parser.add_argument("--max-carryover", type=int, default=64)
    parser.add_argument("--initial-bankroll", type=int, default=100_000)
    parser.add_argument("--stake-per-point", type=int, default=100)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--prompt-file", default="")
    parser.add_argument("--decoding", action="append", default=None)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    base_seeds = _parse_base_seeds(args.base_seeds)
    output_dir = args.output_dir or _default_output_dir("openrouter_family_study")
    prompt = DEFAULT_PROMPT_TEMPLATE
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    decoding = _parse_decoding(args.decoding)
    result = run_family_study(
        args.family,
        base_seeds=base_seeds,
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
                "family": args.family,
                "baseline_model": result["baseline_model"],
                "models": result["models"],
                "base_seeds": result["base_seeds"],
                "layout_count": len(result["layouts"]),
                "bundle": result["bundle"],
                "ranking": result["report"]["ranking"],
                "output_dir": output_dir,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
