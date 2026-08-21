"""Regenerate section_ablation_paired_diffs.csv at blend.py's constants.

The committed paired artifact (last touched 2026-08-13) predated both the
returns regeneration (c6e02f7) and the constants promotion, and its exact
numbers (45/66-pair family, -6.8pp at p=0.055) reproduce from NO committed
input under any pairing convention - they came from a pre-regrade working
state that was never committed. Established 2026-08-21; group decision
(flag C) replaced the family with values recomputed from the committed
per-event results.

Conventions, per the artifact's own definitions:
  strict    - events where BOTH arms trade AND the event moves >2% (both
              graded); correctness is direction.
  inclusive - events where EITHER arm is graded; the ungraded side scores 0.5.

Gate: the per-arm graded/correct counts at the promoted constants must
reproduce the frozen reference below, which is what the committed
section_ablation_results.csv asserts (input-pinned, not read-what-you-write).
The same frame reproduces the workbook's Item_C_Ablation per-arm table.

Run: python -m experiments.section_ablation_paired_rethreshold
"""
from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blend import DEFAULT_HOLD_LOWER, DEFAULT_HOLD_UPPER, derive_signal  # noqa: E402
from bootstrap_stats import bootstrap_paired_difference  # noqa: E402

SUMMARY = ROOT / "outputs" / "global" / "summary"
RESULTS_CSV = SUMMARY / "section_ablation_results.csv"
OUT_CSV = SUMMARY / "section_ablation_paired_diffs.csv"

BAND = 0.02
ARMS = ["press_release", "prepared_remarks", "qa_only"]

# What the committed input asserts at the promoted constants (four-arm set):
# arm -> (graded_traded, correct). Matches the workbook's per-arm table.
INPUT_GATE = {
    "full_bundle": (48, 31),
    "press_release": (37, 24),
    "prepared_remarks": (45, 29),
    "qa_only": (39, 27),
}


def load_results():
    with RESULTS_CSV.open(newline="") as fh:
        rows = [r for r in csv.DictReader(l for l in fh if not l.startswith("#"))
                if r.get("document_id")]
    return rows


def main() -> int:
    rows = load_results()
    by_doc_arm = {}
    arms_of = {}
    for r in rows:
        d = r["document_id"]
        by_doc_arm[(d, r["arm"])] = r
        arms_of.setdefault(d, set()).add(r["arm"])
    four = sorted(d for d, a in arms_of.items() if len(a) == 4)
    print(f"four-arm complete events: {len(four)}")

    def graded_correct(r):
        sig = derive_signal(float(r["sentiment_score"]),
                            DEFAULT_HOLD_UPPER, DEFAULT_HOLD_LOWER)
        ret = float(r["ret_overnight"])
        graded = sig != "HOLD" and abs(ret) > BAND
        correct = (sig == "BUY" and ret > BAND) or (sig == "SELL" and ret < -BAND)
        return graded, correct

    fails = []
    for arm, (gn, cn) in INPUT_GATE.items():
        got = [graded_correct(by_doc_arm[(d, arm)]) for d in four]
        g = sum(1 for gg, _ in got if gg)
        c = sum(1 for gg, cc in got if gg and cc)
        ok = (g, c) == (gn, cn)
        print(f"  [{'OK' if ok else 'FAIL'}] {arm}: graded/correct "
              f"gate={gn}/{cn}, recomputed={g}/{c}")
        if not ok:
            fails.append(arm)
    if fails:
        raise SystemExit(f"{len(fails)} input gate(s) failed. Nothing written.")

    out_rows = []
    run_id = rows[0]["run_id"]
    for arm in ARMS:
        strict_a, strict_b, incl_a, incl_b = [], [], [], []
        fb_only = 0
        for d in four:
            fg, fc = graded_correct(by_doc_arm[(d, "full_bundle")])
            ag, ac = graded_correct(by_doc_arm[(d, arm)])
            if fg and ag:
                strict_a.append(1.0 if ac else 0.0)
                strict_b.append(1.0 if fc else 0.0)
            if fg or ag:
                incl_a.append((1.0 if ac else 0.0) if ag else 0.5)
                incl_b.append((1.0 if fc else 0.0) if fg else 0.5)
                fb_only += (fg and not ag)
        for tag, (a, b) in (("strict (both graded)", (strict_a, strict_b)),
                            ("inclusive (either graded, ungraded=0.5)",
                             (incl_a, incl_b))):
            bd = bootstrap_paired_difference(a, b)
            note = ""
            if arm == "press_release" and tag.startswith("inclusive"):
                note = (f"Full bundle leads by "
                        f"{-bd['point_diff']*100:.1f}pp inclusive - inside the "
                        f"~12pp paired MDE; the full bundle trades {fb_only} "
                        f"events this arm passes on")
            out_rows.append({
                "comparison": f"{arm} vs full_bundle", "set": "four_arm",
                "method": tag, "n_paired": bd["n"],
                "point_diff": round(bd["point_diff"], 4),
                "ci_low": round(bd["ci_low"], 4),
                "ci_high": round(bd["ci_high"], 4),
                "p_value": round(bd["p_value"], 4),
                "note": note, "metric": "accuracy_overnight", "run_id": run_id,
            })
            print(f"  {arm:<17} {tag[:9]:<9} n={bd['n']:>2} "
                  f"diff={bd['point_diff']:+.4f} p={bd['p_value']:.4f}")

    with OUT_CSV.open("w", newline="") as fh:
        fh.write("# Section ablation paired differences vs full bundle\n")
        fh.write(f"# Run ID: {run_id} (scores); regraded {date.today().isoformat()} "
                 "by experiments/section_ablation_paired_rethreshold.py\n")
        fh.write(f"# Thresholds: hold_upper={DEFAULT_HOLD_UPPER}, "
                 f"hold_lower={DEFAULT_HOLD_LOWER} (blend.py); returns from the "
                 "committed section_ablation_results.csv (post-c6e02f7 regrade)\n")
        fh.write("# Grading: pre-registered +-2% raw overnight band\n")
        fh.write("# strict = both arms trade AND the event moves (both graded); "
                 "inclusive = either graded, ungraded side scored 0.5\n")
        fh.write("# Paired MDE: ~+-12pp.\n")
        fh.write("# The 2026-08-13 values this file replaces (-6.8pp at p=0.055 "
                 "on 66 pairs, 45/53/43 strict) reproduce from no committed\n")
        fh.write("# input under any pairing convention - they predate the "
                 "returns regrade and the constants promotion.\n#\n")
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    print(f"Wrote {OUT_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
