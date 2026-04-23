from __future__ import annotations

import argparse
import json
from datetime import datetime
from dataclasses import asdict

from agents import GreedyProfitAgent, RandomAgent, RuleBasedAgent, SurvivalAgent
from analysis import build_report, export_experiment_bundle
from engine.state import GameConfig
from simulator import run_cross_play


def _baseline_factories():
    return {
        "RandomAgent": lambda: RandomAgent(name="RandomAgent"),
        "RuleBasedAgent": lambda: RuleBasedAgent(name="RuleBasedAgent"),
        "GreedyProfitAgent": lambda: GreedyProfitAgent(name="GreedyProfitAgent"),
        "SurvivalAgent": lambda: SurvivalAgent(name="SurvivalAgent"),
    }


def _parse_args():
    parser = argparse.ArgumentParser(description="Run the Go-Stop evaluation harness.")
    parser.add_argument("--base-seed", type=int, default=7)
    parser.add_argument("--session-hands", type=int, default=None)
    parser.add_argument("--layout-repetitions", type=int, default=10)
    parser.add_argument("--max-carryover", type=int, default=64)
    parser.add_argument("--initial-bankroll", type=int, default=100_000)
    parser.add_argument("--stake-per-point", type=int, default=100)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--stdout-json", action="store_true")
    return parser.parse_args()


def _default_output_dir(prefix: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"results/{prefix}_{stamp}"


def main() -> None:
    args = _parse_args()
    config = GameConfig(
        session_hands=args.session_hands,
        layout_repetitions=args.layout_repetitions,
        max_carryover_multiplier=args.max_carryover,
        initial_bankroll=args.initial_bankroll,
        stake_per_point=args.stake_per_point,
    )
    result = run_cross_play(_baseline_factories(), config=config, base_seed=args.base_seed)
    report = build_report(result)
    output_dir = args.output_dir or _default_output_dir("paper_run")
    bundle = export_experiment_bundle(
        output_dir,
        config={"base_seed": args.base_seed, **asdict(config)},
        report=report,
        cross_play_result=result,
    )
    if args.stdout_json:
        print(json.dumps({"bundle": bundle, "report": report}, ensure_ascii=False, indent=2, sort_keys=True))
        return
    print(json.dumps({"output_dir": output_dir, "bundle": bundle, "ranking": report["ranking"]}, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
