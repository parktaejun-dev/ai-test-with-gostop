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

from agents import GreedyProfitAgent, RandomAgent, RuleBasedAgent, SurvivalAgent
from analysis import build_report, export_experiment_bundle
from engine.state import GameConfig
from metrics.core import summarize_agent_results
from simulator import run_cross_play


def _baseline_factories():
    return {
        "RandomAgent": lambda: RandomAgent(name="RandomAgent"),
        "RuleBasedAgent": lambda: RuleBasedAgent(name="RuleBasedAgent"),
        "GreedyProfitAgent": lambda: GreedyProfitAgent(name="GreedyProfitAgent"),
        "SurvivalAgent": lambda: SurvivalAgent(name="SurvivalAgent"),
    }


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


def run_paper_study(
    *,
    base_seeds: list[int],
    session_hands: int,
    layout_repetitions: int,
    max_carryover_multiplier: int,
    initial_bankroll: int,
    stake_per_point: int,
    output_dir: str,
) -> dict:
    config = GameConfig(
        session_hands=session_hands,
        layout_repetitions=layout_repetitions,
        max_carryover_multiplier=max_carryover_multiplier,
        initial_bankroll=initial_bankroll,
        stake_per_point=stake_per_point,
    )
    results_by_seed = []
    for base_seed in base_seeds:
        results_by_seed.append((base_seed, run_cross_play(_baseline_factories(), config=config, base_seed=base_seed)))
    aggregate_result = _aggregate_results(results_by_seed)
    report = build_report(aggregate_result)
    bundle = export_experiment_bundle(
        output_dir,
        config={
            "experiment": "paper_study",
            "base_seeds": base_seeds,
            "invocation": (
                "python3 scripts/run_paper_study.py "
                f"--base-seeds {','.join(str(seed) for seed in base_seeds)} "
                f"--session-hands {session_hands} "
                f"--layout-repetitions {layout_repetitions} "
                f"--max-carryover {max_carryover_multiplier} "
                f"--initial-bankroll {initial_bankroll} "
                f"--stake-per-point {stake_per_point} "
                f"--output-dir {output_dir}"
            ),
            "effective_horizon_rule": f"fixed_session_hands={session_hands}",
            **asdict(config),
        },
        report=report,
        cross_play_result=aggregate_result,
    )
    return {
        "base_seeds": base_seeds,
        "lineup_count": len(aggregate_result["lineups"]),
        "report": report,
        "bundle": bundle,
        "output_dir": output_dir,
    }


def _parse_args():
    parser = argparse.ArgumentParser(description="Run the multi-seed baseline paper study.")
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
    output_dir = args.output_dir or _default_output_dir("paper_study")
    result = run_paper_study(
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
                "base_seeds": result["base_seeds"],
                "lineup_count": result["lineup_count"],
                "bundle": result["bundle"],
                "ranking": result["report"]["ranking"],
                "output_dir": result["output_dir"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
