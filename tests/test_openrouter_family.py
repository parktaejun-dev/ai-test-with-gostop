from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from experiments.openrouter_family_eval import (
    canonical_lineups,
    expand_layouts,
    model_label,
    parse_param_size_b,
    resolve_family_models,
)


class OpenRouterFamilyTests(unittest.TestCase):
    def test_parse_param_size_b(self):
        self.assertEqual(parse_param_size_b("google/gemma-3-4b-it:free"), 4.0)
        self.assertEqual(parse_param_size_b("google/gemma-3-27b-it:free"), 27.0)
        self.assertEqual(parse_param_size_b("google/gemma-3n-e2b-it:free"), 2.0)

    def test_canonical_lineups_duplicate_three_model_family(self):
        lineups = canonical_lineups(
            [
                "google/gemma-3-4b-it:free",
                "google/gemma-3-12b-it:free",
                "google/gemma-3-27b-it:free",
            ]
        )
        self.assertEqual(len(lineups), 3)
        self.assertTrue(any(lineup.count("google/gemma-3-4b-it:free") == 2 for lineup in lineups))

    @patch.dict(os.environ, {}, clear=True)
    def test_resolve_family_models_gemma_returns_four(self):
        models = resolve_family_models("gemma")
        self.assertGreaterEqual(len(models), 4)
        self.assertEqual(len(models[:4]), 4)
        self.assertIn("google/gemma-3n-e2b-it:free", models)
        self.assertIn("google/gemma-4-31b-it:free", models)

    def test_canonical_lineups_four_model_family(self):
        lineups = canonical_lineups(
            [
                "google/gemma-3n-e2b-it:free",
                "google/gemma-3n-e4b-it:free",
                "google/gemma-4-26b-a4b-it:free",
                "google/gemma-4-31b-it:free",
            ]
        )
        self.assertEqual(len(lineups), 1)
        self.assertEqual(len(lineups[0]), 4)

    def test_expand_layouts_deduplicates_permutations(self):
        layouts = expand_layouts([("a", "b", "c", "a")])
        self.assertEqual(len(layouts), 12)

    def test_model_label_is_filesystem_safe(self):
        self.assertEqual(model_label("google/gemma-3-4b-it:free"), "google__gemma-3-4b-it__free")


if __name__ == "__main__":
    unittest.main()
