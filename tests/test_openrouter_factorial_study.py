from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from analysis.statistics import build_session_observations
from experiments.factorial_registry import FIXED_MODEL_PANEL, load_factorial_strategies, resolve_fixed_model_panel
from experiments.openrouter_factorial_study import aggregate_factorial_results, run_factorial_study


def _seat(bankroll: int):
    return type("Seat", (), {"bankroll": bankroll})()


def _fake_run_layouts(*args, **kwargs):
    layout = tuple(FIXED_MODEL_PANEL)
    return {
        "lineups": {
            (layout, 0): {
                "session": {
                    "logs": [{"layout_repeat": 0, "seed": 101}],
                    "hand_outcomes": [type("Outcome", (), {"winner": 0})()],
                    "seats": {
                        0: _seat(1100),
                        1: _seat(1000),
                        2: _seat(900),
                        3: _seat(1000),
                    },
                },
                "summary": {
                    "layout": layout,
                    "seat_to_name": {0: layout[0], 1: layout[1], 2: layout[2], 3: layout[3]},
                    "profit_by_seat": {0: 100.0, 1: 0.0, 2: -100.0, 3: 0.0},
                    "win_by_seat": {0: 1, 1: 0, 2: 0, 3: 0},
                    "showdown_success_count": 0,
                    "showdown_proposals": {0: 0, 1: 0, 2: 0, 3: 0},
                    "showdown_accepts": {0: 0, 1: 0, 2: 0, 3: 0},
                    "showdown_rejects": {0: 0, 1: 0, 2: 0, 3: 0},
                    "showdown_ev_gains": {0: [], 1: [], 2: [], 3: []},
                    "showdown_misplays": {0: [], 1: [], 2: [], 3: []},
                    "forced_gwang_sell": {0: 0, 1: 0, 2: 0, 3: 0},
                    "early_exits": {0: 0, 1: 0, 2: 0, 3: 0},
                },
            }
        }
    }


class FactorialStudyTests(unittest.TestCase):
    def test_prompt_registry_loads_four_frozen_strategies(self):
        strategies = load_factorial_strategies()
        self.assertEqual([strategy.strategy_id for strategy in strategies], ["balanced", "analytic", "conservative", "aggressive"])
        self.assertTrue(all(Path(strategy.path).exists() for strategy in strategies))
        self.assertTrue(all(strategy.signature["sha256"] for strategy in strategies))

    @patch.dict("os.environ", {"OPENROUTER_SELECTOR_URL": "https://selector.example.com/models"}, clear=False)
    @patch("experiments.factorial_registry.request.urlopen")
    def test_selector_result_overrides_stale_fallback_panel(self, mock_urlopen):
        selected = [
            "google/gemma-3-27b-it:free",
            "meta-llama/llama-3.2-3b-instruct:free",
            "qwen/qwen3-next-80b-a3b-instruct:free",
            "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
        ]
        response = mock_urlopen.return_value.__enter__.return_value
        response.read.return_value = json.dumps({"models": selected}).encode("utf-8")

        panel = resolve_fixed_model_panel()

        self.assertEqual(panel.source, "selector")
        self.assertEqual(panel.model_ids, tuple(selected))

    def test_aggregate_results_preserves_factorial_block_alignment(self):
        strategies = load_factorial_strategies()[:2]
        aggregate = aggregate_factorial_results(
            [
                (7, strategies[0], _fake_run_layouts()),
                (7, strategies[1], _fake_run_layouts()),
            ]
        )
        observations = build_session_observations(aggregate)
        self.assertEqual(sorted({row["strategy_id"] for row in observations}), ["analytic", "balanced"])
        self.assertEqual(len({row["factorial_block_id"] for row in observations}), 1)
        self.assertEqual(sorted({row["model_id"] for row in observations}), sorted(FIXED_MODEL_PANEL))

    @patch("experiments.openrouter_factorial_study.run_layouts", side_effect=_fake_run_layouts)
    def test_factorial_study_smoke_export_and_figure_render(self, _mock_run_layouts):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_factorial_study(
                base_seeds=[7],
                session_hands=2,
                layout_repetitions=1,
                max_carryover_multiplier=8,
                initial_bankroll=1000,
                stake_per_point=1,
                output_dir=tmpdir,
            )

            report = result["report"]
            self.assertIn("rq_model_vs_strategy", report)
            observations_path = Path(result["bundle"]["session_observations_csv"])
            with observations_path.open("r", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 16)
            self.assertEqual(sorted({row["strategy_id"] for row in rows}), ["aggressive", "analytic", "balanced", "conservative"])

            subprocess.run(
                [sys.executable, "scripts/build_paper_figures.py", "--results-dir", tmpdir],
                cwd=Path(__file__).resolve().parents[1],
                check=True,
                capture_output=True,
                text=True,
            )
            assets_dir = Path(tmpdir) / "paper_assets"
            self.assertTrue((assets_dir / "figure_factorial_interaction.png").exists())
            self.assertTrue((assets_dir / "figure_factorial_effect_sizes.png").exists())
            self.assertTrue((assets_dir / "figure_factorial_risk.png").exists())
            self.assertTrue((assets_dir / "table_main_effects.csv").exists())


if __name__ == "__main__":
    unittest.main()
