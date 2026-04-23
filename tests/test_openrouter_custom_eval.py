from __future__ import annotations

import unittest

from experiments.openrouter_custom_eval import parse_models_arg


class OpenRouterCustomEvalTests(unittest.TestCase):
    def test_parse_models_arg_dedupes_and_strips(self):
        parsed = parse_models_arg(
            " google/gemma-3-4b-it:free,google/gemma-3-12b-it:free, google/gemma-3-4b-it:free "
        )
        self.assertEqual(
            parsed,
            ["google/gemma-3-4b-it:free", "google/gemma-3-12b-it:free"],
        )

    def test_parse_models_arg_requires_at_least_one_model(self):
        with self.assertRaises(ValueError):
            parse_models_arg(" , , ")


if __name__ == "__main__":
    unittest.main()
