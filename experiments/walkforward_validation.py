"""
experiments/walkforward_validation.py
Item E: Walk-forward (rolling) validation of HOLD threshold selection.

RETROSPECTIVE VALIDATION — NOT PRE-REGISTERED.

The deployed thresholds (hold_upper=+0.25, hold_lower=-0.05) were selected by
optimising compounded total return (now retired as order-dependent) on the full
dataset (PSR=0.0, permutation p=0.150). This script refits hold_upper and
hold_lower out of sample using rolling windows, to test whether the 65.3%
selectivity accuracy survives without in-sample selection.

Design:
  - Weights are FIXED at DEFAULT_WEIGHTS=(0.55, 0.45, 0.0, 0.0). Only the two
    HOLD thresholds are refit per window.
  - Objective: maximise MEAN NET PER TRADE on the training window (not summed
    or compounded total return — order-independent, doesn't scale with N).
  - Rolling: start at ~40% of events by release_date, step forward one calendar
    quarter, refit thresholds on training slice, score next quarter OOS.
  - Two-window headline: fit on events <= 2026-08-10, score events after.
    Currently empty (all 233 clean events predate the freeze).
  - Degenerate-window assertion: if any window's OOS trade count falls below
    MIN_TRADES_FLOOR, assert loudly (threshold went degenerate).

Exclusions (35 events from 268 -> N=233 clean):
  - 25 worksheet contamination (worksheet_leak_flags.csv)
  - 1 SPOT_FQ1_2026 (misattributed document)
  - 9 timing-excluded (timing_excluded=YES in returns_matrix.csv)

Run: python -m experiments.walkforward_validation
"""
from __future__ import annotations

import csv
import itertools
import json
import sys
from datetime import datetime
from pathlib import Path
from statistics import mean, pstdev

import numpy as np
from scipy import stats as sp_stats

# -- project imports ----------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from blend import (
    DEFAULT_HOLD_LOWER,
    DEFAULT_HOLD_UPPER,
    DEFAULT_WEIGHTS,
    blend_scores,
)
from bootstrap_stats import bootstrap_trade_stats, bootstrap_unpaired_difference

# -- paths --------------------------------------------------------------------
SUMMARY_DIR = Path(__file__).resolve().parent.parent / "outputs" / "global" / "summary"
RETURNS_CSV = SUMMARY_DIR / "returns_matrix.csv"
CALIBRATION_CSV = SUMMARY_DIR / "global_outcome_calibration_phase2.csv"
LEAK_FLAGS_CSV = SUMMARY_DIR / "worksheet_leak_flags.csv"

OUT_CSV = SUMMARY_DIR / "item_e_walkforward.csv"
OUT_JSON = SUMMARY_DIR / "item_e_walkforward.json"

# -- constants ----------------------------------------------------------------
COST_BPS = 10.0
SHORT_BORROW_BPS = 0.0
COST_FRAC = COST_BPS / 10_000
FLAT_BAND = 0.02  # +/- 2% overnight grading band

# Threshold search grid
THRESH_UPPER_RANGE = np.arange(0.05, 0.55, 0.05)  # 0.05 to 0.50
THRESH_LOWER_RANGE = np.arange(-0.50, 0.05, 0.05)  # -0.50 to 0.00

# Degenerate-window floor
MIN_TRADES_FLOOR = 5

# Two-window freeze date
FREEZE_DATE = "2026-08-10"


# -- data loading -------------------------------------------------------------
def _num(x):
    if x is None or x == "":
        return None
    return float(x)


