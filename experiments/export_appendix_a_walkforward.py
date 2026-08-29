"""
experiments/export_appendix_a_walkforward.py
Appendix A (Section 4.3): exports the full walk-forward robustness grids into
clean, labelled CSVs for the report appendix, read-only against already
computed JSON outputs -- no rescoring, no new analysis.

Sources:
  outputs/global/summary/item_e_walkforward.json           (rolling walk-forward, N=233)
  outputs/global/summary/item_e_walkforward_coarse_grid.json (grid-resolution check)
  outputs/global/summary/item_e_walkforward_best_effort.json (20-cell swept grid)
  outputs/global/summary/item_e_combined_walkforward.json    (combined re-run)

Outputs (report/appendix/):
  appendix_a1_rolling_walkforward.csv
  appendix_a2_grid_resolution_check.csv
  appendix_a3_best_effort_grid.csv
  appendix_a4_combined_walkforward.csv

Run: python -m experiments.export_appendix_a_walkforward
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SUMMARY_DIR = BASE_DIR / "outputs" / "global" / "summary"
OUT_DIR = BASE_DIR / "report" / "appendix"


def _load(name):
    with open(SUMMARY_DIR / name) as f:
        return json.load(f)


def export_a1_rolling_walkforward():
    """Per-window detail for the main N=233 rolling walk-forward, both objectives."""
    d = _load("item_e_walkforward.json")
    rows = []
    for objective_key, objective_label in [
        ("mean_net_objective", "mean_net_per_trade"),
        ("accuracy_objective", "directional_accuracy"),
    ]:
        obj = d["rolling_walkforward"][objective_key]
        for w in obj["windows"]:
            rows.append({
                "objective": objective_label,
                "window_idx": w["window_idx"],
                "train_cutoff": w["train_cutoff"],
                "test_start": w["test_start"],
                "test_end": w["test_end"],
                "fitted_upper": w["fitted_upper"],
                "fitted_lower": w["fitted_lower"],
                "train_n": w["train_n"],
                "train_trades": w["train_trades"],
                "train_accuracy": w["train_accuracy"],
                "test_trades": w["test_trades"],
                "test_n_graded": w["test_n_graded"],
                "test_n_correct": w["test_n_correct"],
                "test_accuracy": w["test_accuracy"],
                "test_mean_net": w["test_mean_net"],
            })
        pooled = obj["pooled_oos"]
        rows.append({
            "objective": objective_label,
            "window_idx": "POOLED",
            "train_cutoff": "",
            "test_start": "",
            "test_end": "",
            "fitted_upper": "",
            "fitted_lower": "",
            "train_n": "",
            "train_trades": "",
            "train_accuracy": "",
            "test_trades": pooled["n_trades"],
            "test_n_graded": pooled["n_graded"],
            "test_n_correct": pooled["n_correct"],
            "test_accuracy": pooled["accuracy"],
            "test_mean_net": pooled["mean_net_pct"],
        })

    out_path = OUT_DIR / "appendix_a1_rolling_walkforward.csv"
    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="") as f:
        f.write("# Appendix A1: N=233 rolling walk-forward, per-window detail, both objectives\n")
        f.write("# Source: outputs/global/summary/item_e_walkforward.json\n")
        f.write(f"# n_clean_events: {d['n_clean_events']}, date_range: {d['date_range']}\n")
        f.write(f"# weights_fixed: {d['weights_fixed']}, cost_bps: {d['cost_bps']}\n")
        f.write("# window_idx=POOLED rows are the pooled out-of-sample result across all windows.\n")
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {out_path} ({len(rows)} rows)")


def export_a2_grid_resolution_check():
    """Coarse-grid variants vs the original fine grid, summary only."""
    d = _load("item_e_walkforward_coarse_grid.json")
    rows = []
    orig = d["original_fine_grid"]
    rows.append({
        "variant": "original_fine_grid",
        "grid_note": orig["grid_note"],
        "objective": "mean_net_per_trade",
        "degenerate_windows": orig["mean_net_degenerate"],
        "total_windows": orig["n_windows"],
    })
    rows.append({
        "variant": "original_fine_grid",
        "grid_note": orig["grid_note"],
        "objective": "directional_accuracy",
        "degenerate_windows": orig["accuracy_degenerate"],
        "total_windows": orig["n_windows"],
    })
    for variant_name, variant in d["variants"].items():
        for objective_key, objective_label in [
            ("mean_net_objective", "mean_net_per_trade"),
            ("accuracy_objective", "directional_accuracy"),
        ]:
            obj = variant[objective_key]
            rows.append({
                "variant": variant_name,
                "grid_note": variant["grid_note"],
                "objective": objective_label,
                "degenerate_windows": obj["degenerate_windows"],
                "total_windows": obj["n_windows"],
                "pooled_n_trades": obj["pooled_oos"]["n_trades"],
                "pooled_n_graded": obj["pooled_oos"]["n_graded"],
                "pooled_accuracy": obj["pooled_oos"]["accuracy"],
                "pooled_mean_net_pct": obj["pooled_oos"]["mean_net_pct"],
            })

    out_path = OUT_DIR / "appendix_a2_grid_resolution_check.csv"
    fieldnames = ["variant", "grid_note", "objective", "degenerate_windows",
                  "total_windows", "pooled_n_trades", "pooled_n_graded",
                  "pooled_accuracy", "pooled_mean_net_pct"]
    with open(out_path, "w", newline="") as f:
        f.write("# Appendix A2: grid-resolution robustness check (coarser threshold grids), N=233\n")
        f.write("# Source: outputs/global/summary/item_e_walkforward_coarse_grid.json\n")
        f.write("# Tests whether the main walk-forward's degeneracy is an artefact of the fine\n")
        f.write("# (0.05-step) threshold grid. It is not: coarser grids reproduce the same failure.\n")
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
    print(f"Wrote {out_path} ({len(rows)} rows)")


def export_a3_best_effort_grid():
    """The 20-cell swept grid (5 window schemes x mean-net-floor/accuracy variants)."""
    d = _load("item_e_walkforward_best_effort.json")
    rows = d["grid"]

    out_path = OUT_DIR / "appendix_a3_best_effort_grid.csv"
    fieldnames = ["label", "n_windows", "degenerate_windows", "n_trades", "n_graded",
                  "n_correct", "accuracy", "mean_net_pct", "bootstrap_ci_low",
                  "bootstrap_ci_high", "majority_direction_floor",
                  "majority_direction_label", "margin_vs_floor_pp", "binomial_p", "mde_pp"]
    with open(out_path, "w", newline="") as f:
        f.write("# Appendix A3: 20-cell best-effort swept grid, N=233\n")
        f.write("# Source: outputs/global/summary/item_e_walkforward_best_effort.json\n")
        f.write(f"# {d['label']}\n")
        f.write("# 5 window schemes x {mean-net at 10/15/20% min-trade floor, accuracy at fixed 15%}\n")
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            ci = row.get("bootstrap_90ci_mean_net_pct", {})
            writer.writerow({
                "label": row["label"],
                "n_windows": row["n_windows"],
                "degenerate_windows": row["degenerate_windows"],
                "n_trades": row["n_trades"],
                "n_graded": row["n_graded"],
                "n_correct": row["n_correct"],
                "accuracy": row["accuracy"],
                "mean_net_pct": row["mean_net_pct"],
                "bootstrap_ci_low": ci.get("ci_low", ""),
                "bootstrap_ci_high": ci.get("ci_high", ""),
                "majority_direction_floor": row["majority_direction_floor"],
                "majority_direction_label": row["majority_direction_label"],
                "margin_vs_floor_pp": row["margin_vs_floor_pp"],
                "binomial_p": row["binomial_p"],
                "mde_pp": row["mde_pp"],
            })
    print(f"Wrote {out_path} ({len(rows)} rows)")


def export_a4_combined_walkforward():
    """Per-window detail for the combined (clean + extension) walk-forward.

    All counts are read from the JSON rather than hardcoded: an earlier version
    asserted N=326 while the source said 325.
    """
    d = _load("item_e_combined_walkforward.json")
    rows = []
    for objective_key, objective_label in [
        ("mean_net_per_trade", "mean_net_per_trade"),
        ("directional_accuracy", "directional_accuracy"),
    ]:
        obj = d["rolling_walkforward"][objective_key]
        for w in obj["windows"]:
            rows.append({
                "objective": objective_label,
                "window_idx": w.get("window_idx"),
                "test_trades": w.get("test_trades"),
                "test_n_graded": w.get("test_n_graded"),
                "test_n_correct": w.get("test_n_correct"),
                "test_accuracy": w.get("test_accuracy"),
                "test_mean_net": w.get("test_mean_net"),
            })
        pooled = obj["pooled_oos"]
        rows.append({
            "objective": objective_label,
            "window_idx": "POOLED",
            "test_trades": pooled.get("n_trades"),
            "test_n_graded": pooled.get("n_graded"),
            "test_n_correct": pooled.get("n_correct"),
            "test_accuracy": pooled.get("accuracy"),
            "test_mean_net": pooled.get("mean_net_pct"),
        })

    out_path = OUT_DIR / "appendix_a4_combined_walkforward.csv"
    fieldnames = ["objective", "window_idx", "test_trades", "test_n_graded",
                  "test_n_correct", "test_accuracy", "test_mean_net"]
    with open(out_path, "w", newline="") as f:
        f.write(f"# Appendix A4: combined rolling walk-forward, N={d['n_combined_events']}\n")
        f.write("# Source: outputs/global/summary/item_e_combined_walkforward.json\n")
        f.write(f"# n_combined_events: {d['n_combined_events']} ({d['n_phase2_events']} clean + {d['n_extension_events']} extension)\n")
        f.write(f"# Retrospective: all {d['n_combined_events']} events were already seen before this analysis was run.\n")
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {out_path} ({len(rows)} rows)")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    export_a1_rolling_walkforward()
    export_a2_grid_resolution_check()
    export_a3_best_effort_grid()
    export_a4_combined_walkforward()


if __name__ == "__main__":
    main()
