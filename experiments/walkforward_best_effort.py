"""
experiments/walkforward_best_effort.py
Item E follow-up #4 (canonical): the best achievable rolling walk-forward
result using ONLY the existing N=233 clean event set -- no new document
sourcing, no new API calls.

CONTEXT. experiments/walkforward_validation.py is the project's original,
still-canonical walk-forward finding: refitting the deployed thresholds on
rolling windows degenerates under both objectives (3/4 windows for mean-net,
2/4 for accuracy). That script and its output (item_e_walkforward.json) are
UNCHANGED and UNTOUCHED by this script -- this is an additional, clearly
separate robustness layer on top of it, not a replacement.

Investigating that degeneracy directly (this session, via three scratch
scripts: walkforward_coarse_grid.py, walkforward_equal_count.py,
walkforward_constrained_meannet.py) found two distinct, real causes:

  1. fit_thresholds_mean_net() in walkforward_validation.py has NO minimum-
     trade-count floor, unlike fit_thresholds_accuracy() (which already
     requires >=15% of training events to be traded). An unconstrained
     "maximise the mean" search is trivially won by isolating a single lucky
     outlier trade. This is a fixable METHODOLOGY gap, not data scarcity.
  2. Calendar-quarter windowing forces a near-empty final test window (3
     events), because the last calendar quarter in the dataset isn't
     finished. Equal-event-count windowing removes this specific failure
     mode. On its own (without fix #1) it did NOT help the mean-net
     objective -- confirming #1, not window construction, was the real
     driver of that objective's degeneracy.

This script consolidates both fixes into ONE swept grid -- not a single
hand-picked "best" combination, deliberately, to avoid exactly the kind of
undisclosed search-then-report-the-best-cell problem this project's own
audit trail (CLAUDE.md's "nine-instance pattern", report's Section 4.4) has
repeatedly flagged elsewhere. Every cell is printed and persisted.

Sweep:
  - Window scheme: calendar-quarter (original) x equal-count with
    n_windows in {2, 3, 4, 5}.
  - Objective: mean-net (constrained, min_trade_fraction swept over
    {0.10, 0.15, 0.20} for sensitivity) x accuracy (already constrained at
    a fixed 15% in walkforward_validation.py, used unchanged).

RETROSPECTIVE VALIDATION -- NOT PRE-REGISTERED. Improving the fitting
procedure's honesty does not make this a prospective test; it is still
being evaluated on data that existed when every threshold pair was chosen.

Run: python -m experiments.walkforward_best_effort
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path
from statistics import mean

import numpy as np
from scipy.stats import binomtest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import experiments.walkforward_validation as wf  # noqa: E402
from bootstrap_stats import bootstrap_trade_stats  # noqa: E402

SUMMARY_DIR = Path(__file__).resolve().parent.parent / "outputs" / "global" / "summary"
OUT_JSON = SUMMARY_DIR / "item_e_walkforward_best_effort.json"
OUT_CSV = SUMMARY_DIR / "item_e_walkforward_best_effort.csv"

TRAIN_FRACTION = 0.4
EQUAL_COUNT_WINDOWS = (2, 3, 4, 5)
MEAN_NET_FRACTIONS = (0.10, 0.15, 0.20)
Z_ALPHA = 1.282
Z_BETA = 0.842


# -- constrained mean-net fit function (fix #1) -------------------------------
def make_fit_mean_net_constrained(min_trade_fraction: float):
    """Returns a fit function identical to wf.fit_thresholds_mean_net, except
    it rejects any threshold pair producing fewer than
    max(MIN_TRADES_FLOOR, len(train)*min_trade_fraction) trades -- the same
    floor wf.fit_thresholds_accuracy() already applies, parametrized here for
    a sensitivity sweep."""

    def _fit(train_events: list[dict]) -> tuple[float, float, dict]:
        min_trades = max(wf.MIN_TRADES_FLOOR, int(len(train_events) * min_trade_fraction))
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

    _fit.__name__ = f"fit_mean_net_constrained_{min_trade_fraction:.2f}"
    return _fit


# -- equal-event-count windowing (fix #2), with correct truth tally ----------
def equal_count_windows(events: list[dict], fit_fn, n_windows: int) -> list[dict]:
    """Expanding-training-window walk-forward with equal-EVENT-COUNT test
    windows. Truth_up/truth_down are computed directly from each window's
    own test events at construction time (not re-derived from date ranges
    afterward), avoiding the pooling bug found in the earlier scratch
    version (walkforward_equal_count.py's _pool_manual stub)."""
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
        truth_down = 0
        truth_up = 0
        for ev, sig in zip(test, test_result["signals"]):
            if sig["position"] != 0 and abs(ev["ret_overnight"]) >= wf.FLAT_BAND:
                truth = "BUY" if ev["ret_overnight"] > 0 else "SELL"
                test_graded_correct.append(1 if sig["signal"] == truth else 0)
                if ev["ret_overnight"] < 0:
                    truth_down += 1
                else:
                    truth_up += 1

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
            "truth_down": truth_down,
            "truth_up": truth_up,
        })
    return windows


