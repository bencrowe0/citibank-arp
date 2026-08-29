"""
experiments/walkforward_equal_count.py
Item E follow-up #2: is the rolling walk-forward degeneracy fixable with the
existing N=233 data by restructuring the windows themselves?

DIAGNOSTIC ONLY -- exploring whether the failure is fixable, not yet a
report-ready result.

walkforward_validation.py splits by *calendar quarter*, which leaves whatever
falls in the last quarter as the final test window -- currently just 3 events
(2026-07-01 to 2026-07-14), because that quarter isn't finished. That alone
could explain degeneracy in the last window regardless of anything about the
underlying signal: no threshold-fitting procedure produces a stable estimate
from 3 events.

This script keeps the identical expanding-training-window philosophy and the
identical fitting/evaluation code (imported from walkforward_validation.py,
unchanged), but replaces the calendar-quarter test-window boundaries with
equal-EVENT-COUNT boundaries: after an initial 40% training slice, the
remaining events are split into windows of a fixed event count rather than a
fixed calendar span. This uses no new data -- same 233 events, same fitting
logic -- only the window-construction rule changes.

Run: python -m experiments.walkforward_equal_count
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import experiments.walkforward_validation as wf  # noqa: E402

SUMMARY_DIR = Path(__file__).resolve().parent.parent / "outputs" / "global" / "summary"
OUT_JSON = SUMMARY_DIR / "item_e_walkforward_equal_count.json"

TRAIN_FRACTION = 0.4


def equal_count_walkforward(events: list[dict], fit_fn, n_windows: int) -> list[dict]:
    """Expanding-window walk-forward with equal-EVENT-COUNT test windows,
    instead of walkforward_validation.py's equal-calendar-quarter windows.
    """
    n_total = len(events)
    start_idx = int(n_total * TRAIN_FRACTION)
    remaining = n_total - start_idx
    chunk = remaining // n_windows

    windows = []
    for w_idx in range(n_windows):
        train_end = start_idx + w_idx * chunk
        test_end = start_idx + (w_idx + 1) * chunk if w_idx < n_windows - 1 else n_total

        train = events[:train_end]
        test = events[train_end:test_end]
        if not test or len(train) < wf.MIN_TRADES_FLOOR:
            continue

        fitted_upper, fitted_lower, train_result = fit_fn(train)
        test_result = wf._evaluate_thresholds(test, fitted_upper, fitted_lower)

        test_nets = [s["net"] for s in test_result["signals"] if s["position"] != 0]
        test_graded_correct = []
        for ev, sig in zip(test, test_result["signals"]):
            if sig["position"] != 0 and abs(ev["ret_overnight"]) >= wf.FLAT_BAND:
                truth = "BUY" if ev["ret_overnight"] > 0 else "SELL"
                test_graded_correct.append(1 if sig["signal"] == truth else 0)

        windows.append({
            "window_idx": w_idx,
            "train_cutoff": train[-1]["release_date"],
            "test_start": test[0]["release_date"],
            "test_end": test[-1]["release_date"],
            "fitted_upper": fitted_upper,
            "fitted_lower": fitted_lower,
            "train_n": len(train),
            "train_trades": train_result["n_trades"],
            "train_mean_net": train_result["mean_net"],
            "train_accuracy": train_result["accuracy"],
            "train_n_graded": train_result["n_graded"],
            "test_n": len(test),
            "test_trades": test_result["n_trades"],
            "test_mean_net": test_result["mean_net"],
            "test_accuracy": test_result["accuracy"],
            "test_n_graded": test_result["n_graded"],
            "test_n_correct": test_result["n_correct"],
            "test_nets": test_nets,
            "test_graded_correct": test_graded_correct,
        })
    return windows


def _run(events, n_windows):
    print("\n" + "=" * 80)
    print(f"EQUAL-COUNT WINDOWS: n_windows={n_windows} (~{(len(events) - int(len(events)*TRAIN_FRACTION)) // n_windows} events/test-window)")
    print("=" * 80)

    windows_mn = equal_count_walkforward(events, wf.fit_thresholds_mean_net, n_windows)
    degen_mn = wf._print_windows(windows_mn, "mean_net")
    pool_mn = wf._pool_windows_by_index(windows_mn) if hasattr(wf, "_pool_windows_by_index") else _pool_manual(windows_mn)
    wf._print_pooled(pool_mn, "mean_net")

    windows_acc = equal_count_walkforward(events, wf.fit_thresholds_accuracy, n_windows)
    degen_acc = wf._print_windows(windows_acc, "accuracy")
    pool_acc = _pool_manual(windows_acc)
    wf._print_pooled(pool_acc, "accuracy")

    print(f"\n  Degeneracy: mean_net {len(degen_mn)}/{len(windows_mn)}, "
          f"accuracy {len(degen_acc)}/{len(windows_acc)}")

    return windows_mn, pool_mn, degen_mn, windows_acc, pool_acc, degen_acc


def _pool_manual(windows):
    """wf._pool_windows() re-derives test sets from calendar cutoffs, which
    doesn't apply to equal-count windows -- pool directly from each window's
    stored test_nets/test_graded_correct instead."""
    from statistics import mean as _mean
    pooled_nets = []
    pooled_graded = []
    truth_down = 0
    truth_up = 0
    for w in windows:
        pooled_nets.extend(w["test_nets"])
        pooled_graded.extend(w["test_graded_correct"])
    n_trades = len(pooled_nets)
    n_graded = len(pooled_graded)
    n_correct = sum(pooled_graded)
    accuracy = n_correct / n_graded if n_graded > 0 else None
    mean_net = _mean(pooled_nets) if pooled_nets else 0.0
    return {
        "n_trades": n_trades, "n_graded": n_graded, "n_correct": n_correct,
        "accuracy": accuracy, "mean_net": mean_net,
        "summed_pct": sum(pooled_nets) * 100 if pooled_nets else 0.0,
        "pooled_nets": pooled_nets, "pooled_graded": pooled_graded,
        "truth_down": n_graded - n_correct if accuracy is not None and accuracy < 0.5 else 0,
        "truth_up": 0,
    }


def main():
    events = wf._load_clean_events()
    n = len(events)
    print(f"Loaded {n} clean events (expected 233)")

    results = {}
    for n_windows in (4, 3):
        wmn, pmn, dmn, wacc, pacc, dacc = _run(events, n_windows)
        results[f"{n_windows}_windows"] = {
            "n_windows_requested": n_windows,
            "n_windows_actual": len(wmn),
            "test_window_sizes": [w["test_n"] for w in wmn],
            "mean_net_objective": {
                "degenerate_windows": len(dmn),
                "pooled_oos": {
                    "n_trades": pmn["n_trades"], "n_graded": pmn["n_graded"],
                    "n_correct": pmn["n_correct"],
                    "accuracy": round(pmn["accuracy"], 4) if pmn["accuracy"] is not None else None,
                    "mean_net_pct": round(pmn["mean_net"] * 100, 4),
                },
            },
            "accuracy_objective": {
                "degenerate_windows": len(dacc),
                "pooled_oos": {
                    "n_trades": pacc["n_trades"], "n_graded": pacc["n_graded"],
                    "n_correct": pacc["n_correct"],
                    "accuracy": round(pacc["accuracy"], 4) if pacc["accuracy"] is not None else None,
                    "mean_net_pct": round(pacc["mean_net"] * 100, 4),
                },
            },
        }

    print("\n" + "=" * 80)
    print("SUMMARY: does equal-count windowing fix the degeneracy?")
    print("=" * 80)
    for label, r in results.items():
        print(f"\n  {label}: test-window sizes = {r['test_window_sizes']}")
        print(f"    mean_net: {r['mean_net_objective']['degenerate_windows']}/{r['n_windows_actual']} degenerate, "
              f"pooled {r['mean_net_objective']['pooled_oos']}")
        print(f"    accuracy: {r['accuracy_objective']['degenerate_windows']}/{r['n_windows_actual']} degenerate, "
              f"pooled {r['accuracy_objective']['pooled_oos']}")

    with open(OUT_JSON, "w") as f:
        json.dump({"label": "Equal-event-count window diagnostic, N=233, same fitting logic as "
                            "walkforward_validation.py, DIAGNOSTIC ONLY", "results": results},
                  f, indent=2, default=str)
    print(f"\nWrote -> {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
