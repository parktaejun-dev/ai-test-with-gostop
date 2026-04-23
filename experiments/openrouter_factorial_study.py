from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from agents import OpenRouterModelAgent
from analysis.export import export_experiment_bundle
from analysis.report import build_factorial_report
from engine.state import GameConfig
from experiments.factorial_registry import (
    fixed_model_panel_metadata,
    fixed_model_panel_signature,
    load_factorial_strategies,
    resolve_fixed_model_panel,
)
from experiments.openrouter_family_eval import canonical_lineups, expand_layouts
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


def _resolve_layout_repeat(lineup_key, session_payload: dict) -> int:
    logs = session_payload.get("logs", [])
    if logs and "layout_repeat" in logs[0]:
        return int(logs[0]["layout_repeat"])
    if isinstance(lineup_key, tuple) and len(lineup_key) == 2 and isinstance(lineup_key[1], int):
        return int(lineup_key[1])
    return 0


def aggregate_factorial_results(
    strategy_runs: list[tuple[int, object, dict]],
) -> dict:
    aggregate = {"lineups": {}, "agent_summary": {}}
    global_session_id = 0
    global_layout_id = 0
    for base_seed, strategy_prompt, result in strategy_runs:
        for lineup_key, payload in result.get("lineups", {}).items():
            session_payload = deepcopy(payload["session"])
            summary = deepcopy(payload["summary"])
            layout = tuple(summary.get("layout", ()))
            layout_label = " > ".join(layout)
            layout_repeat = _resolve_layout_repeat(lineup_key, session_payload)
            factorial_block_id = f"{base_seed}|{layout_label}|{layout_repeat}"
            session_logs = []
            for entry in session_payload.get("logs", []):
                annotated = dict(entry)
                annotated["base_seed"] = base_seed
                annotated["layout_id"] = global_layout_id
                annotated["session_id"] = global_session_id
                annotated["strategy_id"] = strategy_prompt.strategy_id
                annotated["strategy_label"] = strategy_prompt.label
                annotated["prompt_sha256"] = strategy_prompt.signature["sha256"]
                annotated["factorial_block_id"] = factorial_block_id
                session_logs.append(annotated)
            session_payload["logs"] = session_logs
            summary["strategy_id"] = strategy_prompt.strategy_id
            summary["strategy_label"] = strategy_prompt.label
            summary["prompt_sha256"] = strategy_prompt.signature["sha256"]
            summary["factorial_block_id"] = factorial_block_id
            summary["seat_to_model_id"] = {seat: layout[seat] for seat in range(len(layout))}
            aggregate["lineups"][(strategy_prompt.strategy_id, base_seed, lineup_key)] = {
                "session": session_payload,
                "summary": summary,
            }
            global_session_id += 1
            global_layout_id += 1
    return aggregate


def run_factorial_study(
    *,
    base_seeds: list[int],
    session_hands: int,
    layout_repetitions: int,
    max_carryover_multiplier: int,
    initial_bankroll: int,
    stake_per_point: int,
    output_dir: str,
) -> dict:
    strategies = load_factorial_strategies()
    panel = resolve_fixed_model_panel()
    model_panel = panel.model_ids
    layouts = expand_layouts(canonical_lineups(list(model_panel)))
    config = GameConfig(
        session_hands=session_hands,
        layout_repetitions=layout_repetitions,
        max_carryover_multiplier=max_carryover_multiplier,
        initial_bankroll=initial_bankroll,
        stake_per_point=stake_per_point,
    )
    strategy_runs: list[tuple[int, object, dict]] = []
    for strategy_prompt in strategies:
        factories = {
            model_id: (
                lambda mid=model_id, prompt_text=strategy_prompt.text: OpenRouterModelAgent(
                    name=mid,
                    model_id=mid,
                    prompt_template=prompt_text,
                )
            )
            for model_id in model_panel
        }
        for base_seed in base_seeds:
            strategy_runs.append(
                (
                    base_seed,
                    strategy_prompt,
                    run_layouts(
                        layouts,
                        agent_factories=factories,
                        config=config,
                        base_seed=base_seed,
                        layout_repetitions=config.layout_repetitions,
                    ),
                )
            )
    aggregate_result = aggregate_factorial_results(strategy_runs)
    report = build_factorial_report(
        aggregate_result,
        model_panel=fixed_model_panel_metadata(model_panel),
        strategy_panel=strategies,
    )
    bundle = export_experiment_bundle(
        output_dir,
        config={
            "experiment": "openrouter_factorial_study",
            "model_panel_id": panel.panel_id,
            "model_panel_source": panel.source,
            "model_panel_sha256": fixed_model_panel_signature(model_panel),
            "model_panel": fixed_model_panel_metadata(model_panel),
            "prompt_strategies": [strategy.to_manifest() for strategy in strategies],
            "base_seeds": base_seeds,
            "layout_count": len(layouts),
            "seed_count": len(base_seeds),
            "strategy_count": len(strategies),
            "factorial_design": {
                "models": len(model_panel),
                "strategies": len(strategies),
                "cells_per_block": len(model_panel) * len(strategies),
                "factorial_block_id": "base_seed|layout|layout_repeat",
            },
            "session_hands": session_hands,
            "layout_repetitions": layout_repetitions,
            "max_carryover_multiplier": max_carryover_multiplier,
            "initial_bankroll": initial_bankroll,
            "stake_per_point": stake_per_point,
        },
        report=report,
        cross_play_result=aggregate_result,
    )
    return {
        "report": report,
        "bundle": bundle,
        "output_dir": output_dir,
        "cross_play_result": aggregate_result,
        "strategies": [strategy.to_manifest() for strategy in strategies],
        "model_panel": fixed_model_panel_metadata(model_panel),
    }


def _parse_args():
    parser = argparse.ArgumentParser(description="Run the blocked factorial OpenRouter model-vs-strategy study.")
    parser.add_argument("--base-seeds", default="7,11,13,17,19")
    parser.add_argument("--session-hands", type=int, default=300)
    parser.add_argument("--layout-repetitions", type=int, default=10)
    parser.add_argument("--max-carryover", type=int, default=64)
    parser.add_argument("--initial-bankroll", type=int, default=1000)
    parser.add_argument("--stake-per-point", type=int, default=1)
    parser.add_argument("--output-dir", default="")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    base_seeds = _parse_base_seeds(args.base_seeds)
    output_dir = args.output_dir or _default_output_dir("openrouter_factorial_study")
    result = run_factorial_study(
        base_seeds=base_seeds,
        session_hands=args.session_hands,
        layout_repetitions=args.layout_repetitions,
        max_carryover_multiplier=args.max_carryover,
        initial_bankroll=args.initial_bankroll,
        stake_per_point=args.stake_per_point,
        output_dir=output_dir,
    )
    print(
        json.dumps(
            {
                "bundle": result["bundle"],
                "output_dir": result["output_dir"],
                "dominant_main_effect": result["report"]["rq_model_vs_strategy"]["dominant_main_effect"],
                "model_panel": result["model_panel"],
                "strategies": result["strategies"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
