"""
experiments/score_return_scatter_figure.py
Figure for Section 4.1 (H1): the blended sentiment score against the realised
overnight return, one point per clean event.

Purpose is to make the size of the relationship visible. Section 4.1 reports
rho = 0.259 and describes it as "modest"; a reader without an intuition for
rank correlation cannot tell from the number alone whether that is a tight
relationship or a faint one. The scatter answers it directly, and it guards
the claim rather than inflating it: the cloud is plainly a cloud.

The deployed HOLD band and the pre-registered +/-2% grading band are shaded
in behind the points, so the reader can also see that a wide spread of
outcomes sits inside the band where the model declines to trade - which is
why Section 4.3 treats the threshold layer as a separate problem from the
score itself.

Read-only. Scores are recomputed at the deployed weights via
walkforward_validation._blend_score, the same function the walk-forward and
paired-comparison work uses, so this figure cannot drift from them.

Output: report/figures/figure_score_scatter.png (main body, Section 4.1)

Run: python -m experiments.score_return_scatter_figure
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from blend import DEFAULT_HOLD_LOWER, DEFAULT_HOLD_UPPER
from experiments.walkforward_validation import _blend_score, _load_clean_events

OUT_PNG = BASE_DIR / "report" / "figures" / "figure_score_scatter.png"
FLAT_BAND_PCT = 2.0


def main() -> None:
    events = _load_clean_events()
    scores = np.array([_blend_score(e) for e in events])
    returns = np.array([e["ret_overnight"] for e in events]) * 100

    fig, ax = plt.subplots(figsize=(8.5, 5.5))

    # Bands first, so points sit on top of them.
    ax.axhspan(-FLAT_BAND_PCT, FLAT_BAND_PCT, color="#d1d5db", alpha=0.55, zorder=1)
    ax.axvspan(DEFAULT_HOLD_LOWER, DEFAULT_HOLD_UPPER, color="#fde68a", alpha=0.45, zorder=1)

    ax.scatter(scores, returns, s=24, alpha=0.6, color="#2563eb",
               edgecolors="none", zorder=3)

    slope, intercept = np.polyfit(scores, returns, 1)
    xs = np.linspace(scores.min(), scores.max(), 50)
    ax.plot(xs, slope * xs + intercept, color="#b91c1c", linewidth=1.8, zorder=4)

    ax.axhline(0, color="#6b7280", linewidth=0.6, zorder=2)
    ax.axvline(0, color="#6b7280", linewidth=0.6, zorder=2)

    # Band labels, placed against the axes rather than floating in the cloud.
    ax.text(DEFAULT_HOLD_LOWER + (DEFAULT_HOLD_UPPER - DEFAULT_HOLD_LOWER) / 2,
            returns.max() * 0.97, "model holds", ha="center", va="top",
            fontsize=8, color="#92400e", style="italic", zorder=5)
    ax.text(scores.min(), 0, " outcome inside the grading band ",
            ha="left", va="center", fontsize=8, color="#4b5563",
            style="italic", zorder=6,
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                      edgecolor="none", alpha=0.85))

    ax.set_xlabel("Blended sentiment score")
    ax.set_ylabel("Realised overnight return (%)")
    # No title: the LaTeX caption carries it (report/latex/main.tex). Keeping
    # both duplicates the text on the page and in the List of Figures.
    ax.grid(alpha=0.2, zorder=0)

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)
    print(f"Wrote {OUT_PNG}")
    print(f"  N={len(events)}, fitted slope {slope:.2f}% return per unit of score")


if __name__ == "__main__":
    main()