def pool_windows_correct(windows: list[dict]) -> dict:
    """Generic pooling: sums each window's own pre-computed test_nets /
    test_graded_correct / truth_down / truth_up. Works for equal-count
    windows (built above) and is shape-compatible with wf._pool_windows()'s
    output, so wf._print_pooled() works unchanged on either."""
    pooled_nets = []
    pooled_graded = []
    truth_down = 0
    truth_up = 0
    for w in windows:
        pooled_nets.extend(w["test_nets"])
        pooled_graded.extend(w["test_graded_correct"])
        truth_down += w["truth_down"]
        truth_up += w["truth_up"]

    n_trades = len(pooled_nets)
    n_graded = len(pooled_graded)
    n_correct = sum(pooled_graded)
    accuracy = n_correct / n_graded if n_graded > 0 else None
    mean_net = mean(pooled_nets) if pooled_nets else 0.0

    return {
        "n_trades": n_trades, "n_graded": n_graded, "n_correct": n_correct,
        "accuracy": accuracy, "mean_net": mean_net,
        "summed_pct": sum(pooled_nets) * 100 if pooled_nets else 0.0,
        "pooled_nets": pooled_nets, "pooled_graded": pooled_graded,
        "truth_down": truth_down, "truth_up": truth_up,
    }


def _cell_summary(windows, pool, degen, label):
    d = {
        "label": label,
        "n_windows": len(windows),
        "degenerate_windows": len(degen),
        "n_trades": pool["n_trades"],
        "n_graded": pool["n_graded"],
        "n_correct": pool["n_correct"],
        "accuracy": round(pool["accuracy"], 4) if pool["accuracy"] is not None else None,
        "mean_net_pct": round(pool["mean_net"] * 100, 4),
    }
    if pool["pooled_nets"]:
        bs = bootstrap_trade_stats(pool["pooled_nets"])
        d["bootstrap_90ci_mean_net_pct"] = {
            "ci_low": round(bs["mean_per_trade"]["ci_low"] * 100, 4),
            "ci_high": round(bs["mean_per_trade"]["ci_high"] * 100, 4),
        }
    if pool["n_graded"] > 0:
        majority_n = max(pool["truth_down"], pool["truth_up"])
        majority_label = "always-DOWN" if pool["truth_down"] >= pool["truth_up"] else "always-BUY"
        floor = majority_n / pool["n_graded"]
        d["majority_direction_floor"] = round(floor, 4)
        d["majority_direction_label"] = majority_label
        if pool["accuracy"] is not None:
            d["margin_vs_floor_pp"] = round((pool["accuracy"] - floor) * 100, 1)
            binom = binomtest(pool["n_correct"], pool["n_graded"], floor, alternative="greater")
            d["binomial_p"] = round(binom.pvalue, 4)
        mde = (Z_ALPHA + Z_BETA) * np.sqrt(2 * floor * (1 - floor) / pool["n_graded"])
        d["mde_pp"] = round(mde * 100, 1)
    return d


