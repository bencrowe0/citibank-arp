"""
experiments/weight_search_n233_full4.py

Full 4-layer follow-up to experiments/weight_reduced_search_n233.py (which
restricted the search to micro/macro only, news=quant=0 fixed, and found
combos clearing PSR/permutation while roughly matching the deployed
default's P&L). This script reopens all four dimensions (micro, macro,
news, quant) and asks the same question properly: is there a weighting of
the FULL layer set that performs well on P&L and clears PSR/permutation,
at a small enough, honestly-disclosed trial count that the Deflated Sharpe
Ratio's own trial-count correction (Bailey & Lopez de Prado, 2014) doesn't
guarantee failure the way the original 113,344-combo N=161 search did
(PSR=0.0, permutation p=0.150 at selection time - see blend.py's
DEFAULT_WEIGHTS docstring / CLAUDE.md Architecture > Blend).

SWEPT GRID, NOTHING CHERRY-PICKED (same discipline as
experiments/walkforward_best_effort.py): 3 weight-grid step sizes (0.05,
0.10, 0.20) x 2 threshold-grid variants (coarse asymmetric, symmetric) = 6
cells. [Note: the approved plan's write-up said "12 cells" - that was a
multiplication error (3 steps x 2 variants = 6, not 12); this script
implements the correct 6, disclosed here rather than silently padding the
grid to match a wrong number.] Every cell is run and printed, including
cells that fail.

Weight grid: full 4-dim simplex via weight_threshold_sweep.weight_grid(step)
(the same generic compositions-summing-to-1 builder production's own
113k-combo sweep used) - NOT restricted to micro/macro this time.

Min-trade floor: 15% of N=233 (~34 trades), same convention as
walkforward_validation.fit_thresholds_accuracy and the prior 2-layer pass -
prevents a combo winning by isolating a single lucky outlier trade.

Data: experiments.walkforward_validation._load_clean_events() - the same
verified N=233 clean, release_date-anchored, exclusion-applied universe
used everywhere else in this project's Item E work.

RETROSPECTIVE - NOT PRE-REGISTERED. N=233 was fully assembled and seen
before this script ran.

Run: python -m experiments.weight_search_n233_full4
Out: outputs/global/summary/item_e_weight_search_full4.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from blend import DEFAULT_HOLD_LOWER, DEFAULT_HOLD_UPPER, DEFAULT_WEIGHTS  # noqa: E402
from bootstrap_stats import bootstrap_trade_stats  # noqa: E402
from experiments.weight_threshold_sweep import build_layer_matrices, dist_from_default, weight_grid  # noqa: E402
from experiments.pnl_weight_threshold_sweep import (  # noqa: E402
    PERMUTATIONS,
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
WEIGHT_STEPS = [0.05, 0.10, 0.20]

SUMMARY_DIR = Path(__file__).resolve().parent.parent / "outputs" / "global" / "summary"
OUT_JSON = SUMMARY_DIR / "item_e_weight_search_full4.json"


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


def run_cell(label, docs, W, threshold_pairs, min_trades, cost_bps, short_borrow_bps):
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
        return {"label": label, "n_combos_total": ncombo, "n_combos_eligible": 0,
                "min_trade_floor": min_trades, "status": "NO ELIGIBLE COMBO"}
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

    perm_p = permutation_test_pnl(
        POS[elig_idx], cost_bps, short_borrow_bps, gap, float(total_return[best_ci]),
    )

    log_net = np.log1p(NET[elig_idx])
    total_log = log_net.sum(axis=1)
    traded_elig = POS[elig_idx] != 0
    n_trades_elig = n_trades[elig_idx]

    held_net = np.zeros(ndoc)
    held_pos = np.zeros(ndoc, dtype=np.int8)
    for i in range(ndoc):
        loo_log = total_log - log_net[:, i]
        loo_n_trades = n_trades_elig - traded_elig[:, i]
        ok = loo_n_trades >= min_trades
        if not ok.any():
            ok = np.ones_like(ok, dtype=bool)
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
        "status": "OK",
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
    print(f"Min-trade floor: {min_trades} ({MIN_TRADE_FRACTION:.0%} of N={n})\n")

    variant_a_thresholds = [(round(hu, 2), round(hl, 2))
                             for hu in [0.10, 0.20, 0.30, 0.40, 0.50]
                             for hl in [-0.10, -0.20, -0.30, -0.40, -0.50]]
    variant_b_thresholds = [(round(t, 2), round(-t, 2)) for t in
                             [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]]
    threshold_variants = [("coarse_asymmetric", variant_a_thresholds),
                           ("symmetric", variant_b_thresholds)]

    cells = []
    for step in WEIGHT_STEPS:
        W = weight_grid(step)
        print(f"weight_step={step}: {W.shape[0]} weight points (full micro/macro/news/quant simplex)")
        for tv_name, thresholds in threshold_variants:
            label = f"step{step:.2f}_{tv_name}"
            r = run_cell(label, docs, W, thresholds, min_trades, COST_BPS, SHORT_BORROW_BPS)
            cells.append(r)
            if r["status"] != "OK":
                print(f"  [{label}] {r['status']}")
                continue
            gb = r["global_best"]
            dsr = gb["deflated_sharpe"]
            psr_txt = f"psr={dsr['psr']}" if dsr else "psr=n/a"
            print(f"  [{label}] {r['n_combos_total']} combos ({r['n_combos_eligible']} eligible >= {min_trades} trades)")
            print(f"    best: w={gb['weights']} thr=(+{gb['hold_upper']}/{gb['hold_lower']}) "
                  f"total_return={gb['total_return_pct']}% n_trades={gb['n_trades']} "
                  f"avg/trade={gb['avg_net_per_trade_pct']}% sharpe={gb['sharpe_per_trade']} ({psr_txt})")
            print(f"    bootstrap 90% CI mean net/trade: [{gb['bootstrap_90ci_mean_net_pct']['ci_low']}%, "
                  f"{gb['bootstrap_90ci_mean_net_pct']['ci_high']}%]")
            print(f"    permutation p (vs {PERMUTATIONS} gap-shuffles, eligible combos only): "
                  f"{r['permutation_p_vs_gap_shuffles']}")
            print(f"    LOOCV: total_return={r['loocv']['total_return_pct']}% n_trades={r['loocv']['n_trades']} "
                  f"avg/trade={r['loocv']['avg_net_per_trade_pct']}% hit_rate={r['loocv']['hit_rate']}")

    # --- deployed default, evaluated on the identical N=233 docs, for direct comparison ---
    deployed = wf._evaluate_thresholds(events, DEFAULT_HOLD_UPPER, DEFAULT_HOLD_LOWER)
    deployed_nets = [s["net"] for s in deployed["signals"] if s["position"] != 0]
    deployed_total_return = float(np.expm1(np.log1p(np.array(deployed_nets)).sum())) if deployed_nets else 0.0
    print(f"\n[deployed 0.55/0.45/0/0 @ +{DEFAULT_HOLD_UPPER}/{DEFAULT_HOLD_LOWER}] (reference, not re-run "
          f"through this script's own DSR)")
    print(f"  total_return={deployed_total_return*100:.2f}% n_trades={deployed['n_trades']} "
          f"mean_net/trade={deployed['mean_net']*100:.4f}%")

    out = {
        "label": "Full 4-layer (micro/macro/news/quant) reduced-dimension weight/threshold search, "
                 "N=233 clean universe. RETROSPECTIVE - NOT PRE-REGISTERED. 6 cells swept "
                 "(3 weight-grid steps x 2 threshold-grid variants), none cherry-picked.",
        "n_clean_events": n,
        "cost_bps": COST_BPS,
        "short_borrow_bps": SHORT_BORROW_BPS,
        "min_trade_floor": min_trades,
        "min_trade_fraction": MIN_TRADE_FRACTION,
        "weight_steps": WEIGHT_STEPS,
        "threshold_variants": ["coarse_asymmetric (5x5=25 pairs)", "symmetric (10 values, hold_upper=-hold_lower)"],
        "deployed_default_reference": {
            "weights": list(DEFAULT_WEIGHTS),
            "hold_upper": DEFAULT_HOLD_UPPER, "hold_lower": DEFAULT_HOLD_LOWER,
            "total_return_pct": round(deployed_total_return * 100, 2),
            "n_trades": deployed["n_trades"],
            "mean_net_per_trade_pct": round(deployed["mean_net"] * 100, 4),
            "note": "Its own PSR=0.0/p=0.150 figure comes from the original N=161/113,344-combo "
                    "search and is NOT recomputed here.",
        },
        "cells": cells,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nWrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
