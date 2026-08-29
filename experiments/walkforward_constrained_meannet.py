"""
experiments/walkforward_constrained_meannet.py
Item E follow-up #3: root-cause test for the mean-net-objective degeneracy.

DIAGNOSTIC ONLY.

fit_thresholds_mean_net() in walkforward_validation.py has NO minimum-trade-
count floor -- unlike fit_thresholds_accuracy(), which requires at least
MIN_TRADE_FRACTION (15%) of training events to be traded before a threshold
pair is even considered. Maximising the mean of an unconstrained, variably-
sized subset is maximised by shrinking the subset to isolate a single lucky
outlier trade (a training set of 1 trade with a +6.8% return has a "perfect"
mean of +6.8%). That is very plausibly why the mean-net objective degenerates
even under equal-count windows with 93-185 training events (see
walkforward_equal_count.py's result: 4/4 and 3/3 windows degenerate,
WORSE than the original calendar-quarter scheme) -- more training data does
not help an objective that is happy to throw almost all of it away.

This script tests that directly: refit mean-net thresholds with the same
15%-minimum-trade-count floor already used for the accuracy objective, on
both the original calendar-quarter windows and the equal-count windows.
No new data; same N=233 event set; same fitting/evaluation code otherwise.

Run: python -m experiments.walkforward_constrained_meannet
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import experiments.walkforward_validation as wf  # noqa: E402
from experiments.walkforward_equal_count import equal_count_walkforward, _pool_manual  # noqa: E402

SUMMARY_DIR = Path(__file__).resolve().parent.parent / "outputs" / "global" / "summary"
OUT_JSON = SUMMARY_DIR / "item_e_walkforward_constrained_meannet.json"


def fit_thresholds_mean_net_constrained(train_events: list[dict]) -> tuple[float, float, dict]:
    """Same grid as fit_thresholds_mean_net, but requires at least
    MIN_TRADE_FRACTION of training events to be traded (same floor already
    used by fit_thresholds_accuracy), so the search can no longer "win" by
    isolating a single outlier trade."""
    import itertools
    min_trades = max(wf.MIN_TRADES_FLOOR, int(len(train_events) * wf.MIN_TRADE_FRACTION))

    best = None
    best_upper = wf.DEFAULT_HOLD_UPPER
    best_lower = wf.DEFAULT_HOLD_LOWER

    for hu, hl in itertools.product(wf.THRESH_UPPER_RANGE, wf.THRESH_LOWER_RANGE):
        hu_r = round(float(hu), 2)
        hl_r = round(float(hl), 2)
        if hu_r <= hl_r:
            continue
        result = wf._evaluate_thresholds(train_events, hu_r, hl_r)
        if result["n_trades"] < min_trades:
            continue
        if best is None or result["mean_net"] > best["mean_net"]:
            best = result
            best_upper = hu_r
            best_lower = hl_r

    if best is None:
        best = wf._evaluate_thresholds(train_events, wf.DEFAULT_HOLD_UPPER, wf.DEFAULT_HOLD_LOWER)
        best_upper = wf.DEFAULT_HOLD_UPPER
        best_lower = wf.DEFAULT_HOLD_LOWER

    return best_upper, best_lower, best


def _run_calendar(events):
    print("\n" + "=" * 80)
    print("CALENDAR-QUARTER WINDOWS (original scheme), constrained mean-net")
    print("=" * 80)
    windows = wf.rolling_walkforward(events, fit_thresholds_mean_net_constrained)
    degen = wf._print_windows(windows, "constrained mean_net")
    pool = wf._pool_windows(windows, events)
    wf._print_pooled(pool, "constrained mean_net")
    return windows, pool, degen


def _run_equal_count(events, n_windows):
    print("\n" + "=" * 80)
    print(f"EQUAL-COUNT WINDOWS (n_windows={n_windows}), constrained mean-net")
    print("=" * 80)
    windows = equal_count_walkforward(events, fit_thresholds_mean_net_constrained, n_windows)
    degen = wf._print_windows(windows, "constrained mean_net")
    pool = _pool_manual(windows)
    wf._print_pooled(pool, "constrained mean_net")
    return windows, pool, degen


def _pool_summary(pool):
    return {
        "n_trades": pool["n_trades"], "n_graded": pool["n_graded"],
        "n_correct": pool["n_correct"],
        "accuracy": round(pool["accuracy"], 4) if pool["accuracy"] is not None else None,
        "mean_net_pct": round(pool["mean_net"] * 100, 4),
    }


def main():
    events = wf._load_clean_events()
    n = len(events)
    print(f"Loaded {n} clean events (expected 233)")

    results = {}

    w_cal, p_cal, d_cal = _run_calendar(events)
    results["calendar_quarter_constrained"] = {
        "n_windows": len(w_cal), "degenerate_windows": len(d_cal),
        "pooled_oos": _pool_summary(p_cal),
    }

    for nw in (4, 3):
        w_ec, p_ec, d_ec = _run_equal_count(events, nw)
        results[f"equal_count_{nw}w_constrained"] = {
            "n_windows": len(w_ec), "degenerate_windows": len(d_ec),
            "test_window_sizes": [w["test_n"] for w in w_ec],
            "pooled_oos": _pool_summary(p_ec),
        }

    print("\n" + "=" * 80)
    print("SUMMARY: does a minimum-trade-count floor fix the mean-net objective?")
    print("=" * 80)
    print(f"\n  ORIGINAL (no floor, calendar-quarter): 3/4 degenerate (from walkforward_validation.py)")
    print(f"  ORIGINAL (no floor, equal-count 4w):    4/4 degenerate (from walkforward_equal_count.py)")
    for label, r in results.items():
        print(f"\n  {label}: {r['degenerate_windows']}/{r['n_windows']} degenerate, pooled={r['pooled_oos']}")

    with open(OUT_JSON, "w") as f:
        json.dump({"label": "Constrained mean-net objective (15% min-trade floor) diagnostic, "
                            "N=233, DIAGNOSTIC ONLY", "results": results}, f, indent=2, default=str)
    print(f"\nWrote -> {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
