import unittest
from unittest.mock import patch

from experiments.dashscope_qwen_parameter_sweep import model_metadata, parse_models_arg, run_parameter_sweep


class DashScopeQwenParameterSweepTests(unittest.TestCase):
    def test_default_models_are_qwen_size_panel(self):
        self.assertEqual(
            parse_models_arg(""),
            [
                "qwen3-coder-30b-a3b-instruct",
                "qwen3.5-122b-a10b",
                "qwen3.5-397b-a17b",
                "qwen3-coder-480b-a35b-instruct",
            ],
        )
        with self.assertRaises(ValueError):
            parse_models_arg("qwen3-coder-30b-a3b-instruct")

    def test_model_metadata_extracts_total_and_active_parameters(self):
        self.assertEqual(
            model_metadata(["qwen3-coder-480b-a35b-instruct"]),
            [
                {
                    "model_id": "qwen3-coder-480b-a35b-instruct",
                    "parameter_size_b": 480.0,
                    "active_parameter_size_b": 35.0,
                }
            ],
        )

    @patch("experiments.dashscope_qwen_parameter_sweep.export_experiment_bundle", return_value={"output_dir": "out"})
    @patch("experiments.dashscope_qwen_parameter_sweep.build_report", return_value={"ranking": []})
    @patch("experiments.dashscope_qwen_parameter_sweep.run_layouts", return_value={"lineups": {}, "agent_summary": {}})
    def test_run_parameter_sweep_defaults_are_small(
        self,
        mock_run_layouts,
        mock_build_report,
        mock_export_experiment_bundle,
    ):
        run_parameter_sweep(
            ["qwen3-coder-30b-a3b-instruct", "qwen3-coder-480b-a35b-instruct"],
            base_seed=7,
            initial_bankroll=1000,
            stake_per_point=1,
            output_dir="out",
        )
        config = mock_run_layouts.call_args.kwargs["config"]
        self.assertEqual(config.session_hands, 10)
        self.assertEqual(config.layout_repetitions, 1)
        self.assertEqual(config.remote_eval_hands, 10)
        mock_build_report.assert_called_once()
        mock_export_experiment_bundle.assert_called_once()


if __name__ == "__main__":
    unittest.main()
