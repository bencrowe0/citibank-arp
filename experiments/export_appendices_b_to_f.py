"""
experiments/export_appendices_b_to_f.py
Appendices B-F: supporting evidence for the report's H1/H3 and
methodology claims, exported as labelled CSVs.

Read-only against committed artifacts. No rescoring, no recomputation of
any published figure -- every value here is copied from a source file and
that file is named in the CSV header.

STALENESS GUARDS (this repo has a documented history of artifacts that look
authoritative but predate the 2026-08-18 weight promotion):
  * item_e_weight_*.json each carry a `deployed_default_reference` block and
    a `label` string describing the SUPERSEDED 0.55/0.45 combination. Both
    are deliberately NOT exported -- the report must contain no trace of the
    old weighting.
  * effective_sample_funnel.md's exclusion steps (268->242->233) are
    weight-independent and safe; its trading/grading rows (146 traded, 95
    graded, 65.3%, 1.8617%) are OLD-WEIGHTING and are NOT copied. Those
    rows are rebuilt from item_e_walkforward.json's in_sample_deployed block.
  * workbook_metrics.csv and human_vs_llm_statistics.csv are stale
    throughout and are not used by this script at all.

Appendices:
  B  Weight/threshold selection-validity search   (backs Sections 3.1, 3.5)
  C  Sample construction and exclusions           (backs Section 3.2)
  D  H1 evidence: holding curve, per-trade stats  (backs Sections 3.4, 4.1)
  E  Cost, latency, and breakeven evidence        (backs Section 4.2)
  F  Transfer evidence: cross-issuer + extension  (backs Section 4.3)

Run: python -m experiments.export_appendices_b_to_f
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SUMMARY = BASE_DIR / "outputs" / "global" / "summary"
OUT_DIR = BASE_DIR / "report" / "appendix"


def _load_json(name: str) -> dict:
    with open(SUMMARY / name, encoding="utf-8") as f:
        return json.load(f)


def _write(path: Path, header_lines: list[str], fieldnames: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        for line in header_lines:
            f.write(f"# {line}\n")
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
    print(f"Wrote {path.name} ({len(rows)} rows)")


# --------------------------------------------------------------------------
# Appendix B: weight/threshold selection-validity search
# --------------------------------------------------------------------------
def export_b() -> None:
    reduced = _load_json("item_e_weight_reduced_search.json")
    full4 = _load_json("item_e_weight_search_full4.json")

    rows = []

    def add(search: str, label: str, cell: dict) -> None:
        gb = cell["global_best"]
        ds = gb.get("deflated_sharpe", {}) or {}
        w = gb["weights"]
        loocv = cell.get("loocv", {}) or {}
        rows.append({
            "search": search,
            "cell": label,
            "n_combos_total": cell["n_combos_total"],
            "n_combos_eligible": cell["n_combos_eligible"],
            "min_trade_floor": cell.get("min_trade_floor", ""),
            "best_micro": w.get("micro"), "best_macro": w.get("macro"),
            "best_news": w.get("news"), "best_quant": w.get("quant"),
            "best_hold_upper": gb["hold_upper"], "best_hold_lower": gb["hold_lower"],
            "n_trades": gb["n_trades"],
            "mean_net_per_trade_pct": gb["avg_net_per_trade_pct"],
            "sharpe_per_trade": gb["sharpe_per_trade"],
            "dsr": ds.get("psr", ""),
            "dsr_sr0_expected_max_under_null": ds.get("sr0_expected_max_under_null", ""),
            "dsr_n_trials_corrected_for": ds.get("n_trials_corrected_for", ""),
            "permutation_p": cell["permutation_p_vs_gap_shuffles"],
            "loocv_mean_net_per_trade_pct": loocv.get("avg_net_per_trade_pct", ""),
            "loocv_n_trades": loocv.get("n_trades", ""),
        })

    add("restricted_micro_macro", reduced["variant_A_coarse_asymmetric"]["label"],
        reduced["variant_A_coarse_asymmetric"])
    add("restricted_micro_macro", reduced["variant_B_symmetric"]["label"],
        reduced["variant_B_symmetric"])
    for cell in full4["cells"]:
        add("full_four_layer", cell["label"], cell)

    _write(
        OUT_DIR / "appendix_b_weight_search.csv",
        [
            "Appendix B: weight/threshold selection-validity search (backs Sections 3.1 and 3.5).",
            "Sources: item_e_weight_reduced_search.json, item_e_weight_search_full4.json.",
            f"N=233 clean events; cost_bps={reduced['cost_bps']}; "
            f"minimum-trade floor={reduced['min_trade_floor']} ({reduced['min_trade_fraction']:.0%} of N).",
            "RETROSPECTIVE, NOT PRE-REGISTERED.",
            "'dsr' is the Deflated Sharpe Ratio (Bailey and Lopez de Prado, 2014): the Sharpe corrected",
            "for how many combinations were searched, via sr0 (expected max Sharpe under a zero-skill",
            "null given that trial count). The deployed combination is the restricted search's",
            "coarse-asymmetric winner: micro 0.80 / macro 0.20, thresholds +0.20 / -0.10, DSR 0.964.",
            "The full four-layer search converges on the SAME weights and thresholds at two of its",
            "three grid steps when news and quant are free to earn weight and decline it; all six of",
            "its cells score DSR 0.0 because opening two noisier layers inflates sr0 to 6.0-11.2,",
            "raising the bar the winner must clear even though the winner itself does not move.",
            "Each source file also contains a comparison block for a superseded weighting; that block",
            "is deliberately not exported here.",
        ],
        ["search", "cell", "n_combos_total", "n_combos_eligible", "min_trade_floor",
         "best_micro", "best_macro", "best_news", "best_quant",
         "best_hold_upper", "best_hold_lower", "n_trades", "mean_net_per_trade_pct",
         "sharpe_per_trade", "dsr", "dsr_sr0_expected_max_under_null",
         "dsr_n_trials_corrected_for", "permutation_p",
         "loocv_mean_net_per_trade_pct", "loocv_n_trades"],
        rows,
    )


# --------------------------------------------------------------------------
# Appendix C: sample construction and exclusions
# --------------------------------------------------------------------------
def export_c() -> None:
    wf = _load_json("item_e_walkforward.json")
    dep = wf["in_sample_deployed"]

    # Exclusion counts, recounted from the flag file rather than trusted from prose.
    with open(SUMMARY / "worksheet_leak_flags.csv", encoding="utf-8") as f:
        leak_rows = list(csv.DictReader(f))
    n_worksheet = sum(1 for r in leak_rows if r.get("has_human_score", "").strip() == "True")

    rows = [
        {"step": "1. Total company-quarters scored", "n_remaining": 268, "n_lost": "",
         "reason": "", "weight_dependent": "no"},
        {"step": "2. After worksheet-contamination exclusion", "n_remaining": 268 - n_worksheet,
         "n_lost": n_worksheet,
         "reason": "LLM input included a human rater worksheet (recounted from worksheet_leak_flags.csv)",
         "weight_dependent": "no"},
        {"step": "3. After misattributed-document exclusion", "n_remaining": 268 - n_worksheet - 1,
         "n_lost": 1, "reason": "SPOT_FQ1_2026 misattribution", "weight_dependent": "no"},
        {"step": "4. After timing exclusion (clean universe)", "n_remaining": 233, "n_lost": 9,
         "reason": "9 non-US issuers, overnight timing unresolved", "weight_dependent": "no"},
        {"step": "5. Model called BUY or SELL (traded)", "n_remaining": dep["n_trades"],
         "n_lost": 233 - dep["n_trades"],
         "reason": "Model called HOLD: no trade, no directional test",
         "weight_dependent": "YES"},
        {"step": "6. Overnight |return| > 2% band (graded)", "n_remaining": dep["n_graded"],
         "n_lost": dep["n_trades"] - dep["n_graded"],
         "reason": "Return inside the pre-registered +/-2% band: traded but ungraded",
         "weight_dependent": "YES"},
        {"step": "7. Of which directionally correct", "n_remaining": dep["n_correct"],
         "n_lost": dep["n_graded"] - dep["n_correct"],
         "reason": f"Selectivity accuracy {dep['accuracy']:.4f}",
         "weight_dependent": "YES"},
    ]

    _write(
        OUT_DIR / "appendix_c_sample_funnel.csv",
        [
            "Appendix C: sample construction and exclusions (backs Section 3.2).",
            "Exclusion steps 1-4 sourced from effective_sample_funnel.md and recounted against",
            "worksheet_leak_flags.csv. These steps are weight-independent.",
            "Steps 5-7 are weight-DEPENDENT and are taken from item_e_walkforward.json's",
            "in_sample_deployed block at the deployed weights (micro 0.80 / macro 0.20,",
            "thresholds +0.20 / -0.10). They are NOT copied from effective_sample_funnel.md,",
            "whose own trading rows predate the deployed weighting and would understate the",
            "traded and graded counts.",
            f"Deployed: {dep['n_trades']} traded, {dep['n_graded']} graded, "
            f"{dep['n_correct']} correct, accuracy {dep['accuracy']:.4f}, "
            f"mean net {dep['mean_net_pct']}%.",
        ],
        ["step", "n_remaining", "n_lost", "reason", "weight_dependent"],
        rows,
    )


# --------------------------------------------------------------------------
# Appendix D: H1 evidence
# --------------------------------------------------------------------------
def export_d() -> None:
    with open(SUMMARY / "ext2_holding_curve.csv", encoding="utf-8") as f:
        lines = [l for l in f if not l.startswith("#")]
    curve = list(csv.DictReader(lines))

    rows = []
    for r in curve:
        rows.append({
            "horizon": r["horizon"],
            "spearman_rho": round(float(r["rank_correlation"]), 4),
            "rho_p_value": f"{float(r['rho_pvalue']):.4g}",
            "mean_net_per_trade_pct": round(float(r["mean_net_per_trade"]) * 100, 4),
            "bootstrap_90ci_low_pct": round(float(r["bootstrap_ci_low"]) * 100, 4),
            "bootstrap_90ci_high_pct": round(float(r["bootstrap_ci_high"]) * 100, 4),
            "selectivity_accuracy": round(float(r["accuracy"]), 4),
            "n_graded": r["graded_n"],
            "n_traded": r["traded_n"],
            "hold_band": r["hold_band"],
            "band_status": r["band_status"],
        })

    with open(SUMMARY / "per_trade_stats.csv", encoding="utf-8") as f:
        stats = {r["metric"]: r["value"] for r in csv.DictReader(f)}

    _write(
        OUT_DIR / "appendix_d_holding_curve.csv",
        [
            "Appendix D: H1 evidence, rank correlation and return across holding horizons",
            "(backs Sections 3.4 and 4.1).",
            "Source: ext2_holding_curve.csv, produced by experiments/holding_period_curve.py",
            "at the deployed weights (micro 0.80 / macro 0.20, thresholds +0.20 / -0.10).",
            "The overnight +/-2% band is PRE-REGISTERED; all longer-horizon bands are",
            "RECALIBRATED and secondary. Returns are alternative versions of the same trade,",
            "never compounded across horizons.",
            "Per-trade statistics at the overnight horizon (source: per_trade_stats.csv): "
            f"n_trades={stats.get('n_trades')}, "
            f"mean_net={stats.get('mean_net_per_trade_pct')}%, "
            f"sd={stats.get('sd_pct')}%, "
            f"t_statistic={stats.get('t_statistic')}, "
            f"info_ratio={stats.get('info_ratio_per_trade')}.",
        ],
        ["horizon", "spearman_rho", "rho_p_value", "mean_net_per_trade_pct",
         "bootstrap_90ci_low_pct", "bootstrap_90ci_high_pct",
         "selectivity_accuracy", "n_graded", "n_traded", "hold_band", "band_status"],
        rows,
    )


# --------------------------------------------------------------------------
# Appendix E: cost, latency, breakeven
# --------------------------------------------------------------------------
def export_e() -> None:
    grid = _load_json("ext9_cost_grid_n233.json")
    n233 = grid["n233_corrected_anchor"]

    rows = []
    for k, v in n233.items():
        if isinstance(v, (int, float, str)):
            rows.append({"metric": k, "value": v, "source": "ext9_cost_grid_n233.json"})
        elif isinstance(v, dict):
            for kk, vv in v.items():
                if isinstance(vv, (int, float, str)):
                    rows.append({"metric": f"{k}.{kk}", "value": vv,
                                 "source": "ext9_cost_grid_n233.json"})

    # API cost per prediction, recomputed from the ledger's micro-layer rows.
    with open(SUMMARY / "api_cost_ledger.csv", encoding="utf-8") as f:
        ledger = list(csv.DictReader(f))
    micro = [r for r in ledger if r.get("layer") == "micro" and r.get("estimated_cost_usd")]
    costs = [float(r["estimated_cost_usd"]) for r in micro]
    if costs:
        rows.append({"metric": "api_cost_per_prediction_usd_mean",
                     "value": round(sum(costs) / len(costs), 6),
                     "source": "api_cost_ledger.csv (layer=micro rows)"})
        rows.append({"metric": "api_cost_ledger_micro_rows", "value": len(costs),
                     "source": "api_cost_ledger.csv"})
        rows.append({"metric": "api_cost_total_micro_usd", "value": round(sum(costs), 4),
                     "source": "api_cost_ledger.csv"})

    _write(
        OUT_DIR / "appendix_e_cost_and_latency.csv",
        [
            "Appendix E: cost, latency, and breakeven-cost evidence (backs Section 4.2).",
            "Breakeven figures: ext9_cost_grid_n233.json, N=233 CORRECTED release_date anchor.",
            "That file also holds a block computed on the superseded report_date anchor, which its",
            "own notes warn must not be tabulated alongside these; that block is not exported here.",
            "API cost is recomputed from api_cost_ledger.csv's micro-layer rows (macro is excluded",
            "because one FOMC score is reused across many company-quarters and is not attributable",
            "to a single prediction).",
            "Measured latency (source: model_latency_2026-08-15.md, 624 API calls): mean 15.92s,",
            "IQR 12.95s-17.31s. Paired against the human full-arm mean of 29.8 min/document",
            "(N=190) this gives the 103x-138x range cited in Section 4.2.",
            "Cost and latency are both weight-independent.",
        ],
        ["metric", "value", "source"],
        rows,
    )


# --------------------------------------------------------------------------
# Appendix F: transfer evidence
# --------------------------------------------------------------------------
def export_f() -> None:
    wf = _load_json("item_e_walkforward.json")
    unseen = wf["genuinely_unseen"]
    post = unseen["post_sweep"]
    insweep = unseen["in_sweep"]

    rows = [
        {"group": "in_sweep", "metric": "n_issuers", "value": unseen["n_issuers_in_sweep"]},
        {"group": "in_sweep", "metric": "n_events", "value": unseen["n_events_in_sweep"]},
        {"group": "in_sweep", "metric": "n_trades", "value": insweep["n_trades"]},
        {"group": "in_sweep", "metric": "n_graded", "value": insweep["n_graded"]},
        {"group": "in_sweep", "metric": "selectivity_accuracy", "value": insweep["accuracy"]},
        {"group": "in_sweep", "metric": "mean_net_per_trade_pct", "value": insweep["mean_net_pct"]},
        {"group": "post_sweep", "metric": "n_issuers", "value": unseen["n_issuers_post_sweep"]},
        {"group": "post_sweep", "metric": "n_events", "value": unseen["n_events_post_sweep"]},
        {"group": "post_sweep", "metric": "n_trades", "value": post["n_trades"]},
        {"group": "post_sweep", "metric": "n_graded", "value": post["n_graded"]},
        {"group": "post_sweep", "metric": "n_correct", "value": post["n_correct"]},
        {"group": "post_sweep", "metric": "selectivity_accuracy", "value": post["accuracy"]},
        {"group": "post_sweep", "metric": "mean_net_per_trade_pct", "value": post["mean_net_pct"]},
        {"group": "post_sweep", "metric": "majority_direction_floor",
         "value": post["majority_direction_floor"]},
        {"group": "post_sweep", "metric": "margin_vs_floor_pp", "value": post["margin_vs_floor_pp"]},
        {"group": "post_sweep", "metric": "binomial_p", "value": post["binomial_p"]},
        {"group": "post_sweep", "metric": "mde_pp", "value": post["mde_pp"]},
    ]

    _write(
        OUT_DIR / "appendix_f_transfer_evidence.csv",
        [
            "Appendix F: cross-issuer transfer evidence (backs Section 4.3).",
            "Source: item_e_walkforward.json, genuinely_unseen block, deployed weights.",
            "'post_sweep' are issuers scored AFTER the original threshold sweep, with zero issuer",
            "overlap with the in-sweep set.",
            "IMPORTANT CAVEAT, carried verbatim from the source file: sweep membership is",
            "RECONSTRUCTED, inferred from issuer ordering and a document-count match, not from a",
            "recorded event list; 453 single-swap alternatives also produce the same count. The two",
            "subsets also span overlapping, interleaved date ranges, so this tests ISSUER transfer,",
            "not temporal generalisation.",
            "The 93-event extension's pre-registered accuracy prior is documented separately in",
            "extension_preregistration_2026-08-13.md, dated before any extension document was",
            "gathered; that document is the evidence for Section 4.3's 'predicted-then-contradicted'",
            "argument.",
        ],
        ["group", "metric", "value"],
        rows,
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    export_b()
    export_c()
    export_d()
    export_e()
    export_f()


if __name__ == "__main__":
    main()
