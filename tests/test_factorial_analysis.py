from __future__ import annotations

import unittest

from analysis.statistics import analyze_model_strategy_effects


def _synthetic_observations(model_scale: float, strategy_scale: float, interaction_scale: float) -> list[dict]:
    observations = []
    models = ("model_a", "model_b")
    strategies = ("balanced", "aggressive")
    block_offsets = [0.0, 0.5, -0.25, 0.75, -0.4, 0.2, -0.1, 0.35]
    interaction_pattern = {
        ("model_a", "balanced"): interaction_scale,
        ("model_a", "aggressive"): -interaction_scale,
        ("model_b", "balanced"): -interaction_scale,
        ("model_b", "aggressive"): interaction_scale,
    }
    for block_index, block_offset in enumerate(block_offsets):
        for model_index, model_id in enumerate(models):
            for strategy_index, strategy_id in enumerate(strategies):
                noise = ((block_index + (model_index * 2) + strategy_index) % 5 - 2) * 0.05
                profit = (
                    block_offset
                    + (model_index * model_scale)
                    + (strategy_index * strategy_scale)
                    + interaction_pattern[(model_id, strategy_id)]
                    + noise
                )
                observations.append(
                    {
                        "factorial_block_id": f"block_{block_index}",
                        "model_id": model_id,
                        "strategy_id": strategy_id,
                        "profit": profit,
                    }
                )
    return observations


class FactorialAnalysisTests(unittest.TestCase):
    def test_model_effect_can_dominate(self):
        result = analyze_model_strategy_effects(_synthetic_observations(model_scale=4.0, strategy_scale=0.5, interaction_scale=0.1))
        self.assertGreater(result["terms"]["model"]["partial_eta_squared"], result["terms"]["strategy"]["partial_eta_squared"])
        self.assertGreater(result["terms"]["model"]["partial_eta_squared"], result["terms"]["interaction"]["partial_eta_squared"])

    def test_strategy_effect_can_dominate(self):
        result = analyze_model_strategy_effects(_synthetic_observations(model_scale=0.5, strategy_scale=4.0, interaction_scale=0.1))
        self.assertGreater(result["terms"]["strategy"]["partial_eta_squared"], result["terms"]["model"]["partial_eta_squared"])
        self.assertGreater(result["terms"]["strategy"]["partial_eta_squared"], result["terms"]["interaction"]["partial_eta_squared"])

    def test_interaction_effect_can_dominate(self):
        result = analyze_model_strategy_effects(_synthetic_observations(model_scale=0.2, strategy_scale=0.2, interaction_scale=4.0))
        self.assertGreater(result["terms"]["interaction"]["partial_eta_squared"], result["terms"]["model"]["partial_eta_squared"])
        self.assertGreater(result["terms"]["interaction"]["partial_eta_squared"], result["terms"]["strategy"]["partial_eta_squared"])


if __name__ == "__main__":
    unittest.main()
