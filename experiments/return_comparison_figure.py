"""
experiments/return_comparison_figure.py
Figure for Section 4.2 (H2): mean net return per trade, model vs. human arm,
the report's central comparison. Read-only against already-verified figures
(Section 3.4 / ext2_holding_curve.csv for the model side; the human-arm
figures newly derived in Section 3.4 -- no CI was computed for the human
side, so it is shown as a point estimate only, stated explicitly on the
figure rather than implying false precision).

Output: report/figures/figure_return_comparison.png (main body, Section 4.2)

Run: python -m experiments.return_comparison_figure
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_PNG = BASE_DIR / "report" / "figures" / "figure_return_comparison.png"

# Verified figures, Section 3.4 / Section 4.2:
MODEL_MEAN = 1.798        # ext2_holding_curve.csv, overnight row
MODEL_CI_LOW = 1.00
MODEL_CI_HIGH = 2.63
HUMAN_MEAN = -0.06         # trade-weighted, n=205, no CI computed


def main():
    fig, ax = plt.subplots(figsize=(6, 5))

    labels = ["Model\n(169 trades)", "Human arm\n(n=205, trade-weighted)"]
    means = [MODEL_MEAN, HUMAN_MEAN]
    colors = ["#2563eb", "#dc2626"]

    bars = ax.bar(labels, means, color=colors, width=0.5, zorder=3)

    # Model CI as an error bar; human arm has no computed CI, shown as a
    # bare point estimate (stated in the caption, not implied by the chart).
    ax.errorbar(
        [0], [MODEL_MEAN],
        yerr=[[MODEL_MEAN - MODEL_CI_LOW], [MODEL_CI_HIGH - MODEL_MEAN]],
        fmt="none", ecolor="black", elinewidth=1.5, capsize=6, zorder=4,
    )

    ax.axhline(0, color="gray", linestyle="-", linewidth=0.8, zorder=2)
    # Headroom below zero so the negative bar's value label clears the axis.
    ax.set_ylim(-0.45, 2.95)
    ax.set_ylabel("Mean net return per trade (%)")
    # No title: the LaTeX caption carries it (report/latex/main.tex), including
    # the p=0.013 that used to sit in the title's second line.

    # Model label is nudged left of centre so the CI whisker does not run
    # through it; the human bar has no whisker, so its label stays centred.
    ax.annotate(f"{MODEL_MEAN:+.2f}%", (0, MODEL_MEAN), textcoords="offset points",
                 xytext=(-46, 6), ha="center", fontsize=10, fontweight="bold")
    ax.annotate(f"{HUMAN_MEAN:+.2f}%", (1, HUMAN_MEAN), textcoords="offset points",
                 xytext=(0, -18), ha="center", fontsize=10, fontweight="bold")

    ax.text(1, MODEL_CI_HIGH * 0.15, "no CI computed\nfor human arm",
             ha="center", fontsize=8, color="#6b7280", style="italic")

    ax.grid(axis="y", alpha=0.3, zorder=1)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)
    print(f"Wrote {OUT_PNG}")


if __name__ == "__main__":
    main()