def _load_clean_events() -> list[dict]:
    """Load the N=233 clean event universe, merging calibration + returns_matrix.

    Each event dict has:
      document_id, ticker, issuer, report_date (from calibration),
      release_date (from returns_matrix report_date, which IS the release_date),
      micro_score, macro_score, news_score, quant_score,
      ret_overnight, blend_predicted_signal_default
    """
    # Load calibration
    cal = {}
    with open(CALIBRATION_CSV) as f:
        for r in csv.DictReader(f):
            cal[r["document_id"]] = r

    # Load returns_matrix (anchored to release_date)
    rm = {}
    with open(RETURNS_CSV) as f:
        for r in csv.DictReader(f):
            rm[r["document_id"]] = r

    # Load exclusion sets
    worksheet_excluded = set()
    with open(LEAK_FLAGS_CSV) as f:
        for r in csv.DictReader(f):
            if r.get("has_human_score", "").strip() == "True":
                worksheet_excluded.add(r["document_id"])
    spot_excluded = {"SPOT_FQ1_2026"}

    # Merge and filter
    events = []
    for did, c in cal.items():
        # Worksheet exclusion
        if did in worksheet_excluded:
            continue
        # SPOT exclusion
        if did in spot_excluded:
            continue
        # Timing exclusion
        r = rm.get(did)
        if r is None:
            continue
        if r.get("timing_excluded") == "YES":
            continue

        ret_overnight = _num(r.get("ret_overnight"))
        if ret_overnight is None:
            continue

        events.append({
            "document_id": did,
            "ticker": c["ticker"],
            "issuer": c["issuer"],
            # release_date = returns_matrix's report_date (already anchored)
            "release_date": r["report_date"],
            "micro_score": _num(c["micro_score"]),
            "macro_score": _num(c["macro_score"]),
            "news_score": _num(c["news_score"]),
            "quant_score": _num(c["quant_score"]),
            "ret_overnight": ret_overnight,
            "blend_predicted_signal_default": c["blend_predicted_signal_default"],
        })

    # Sort by release_date
    events.sort(key=lambda e: e["release_date"])
    return events


def _blend_score(ev: dict) -> float:
    """Compute the deployed blended score for an event."""
    return blend_scores(
        ev["micro_score"],
        ev["macro_score"],
        ev["news_score"],
        ev["quant_score"],
        DEFAULT_WEIGHTS,
    )


def _derive_signal(score: float, hold_upper: float, hold_lower: float) -> str:
    """BUY/HOLD/SELL from a blended score and threshold pair.
    Matches blend.derive_signal(): strict inequalities (score ON the boundary = HOLD)."""
    if score > hold_upper:
        return "BUY"
    elif score < hold_lower:
        return "SELL"
    return "HOLD"


def _net_return(position: int, gap: float) -> float:
    """Net return for a single trade, after costs."""
    if position == 0:
        return 0.0
    gross = position * gap
    cost = COST_FRAC + (SHORT_BORROW_BPS / 10_000 if position < 0 else 0.0)
    return gross - cost


# -- threshold fitting --------------------------------------------------------
def _evaluate_thresholds(
    events: list[dict],
    hold_upper: float,
    hold_lower: float,
) -> dict:
    """Evaluate a threshold pair on a set of events.

    Returns dict with: mean_net, n_trades, n_graded, n_correct, accuracy,
    summed_return, signals list.
    """
    nets = []
    n_graded = 0
    n_correct = 0
    signals = []

    for ev in events:
        score = _blend_score(ev)
        signal = _derive_signal(score, hold_upper, hold_lower)
        ret = ev["ret_overnight"]

        if signal == "BUY":
            position = 1
        elif signal == "SELL":
            position = -1
        else:
            position = 0

        net = _net_return(position, ret)

        if position != 0:
            nets.append(net)

            # Grade against +/- 2% band
            if abs(ret) >= FLAT_BAND:
                n_graded += 1
                truth = "BUY" if ret > 0 else "SELL"
                if signal == truth:
                    n_correct += 1

        signals.append({
            "document_id": ev["document_id"],
            "signal": signal,
            "position": position,
            "net": net,
        })

    n_trades = len(nets)
    mean_net = mean(nets) if nets else 0.0
    accuracy = n_correct / n_graded if n_graded > 0 else None

    return {
        "hold_upper": hold_upper,
        "hold_lower": hold_lower,
        "mean_net": mean_net,
        "n_trades": n_trades,
        "n_graded": n_graded,
        "n_correct": n_correct,
        "accuracy": accuracy,
        "summed_return": sum(nets),
        "signals": signals,
    }


