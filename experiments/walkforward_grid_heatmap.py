"""
experiments/walkforward_grid_heatmap.py
Figure for Section 4.3 (H3): heatmap of the 20-cell best-effort walk-forward
grid (5 window schemes x 4 objective/floor variants), read-only against the
already-verified Appendix A3 CSV -- no rescoring, no new analysis.

Source: report/appendix/appendix_a3_best_effort_grid.csv
Output: report/appendix/figure_walkforward_grid.png

Run: python -m experiments.walkforward_grid_heatmap
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "outputs" / "appendix" / "appendix_a3_best_effort_grid.csv"
OUT_PNG = BASE_DIR / "outputs" / "appendix" / "figure_walkforward_grid.png"

WINDOW_SCHEMES = ["calendar_quarter", "equal_count_2w", "equal_count_3w", "equal_count_4w", "equal_count_5w"]
WINDOW_LABELS = ["Calendar\nquarter", "Equal count\n(2 windows)", "Equal count\n(3 windows)", "Equal count\n(4 windows)", "Equal count\n(5 windows)"]
VARIANTS = ["mean_net(floor=10%)", "mean_net(floor=15%)", "mean_net(floor=20%)", "accuracy(floor=15%, fixed)"]
VARIANT_LABELS = ["Return,\nfloor=10%", "Return,\nfloor=15%", "Return,\nfloor=20%", "Accuracy,\nfloor=15%"]


def load_grid():
    with open(CSV_PATH) as f:
        lines = [l for l in f if not l.startswith("#")]
    reader = csv.DictReader(lines)
    rows = {row["label"]: row for row in reader}
    return rows


def main():
    rows = load_grid()

    p_matrix = np.full((len(WINDOW_SCHEMES), len(VARIANTS)), np.nan)
    margin_matrix = np.full((len(WINDOW_SCHEMES), len(VARIANTS)), np.nan)

    for i, scheme in enumerate(WINDOW_SCHEMES):
        for j, variant in enumerate(VARIANTS):
            label = f"{scheme} / {variant}"
            row = rows.get(label)
            if row is None:
                continue
            p_matrix[i, j] = float(row["binomial_p"])
            margin_matrix[i, j] = float(row["margin_vs_floor_pp"])

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(p_matrix, cmap="RdYlGn_r", vmin=0, vmax=1, aspect="auto")

    ax.set_xticks(range(len(VARIANTS)))
    ax.set_xticklabels(VARIANT_LABELS, fontsize=9)
    ax.set_yticks(range(len(WINDOW_SCHEMES)))
    ax.set_yticklabels(WINDOW_LABELS, fontsize=9)

    for i in range(len(WINDOW_SCHEMES)):
        for j in range(len(VARIANTS)):
            p = p_matrix[i, j]
            m = margin_matrix[i, j]
            if np.isnan(p):
                continue
            text_color = "white" if p < 0.35 else "black"
            ax.text(j, i, f"p={p:.2f}\n+{m:.1f}pp", ha="center", va="center",
                     fontsize=8, color=text_color)

    ax.axhline(y=-0.5, color="black", linewidth=0.5)
    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("p-value (significance test vs. majority-direction floor)", fontsize=9)

    # No title: the LaTeX caption carries it (report/latex/main.tex), including
    # the "no cell reaches significance" finding.
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)
    print(f"Wrote {OUT_PNG}")


if __name__ == "__main__":
    main()
