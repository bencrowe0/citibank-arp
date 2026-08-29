"""
experiments/pipeline_architecture_figure.py
Figure for Section 3.1: schematic of the four-layer blend and deployed
thresholds. No underlying data -- a design diagram, not a results figure.
Weights and thresholds pulled live from blend.py so this can never drift
from the deployed default.

Output: report/figures/figure_pipeline_architecture.png (main body, Section 3.1)

Run: python -m experiments.pipeline_architecture_figure
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR.parent))
from blend import DEFAULT_HOLD_LOWER, DEFAULT_HOLD_UPPER, DEFAULT_WEIGHTS

OUT_PNG = BASE_DIR.parent / "report" / "figures" / "figure_pipeline_architecture.png"

ACTIVE = "#2563eb"
INACTIVE = "#9ca3af"

# (name, description, weight, is_active)
LAYERS = [
    ("Micro", "Earnings materials\n(release, deck, transcript)", DEFAULT_WEIGHTS[0], True),
    ("Macro", "FOMC minutes\n(reused across reports)", DEFAULT_WEIGHTS[1], True),
    ("News", "Pre-earnings\nexpectations digest", DEFAULT_WEIGHTS[2], False),
    ("Quant", "Momentum, EPS surprise,\nmacro-numeric", DEFAULT_WEIGHTS[3], False),
]

BOX_W = 2.30
BOX_H = 1.55
LAYER_Y = 8.35
LAYER_XS = [1.25, 3.75, 6.25, 8.75]

BLEND_X, BLEND_Y = 5.0, 5.55
BLEND_W, BLEND_H = 6.4, 1.05

CALL_Y = 2.75
CALL_W, CALL_H = 2.65, 1.25


def box(ax, x, y, w, h, facecolor, edgecolor="#374151", linewidth=1.2):
    ax.add_patch(FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.01,rounding_size=0.06",
        facecolor=facecolor, edgecolor=edgecolor, linewidth=linewidth, zorder=2,
    ))


def arrow(ax, x0, y0, x1, y1, color="#374151"):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.1,
                                shrinkA=0, shrinkB=0), zorder=1)


def main():
    # Height tracks the y-span so box proportions match the titled version.
    # Top of the layer boxes is 9.125 (LAYER_Y + BOX_H/2).
    fig, ax = plt.subplots(figsize=(10, 6.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0.9, 9.35)
    ax.axis("off")

    # -- four scored layers ---------------------------------------------------
    # Arrow targets spread along the top edge of the blend box so the four
    # lines stay visually distinct instead of converging on one point.
    arrow_targets = [3.0, 4.35, 5.65, 7.0]

    for (name, desc, weight, is_active), x, target in zip(LAYERS, LAYER_XS, arrow_targets):
        color = ACTIVE if is_active else INACTIVE
        text_color = "white" if is_active else "#1f2937"
        box(ax, x, LAYER_Y, BOX_W, BOX_H, color)
        ax.text(x, LAYER_Y + 0.44, name, ha="center", va="center",
                fontsize=11, fontweight="bold", color=text_color, zorder=3)
        ax.text(x, LAYER_Y + 0.02, desc, ha="center", va="center",
                fontsize=7.5, color=text_color, zorder=3, linespacing=1.35)
        ax.text(x, LAYER_Y - 0.50, f"weight {weight:.2f}", ha="center", va="center",
                fontsize=8.5, fontweight="bold", color=text_color, zorder=3)
        arrow(ax, x, LAYER_Y - BOX_H / 2, target, BLEND_Y + BLEND_H / 2)

    # -- blended score --------------------------------------------------------
    box(ax, BLEND_X, BLEND_Y, BLEND_W, BLEND_H, "#fef3c7", edgecolor="#b45309")
    ax.text(BLEND_X, BLEND_Y + 0.23, "Weighted blend score", ha="center", va="center",
            fontsize=11, fontweight="bold", color="#78350f", zorder=3)
    ax.text(BLEND_X, BLEND_Y - 0.23,
            f"micro {DEFAULT_WEIGHTS[0]:.2f}  +  macro {DEFAULT_WEIGHTS[1]:.2f}  +  "
            f"news {DEFAULT_WEIGHTS[2]:.2f}  +  quant {DEFAULT_WEIGHTS[3]:.2f}      "
            f"(range −1 to +1)",
            ha="center", va="center", fontsize=8.5, color="#78350f", zorder=3)

    # -- threshold split ------------------------------------------------------
    calls = [
        (2.0, "SELL", f"score ≤ {DEFAULT_HOLD_LOWER:+.2f}", "#fecaca", "#991b1b"),
        (5.0, "HOLD", f"{DEFAULT_HOLD_LOWER:+.2f} < score < {DEFAULT_HOLD_UPPER:+.2f}", "#e5e7eb", "#374151"),
        (8.0, "BUY", f"score ≥ {DEFAULT_HOLD_UPPER:+.2f}", "#bbf7d0", "#166534"),
    ]
    for x, label, rule, facecolor, textcolor in calls:
        box(ax, x, CALL_Y, CALL_W, CALL_H, facecolor, edgecolor=textcolor)
        ax.text(x, CALL_Y + 0.24, label, ha="center", va="center",
                fontsize=12, fontweight="bold", color=textcolor, zorder=3)
        ax.text(x, CALL_Y - 0.26, rule, ha="center", va="center",
                fontsize=9, color=textcolor, zorder=3)

    # Blend box bottom -> a short stem, then out to each of the three calls.
    stem_y = 4.15
    arrow(ax, BLEND_X, BLEND_Y - BLEND_H / 2, BLEND_X, stem_y + 0.02)
    ax.plot([2.0, 8.0], [stem_y, stem_y], color="#374151", lw=1.1, zorder=1)
    for x, *_ in calls:
        arrow(ax, x, stem_y, x, CALL_Y + CALL_H / 2)

    # -- note -----------------------------------------------------------------
    # No title: the LaTeX caption carries it (report/latex/main.tex). Keeping
    # both duplicates the text on the page and in the List of Figures.
    ax.text(5.0, 1.35,
            "News and Quant earn zero blend weight in the deployed configuration (greyed above) but remain\n"
            "in the search space; see Section 3.1 for the selection process.",
            ha="center", fontsize=8, color="#6b7280", style="italic", linespacing=1.5)

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)
    print(f"Wrote {OUT_PNG}")


if __name__ == "__main__":
    main()
