from __future__ import annotations

import unittest

from simulator.runner import layout_seed_for


class RunnerTests(unittest.TestCase):
    def test_layout_seed_is_order_stable(self):
        layout = ("a", "b", "c", "d")
        self.assertEqual(layout_seed_for(7, layout), layout_seed_for(7, layout))

    def test_layout_seed_changes_with_layout(self):
        left = layout_seed_for(7, ("a", "b", "c", "d"))
        right = layout_seed_for(7, ("a", "b", "d", "c"))
        self.assertNotEqual(left, right)


if __name__ == "__main__":
    unittest.main()