def fit_thresholds(train_events: list[dict]) -> tuple[float, float, dict]:
    """Grid-search for (hold_upper, hold_lower) maximising mean net per trade
    on the training events.

    Returns (best_upper, best_lower, best_result_dict).
    """
    best = None
    best_upper = DEFAULT_HOLD_UPPER
    best_lower = DEFAULT_HOLD_LOWER

    for hu, hl in itertools.product(THRESH_UPPER_RANGE, THRESH_LOWER_RANGE):
        hu_r = round(float(hu), 2)
        hl_r = round(float(hl), 2)
        if hu_r <= hl_r:
            continue  # upper must exceed lower

        result = _evaluate_thresholds(train_events, hu_r, hl_r)

        # Skip combos that produce no trades (degenerate)
        if result["n_trades"] == 0:
            continue

        if best is None or result["mean_net"] > best["mean_net"]:
            best = result
            best_upper = hu_r
            best_lower = hl_r

    if best is None:
        # Fallback to deployed defaults
        best = _evaluate_thresholds(train_events, DEFAULT_HOLD_UPPER, DEFAULT_HOLD_LOWER)
        best_upper = DEFAULT_HOLD_UPPER
        best_lower = DEFAULT_HOLD_LOWER

    return best_upper, best_lower, best


# -- walk-forward engine ------------------------------------------------------
def _quarter_cutoffs(events: list[dict]) -> list[str]:
    """Generate calendar quarter cutoff dates spanning the event set.

    Returns dates like ["2025-03-31", "2025-06-30", "2025-09-30", ...] that
    partition the event timeline into quarters.
    """
    dates = sorted(set(e["release_date"] for e in events))
    if not dates:
        return []

    start_dt = datetime.strptime(dates[0], "%Y-%m-%d")
    end_dt = datetime.strptime(dates[-1], "%Y-%m-%d")

    cutoffs = []
    # Start from the quarter containing the first event
    year = start_dt.year
    q = (start_dt.month - 1) // 3  # 0-based quarter
    while True:
        # End of this quarter
        month_end = [3, 6, 9, 12][q]
        if month_end == 12:
            cutoff = f"{year}-12-31"
        else:
            cutoff = f"{year}-{month_end:02d}-30"
        # Use actual last day of quarter
        if month_end == 3:
            cutoff = f"{year}-03-31"
        elif month_end == 6:
            cutoff = f"{year}-06-30"
        elif month_end == 9:
            cutoff = f"{year}-09-30"
        else:
            cutoff = f"{year}-12-31"

        if cutoff > end_dt.strftime("%Y-%m-%d"):
            break
        cutoffs.append(cutoff)

        q += 1
        if q > 3:
            q = 0
            year += 1

    return cutoffs


def rolling_walkforward(events: list[dict]) -> list[dict]:
    """Rolling walk-forward: start at ~40% of events, step one quarter.

    Returns a list of window results, each containing:
      window_idx, train_cutoff, test_start, test_end,
      fitted_upper, fitted_lower,
      train_n, train_trades, train_mean_net, train_accuracy,
      test_n, test_trades, test_mean_net, test_accuracy,
      test_n_graded, test_n_correct,
      test_nets (list of per-trade net returns for pooling)
    """
    n_total = len(events)
    cutoffs = _quarter_cutoffs(events)
    if not cutoffs:
        return []

    # Find the cutoff at ~40% of events
    start_idx = None
    for i, cutoff in enumerate(cutoffs):
        n_before = sum(1 for e in events if e["release_date"] <= cutoff)
        if n_before >= 0.4 * n_total:
            start_idx = i
            break
    if start_idx is None:
        start_idx = len(cutoffs) - 2  # fallback

    windows = []
    for w_idx, cutoff_idx in enumerate(range(start_idx, len(cutoffs))):
        train_cutoff = cutoffs[cutoff_idx]
        train = [e for e in events if e["release_date"] <= train_cutoff]
        if len(train) < MIN_TRADES_FLOOR:
            continue

        # Test: next quarter (from day after train_cutoff to next cutoff or end)
        if cutoff_idx + 1 < len(cutoffs):
            test_end = cutoffs[cutoff_idx + 1]
        else:
            # Last window: test on everything after train_cutoff
            test_end = "9999-12-31"

        test = [e for e in events
                if e["release_date"] > train_cutoff
                and e["release_date"] <= test_end]

        if not test:
            continue

        # Fit thresholds on training window
        fitted_upper, fitted_lower, train_result = fit_thresholds(train)

        # Evaluate on test window with fitted thresholds
        test_result = _evaluate_thresholds(test, fitted_upper, fitted_lower)

        # Collect test nets for pooling
        test_nets = [s["net"] for s in test_result["signals"] if s["position"] != 0]

        # Collect test grading details for per-event pooling
        test_graded_correct = []
        for ev, sig in zip(test, test_result["signals"]):
            if sig["position"] != 0 and abs(ev["ret_overnight"]) >= FLAT_BAND:
                truth = "BUY" if ev["ret_overnight"] > 0 else "SELL"
                test_graded_correct.append(1 if sig["signal"] == truth else 0)

        window = {
            "window_idx": w_idx,
            "train_cutoff": train_cutoff,
            "test_start": test[0]["release_date"] if test else None,
            "test_end": test[-1]["release_date"] if test else None,
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
        }
        windows.append(window)

    return windows


