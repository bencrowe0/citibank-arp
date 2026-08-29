"""
experiments/holding_curve_figure_report.py
Figure for Section 4.1 (H1): combines mean net return AND rank correlation
(rho) decay across holding horizons on one chart -- the canonical
experiments/holding_period_curve.py only plots return, but Section 4.1's
argument rests on both curves decaying together. Read-only against the
already-regenerated outputs/global/summary/ext2_holding_curve.csv; does not
modify the canonical script.

Output: report/figures/figure_holding_curve.png (main body, Section 4.1)

Run: python -m experiments.holding_curve_figure_report
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "outputs" / "global" / "summary" / "ext2_holding_curve.csv"
OUT_PNG = BASE_DIR / "report" / "figures" / "figure_holding_curve.png"


def load_curve():
    with open(CSV_PATH) as f:
        lines = [l for l in f if not l.startswith("#")]
    reader = csv.DictReader(lines)
    return list(reader)


def main():
    rows = load_curve()
    horizons = [r["horizon"] for r in rows]
    x = np.arange(len(horizons))
    returns = [float(r["mean_net_per_trade"]) * 100 for r in rows]
    rho = [float(r["rank_correlation"]) for r in rows]

    fig, ax1 = plt.subplots(figsize=(9, 5.5))
    ax2 = ax1.twinx()

    ax1.plot(x, returns, "o-", color="#2563eb", linewidth=2, markersize=7, label="Mean net return per trade", zorder=3)
    ax1.axhline(0, color="#2563eb", linestyle="--", linewidth=0.6, alpha=0.4)
    ax1.set_ylabel("Mean net return per trade (%)", color="#2563eb")
    ax1.tick_params(axis="y", labelcolor="#2563eb")

    ax2.plot(x, rho, "s-", color="#d97706", linewidth=2, markersize=7, label="Spearman's rho", zorder=3)
    ax2.set_ylabel("Spearman's rho (score vs. return)", color="#d97706")
    ax2.tick_params(axis="y", labelcolor="#d97706")
    ax2.set_ylim(0, 0.3)

    ax1.set_xticks(x)
    ax1.set_xticklabels(horizons)
    ax1.set_xlabel("Holding horizon")
    # No title: the LaTeX caption carries it (report/latex/main.tex). Keeping
    # both duplicates the text on the page and in the List of Figures.

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=9)

    ax1.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)
    print(f"Wrote {OUT_PNG}")


if __name__ == "__main__":
    main()
