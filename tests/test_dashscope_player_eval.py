import unittest
from unittest.mock import patch

from experiments.dashscope_player_eval import parse_seat_models_arg, run_player_eval


class DashScopePlayerEvalTests(unittest.TestCase):
    def test_parse_seat_models_arg_requires_four_models(self):
        self.assertEqual(
            parse_seat_models_arg("qwen-plus,qwen-turbo,qwen-max,qwen-plus"),
            ["qwen-plus", "qwen-turbo", "qwen-max", "qwen-plus"],
        )
        with self.assertRaises(ValueError):
            parse_seat_models_arg("qwen-plus,qwen-turbo")

    @patch("experiments.dashscope_player_eval.export_experiment_bundle", return_value={"output_dir": "out"})
    @patch("experiments.dashscope_player_eval.build_report", return_value={"ranking": []})
    @patch("experiments.dashscope_player_eval.run_layouts", return_value={"lineups": {}, "agent_summary": {}})
    def test_run_player_eval_defaults_are_small_for_free_quota(
        self,
        mock_run_layouts,
        mock_build_report,
        mock_export_experiment_bundle,
    ):
        run_player_eval(
            ["qwen-plus", "qwen-turbo", "qwen-max", "qwen-plus"],
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
