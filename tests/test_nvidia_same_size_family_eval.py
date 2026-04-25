import unittest
from unittest.mock import patch

from experiments.nvidia_same_size_family_eval import model_metadata, parse_models_arg, run_same_size_family_eval


class NvidiaSameSizeFamilyEvalTests(unittest.TestCase):
    def test_default_models_are_120b_cross_family_panel(self):
        self.assertEqual(
            parse_models_arg(""),
            [
                "qwen/qwen3.5-122b-a10b",
                "mistralai/mistral-small-4-119b-2603",
                "nvidia/nemotron-3-super-120b-a12b",
                "stockmark/stockmark-2-100b-instruct",
            ],
        )
        with self.assertRaises(ValueError):
            parse_models_arg("qwen/qwen3.5-122b-a10b")

    def test_model_metadata_extracts_family_and_size(self):
        self.assertEqual(
            model_metadata(["mistralai/mistral-small-4-119b-2603"]),
            [
                {
                    "model_id": "mistralai/mistral-small-4-119b-2603",
                    "family": "mistralai",
                    "parameter_size_b": 119.0,
                }
            ],
        )

    @patch("experiments.nvidia_same_size_family_eval.export_experiment_bundle", return_value={"output_dir": "out"})
    @patch("experiments.nvidia_same_size_family_eval.build_report", return_value={"ranking": []})
    @patch("experiments.nvidia_same_size_family_eval.run_layouts", return_value={"lineups": {}, "agent_summary": {}})
    def test_run_same_size_family_eval_defaults_are_small(
        self,
        mock_run_layouts,
        mock_build_report,
        mock_export_experiment_bundle,
    ):
        run_same_size_family_eval(
            ["qwen/qwen3.5-122b-a10b", "mistralai/mistral-small-4-119b-2603"],
            base_seed=7,
            max_remote_calls_per_agent=1,
            initial_bankroll=1000,
            stake_per_point=1,
            output_dir="out",
        )
        config = mock_run_layouts.call_args.kwargs["config"]
        self.assertEqual(config.session_hands, 10)
        self.assertEqual(config.layout_repetitions, 1)
        self.assertEqual(config.remote_eval_hands, 10)
        factory = mock_run_layouts.call_args.kwargs["agent_factories"]["qwen/qwen3.5-122b-a10b"]
        self.assertEqual(factory().max_calls, 1)
        mock_build_report.assert_called_once()
        mock_export_experiment_bundle.assert_called_once()


if __name__ == "__main__":
    unittest.main()
