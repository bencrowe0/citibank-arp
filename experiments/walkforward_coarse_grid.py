"""
experiments/walkforward_coarse_grid.py
Item E follow-up: does a smaller threshold search space fix the rolling
walk-forward degeneracy found in walkforward_validation.py?

CONTEXT (see experiments/walkforward_validation.py's own module docstring for
the full original finding): refitting hold_upper/hold_lower per window on a
fine 0.05-step 2D grid (~90 valid combos) degenerates to near-untradeable
extreme thresholds in most windows under the mean-net objective, and barely
clears its own floor under the accuracy objective. That instability could be
a property of the underlying signal, or an artefact of searching too large a
space on too little training data per window. This script tests the second
possibility directly, at zero new data cost, by rerunning the identical
rolling-window engine with two smaller search spaces:

  Variant A — coarse asymmetric grid: same two free parameters
  (hold_upper, hold_lower), but a 0.10 step instead of 0.05
  (~5x6=30 combos vs ~90).

  Variant B — symmetric single-parameter band: hold_upper = t,
  hold_lower = -t, searched over one free parameter t in
  {0.05, 0.10, ..., 0.50} (10 combos). This deliberately departs from the
  deployed (asymmetric +0.25/-0.05) convention -- it is a simplification
  being tested for stability, not a claim that the deployed thresholds
  should be symmetric.

Reuses walkforward_validation.py's data loading, evaluation, and rolling-
window engine unchanged (imported as `wf`) -- only the threshold search
itself differs. Does not modify or overwrite any of that script's outputs.

Run: python -m experiments.walkforward_coarse_grid
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path
from statistics import mean

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import experiments.walkforward_validation as wf  # noqa: E402

SUMMARY_DIR = Path(__file__).resolve().parent.parent / "outputs" / "global" / "summary"
OUT_JSON = SUMMARY_DIR / "item_e_walkforward_coarse_grid.json"

# Variant A: coarse asymmetric grid (0.10 step vs original 0.05 step)
COARSE_UPPER_RANGE = np.arange(0.05, 0.55, 0.10)
COARSE_LOWER_RANGE = np.arange(-0.50, 0.05, 0.10)

# Variant B: symmetric single-parameter band
SYMMETRIC_BAND_RANGE = np.arange(0.05, 0.55, 0.05)


def fit_thresholds_mean_net_symmetric(train_events: list[dict]) -> tuple[float, float, dict]:
    """Grid-search a single symmetric band t (hold_upper=t, hold_lower=-t)
    maximising mean net per trade."""
    best = None
    best_t = wf.DEFAULT_HOLD_UPPER

    for t in SYMMETRIC_BAND_RANGE:
        t_r = round(float(t), 2)
        result = wf._evaluate_thresholds(train_events, t_r, -t_r)
        if result["n_trades"] == 0:
            continue
        if best is None or result["mean_net"] > best["mean_net"]:
            best = result
            best_t = t_r

    if best is None:
        best = wf._evaluate_thresholds(train_events, wf.DEFAULT_HOLD_UPPER, wf.DEFAULT_HOLD_LOWER)
        best_t = wf.DEFAULT_HOLD_UPPER

    return best_t, -best_t, best


def fit_thresholds_accuracy_symmetric(train_events: list[dict]) -> tuple[float, float, dict]:
    """Grid-search a single symmetric band t maximising directional accuracy,
    subject to the same minimum trade-count constraint as the original script."""
    min_trades = max(wf.MIN_TRADES_FLOOR, int(len(train_events) * wf.MIN_TRADE_FRACTION))

    best = None
    best_t = wf.DEFAULT_HOLD_UPPER

    for t in SYMMETRIC_BAND_RANGE:
        t_r = round(float(t), 2)
        result = wf._evaluate_thresholds(train_events, t_r, -t_r)
        if result["n_trades"] < min_trades:
            continue
        if result["n_graded"] == 0:
            continue
        if best is None or result["accuracy"] > best["accuracy"]:
            best = result
            best_t = t_r

    if best is None:
        best = wf._evaluate_thresholds(train_events, wf.DEFAULT_HOLD_UPPER, wf.DEFAULT_HOLD_LOWER)
        best_t = wf.DEFAULT_HOLD_UPPER

    return best_t, -best_t, best


def _run_variant(events, label, fit_mean_net, fit_accuracy, grid_note):
    print("\n" + "=" * 80)
    print(f"VARIANT: {label}")
    print(f"  {grid_note}")
    print("=" * 80)

    windows_mn = wf.rolling_walkforward(events, fit_mean_net)
    degen_mn = wf._print_windows(windows_mn, f"{label} / mean_net")
    pool_mn = wf._pool_windows(windows_mn, events)
    wf._print_pooled(pool_mn, f"{label} / mean_net")

    windows_acc = wf.rolling_walkforward(events, fit_accuracy)
    degen_acc = wf._print_windows(windows_acc, f"{label} / accuracy")
    pool_acc = wf._pool_windows(windows_acc, events)
    wf._print_pooled(pool_acc, f"{label} / accuracy")

    total_windows = len(windows_mn)
    print(f"\n  Degeneracy: mean_net {len(degen_mn)}/{total_windows}, "
          f"accuracy {len(degen_acc)}/{total_windows}")

    def _summ(windows, degen, pool):
        return {
            "n_windows": len(windows),
            "degenerate_windows": len(degen),
            "fitted_thresholds_by_window": [
                {"window_idx": w["window_idx"], "fitted_upper": w["fitted_upper"],
                 "fitted_lower": w["fitted_lower"], "test_trades": w["test_trades"]}
                for w in windows
            ],
            "pooled_oos": {
                "n_trades": pool["n_trades"],
                "n_graded": pool["n_graded"],
                "n_correct": pool["n_correct"],
                "accuracy": round(pool["accuracy"], 4) if pool["accuracy"] is not None else None,
                "mean_net_pct": round(pool["mean_net"] * 100, 4),
            },
        }

    return {
        "grid_note": grid_note,
        "mean_net_objective": _summ(windows_mn, degen_mn, pool_mn),
        "accuracy_objective": _summ(windows_acc, degen_acc, pool_acc),
        "both_degenerate": len(degen_mn) > 0 and len(degen_acc) > 0,
    }


def main():
    events = wf._load_clean_events()
    n = len(events)
    print(f"Loaded {n} clean events (expected 233)")
    assert n > 200, f"Expected ~233, got {n}"

    results = {}

    # --- Variant A: coarse asymmetric grid (monkey-patch wf's module-level
    # grid globals, since wf.fit_thresholds_mean_net/accuracy read them as
    # module globals at call time) ---
    orig_upper, orig_lower = wf.THRESH_UPPER_RANGE, wf.THRESH_LOWER_RANGE
    wf.THRESH_UPPER_RANGE = COARSE_UPPER_RANGE
    wf.THRESH_LOWER_RANGE = COARSE_LOWER_RANGE
    n_combos_coarse = sum(1 for hu, hl in itertools.product(COARSE_UPPER_RANGE, COARSE_LOWER_RANGE)
                           if round(float(hu), 2) > round(float(hl), 2))
    try:
        results["coarse_asymmetric"] = _run_variant(
            events, "COARSE ASYMMETRIC (0.10 step)",
            wf.fit_thresholds_mean_net, wf.fit_thresholds_accuracy,
            f"{n_combos_coarse} valid (hu,hl) combos vs original ~90 (0.05 step)",
        )
    finally:
        wf.THRESH_UPPER_RANGE, wf.THRESH_LOWER_RANGE = orig_upper, orig_lower

    # --- Variant B: symmetric single-parameter band ---
    results["symmetric_band"] = _run_variant(
        events, "SYMMETRIC BAND (single parameter t, hold_upper=t/hold_lower=-t)",
        fit_thresholds_mean_net_symmetric, fit_thresholds_accuracy_symmetric,
        f"{len(SYMMETRIC_BAND_RANGE)} valid t values vs original ~90 (hu,hl) combos",
    )

    # --- Comparison against the original fine-grid finding on disk ---
    orig_path = SUMMARY_DIR / "item_e_walkforward.json"
    orig_summary = None
    if orig_path.exists():
        with open(orig_path) as f:
            orig = json.load(f)
        rw = orig["rolling_walkforward"]
        orig_summary = {
            "grid_note": "original fine grid, 0.05 step, ~90 combos",
            "n_windows": rw["n_windows"],
            "mean_net_degenerate": rw["degeneracy_finding"]["mean_net_degenerate"],
            "accuracy_degenerate": rw["degeneracy_finding"]["accuracy_degenerate"],
            "both_degenerate": rw["degeneracy_finding"]["both_degenerate"],
        }

    print("\n" + "=" * 80)
    print("SUMMARY: DOES A SMALLER SEARCH SPACE FIX THE DEGENERACY?")
    print("=" * 80)
    if orig_summary:
        print(f"\n  Original (fine, 0.05 step):     "
              f"mean_net {orig_summary['mean_net_degenerate']}/{orig_summary['n_windows']} degenerate, "
              f"accuracy {orig_summary['accuracy_degenerate']}/{orig_summary['n_windows']} degenerate, "
              f"both={orig_summary['both_degenerate']}")
    ca = results["coarse_asymmetric"]
    print(f"  Coarse asymmetric (0.10 step):  "
          f"mean_net {ca['mean_net_objective']['degenerate_windows']}/{ca['mean_net_objective']['n_windows']} degenerate, "
          f"accuracy {ca['accuracy_objective']['degenerate_windows']}/{ca['accuracy_objective']['n_windows']} degenerate, "
          f"both={ca['both_degenerate']}")
    sb = results["symmetric_band"]
    print(f"  Symmetric band (1 free param):  "
          f"mean_net {sb['mean_net_objective']['degenerate_windows']}/{sb['mean_net_objective']['n_windows']} degenerate, "
          f"accuracy {sb['accuracy_objective']['degenerate_windows']}/{sb['accuracy_objective']['n_windows']} degenerate, "
          f"both={sb['both_degenerate']}")

    output = {
        "label": "Item E follow-up — coarser/simpler threshold search spaces, "
                 "same rolling-window engine and N=233 event set as "
                 "walkforward_validation.py. RETROSPECTIVE, NOT PRE-REGISTERED.",
        "n_clean_events": n,
        "original_fine_grid": orig_summary,
        "variants": results,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nWrote full results -> {OUT_JSON}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
