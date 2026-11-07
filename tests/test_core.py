"""Small invariant tests for the evaluator and watershed pipeline."""
import unittest
import numpy as np
from coinlab.metrics import evaluate
from coinlab.improved import segment
from coinlab.dataset import make_scene


class CoreTests(unittest.TestCase):
    def test_empty(self):
        blank = np.zeros((64, 64), dtype=np.uint8)
        labels, _ = segment(blank)
        self.assertEqual(labels.max(), 0)
        self.assertEqual(evaluate(blank, labels)["instance_f1"], 1)

    def test_perfect_nonconsecutive_ids(self):
        a = np.zeros((8, 8), dtype=int); a[1:3, 1:3] = 4; a[5:7, 5:7] = 12
        b = np.where(a == 4, 7, np.where(a == 12, 2, 0))
        self.assertEqual(evaluate(a, b)["pq"], 1)
        self.assertEqual(evaluate(a, b)["true_count"], 2)

    def test_merge_is_not_two_matches(self):
        a = np.zeros((8, 8), dtype=int); a[1:3, 1:3] = 1; a[5:7, 5:7] = 2
        b = (a > 0).astype(int)
        score = evaluate(a, b)
        self.assertEqual(score["tp"], 0)  # Each IoU == 0.5; the rule is strictly >.
        self.assertEqual(score["foreground_iou"], 1)
        self.assertEqual(score["abs_count_error"], 1)

    def test_touching_disks(self):
        yy, xx = np.mgrid[:100, :120]
        foreground = ((yy - 50)**2 + (xx - 43)**2 < 20**2) | ((yy - 50)**2 + (xx - 76)**2 < 20**2)
        labels, _ = segment(foreground.astype(float) * 160 + 40, background_size=61, h=2)
        self.assertEqual(labels.max(), 2)

    def test_generator_deterministic(self):
        a, gt_a = make_scene(123, "uneven_touching")
        b, gt_b = make_scene(123, "uneven_touching")
        np.testing.assert_array_equal(a, b); np.testing.assert_array_equal(gt_a, gt_b)
        self.assertEqual(len(np.unique(gt_a)) - 1, gt_a.max())

    def test_invalid_parameters(self):
        with self.assertRaises(ValueError): segment(np.zeros((16, 16)), h=0)


if __name__ == "__main__": unittest.main()
