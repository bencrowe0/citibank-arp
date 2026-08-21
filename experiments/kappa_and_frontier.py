"""Regenerate kappa_near_independence.csv and frontier_table.csv.

Both artefacts were hand-built and neither had an owning script in the repo, so
neither could be regenerated when blend.py's constants moved - they simply went
stale silently while every file around them was rebuilt. This is that script.

Discipline, unchanged from the rest of the project: each figure is computed at
the SUPERSEDED constants first and checked against the committed artefact. If
the old value does not reproduce, nothing is written - a harness that cannot
regenerate a known answer is not trusted with an unknown one.

Only the deployed-model row of frontier_table.csv moves. The three baselines
(majority-class HOLD, Loughran-McDonald, FinBERT) do not read blend.py's
constants at all, so they are carried through unchanged rather than recomputed.

Usage:
  python -m experiments.kappa_and_frontier
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

from blend import (  # noqa: E402
    DEFAULT_HOLD_LOWER, DEFAULT_HOLD_UPPER, DEFAULT_WEIGHTS, blend_scores, derive_signal,
)
import experiments.human_vs_llm_backing as hb  # noqa: E402
import experiments.walkforward_validation as wf  # noqa: E402

SUMMARY = ROOT / "outputs" / "global" / "summary"
KAPPA_CSV = SUMMARY / "kappa_near_independence.csv"
FRONTIER_CSV = SUMMARY / "frontier_table.csv"
CALIBRATION_CSV = SUMMARY / "global_outcome_calibration_phase2.csv"

SUPERSEDED_W, SUPERSEDED_HU, SUPERSEDED_HL = (0.55, 0.45, 0.0, 0.0), 0.25, -0.05
DEPLOYED = (tuple(DEFAULT_WEIGHTS), DEFAULT_HOLD_UPPER, DEFAULT_HOLD_LOWER)

LABELS = ("BUY", "HOLD", "SELL")
N_BOOT, RNG_SEED, CI = 10_000, 20260709, 0.90
EVAL_SPLIT_FRACTION = 0.20  # earliest 20% by release date is the dev split

# What the committed artefacts assert. The gate is against these, not against
# anything this script computes twice.
#
# 2026-08-21: reference moved from the 171-pair N=233 universe to the 170-pair
# N=232 universe (DIS_FQ1_2025 excluded for look-ahead, ruling of 2026-08-24 in
# eval/excluded_events.py). At the superseded constants DIS's pair was
# human BUY / LLM HOLD - a disagreement - so agreements stay 65 and only the
# BUY/HOLD cell and the denominators move. The old 171-pair reference remains
# recorded here: n=171, obs=0.3801, exp=0.3041, kappa=0.1092, BUY/HOLD=43.
KAPPA_GATE = {"n_paired_events": 170, "observed_agreement": 0.3824,
              "expected_agreement": 0.3048, "cohens_kappa": 0.1115}
KAPPA_MATRIX_GATE = {("BUY", "BUY"): 32, ("BUY", "HOLD"): 42, ("BUY", "SELL"): 21,
                     ("HOLD", "BUY"): 6, ("HOLD", "HOLD"): 14, ("HOLD", "SELL"): 20,
                     ("SELL", "BUY"): 4, ("SELL", "HOLD"): 12, ("SELL", "SELL"): 19}
FRONTIER_GATE = {"eval_n": 186, "graded_n": 119, "correct_flat_excluded": 51,
                 "correct_flat_as_wrong": 82, "ci_low": 0.353, "ci_high": 0.504}

# 2026-08-21: the three baseline rows are no longer carried through unchanged.
# They went stale when the Lowe's dateline correction re-fitted the baseline
# dev thresholds (7012bd9 regenerated the eval CSVs; frontier_table kept the
# pre-re-fit rows: FinBERT 41/119, 60/186, traded 147, CI [0.277, 0.420];
# LM 18/119, 65/186, traded 59 - all of which reproduce exactly from the
# pre-7012bd9 CSV vintages, validating this method). The rows now rebuild from
# the committed per-event eval CSVs in the tree. This gate pins what those
# INPUT artifacts assert - stable across runs of this script, so it is not a
# read-what-you-write gate.
BASELINE_INPUT_GATE = {
    "Majority-class HOLD": {"flat_excluded": 65, "flat_as_wrong": 67, "traded": 0},
    "Loughran-McDonald (LM)": {"flat_excluded": 4, "flat_as_wrong": 70, "traded": 6},
    "FinBERT (ProsusAI/finbert)": {"flat_excluded": 21, "flat_as_wrong": 61, "traded": 75},
}
FINBERT_EVAL_CSV = SUMMARY / "finbert_eval_results.csv"
LM_EVAL_CSV = SUMMARY / "lm_baseline_eval_results.csv"


def _num(x):
    x = (x or "").strip()
    return None if x == "" else float(x)


def score_at(row, weights):
    return blend_scores(_num(row["micro_score"]), _num(row["macro_score"]),
                        _num(row["news_score"]), _num(row["quant_score"]), weights)


def load_calibration():
    with CALIBRATION_CSV.open(newline="") as fh:
        return {r["document_id"]: r for r in csv.DictReader(fh)}


# ---------------------------------------------------------------------------
# Cohen's kappa
# ---------------------------------------------------------------------------

def kappa_from(pairs):
    """pairs: list of (human_call, llm_call). Three-way, unweighted."""
    n = len(pairs)
    obs = sum(1 for h, l in pairs if h == l) / n
    exp = sum((sum(1 for h, _ in pairs if h == L) / n) *
              (sum(1 for _, l in pairs if l == L) / n) for L in LABELS)
    return obs, exp, (obs - exp) / (1 - exp)


def kappa_ci(pairs):
    rng = np.random.RandomState(RNG_SEED)
    n = len(pairs)
    boot = np.empty(N_BOOT)
    for i in range(N_BOOT):
        idx = rng.randint(0, n, size=n)
        boot[i] = kappa_from([pairs[j] for j in idx])[2]
    alpha = 1 - CI
    return (float(np.percentile(boot, 100 * alpha / 2)),
            float(np.percentile(boot, 100 * (1 - alpha / 2))))


def confusion(pairs):
    return {(h, l): sum(1 for a, b in pairs if a == h and b == l)
            for h in LABELS for l in LABELS}


def build_kappa(paired, cal):
    """(gate_result, deployed_result) - both computed from the same code path."""
    out = {}
    for tag, (w, hu, hl) in (("superseded", (SUPERSEDED_W, SUPERSEDED_HU, SUPERSEDED_HL)),
                             ("deployed", DEPLOYED)):
        pairs = []
        for p in paired:
            row = cal.get(p["document_id"])
            if row is None:
                continue
            pairs.append((p["human_decision"], derive_signal(score_at(row, w), hu, hl)))
        obs, exp, k = kappa_from(pairs)
        out[tag] = {"pairs": pairs, "n": len(pairs), "obs": obs, "exp": exp, "kappa": k,
                    "weights": w, "hu": hu, "hl": hl}
    return out


# ---------------------------------------------------------------------------
# Baseline frontier, deployed-model row
# ---------------------------------------------------------------------------

def build_frontier(events):
    ordered = sorted(events, key=lambda e: e["release_date"])
    eval_split = ordered[round(len(ordered) * EVAL_SPLIT_FRACTION):]
    graded = [e for e in eval_split if abs(e["ret_overnight"]) > wf.FLAT_BAND]
    out = {}
    for tag, (w, hu, hl) in (("superseded", (SUPERSEDED_W, SUPERSEDED_HU, SUPERSEDED_HL)),
                             ("deployed", DEPLOYED)):
        def call(e):
            return derive_signal(blend_scores(e["micro_score"], e["macro_score"],
                                              e["news_score"], e["quant_score"], w), hu, hl)
        # FLAT-excluded: two-way, on movers only - truth is the sign of the move.
        # FLAT-as-wrong: three-way over every eval event - truth is HOLD when the
        # event did not clear the band, so HOLD on a mover is wrong and HOLD on a
        # non-mover is right. The committed majority-class HOLD baseline pins this
        # down: its 0.3602 is 67/186, exactly the count of non-movers.
        def truth(e, three_way=False):
            r = e["ret_overnight"]
            if three_way and abs(r) <= wf.FLAT_BAND:
                return "HOLD"
            return "BUY" if r > 0 else "SELL"
        c_excl = sum(1 for e in graded if call(e) == truth(e))
        c_wrong = sum(1 for e in eval_split if call(e) == truth(e, three_way=True))
        traded = sum(1 for e in eval_split if call(e) in ("BUY", "SELL"))
        # The committed row's CI [0.353, 0.504] reproduces from this, so the new
        # row gets a recomputed CI rather than the old one carried forward beside
        # a changed point estimate.
        hits = np.array([1.0 if call(e) == truth(e) else 0.0 for e in graded])
        rng = np.random.RandomState(RNG_SEED)
        boot = np.array([hits[rng.randint(0, len(hits), len(hits))].mean()
                         for _ in range(N_BOOT)])
        alpha = 1 - CI
        out[tag] = {"eval_n": len(eval_split), "graded_n": len(graded),
                    "correct_flat_excluded": c_excl, "correct_flat_as_wrong": c_wrong,
                    "traded": traded,
                    "acc_flat_excluded": c_excl / len(graded),
                    "acc_flat_as_wrong": c_wrong / len(eval_split),
                    "ci_low": float(np.percentile(boot, 100 * alpha / 2)),
                    "ci_high": float(np.percentile(boot, 100 * (1 - alpha / 2))),
                    "weights": w, "hu": hu, "hl": hl}
    return out


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------

def gate(label, got, want, tol=5e-5):
    fails = []
    for k, v in want.items():
        g = got[k]
        ok = abs(g - v) <= tol if isinstance(v, float) else g == v
        print(f"  [{'OK' if ok else 'FAIL'}] {label}.{k}: committed={v}, recomputed="
              f"{round(g, 4) if isinstance(g, float) else g}")
        if not ok:
            fails.append(k)
    return fails


def main() -> int:
    print(f"Deployed constants: weights={DEPLOYED[0]} hold_upper={DEPLOYED[1]} "
          f"hold_lower={DEPLOYED[2]}")
    cal = load_calibration()
    paired = hb.load_data()
    events = wf._load_clean_events()
    print(f"Paired human/model events: {len(paired)}; clean universe: {len(events)}")

    k = build_kappa(paired, cal)
    f = build_frontier(events)

    print("\n=== GATE at the superseded constants (0.55/0.45, +0.25/-0.05) ===")
    fails = gate("kappa", {"n_paired_events": k["superseded"]["n"],
                           "observed_agreement": k["superseded"]["obs"],
                           "expected_agreement": k["superseded"]["exp"],
                           "cohens_kappa": k["superseded"]["kappa"]}, KAPPA_GATE)
    cm = confusion(k["superseded"]["pairs"])
    bad = [f"{h}/{l}" for (h, l), v in KAPPA_MATRIX_GATE.items() if cm[(h, l)] != v]
    print(f"  [{'OK' if not bad else 'FAIL'}] kappa.confusion_matrix: "
          f"{'all 9 cells reproduce' if not bad else 'differs at ' + ', '.join(bad)}")
    fails += bad
    fails += gate("frontier", f["superseded"], FRONTIER_GATE, tol=5e-4)
    baselines, bfails = build_baselines()
    fails += bfails

    if fails:
        raise SystemExit(f"\n{len(fails)} gate check(s) failed. Nothing written.")
    print("  gate OK - every committed value reproduces")

    kl, kh = kappa_ci(k["deployed"]["pairs"])
    d, fd = k["deployed"], f["deployed"]
    print(f"\n=== AT THE DEPLOYED CONSTANTS ===")
    print(f"  kappa    {d['kappa']:.4f}  90% CI [{kl:.3f}, {kh:.3f}]  "
          f"agreement {d['obs']:.4f}/{d['exp']:.4f}")
    print(f"  frontier flat-excluded {fd['correct_flat_excluded']}/{fd['graded_n']} = "
          f"{fd['acc_flat_excluded']*100:.1f}% 90% CI [{fd['ci_low']:.3f}, {fd['ci_high']:.3f}]"
          f"   flat-as-wrong {fd['correct_flat_as_wrong']}/{fd['eval_n']} = "
          f"{fd['acc_flat_as_wrong']*100:.1f}%")

    write_kappa(d, kl, kh)
    write_frontier(fd, baselines)
    return 0


def write_kappa(d, ci_low, ci_high):
    cm = confusion(d["pairs"])
    n = d["n"]
    with KAPPA_CSV.open("w", newline="") as fh:
        fh.write("# Cohen's kappa: human vs LLM directional calls\n")
        fh.write("# Subset: section=All, first_rater_for_event=YES, in_llm_universe=YES,\n")
        fh.write("#   document_id in N=232 clean universe (25 worksheet + 1 SPOT + "
                 "1 DIS look-ahead + 9 timing excluded)\n")
        fh.write("# LLM decision: blend.derive_signal over blend.blend_scores\n")
        fh.write(f"#   (deployed weights {'/'.join(str(x) for x in d['weights'])}, "
                 f"thresholds {d['hu']:+g}/{d['hl']:+g})\n")
        fh.write("# Grading convention: BUY/HOLD/SELL calls compared directly (no return-based grading)\n")
        fh.write(f"# Bootstrap: {N_BOOT:,} resamples, RNG seed {RNG_SEED}, {int(CI*100)}% CI\n")
        fh.write("# Regenerated by experiments/kappa_and_frontier.py, gated at 0.55/0.45 +0.25/-0.05\n")
        fh.write(f"# Date: {date.today().isoformat()}\n#\n")
        w = csv.writer(fh)
        w.writerow(["metric", "value"])
        w.writerow(["n_paired_events", n])
        w.writerow(["observed_agreement", f"{d['obs']:.4f}"])
        w.writerow(["expected_agreement", f"{d['exp']:.4f}"])
        w.writerow(["cohens_kappa", f"{d['kappa']:.4f}"])
        w.writerow(["bootstrap_90ci_low", f"{ci_low:.3f}"])
        w.writerow(["bootstrap_90ci_high", f"{ci_high:.3f}"])
        fh.write("\n")
        w.writerow(["arm", "BUY_frac", "HOLD_frac", "SELL_frac"])
        for arm, idx in (("Human", 0), ("LLM", 1)):
            fr = [sum(1 for p in d["pairs"] if p[idx] == L) / n for L in LABELS]
            w.writerow([arm] + [f"{x:.4f}" for x in fr])
        fh.write("\n")
        w.writerow(["confusion_matrix", "LLM_BUY", "LLM_HOLD", "LLM_SELL", "row_total"])
        for h in LABELS:
            row = [cm[(h, l)] for l in LABELS]
            w.writerow([f"Human_{h}"] + row + [sum(row)])
        w.writerow(["col_total"] + [sum(cm[(h, l)] for h in LABELS) for l in LABELS] + [n])
    print(f"  Wrote {KAPPA_CSV}")


def _bootstrap_prop_ci(hits):
    hits = np.asarray(hits, dtype=float)
    rng = np.random.RandomState(RNG_SEED)
    boot = np.array([hits[rng.randint(0, len(hits), len(hits))].mean()
                     for _ in range(N_BOOT)])
    alpha = 1 - CI
    return (float(np.percentile(boot, 100 * alpha / 2)),
            float(np.percentile(boot, 100 * (1 - alpha / 2))))


def build_baselines():
    """Baseline rows recomputed from the committed per-event eval CSVs, in CSV
    row order (date order). Gated against BASELINE_INPUT_GATE."""
    def load(path, sig_col):
        with path.open(newline="") as fh:
            return [r for r in csv.DictReader(
                l for l in fh if not l.startswith("#")) if r.get("document_id")]

    fe = load(FINBERT_EVAL_CSV, "finbert_predicted_signal")
    le = load(LM_EVAL_CSV, "lm_predicted_signal")
    out = {}
    for method, rows, sig_col in (
            ("Majority-class HOLD", fe, None),
            ("Loughran-McDonald (LM)", le, "lm_predicted_signal"),
            ("FinBERT (ProsusAI/finbert)", fe, "finbert_predicted_signal")):
        graded = [r for r in rows if r["outcome_label"] != "HOLD"]
        if sig_col is None:
            # always-HOLD baseline; FLAT-excluded convention = always-DOWN
            hits = [1.0 if r["outcome_label"] == "SELL" else 0.0 for r in graded]
            excl = int(sum(hits))
            wrong = sum(1 for r in rows if r["outcome_label"] == "HOLD")
            traded = 0
        else:
            hits = [1.0 if r[sig_col] == r["outcome_label"] else 0.0 for r in graded]
            excl = int(sum(hits))
            wrong = sum(1 for r in rows if r[sig_col] == r["outcome_label"])
            traded = sum(1 for r in rows if r[sig_col] in ("BUY", "SELL"))
        lo, hi = _bootstrap_prop_ci(hits)
        out[method] = {"flat_excluded": excl, "flat_as_wrong": wrong,
                       "traded": traded, "graded_n": len(graded), "eval_n": len(rows),
                       "ci_low": lo, "ci_high": hi}
    fails = []
    for method, want in BASELINE_INPUT_GATE.items():
        got = out[method]
        for key, v in want.items():
            ok = got[key] == v
            print(f"  [{'OK' if ok else 'FAIL'}] baseline {method}.{key}: "
                  f"gate={v}, recomputed={got[key]}")
            if not ok:
                fails.append(f"baseline.{method}.{key}")
    return out, fails


def write_frontier(fd, baselines):
    """Rewrite the deployed-model row and the three baseline rows; both derive
    from committed inputs (the calibration chain and the eval CSVs)."""
    lines = FRONTIER_CSV.read_text().splitlines()
    body = [l for l in lines if not l.startswith("#")]
    rows = list(csv.DictReader([l for l in body if l.strip()]))
    fields = list(rows[0].keys())
    wtag = "/".join(f"{x:g}" for x in fd["weights"][:2])
    for r in rows:
        if r["method"].startswith("Deployed model"):
            r["method"] = f"Deployed model (DeepSeek, {wtag} micro/macro)"
            r["accuracy_flat_excluded"] = f"{fd['acc_flat_excluded']:.4f}"
            r["accuracy_flat_as_wrong"] = f"{fd['acc_flat_as_wrong']:.4f}"
            r["traded_n"] = fd["traded"]
            r["bootstrap_ci_flat_excluded"] = f"[{fd['ci_low']:.3f}, {fd['ci_high']:.3f}]"
            r["note"] = (f"Structured output with evidence quotes; API cost per document. "
                         f"FLAT-excluded: {fd['correct_flat_excluded']}/{fd['graded_n']}.")
        elif r["method"] in baselines:
            b = baselines[r["method"]]
            r["accuracy_flat_excluded"] = f"{b['flat_excluded'] / b['graded_n']:.4f}"
            r["accuracy_flat_as_wrong"] = f"{b['flat_as_wrong'] / b['eval_n']:.4f}"
            r["traded_n"] = b["traded"]
            r["bootstrap_ci_flat_excluded"] = f"[{b['ci_low']:.3f}, {b['ci_high']:.3f}]"
            note = r["note"].split("FLAT-excluded:")[0].rstrip()
            r["note"] = (f"{note} FLAT-excluded: "
                         f"{'always-DOWN = ' if r['method'].startswith('Majority') else ''}"
                         f"{b['flat_excluded']}/{b['graded_n']}.")
    with FRONTIER_CSV.open("w", newline="") as fh:
        fh.write(f"# Event set: eval split (latest 80% by report_date) of N=232 clean events "
                 f"(36 excluded). Total eval: {fd['eval_n']} events; {fd['graded_n']} graded "
                 f"(|ret_overnight|>2%).\n")
        fh.write("# Grading: overnight returns from returns_matrix.csv (release_date anchor, "
                 "2026-08-12 correction), pre-registered +-2% band.\n")
        fh.write(f"# FLAT-excluded: denominator = {fd['graded_n']} (BUY/SELL outcome events only). "
                 f"FLAT-as-wrong: denominator = {fd['eval_n']} (all eval events; model HOLD on a "
                 "moved event = wrong).\n")
        fh.write("# Majority-direction (FLAT-excluded) = always-DOWN (predict SELL on every event) "
                 f"= 65/{fd['graded_n']}. This is the eval-split floor, NOT the full-sample floor "
                 "(59/109 on N=232 at the deployed constants).\n#\n")
        fh.write(f"# Deployed-model row regenerated {date.today().isoformat()} by "
                 "experiments/kappa_and_frontier.py at blend.py's current constants,\n")
        fh.write("# gated first at the superseded 0.55/0.45 +0.25/-0.05 (51/119 and 82/186 "
                 "reproduce exactly).\n")
        fh.write("# Baseline rows rebuilt from the committed per-event eval CSVs "
                 "(finbert_eval_results.csv, lm_baseline_eval_results.csv), which carry the\n")
        fh.write("# post-Lowe's-dateline threshold fit; the pre-re-fit rows (FinBERT 41/119, "
                 "traded 147; LM 18/119, traded 59) reproduce from the pre-7012bd9 vintages.\n")
        fh.write("# The three figures 42.2% / eval-split FLAT-excluded / eval-split FLAT-as-wrong "
                 "differ in event set and convention, NOT in substance.\n")
        fh.write("# DO NOT cite them together without saying which is which.\n#\n")
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"  Wrote {FRONTIER_CSV}")


if __name__ == "__main__":
    raise SystemExit(main())
