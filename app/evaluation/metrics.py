"""
Evaluation metrics. Pure functions, standard library only, deterministic (seeded).
"""
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Optional, Sequence

Z95 = 1.959963984540054


def wilson_interval(successes: int, n: int, z: float = Z95) -> tuple[float, float]:
    """95% Wilson score interval; better than the normal approximation for small n or p near 0/1."""
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def mcnemar_exact(b: int, c: int) -> float:
    """
    Two-sided exact McNemar test on discordant pairs.
    b = A correct & B wrong, c = A wrong & B correct. Returns the p-value.
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def paired_bootstrap_diff(
    a: Sequence[bool], b: Sequence[bool], iterations: int = 2000, seed: int = 42
) -> tuple[float, float, float]:
    """Accuracy(b) - accuracy(a) on paired outcomes, with a 95% percentile bootstrap CI."""
    if len(a) != len(b):
        raise ValueError("paired samples must have equal length")
    n = len(a)
    if n == 0:
        return (0.0, 0.0, 0.0)
    diff = (sum(b) - sum(a)) / n
    rng = random.Random(seed)
    diffs = []
    for _ in range(iterations):
        idx = [rng.randrange(n) for _ in range(n)]
        diffs.append(sum(b[i] - a[i] for i in idx) / n)
    diffs.sort()
    lo = diffs[int(0.025 * iterations)]
    hi = diffs[min(iterations - 1, int(0.975 * iterations))]
    return (diff, lo, hi)


@dataclass
class ClassStats:
    precision: float
    recall: float
    f1: float
    support: int


def per_class_stats(y_true: Sequence[str], y_pred: Sequence[str], classes: Sequence[str]) -> dict[str, ClassStats]:
    """Prediction buckets outside `classes` (invalid/unmatched) count as misses, never as hits."""
    tp, fp, fn = Counter(), Counter(), Counter()
    for t, p in zip(y_true, y_pred):
        if t == p:
            tp[t] += 1
        else:
            fn[t] += 1
            fp[p] += 1
    support = Counter(y_true)
    out = {}
    for c in classes:
        prec = tp[c] / (tp[c] + fp[c]) if tp[c] + fp[c] else 0.0
        rec = tp[c] / (tp[c] + fn[c]) if tp[c] + fn[c] else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        out[c] = ClassStats(prec, rec, f1, support[c])
    return out


def macro_f1(stats: dict[str, ClassStats]) -> float:
    """Mean F1 over classes that appear in the ground truth."""
    present = [s.f1 for s in stats.values() if s.support > 0]
    return sum(present) / len(present) if present else 0.0


def confusion_matrix(y_true: Sequence[str], y_pred: Sequence[str]) -> dict[str, dict[str, int]]:
    m: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for t, p in zip(y_true, y_pred):
        m[t][p] += 1
    return {t: dict(row) for t, row in m.items()}


def binary_detection(true_diseased: Sequence[bool], pred_diseased: Sequence[bool]) -> dict:
    """Disease vs healthy. Sensitivity = diseased plants flagged; specificity = healthy plants left alone."""
    tp = sum(t and p for t, p in zip(true_diseased, pred_diseased))
    fn = sum(t and not p for t, p in zip(true_diseased, pred_diseased))
    tn = sum((not t) and (not p) for t, p in zip(true_diseased, pred_diseased))
    fp = sum((not t) and p for t, p in zip(true_diseased, pred_diseased))
    return {
        "sensitivity": tp / (tp + fn) if tp + fn else None,
        "specificity": tn / (tn + fp) if tn + fp else None,
        "tp": tp, "fn": fn, "tn": tn, "fp": fp,
    }


def expected_calibration_error(confidences: Sequence[float], correct: Sequence[bool], bins: int = 10) -> Optional[float]:
    """ECE with equal-width bins: weighted mean |accuracy - confidence| per bin."""
    n = len(confidences)
    if n == 0:
        return None
    buckets: dict[int, list[tuple[float, bool]]] = defaultdict(list)
    for conf, ok in zip(confidences, correct):
        conf = min(max(conf, 0.0), 1.0)
        buckets[min(int(conf * bins), bins - 1)].append((conf, ok))
    ece = 0.0
    for items in buckets.values():
        avg_conf = sum(c for c, _ in items) / len(items)
        acc = sum(ok for _, ok in items) / len(items)
        ece += abs(acc - avg_conf) * len(items) / n
    return ece


def reliability_table(confidences: Sequence[float], correct: Sequence[bool], bins: int = 5) -> list[dict]:
    rows = []
    for i in range(bins):
        lo, hi = i / bins, (i + 1) / bins
        items = [ok for c, ok in zip(confidences, correct) if (lo <= c < hi) or (i == bins - 1 and c == 1.0)]
        conf = [c for c in confidences if (lo <= c < hi) or (i == bins - 1 and c == 1.0)]
        rows.append({
            "range": f"{lo:.1f}-{hi:.1f}",
            "n": len(items),
            "mean_confidence": sum(conf) / len(conf) if conf else None,
            "accuracy": sum(items) / len(items) if items else None,
        })
    return rows


def brier_score(confidences: Sequence[float], correct: Sequence[bool]) -> Optional[float]:
    if not confidences:
        return None
    return sum((c - float(ok)) ** 2 for c, ok in zip(confidences, correct)) / len(confidences)


def selective_accuracy(confidences: Sequence[float], correct: Sequence[bool], threshold: float) -> dict:
    """Accuracy on answers the app shows as confident (>= threshold), and how many that is."""
    kept = [ok for c, ok in zip(confidences, correct) if c >= threshold]
    return {
        "threshold": threshold,
        "coverage": len(kept) / len(confidences) if confidences else None,
        "accuracy": sum(kept) / len(kept) if kept else None,
        "n": len(kept),
    }


def derangement(items: Sequence, seed: int = 42) -> list:
    """Shuffle so that no element stays in its original position (needs len >= 2)."""
    n = len(items)
    if n < 2:
        raise ValueError("need at least 2 items to derange")
    rng = random.Random(seed)
    while True:
        perm = list(range(n))
        rng.shuffle(perm)
        if all(i != p for i, p in enumerate(perm)):
            return [items[p] for p in perm]