def main():
    events = wf._load_clean_events()
    n = len(events)
    print(f"Loaded {n} clean events (expected 233)")
    assert n > 200, f"Expected ~233, got {n}"

    # ---- consistency check against the canonical original file ----
    deployed = wf._evaluate_thresholds(events, wf.DEFAULT_HOLD_UPPER, wf.DEFAULT_HOLD_LOWER)
    orig_path = SUMMARY_DIR / "item_e_walkforward.json"
    if orig_path.exists():
        with open(orig_path) as f:
            orig = json.load(f)
        od = orig["in_sample_deployed"]
        ok = (od["n_trades"] == deployed["n_trades"]
              and od["n_correct"] == deployed["n_correct"]
              and abs(od["mean_net_pct"] - deployed["mean_net"] * 100) < 1e-3)
        print(f"Consistency check vs item_e_walkforward.json in_sample_deployed: "
              f"{'PASS' if ok else 'FAIL'} (n_trades {deployed['n_trades']} vs {od['n_trades']}, "
              f"mean_net {deployed['mean_net']*100:.4f}% vs {od['mean_net_pct']:.4f}%)")
        assert ok, "Data/baseline drifted from the canonical item_e_walkforward.json -- investigate before trusting this sweep."
    else:
        print("WARNING: item_e_walkforward.json not found, skipping consistency check.")

    grid = []

    # ---- schemes: calendar-quarter (original) + equal-count {2,3,4,5} ----
    schemes = [("calendar_quarter", None)] + [("equal_count", nw) for nw in EQUAL_COUNT_WINDOWS]

    for scheme_name, nw in schemes:
        scheme_label = scheme_name if nw is None else f"{scheme_name}_{nw}w"
        print("\n" + "=" * 80)
        print(f"SCHEME: {scheme_label}")
        print("=" * 80)

        # -- mean-net objective, sweep min_trade_fraction --
        for frac in MEAN_NET_FRACTIONS:
            fit_fn = make_fit_mean_net_constrained(frac)
            cell_label = f"{scheme_label} / mean_net(floor={frac:.0%})"
            if scheme_name == "calendar_quarter":
                windows = wf.rolling_walkforward(events, fit_fn)
                pool = wf._pool_windows(windows, events)
            else:
                windows = equal_count_windows(events, fit_fn, nw)
                pool = pool_windows_correct(windows)
            degen = wf._print_windows(windows, cell_label)
            wf._print_pooled(pool, cell_label)
            grid.append(_cell_summary(windows, pool, degen, cell_label))

        # -- accuracy objective (already constrained at fixed 15% in wf) --
        cell_label = f"{scheme_label} / accuracy(floor=15%, fixed)"
        if scheme_name == "calendar_quarter":
            windows = wf.rolling_walkforward(events, wf.fit_thresholds_accuracy)
            pool = wf._pool_windows(windows, events)
        else:
            windows = equal_count_windows(events, wf.fit_thresholds_accuracy, nw)
            pool = pool_windows_correct(windows)
        degen = wf._print_windows(windows, cell_label)
        wf._print_pooled(pool, cell_label)
        grid.append(_cell_summary(windows, pool, degen, cell_label))

    # ---- summary table ----
    print("\n" + "=" * 100)
    print("FULL GRID SUMMARY (every cell swept, none cherry-picked)")
    print("=" * 100)
    header = (f"{'Cell':<45} {'Win':>4} {'Degen':>6} {'Trades':>7} {'Graded':>7} "
              f"{'Acc':>7} {'MeanNet%':>9} {'MarginPP':>9} {'p':>7} {'MDEpp':>7}")
    print(header)
    print("-" * len(header))
    for c in grid:
        acc_s = f"{c['accuracy']:.1%}" if c["accuracy"] is not None else "N/A"
        margin_s = f"{c.get('margin_vs_floor_pp', ''):+.1f}" if "margin_vs_floor_pp" in c else "N/A"
        p_s = f"{c.get('binomial_p', ''):.4f}" if "binomial_p" in c else "N/A"
        mde_s = f"{c.get('mde_pp', ''):.1f}" if "mde_pp" in c else "N/A"
        print(f"{c['label']:<45} {c['n_windows']:>4} {c['degenerate_windows']:>6} "
              f"{c['n_trades']:>7} {c['n_graded']:>7} {acc_s:>7} {c['mean_net_pct']:>+9.3f} "
              f"{margin_s:>9} {p_s:>7} {mde_s:>7}")

    best_degen = min(grid, key=lambda c: c["degenerate_windows"])
    zero_degen = [c for c in grid if c["degenerate_windows"] == 0]
    print(f"\nOriginal canonical finding (walkforward_validation.py, calendar-quarter, "
          f"unconstrained): mean_net 3/4 degenerate, accuracy 2/4 degenerate.")
    print(f"Best single cell in this sweep by degenerate-window count: "
          f"'{best_degen['label']}' ({best_degen['degenerate_windows']}/{best_degen['n_windows']} degenerate)")
    print(f"Cells with ZERO degenerate windows: {len(zero_degen)}/{len(grid)}"
          + (f" -> {[c['label'] for c in zero_degen]}" if zero_degen else " -- none found."))

    # ---- write outputs ----
    output = {
        "label": "Item E best-effort walk-forward -- full swept grid, N=233, "
                 "NO NEW DATA. RETROSPECTIVE, NOT PRE-REGISTERED. "
                 "Additional robustness layer on top of item_e_walkforward.json "
                 "(unchanged, still canonical).",
        "n_clean_events": n,
        "sweep_dimensions": {
            "window_schemes": ["calendar_quarter"] + [f"equal_count_{nw}w" for nw in EQUAL_COUNT_WINDOWS],
            "mean_net_min_trade_fractions": list(MEAN_NET_FRACTIONS),
            "accuracy_min_trade_fraction": "15% (fixed, unchanged from walkforward_validation.py)",
        },
        "grid": grid,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nWrote full grid JSON -> {OUT_JSON}")

    import csv
    with open(OUT_CSV, "w", newline="") as f:
        fieldnames = ["label", "n_windows", "degenerate_windows", "n_trades", "n_graded",
                      "n_correct", "accuracy", "mean_net_pct", "majority_direction_floor",
                      "margin_vs_floor_pp", "binomial_p", "mde_pp"]
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(grid)
    print(f"Wrote summary CSV -> {OUT_CSV}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