def two_window_headline(events: list[dict]) -> dict:
    """Fit on events <= FREEZE_DATE, score events after.

    Currently expected to be empty (all 233 events predate the freeze).
    Exits cleanly if no test events exist.
    """
    train = [e for e in events if e["release_date"] <= FREEZE_DATE]
    test = [e for e in events if e["release_date"] > FREEZE_DATE]

    result = {
        "freeze_date": FREEZE_DATE,
        "train_n": len(train),
        "test_n": len(test),
        "status": None,
    }

    if not test:
        result["status"] = "DORMANT — no test events after freeze date"
        # Still fit on training to log the thresholds
        if train:
            fitted_upper, fitted_lower, train_result = fit_thresholds(train)
            result["fitted_upper"] = fitted_upper
            result["fitted_lower"] = fitted_lower
            result["train_trades"] = train_result["n_trades"]
            result["train_mean_net"] = train_result["mean_net"]
            result["train_accuracy"] = train_result["accuracy"]
        return result

    fitted_upper, fitted_lower, train_result = fit_thresholds(train)
    test_result = _evaluate_thresholds(test, fitted_upper, fitted_lower)

    result.update({
        "status": "ACTIVE",
        "fitted_upper": fitted_upper,
        "fitted_lower": fitted_lower,
        "train_trades": train_result["n_trades"],
        "train_mean_net": train_result["mean_net"],
        "train_accuracy": train_result["accuracy"],
        "test_trades": test_result["n_trades"],
        "test_mean_net": test_result["mean_net"],
        "test_accuracy": test_result["accuracy"],
        "test_n_graded": test_result["n_graded"],
        "test_n_correct": test_result["n_correct"],
    })
    return result


def _majority_direction_floor(events: list[dict], hold_upper: float,
                               hold_lower: float) -> dict:
    """Compute the majority-direction floor on graded events under a given
    threshold pair.

    Returns {"floor_label": "always-DOWN"|"always-BUY", "floor_rate": float,
             "n_graded": int, "n_down": int, "n_up": int}.
    """
    n_graded = n_down = n_up = 0
    for ev in events:
        score = _blend_score(ev)
        signal = _derive_signal(score, hold_upper, hold_lower)
        ret = ev["ret_overnight"]

        if signal == "HOLD":
            continue
        if abs(ret) < FLAT_BAND:
            continue

        n_graded += 1
        if ret < 0:
            n_down += 1
        else:
            n_up += 1

    if n_graded == 0:
        return {"floor_label": "N/A", "floor_rate": 0.0,
                "n_graded": 0, "n_down": 0, "n_up": 0}

    if n_down >= n_up:
        return {"floor_label": "always-DOWN", "floor_rate": n_down / n_graded,
                "n_graded": n_graded, "n_down": n_down, "n_up": n_up}
    else:
        return {"floor_label": "always-BUY", "floor_rate": n_up / n_graded,
                "n_graded": n_graded, "n_down": n_down, "n_up": n_up}


