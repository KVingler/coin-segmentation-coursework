"""Foreground and instance metrics with strict IoU > 0.5 one-to-one matching."""
import numpy as np
from scipy.optimize import linear_sum_assignment


def evaluate(truth, prediction):
    # Relabel explicitly so the metric also supports nonconsecutive IDs.
    _, gt = np.unique(np.r_[0, truth.ravel()], return_inverse=True)
    gt = gt[1:].reshape(truth.shape)
    _, pr = np.unique(np.r_[0, prediction.ravel()], return_inverse=True)
    pr = pr[1:].reshape(prediction.shape)
    n, m = int(gt.max()), int(pr.max())
    table = np.bincount((gt * (m + 1) + pr).ravel(),
                        minlength=(n + 1) * (m + 1)).reshape(n + 1, m + 1)
    intersections = table[1:, 1:]
    unions = table[1:, :].sum(1)[:, None] + table[:, 1:].sum(0)[None, :] - intersections
    ious = np.divide(intersections, unions, out=np.zeros_like(intersections, dtype=float),
                     where=unions > 0)
    tp, matched_iou = 0, 0.0
    if n and m:
        # Prioritize number of valid matches, then sum of IoUs.
        rows, cols = linear_sum_assignment(-((ious > 0.5) * (min(n, m) + 1) + ious))
        valid = ious[rows, cols] > 0.5
        tp = int(valid.sum())
        matched_iou = float(ious[rows[valid], cols[valid]].sum())
    foreground_union = np.count_nonzero((gt > 0) | (pr > 0))
    foreground_intersection = np.count_nonzero((gt > 0) & (pr > 0))
    return {
        "true_count": n, "pred_count": m, "abs_count_error": abs(n - m),
        "exact_count": int(n == m),
        "foreground_iou": foreground_intersection / foreground_union if foreground_union else 1.0,
        "instance_f1": 2 * tp / (n + m) if n + m else 1.0,
        "pq": matched_iou / (0.5 * (n + m)) if n + m else 1.0,
        "tp": tp, "fp": m - tp, "fn": n - tp,
    }
