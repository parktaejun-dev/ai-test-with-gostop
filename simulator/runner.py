from __future__ import annotations

import hashlib
from itertools import permutations

from engine.game import GameEngine
from engine.state import GameConfig
from logs.recorder import LogRecorder
from metrics.core import summarize_agent_results, summarize_lineup


def layout_seed_for(base_seed: int, layout: tuple[str, ...], repeat_index: int = 0) -> int:
    digest = hashlib.sha256(f"{base_seed}:{'|'.join(layout)}:{repeat_index}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % (2**31)


def run_layouts(
    layouts: list[tuple[str, ...]],
    agent_factories: dict[str, callable],
    config: GameConfig,
    base_seed: int,
    layout_repetitions: int = 1,
) -> dict:
    lineups = {}
    repeats = max(1, int(layout_repetitions))
    for layout_index, layout in enumerate(layouts):
        layout_for_log = list(layout)
        for repeat_index in range(repeats):
            lineup_seed = layout_seed_for(base_seed, layout, repeat_index)
            layout_id = layout_index * repeats + repeat_index
            agents = {seat: agent_factories[name]() for seat, name in enumerate(layout)}
            recorder = LogRecorder()
            result = GameEngine(config=config, recorder=recorder).play_session(
                agents=agents,
                session_seed=lineup_seed,
                num_hands=config.session_hands,
            )
            annotated_logs = []
            for entry in result["logs"]:
                annotated = {
                    "layout_id": layout_id,
                    "layout": layout_for_log,
                    "layout_repeat": repeat_index,
                    "session_id": layout_id,
                    "seed": lineup_seed,
                    **entry,
                }
                annotated_logs.append(annotated)
            result["logs"] = annotated_logs
            lineup_key = (layout, repeat_index) if repeats > 1 else layout
            lineups[lineup_key] = {
                "session": result,
                "summary": summarize_lineup(layout, result),
            }
    return {
        "lineups": lineups,
        "agent_summary": summarize_agent_results(lineups),
    }


def run_cross_play(agent_factories: dict[str, callable], config: GameConfig, base_seed: int) -> dict:
    layouts = list(permutations(agent_factories.keys(), 4))
    return run_layouts(
        layouts,
        agent_factories=agent_factories,
        config=config,
        base_seed=base_seed,
        layout_repetitions=config.layout_repetitions,
    )
