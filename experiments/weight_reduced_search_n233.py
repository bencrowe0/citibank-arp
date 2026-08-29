"""
experiments/weight_reduced_search_n233.py

Addresses the report's own flagged gap (CLAUDE.md, Known gaps: "search for a
weighting that backtests well AND clears PSR/permutation/LOOCV ... constraining
the search to fewer free dimensions ... rather than the full 113k-combo grid
that guarantees an inflated-looking winner").

The deployed default (micro=0.55, macro=0.45, news=0, quant=0; thresholds
+0.25/-0.05) was picked by a 113,344-combo in-sample grid search at N=161 and
FAILED its own validity checks at selection time (PSR=0.0, permutation
p=0.150) - see blend.py's DEFAULT_WEIGHTS docstring / CLAUDE.md Architecture >
Blend. That combo has never been re-searched at the current N=233 clean,
release_date-anchored universe.

This script asks a narrower, more defensible question: on N=233, is there a
weighting that (a) still performs well on P&L, and (b) survives PSR/
permutation, once the search itself is small enough that the Deflated Sharpe
Ratio's own trial-count correction (Bailey & Lopez de Prado, 2014) doesn't
mechanically punish it to death? Two free-dimension reductions, both stated
rather than hidden:

  1. Weight simplex collapsed from 4 free dims (micro/macro/news/quant) to 1
     (micro vs macro only). News and quant are fixed at 0 - not arbitrarily,
     but because every prior sweep in this project (production's own P&L
     sweep, phase2's, weight_threshold_sweep.py's Fed/macro-numeric ablation)
     found quant inert and news either untested-material or explicitly
     zero-weighted by architecture. Reopening those two dimensions here would
     just reproduce the original overfitting problem this script exists to
     avoid.
  2. Two threshold grids, run side by side so neither is cherry-picked:
     Variant A - coarse asymmetric (5x5=25 pairs, step 0.10 vs the deployed
     sweep's step 0.05). Variant B - symmetric (hold_upper = -hold_lower,
     10 single-parameter values). 21 weight points x {25 or 10} threshold
     pairs = 525 / 210 total trials, vs the original 113,344 - roughly
     200x-500x fewer, so DSR's SR0 (expected max Sharpe achievable under a
     zero-skill null given this many trials) shrinks accordingly.

A THIRD, orthogonal fix, reused directly from the walk-forward robustness
follow-up (experiments/walkforward_best_effort.py): the winning combo must
clear a minimum-trade-count floor (15% of N=233, same convention as
walkforward_validation.fit_thresholds_accuracy) BEFORE its total return is
eligible to win. Without this a search can "win" by isolating a handful of
lucky outlier trades - exactly the mechanism that made the original
walk-forward mean-net objective degenerate, and a live risk in ANY
total-return-objective search, including this one, if left unconstrained.

Data: the same N=233 clean, release_date-anchored, exclusion-applied universe
as item_e_walkforward.json (experiments.walkforward_validation._load_clean_events,
reused directly rather than re-implementing the anchor/exclusion logic - see
CLAUDE.md's "nine-instance pattern" lesson on why re-deriving a correction
instead of importing the verified one is exactly how this project's past bugs
happened).

RETROSPECTIVE - NOT PRE-REGISTERED. Same caveat as every other threshold/weight
search in this project: N=233 was fully assembled and seen before this script
ran. This is a narrower-overfit-surface in-sample search, not an out-of-sample
validation. Its LOOCV and permutation-test numbers are the honesty checks
available at this N; they are not a substitute for genuine prospective data.

Run: python -m experiments.weight_reduced_search_n233
Out: outputs/global/summary/item_e_weight_reduced_search.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from blend import DEFAULT_HOLD_LOWER, DEFAULT_HOLD_UPPER, DEFAULT_WEIGHTS  # noqa: E402
from bootstrap_stats import bootstrap_trade_stats  # noqa: E402
from experiments.weight_threshold_sweep import build_layer_matrices, dist_from_default  # noqa: E402
from experiments.pnl_weight_threshold_sweep import (  # noqa: E402
    PERMUTATIONS,
    RNG_SEED,
    deflated_sharpe_ratio,
    permutation_test_pnl,
    pnl_tensor,
    sharpe_and_trade_stats,
    total_return_from_net,
)
import experiments.walkforward_validation as wf  # noqa: E402

COST_BPS = wf.COST_BPS
SHORT_BORROW_BPS = wf.SHORT_BORROW_BPS
MIN_TRADE_FRACTION = 0.15
WEIGHT_STEP = 0.05

SUMMARY_DIR = Path(__file__).resolve().parent.parent / "outputs" / "global" / "summary"
OUT_JSON = SUMMARY_DIR / "item_e_weight_reduced_search.json"


def restricted_weight_grid(step: float) -> np.ndarray:
    """(micro, macro, 0, 0) rows, micro+macro=1, micro from 0 to 1 in `step`
    increments - the 1-free-dimension collapse of the full 4-layer simplex."""
    n = round(1.0 / step)
    rows = []
    for a in range(n + 1):
        micro = round(a * step, 4)
        macro = round(1.0 - micro, 4)
        rows.append((micro, macro, 0.0, 0.0))
    return np.array(rows, dtype=float)


def to_docs(events: list[dict]) -> list[dict]:
    return [{
        "document_id": e["document_id"],
        "gap": e["ret_overnight"],
        "micro": e["micro_score"],
        "macro": e["macro_score"],
        "news": e["news_score"],
        "quant_variants": {"quant_score": e["quant_score"]},
    } for e in events]


def build_positions(S, M, W, threshold_pairs):
    """Same math as pnl_weight_threshold_sweep.position_tensor, generalized to
    an explicit list of (hold_upper, hold_lower) pairs instead of the module's
    global fine-grid constants."""
    num = W @ S.T
    den = W @ M.T
    den = np.where(den == 0, np.nan, den)
    blended = num / den
    nw, ndoc = blended.shape

    meta = []
    blocks = []
    for hu, hl in threshold_pairs:
        pos = np.zeros((nw, ndoc), dtype=np.int8)
        pos[blended > hu] = 1
        pos[blended < hl] = -1
        pos[np.isnan(blended)] = 0
        blocks.append(pos)
        for wi in range(nw):
            meta.append((wi, hu, hl))
    POS = np.concatenate(blocks, axis=0)
    return POS, meta


def run_variant(label, docs, W, threshold_pairs, min_trades, cost_bps, short_borrow_bps):
    gap = np.array([d["gap"] for d in docs])
    S, M = build_layer_matrices(docs, "quant_score")
    POS, meta = build_positions(S, M, W, threshold_pairs)
    NET = pnl_tensor(POS, gap, cost_bps, short_borrow_bps)
    ncombo, ndoc = NET.shape
    n_trials = ncombo

    total_return = total_return_from_net(NET)
    sharpe, n_trades, avg_net_per_trade = sharpe_and_trade_stats(NET, POS)

    eligible = n_trades >= min_trades
    if not eligible.any():
        raise RuntimeError(f"[{label}] no combo meets the {min_trades}-trade floor")
    elig_idx = np.where(eligible)[0]

    best_val = total_return[elig_idx].max()
    tied_local = np.where(total_return[elig_idx] == best_val)[0]
    tied = elig_idx[tied_local]
    best_ci = int(min(tied, key=lambda ci: dist_from_default(W[meta[ci][0]], meta[ci][1], meta[ci][2])))
    bw, bhu, bhl = W[meta[best_ci][0]], meta[best_ci][1], meta[best_ci][2]

    best_traded = POS[best_ci] != 0
    dsr = deflated_sharpe_ratio(
        float(sharpe[best_ci]), int(n_trades[best_ci]), NET[best_ci][best_traded], n_trials, sharpe
    )

    global_best = {
        "total_return_pct": round(float(total_return[best_ci]) * 100, 2),
        "avg_net_per_trade_pct": round(float(avg_net_per_trade[best_ci]) * 100, 4),
        "sharpe_per_trade": round(float(sharpe[best_ci]), 3),
        "n_trades": int(n_trades[best_ci]),
        "weights": {"micro": round(float(bw[0]), 4), "macro": round(float(bw[1]), 4),
                    "news": round(float(bw[2]), 4), "quant": round(float(bw[3]), 4)},
        "hold_upper": bhu, "hold_lower": bhl,
        "n_tied_eligible": int(len(tied)),
        "deflated_sharpe": dsr,
    }

    bs = bootstrap_trade_stats(NET[best_ci][best_traded].tolist())
    global_best["bootstrap_90ci_mean_net_pct"] = {
        "ci_low": round(bs["mean_per_trade"]["ci_low"] * 100, 4),
        "ci_high": round(bs["mean_per_trade"]["ci_high"] * 100, 4),
    }

    # Permutation test, restricted to the SAME eligible set the real selection
    # used - an unconstrained null would compare a floor-constrained observed
    # best against an unconstrained (and therefore inflated) null maximum.
    perm_p = permutation_test_pnl(
        POS[elig_idx], cost_bps, short_borrow_bps, gap, float(total_return[best_ci]),
    )

    # --- pooled LOOCV over the eligible set only, floor re-checked per fold ---
    log_net = np.log1p(NET[elig_idx])            # [ne, ndoc]
    total_log = log_net.sum(axis=1)               # [ne]
    traded_elig = POS[elig_idx] != 0               # [ne, ndoc]
    n_trades_elig = n_trades[elig_idx]             # [ne]

    held_net = np.zeros(ndoc)
    held_pos = np.zeros(ndoc, dtype=np.int8)
    for i in range(ndoc):
        loo_log = total_log - log_net[:, i]
        loo_n_trades = n_trades_elig - traded_elig[:, i]
        ok = loo_n_trades >= min_trades
        if not ok.any():
            ok = np.ones_like(ok, dtype=bool)  # rare edge: fall back to full eligible set
        cand = np.where(ok)[0]
        local_best = cand[np.argmax(loo_log[cand])]
        ci = int(elig_idx[local_best])
        held_net[i] = NET[ci, i]
        held_pos[i] = POS[ci, i]

    loocv_total_return = float(np.expm1(np.log1p(held_net).sum()))
    loo_traded = held_pos != 0
    loocv_trades = int(loo_traded.sum())
    if loocv_trades:
        loo_nets = held_net[loo_traded]
        loocv_avg_net_per_trade = float(loo_nets.mean())
        loocv_hit_rate = round(float((loo_nets > 0).mean()), 4)
    else:
        loocv_avg_net_per_trade = 0.0
        loocv_hit_rate = 0.0

    return {
        "label": label,
        "n_combos_total": ncombo,
        "n_combos_eligible": int(len(elig_idx)),
        "min_trade_floor": min_trades,
        "global_best": global_best,
        "permutation_p_vs_gap_shuffles": perm_p,
        "loocv": {
            "total_return_pct": round(loocv_total_return * 100, 2),
            "avg_net_per_trade_pct": round(loocv_avg_net_per_trade * 100, 4),
            "hit_rate": loocv_hit_rate,
            "n_trades": loocv_trades,
        },
    }


def main() -> int:
    events = wf._load_clean_events()
    n = len(events)
    print(f"Loaded {n} clean events (expected 233)")
    assert n > 200, f"Expected ~233, got {n}"
    docs = to_docs(events)

    min_trades = max(wf.MIN_TRADES_FLOOR, int(n * MIN_TRADE_FRACTION))
    print(f"Min-trade floor: {min_trades} ({MIN_TRADE_FRACTION:.0%} of N={n})")

    W = restricted_weight_grid(WEIGHT_STEP)
    print(f"Weight grid: {W.shape[0]} points (micro/macro only, news=quant=0, step={WEIGHT_STEP})")

    variant_a_thresholds = [(round(hu, 2), round(hl, 2))
                             for hu in [0.10, 0.20, 0.30, 0.40, 0.50]
                             for hl in [-0.10, -0.20, -0.30, -0.40, -0.50]]
    variant_b_thresholds = [(round(t, 2), round(-t, 2)) for t in
                             [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]]

    result_a = run_variant("A_coarse_asymmetric", docs, W, variant_a_thresholds, min_trades,
                            COST_BPS, SHORT_BORROW_BPS)
    result_b = run_variant("B_symmetric", docs, W, variant_b_thresholds, min_trades,
                            COST_BPS, SHORT_BORROW_BPS)

    for r in (result_a, result_b):
        gb = r["global_best"]
        dsr = gb["deflated_sharpe"]
        psr_txt = f"psr={dsr['psr']}" if dsr else "psr=n/a"
        print(f"\n[{r['label']}] {r['n_combos_total']} combos total, {r['n_combos_eligible']} eligible "
              f"(>= {r['min_trade_floor']} trades)")
        print(f"  global_best: w={gb['weights']} thr=(+{gb['hold_upper']}/{gb['hold_lower']}) "
              f"total_return={gb['total_return_pct']}% n_trades={gb['n_trades']} "
              f"avg/trade={gb['avg_net_per_trade_pct']}% sharpe={gb['sharpe_per_trade']} ({psr_txt})")
        print(f"  bootstrap 90% CI mean net/trade: [{gb['bootstrap_90ci_mean_net_pct']['ci_low']}%, "
              f"{gb['bootstrap_90ci_mean_net_pct']['ci_high']}%]")
        print(f"  permutation p (vs {PERMUTATIONS} gap-shuffles, eligible combos only): {r['permutation_p_vs_gap_shuffles']}")
        print(f"  LOOCV: total_return={r['loocv']['total_return_pct']}% n_trades={r['loocv']['n_trades']} "
              f"avg/trade={r['loocv']['avg_net_per_trade_pct']}% hit_rate={r['loocv']['hit_rate']}")

    # --- deployed default, evaluated on the identical N=233 docs, for direct comparison ---
    deployed = wf._evaluate_thresholds(events, DEFAULT_HOLD_UPPER, DEFAULT_HOLD_LOWER)
    deployed_nets = [s["net"] for s in deployed["signals"] if s["position"] != 0]
    deployed_total_return = float(np.expm1(np.log1p(np.array(deployed_nets)).sum())) if deployed_nets else 0.0
    print(f"\n[deployed 0.55/0.45/0/0 @ +{DEFAULT_HOLD_UPPER}/{DEFAULT_HOLD_LOWER}] (reference, not re-run "
          f"through this script's own DSR - its PSR=0.0/p=0.150 comes from the ORIGINAL N=161 search, not "
          f"a re-search here)")
    print(f"  total_return={deployed_total_return*100:.2f}% n_trades={deployed['n_trades']} "
          f"mean_net/trade={deployed['mean_net']*100:.4f}%")

    out = {
        "label": "Reduced-dimension weight/threshold search, N=233 clean universe. "
                 "RETROSPECTIVE - NOT PRE-REGISTERED. Addresses CLAUDE.md's own flagged gap: "
                 "does a smaller, honestly-disclosed search surface a weighting that clears "
                 "PSR/permutation, unlike the original 113,344-combo N=161 search that produced "
                 "the deployed default (PSR=0.0, permutation p=0.150 at selection time).",
        "n_clean_events": n,
        "cost_bps": COST_BPS,
        "short_borrow_bps": SHORT_BORROW_BPS,
        "min_trade_floor": min_trades,
        "min_trade_fraction": MIN_TRADE_FRACTION,
        "weight_grid": {"step": WEIGHT_STEP, "n_points": int(W.shape[0]),
                         "note": "micro+macro=1, news=0, quant=0 - fixed, not searched (see module docstring)"},
        "deployed_default_reference": {
            "weights": list(DEFAULT_WEIGHTS),
            "hold_upper": DEFAULT_HOLD_UPPER, "hold_lower": DEFAULT_HOLD_LOWER,
            "total_return_pct": round(deployed_total_return * 100, 2),
            "n_trades": deployed["n_trades"],
            "mean_net_per_trade_pct": round(deployed["mean_net"] * 100, 4),
            "note": "Evaluated on the same N=233 docs for comparability. Its own PSR=0.0/p=0.150 "
                     "figure comes from the original N=161/113,344-combo search and is NOT recomputed here.",
        },
        "variant_A_coarse_asymmetric": {k: v for k, v in result_a.items()},
        "variant_B_symmetric": {k: v for k, v in result_b.items()},
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nWrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
