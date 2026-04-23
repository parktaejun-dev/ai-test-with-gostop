from __future__ import annotations

import unittest

from experiments.openrouter_player_eval import parse_seat_models_arg


class OpenRouterPlayerEvalTests(unittest.TestCase):
    def test_parse_seat_models_arg_requires_four_models(self):
        with self.assertRaises(ValueError):
            parse_seat_models_arg("a,b,c")

    def test_parse_seat_models_arg_strips_and_preserves_order(self):
        parsed = parse_seat_models_arg(" a , b , a , d ")
        self.assertEqual(parsed, ["a", "b", "a", "d"])


if __name__ == "__main__":
    unittest.main()