# -- main --------------------------------------------------------------------
def main():
    events = _load_clean_events()
    n = len(events)
    print(f"Loaded {n} clean events (expected 233)")
    assert n > 200, f"Expected ~233, got {n}"

    date_range = f"{events[0]['release_date']} to {events[-1]['release_date']}"
    print(f"Date range: {date_range}")

    # ---- In-sample baseline (deployed thresholds) for comparison ----
    deployed = _evaluate_thresholds(events, DEFAULT_HOLD_UPPER, DEFAULT_HOLD_LOWER)
    print(f"\n=== IN-SAMPLE (deployed thresholds +{DEFAULT_HOLD_UPPER}/-{abs(DEFAULT_HOLD_LOWER)}) ===")
    print(f"  N={n}, trades={deployed['n_trades']}, graded={deployed['n_graded']}")
    print(f"  Accuracy: {deployed['n_correct']}/{deployed['n_graded']}"
          f" = {deployed['accuracy']:.1%}" if deployed['accuracy'] else "  Accuracy: N/A")
    print(f"  Mean net/trade: {deployed['mean_net']*100:+.3f}%")

    # ---- Rolling walk-forward ----
    print("\n=== ROLLING WALK-FORWARD ===")
    windows = rolling_walkforward(events)

    if not windows:
        print("  No valid windows produced!")
        return 1

    # Per-window log
    print(f"\n{'Win':>3} {'TrainCut':>10} {'TestSpan':>23} "
          f"{'FitUp':>6} {'FitLo':>6} "
          f"{'TrN':>4} {'TrTrd':>5} {'TrMean%':>8} {'TrAcc':>6} "
          f"{'TsN':>4} {'TsTrd':>5} {'TsMean%':>8} {'TsAcc':>6} {'TsGrd':>5}")
    print("-" * 130)

    degenerate_windows = []
    for w in windows:
        test_span = f"{w['test_start']} - {w['test_end']}"
        tr_acc = f"{w['train_accuracy']:.1%}" if w['train_accuracy'] is not None else "N/A"
        ts_acc = f"{w['test_accuracy']:.1%}" if w['test_accuracy'] is not None else "N/A"

        flag = ""
        if w["test_trades"] < MIN_TRADES_FLOOR:
            flag = " *** DEGENERATE"
            degenerate_windows.append(w)

        print(f"{w['window_idx']:>3} {w['train_cutoff']:>10} {test_span:>23} "
              f"{w['fitted_upper']:>6.2f} {w['fitted_lower']:>+6.2f} "
              f"{w['train_n']:>4} {w['train_trades']:>5} {w['train_mean_net']*100:>+8.3f} {tr_acc:>6} "
              f"{w['test_n']:>4} {w['test_trades']:>5} {w['test_mean_net']*100:>+8.3f} {ts_acc:>6} "
              f"{w['test_n_graded']:>5}{flag}")

    if degenerate_windows:
        print(f"\n  *** WARNING: {len(degenerate_windows)} window(s) have fewer "
              f"than {MIN_TRADES_FLOOR} OOS trades — threshold went degenerate!")
        for w in degenerate_windows:
            print(f"    Window {w['window_idx']}: {w['test_trades']} trades "
                  f"(fitted +{w['fitted_upper']}/{w['fitted_lower']:+.2f})")

    # ---- Pooled OOS results ----
    print("\n=== POOLED OUT-OF-SAMPLE RESULTS ===")

    # Pool all OOS trade nets
    pooled_nets = []
    for w in windows:
        pooled_nets.extend(w["test_nets"])

    # Pool all OOS graded correct/wrong
    pooled_graded = []
    for w in windows:
        pooled_graded.extend(w["test_graded_correct"])

    n_oos_trades = len(pooled_nets)
    n_oos_graded = len(pooled_graded)
    n_oos_correct = sum(pooled_graded)
    oos_accuracy = n_oos_correct / n_oos_graded if n_oos_graded > 0 else None
    oos_mean_net = mean(pooled_nets) if pooled_nets else 0.0
    oos_summed = sum(pooled_nets) * 100 if pooled_nets else 0.0

    print(f"  OOS trades: {n_oos_trades}")
    print(f"  OOS graded: {n_oos_graded}")
    if oos_accuracy is not None:
        print(f"  OOS accuracy: {n_oos_correct}/{n_oos_graded} = {oos_accuracy:.1%}")
    print(f"  OOS mean net/trade: {oos_mean_net*100:+.3f}%")
    print(f"  OOS summed return: {oos_summed:+.2f}%")

    # Bootstrap CI on pooled OOS
    if pooled_nets:
        bs = bootstrap_trade_stats(pooled_nets)
        print(f"\n  Bootstrap (90% CI, {bs['n_resamples']} resamples):")
        print(f"    Mean net/trade: {bs['mean_per_trade']['point']*100:+.3f}% "
              f"[{bs['mean_per_trade']['ci_low']*100:+.3f}%, "
              f"{bs['mean_per_trade']['ci_high']*100:+.3f}%]")
        print(f"    Hit rate: {bs['hit_rate']['point']:.1%} "
              f"[{bs['hit_rate']['ci_low']:.1%}, {bs['hit_rate']['ci_high']:.1%}]")
        print(f"    t-statistic: {bs['t_statistic']['point']:.3f} "
              f"[{bs['t_statistic']['ci_low']:.3f}, {bs['t_statistic']['ci_high']:.3f}]")

    # ---- Majority-direction floor on pooled OOS graded ----
    # The floor must be computed on the events that were actually graded OOS
    # (using the fitted thresholds, not the deployed ones)
    # We need to collect the OOS graded events' directions
    oos_down = sum(1 for c in pooled_graded if c == 0)  # wrong = predicted wrong direction
    # Actually we need to reconstruct: n_down = events where truth=SELL in the graded set
    # Let's re-derive from windows
    oos_truth_down = 0
    oos_truth_up = 0
    for w in windows:
        test_events = [e for e in events
                       if e["release_date"] > w["train_cutoff"]
                       and e["release_date"] <= (w["test_end"] if w["test_end"] else "9999-12-31")]
        test_result = _evaluate_thresholds(test_events, w["fitted_upper"], w["fitted_lower"])
        for ev, sig in zip(test_events, test_result["signals"]):
            if sig["position"] != 0 and abs(ev["ret_overnight"]) >= FLAT_BAND:
                if ev["ret_overnight"] < 0:
                    oos_truth_down += 1
                else:
                    oos_truth_up += 1

    if n_oos_graded > 0:
        majority_n = max(oos_truth_down, oos_truth_up)
        majority_label = "always-DOWN" if oos_truth_down >= oos_truth_up else "always-BUY"
        majority_floor = majority_n / n_oos_graded

        print(f"\n  Majority-direction floor (OOS graded): "
              f"{majority_label} = {majority_n}/{n_oos_graded} = {majority_floor:.1%}")

        if oos_accuracy is not None:
            margin = oos_accuracy - majority_floor
            print(f"  OOS margin vs floor: {margin*100:+.1f}pp")

            # One-sided binomial test: accuracy > floor
            from scipy.stats import binomtest
            binom = binomtest(n_oos_correct, n_oos_graded, majority_floor,
                              alternative="greater")
            print(f"  Binomial test (accuracy > floor): p = {binom.pvalue:.4f}")

    # ---- Minimum detectable effect ----
    print("\n=== MINIMUM DETECTABLE EFFECT ===")
    if n_oos_graded > 0:
        # MDE for unpaired: two-proportion z-test approximation
        # MDE ≈ (z_alpha + z_beta) * sqrt(2 * p0 * (1-p0) / n)
        # alpha=0.10 one-sided, beta=0.20 (80% power)
        z_alpha = 1.282  # one-sided 0.10
        z_beta = 0.842   # 80% power
        p0 = majority_floor if n_oos_graded > 0 else 0.5
        mde_unpaired = (z_alpha + z_beta) * np.sqrt(2 * p0 * (1 - p0) / n_oos_graded)
        print(f"  Unpaired MDE (alpha=0.10 one-sided, 80% power): ±{mde_unpaired*100:.1f}pp "
              f"(N_graded={n_oos_graded})")

    # ---- Deployed thresholds on the same OOS windows (reference) ----
    print("\n=== DEPLOYED THRESHOLDS ON OOS WINDOWS (reference) ===")
    deployed_oos_nets = []
    deployed_oos_graded = []
    for w in windows:
        test_events = [e for e in events
                       if e["release_date"] > w["train_cutoff"]
                       and e["release_date"] <= (w["test_end"] if w["test_end"] else "9999-12-31")]
        dep_result = _evaluate_thresholds(test_events, DEFAULT_HOLD_UPPER, DEFAULT_HOLD_LOWER)
        dep_nets = [s["net"] for s in dep_result["signals"] if s["position"] != 0]
        deployed_oos_nets.extend(dep_nets)
        for ev, sig in zip(test_events, dep_result["signals"]):
            if sig["position"] != 0 and abs(ev["ret_overnight"]) >= FLAT_BAND:
                truth = "BUY" if ev["ret_overnight"] > 0 else "SELL"
                deployed_oos_graded.append(1 if sig["signal"] == truth else 0)
        dep_acc_str = f"{dep_result['accuracy']:.1%}" if dep_result["accuracy"] is not None else "N/A"
        print(f"  Window {w['window_idx']}: {dep_result['n_trades']} trades, "
              f"mean net {dep_result['mean_net']*100:+.3f}%, "
              f"accuracy {dep_acc_str} ({dep_result['n_correct']}/{dep_result['n_graded']})")

    if deployed_oos_nets:
        dep_oos_n_trades = len(deployed_oos_nets)
        dep_oos_mean_net = mean(deployed_oos_nets)
        dep_oos_n_graded = len(deployed_oos_graded)
        dep_oos_n_correct = sum(deployed_oos_graded)
        dep_oos_accuracy = dep_oos_n_correct / dep_oos_n_graded if dep_oos_n_graded > 0 else None
        print(f"  Pooled: {dep_oos_n_trades} trades, mean net {dep_oos_mean_net*100:+.3f}%, "
              f"accuracy {dep_oos_n_correct}/{dep_oos_n_graded}"
              + (f" = {dep_oos_accuracy:.1%}" if dep_oos_accuracy else ""))

    # ---- Compare OOS vs in-sample ----
    print("\n=== OOS vs IN-SAMPLE COMPARISON ===")
    if deployed["accuracy"] is not None and oos_accuracy is not None:
        print(f"  In-sample accuracy (deployed thresholds): "
              f"{deployed['n_correct']}/{deployed['n_graded']} = {deployed['accuracy']:.1%}")
        print(f"  Pooled OOS accuracy (refit thresholds):   "
              f"{n_oos_correct}/{n_oos_graded} = {oos_accuracy:.1%}")
        print(f"  Difference: {(oos_accuracy - deployed['accuracy'])*100:+.1f}pp")

    if deployed["mean_net"] and oos_mean_net:
        print(f"  In-sample mean net/trade: {deployed['mean_net']*100:+.3f}%")
        print(f"  Pooled OOS mean net/trade: {oos_mean_net*100:+.3f}%")
        print(f"  Difference: {(oos_mean_net - deployed['mean_net'])*100:+.3f}pp")

    # ---- Two-window headline ----
    print("\n=== TWO-WINDOW HEADLINE ===")
    tw = two_window_headline(events)
    print(f"  Freeze date: {tw['freeze_date']}")
    print(f"  Train N: {tw['train_n']}, Test N: {tw['test_n']}")
    print(f"  Status: {tw['status']}")
    if tw.get("fitted_upper") is not None:
        print(f"  Fitted thresholds: +{tw['fitted_upper']}/{tw['fitted_lower']:+.2f}")
        if tw.get("train_trades"):
            print(f"  Train trades: {tw['train_trades']}, "
                  f"mean net: {tw['train_mean_net']*100:+.3f}%")

    # ---- Write outputs ----
    # CSV: per-window log
    csv_rows = []
    for w in windows:
        csv_rows.append({
            "window_idx": w["window_idx"],
            "train_cutoff": w["train_cutoff"],
            "test_start": w["test_start"],
            "test_end": w["test_end"],
            "fitted_upper": w["fitted_upper"],
            "fitted_lower": w["fitted_lower"],
            "train_n": w["train_n"],
            "train_trades": w["train_trades"],
            "train_mean_net_pct": round(w["train_mean_net"] * 100, 4),
            "train_accuracy": round(w["train_accuracy"], 4) if w["train_accuracy"] is not None else "",
            "train_n_graded": w["train_n_graded"],
            "test_n": w["test_n"],
            "test_trades": w["test_trades"],
            "test_mean_net_pct": round(w["test_mean_net"] * 100, 4),
            "test_accuracy": round(w["test_accuracy"], 4) if w["test_accuracy"] is not None else "",
            "test_n_graded": w["test_n_graded"],
            "test_n_correct": w["test_n_correct"],
        })

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="") as f:
        fieldnames = list(csv_rows[0].keys()) if csv_rows else []
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"\nWrote per-window CSV -> {OUT_CSV}")

    # JSON: full results
    output = {
        "label": "RETROSPECTIVE VALIDATION — NOT PRE-REGISTERED",
        "n_clean_events": n,
        "date_range": date_range,
        "weights_fixed": list(DEFAULT_WEIGHTS),
        "objective": "mean_net_per_trade",
        "cost_bps": COST_BPS,
        "short_borrow_bps": SHORT_BORROW_BPS,
        "flat_band": FLAT_BAND,
        "threshold_grid": {
            "upper_range": [round(float(x), 2) for x in THRESH_UPPER_RANGE],
            "lower_range": [round(float(x), 2) for x in THRESH_LOWER_RANGE],
        },
        "in_sample_deployed": {
            "hold_upper": DEFAULT_HOLD_UPPER,
            "hold_lower": DEFAULT_HOLD_LOWER,
            "n_trades": deployed["n_trades"],
            "n_graded": deployed["n_graded"],
            "n_correct": deployed["n_correct"],
            "accuracy": round(deployed["accuracy"], 4) if deployed["accuracy"] else None,
            "mean_net_pct": round(deployed["mean_net"] * 100, 4),
            "summed_return_pct": round(deployed["summed_return"] * 100, 2),
        },
        "rolling_walkforward": {
            "n_windows": len(windows),
            "min_trades_floor": MIN_TRADES_FLOOR,
            "degenerate_windows": len(degenerate_windows),
            "windows": [{k: v for k, v in w.items()
                         if k not in ("test_nets", "test_graded_correct")}
                        for w in windows],
            "pooled_oos": {
                "n_trades": n_oos_trades,
                "n_graded": n_oos_graded,
                "n_correct": n_oos_correct,
                "accuracy": round(oos_accuracy, 4) if oos_accuracy is not None else None,
                "mean_net_pct": round(oos_mean_net * 100, 4),
                "summed_return_pct": round(oos_summed, 2),
                "majority_direction_floor": {
                    "label": majority_label if n_oos_graded > 0 else "N/A",
                    "rate": round(majority_floor, 4) if n_oos_graded > 0 else None,
                    "n_down": oos_truth_down,
                    "n_up": oos_truth_up,
                },
                "margin_vs_floor_pp": round(margin * 100, 1) if n_oos_graded > 0 and oos_accuracy is not None else None,
                "binomial_p": round(binom.pvalue, 4) if n_oos_graded > 0 else None,
                "mde_unpaired_pp": round(mde_unpaired * 100, 1) if n_oos_graded > 0 else None,
            },
        },
        "two_window_headline": tw,
    }

    # Add deployed-thresholds OOS reference
    if deployed_oos_nets:
        output["rolling_walkforward"]["deployed_thresholds_oos"] = {
            "hold_upper": DEFAULT_HOLD_UPPER,
            "hold_lower": DEFAULT_HOLD_LOWER,
            "n_trades": dep_oos_n_trades,
            "n_graded": dep_oos_n_graded,
            "n_correct": dep_oos_n_correct,
            "accuracy": round(dep_oos_accuracy, 4) if dep_oos_accuracy is not None else None,
            "mean_net_pct": round(dep_oos_mean_net * 100, 4),
        }

    # Add bootstrap if available
    if pooled_nets:
        output["rolling_walkforward"]["pooled_oos"]["bootstrap_90ci"] = {
            "mean_net_pct": {
                "point": round(bs["mean_per_trade"]["point"] * 100, 4),
                "ci_low": round(bs["mean_per_trade"]["ci_low"] * 100, 4),
                "ci_high": round(bs["mean_per_trade"]["ci_high"] * 100, 4),
            },
            "hit_rate": {
                "point": round(bs["hit_rate"]["point"], 4),
                "ci_low": round(bs["hit_rate"]["ci_low"], 4),
                "ci_high": round(bs["hit_rate"]["ci_high"], 4),
            },
            "t_statistic": {
                "point": round(bs["t_statistic"]["point"], 3),
                "ci_low": round(bs["t_statistic"]["ci_low"], 3),
                "ci_high": round(bs["t_statistic"]["ci_high"], 3),
            },
        }

    with open(OUT_JSON, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"Wrote full results -> {OUT_JSON}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
