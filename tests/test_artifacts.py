from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from csv import DictReader
from pathlib import Path

from analysis import build_report, export_experiment_bundle
from scripts.build_paper_figures import _paired_metric_vs_baseline, _write_summary_table


class ArtifactExportTests(unittest.TestCase):
    def test_bundle_export_writes_expected_files(self):
        report = build_report(
            {
                "lineups": {},
                "agent_summary": {
                    "A": {
                        "mean_profit": 1.0,
                        "variance": 2.0,
                        "cvar_5": -3.0,
                        "ruin_probability": 0.1,
                        "win_rate": 0.2,
                        "profit_per_hand": 0.3,
                        "hands_survived": 4.0,
                        "session_completed_rate": 0.5,
                        "early_exit_rate": 0.1,
                        "forced_gwang_sell_rate": 0.0,
                        "showdown_frequency": 0.0,
                    }
                },
            }
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle = export_experiment_bundle(tmpdir, config={"seed": 7}, report=report, cross_play_result={"lineups": {}})
            for path in bundle.values():
                self.assertTrue(Path(path).exists())
            manifest = json.loads(Path(bundle["manifest"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["config"]["seed"], 7)
            self.assertEqual(manifest["session_observation_count"], 0)

    def test_build_report_ranking_uses_low_support_and_excludes_variance(self):
        report = build_report(
            {
                "lineups": {},
                "agent_summary": {
                    "fallback_high_profit": {
                        "mean_profit": 10.0,
                        "variance": 1.0,
                        "cvar_5": 5.0,
                        "cvar_5_tail_size": 1,
                        "cvar_5_is_fallback": True,
                        "cvar_5_low_support": True,
                        "ruin_probability": 0.0,
                        "win_rate": 0.5,
                        "profit_per_hand": 1.0,
                        "session_completed_rate": 1.0,
                        "early_exit_rate": 0.0,
                    },
                    "stable_lower_profit": {
                        "mean_profit": 9.0,
                        "variance": 999.0,
                        "cvar_5": 4.0,
                        "cvar_5_tail_size": 8,
                        "cvar_5_is_fallback": False,
                        "cvar_5_low_support": False,
                        "ruin_probability": 0.1,
                        "win_rate": 0.4,
                        "profit_per_hand": 0.9,
                        "session_completed_rate": 1.0,
                        "early_exit_rate": 0.0,
                    },
                    "a_mid_variance": {
                        "mean_profit": 8.0,
                        "variance": 50.0,
                        "cvar_5": 3.0,
                        "cvar_5_tail_size": 8,
                        "cvar_5_is_fallback": False,
                        "cvar_5_low_support": False,
                        "ruin_probability": 0.2,
                        "win_rate": 0.3,
                        "profit_per_hand": 0.8,
                        "session_completed_rate": 1.0,
                        "early_exit_rate": 0.0,
                    },
                    "b_low_variance": {
                        "mean_profit": 8.0,
                        "variance": 1.0,
                        "cvar_5": 3.0,
                        "cvar_5_tail_size": 8,
                        "cvar_5_is_fallback": False,
                        "cvar_5_low_support": False,
                        "ruin_probability": 0.2,
                        "win_rate": 0.3,
                        "profit_per_hand": 0.8,
                        "session_completed_rate": 1.0,
                        "early_exit_rate": 0.0,
                    },
                    "c_high_variance": {
                        "mean_profit": 8.0,
                        "variance": 100.0,
                        "cvar_5": 3.0,
                        "cvar_5_tail_size": 8,
                        "cvar_5_is_fallback": False,
                        "cvar_5_low_support": False,
                        "ruin_probability": 0.2,
                        "win_rate": 0.3,
                        "profit_per_hand": 0.8,
                        "session_completed_rate": 1.0,
                        "early_exit_rate": 0.0,
                    },
                },
            }
        )

        self.assertEqual(report["ranking"][0]["agent"], "stable_lower_profit")
        self.assertEqual(report["ranking"][-1]["agent"], "fallback_high_profit")
        self.assertEqual(report["ranking_policy"]["type"], "descriptive_screening")
        self.assertIn("inferential_statistics", report)
        self.assertIn("confirmatory_assessment", report)
        self.assertEqual(report["confirmatory_assessment"]["baseline"], "RandomAgent")
        self.assertIn("design_diagnostics", report)
        tied_agents = [row["agent"] for row in report["ranking"] if row["mean_profit"] == 8.0]
        self.assertEqual(tied_agents, ["a_mid_variance", "b_low_variance", "c_high_variance"])

    def test_build_report_treats_fallback_as_low_support_even_if_flag_is_false(self):
        report = build_report(
            {
                "lineups": {},
                "agent_summary": {
                    "fallback_row": {
                        "mean_profit": 10.0,
                        "variance": 1.0,
                        "cvar_5": 5.0,
                        "cvar_5_tail_size": 10,
                        "cvar_5_is_fallback": True,
                        "cvar_5_low_support": False,
                        "ruin_probability": 0.1,
                        "win_rate": 0.5,
                        "profit_per_hand": 1.0,
                        "session_completed_rate": 1.0,
                        "early_exit_rate": 0.0,
                    },
                    "supported_row": {
                        "mean_profit": 9.0,
                        "variance": 1.0,
                        "cvar_5": 4.0,
                        "cvar_5_tail_size": 10,
                        "cvar_5_is_fallback": False,
                        "cvar_5_low_support": False,
                        "ruin_probability": 0.1,
                        "win_rate": 0.5,
                        "profit_per_hand": 1.0,
                        "session_completed_rate": 1.0,
                        "early_exit_rate": 0.0,
                    },
                },
            }
        )

        self.assertTrue(report["ranking"][-1]["cvar_5_low_support"])
        self.assertEqual(report["ranking"][-1]["agent"], "fallback_row")

    def test_build_dashboard_data_creates_runs_index(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            results_root = tmp_path / "results"
            dashboard_root = tmp_path / "dashboard" / "data" / "runs"
            for run_name in ("run_a", "run_b"):
                run_dir = results_root / run_name
                run_dir.mkdir(parents=True, exist_ok=True)
                for filename, payload in (
                    ("report.json", {"name": run_name}),
                    ("manifest.json", {"config": {"seed": 7}}),
                    ("cross_play_results.json", {"lineups": {}}),
                    ("session_logs.jsonl", '{"event":"EventType.TEST"}\n'),
                    ("agent_performance_table.csv", "agent,mean_profit\nA,1.0\n"),
                ):
                    path = run_dir / filename
                    if filename.endswith(".json"):
                        path.write_text(json.dumps(payload), encoding="utf-8")
                    else:
                        path.write_text(payload, encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "scripts/build_dashboard_data.py",
                    "--results-root",
                    str(results_root),
                    "--dashboard-data-root",
                    str(dashboard_root),
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=True,
                capture_output=True,
                text=True,
            )

            index = json.loads((dashboard_root / "index.json").read_text(encoding="utf-8"))
            self.assertEqual([item["name"] for item in index["runs"]], ["run_a", "run_b"])
            self.assertTrue((dashboard_root / "run_a" / "report.json").exists())
            self.assertTrue((dashboard_root / "run_b" / "manifest.json").exists())

    def test_paired_metric_vs_baseline_uses_pairwise_differences(self):
        report = {
            "confirmatory_assessment": {
                "baseline": "RandomAgent",
                "per_agent": {
                    "RuleBasedAgent": {
                        "cvar_5": {
                            "agent": "RuleBasedAgent",
                            "baseline": "RandomAgent",
                            "estimate": -5.0,
                            "ci_lower": -7.0,
                            "ci_upper": -3.0,
                        }
                    },
                    "SurvivalAgent": {
                        "cvar_5": {
                            "agent": "SurvivalAgent",
                            "baseline": "RandomAgent",
                            "estimate": 8.0,
                            "ci_lower": 6.0,
                            "ci_upper": 10.0,
                        }
                    }
                }
            }
        }

        baseline, labels, estimates, lower_errors, upper_errors = _paired_metric_vs_baseline(report, "cvar_5")

        self.assertEqual(baseline, "RandomAgent")
        self.assertEqual(labels, ["RuleBasedAgent", "SurvivalAgent"])
        self.assertEqual(estimates, [-5.0, 8.0])
        self.assertEqual(lower_errors, [2.0, 2.0])
        self.assertEqual(upper_errors, [2.0, 2.0])

    def test_write_summary_table_uses_ranking_order_and_support_fields(self):
        report = {
            "ranking": [
                {
                    "agent": "B",
                    "mean_profit": 9.0,
                    "cvar_5": 4.0,
                    "cvar_5_low_support": False,
                    "cvar_5_tail_size": 8,
                    "ruin_probability": 0.1,
                    "win_rate": 0.4,
                },
                {
                    "agent": "A",
                    "mean_profit": 10.0,
                    "cvar_5": 5.0,
                    "cvar_5_low_support": True,
                    "cvar_5_tail_size": 1,
                    "ruin_probability": 0.0,
                    "win_rate": 0.5,
                },
            ],
            "agent_performance_table": {
                "A": {"sample_count": 12},
                "B": {"sample_count": 24},
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(_write_summary_table(report, Path(tmpdir)))
            with path.open(encoding="utf-8", newline="") as handle:
                rows = list(DictReader(handle))

        self.assertEqual([row["agent"] for row in rows], ["B", "A"])
        self.assertEqual([row["ranking"] for row in rows], ["1", "2"])
        self.assertEqual([row["cvar_5_low_support"] for row in rows], ["False", "True"])
        self.assertEqual([row["cvar_5_tail_size"] for row in rows], ["8", "1"])
        self.assertEqual([row["sample_count"] for row in rows], ["24", "12"])


if __name__ == "__main__":
    unittest.main()
