"""
experiments/lm_baseline.py
Item 4 of the model-arm spec (Nigel, 2026-08-05), word-list half only
(FinBERT half deliberately deferred - new heavy torch/transformers
dependency). Whether the model's cost buys anything over a method that is
effectively free: a Loughran-McDonald finance word-count score, pushed
through the identical evaluation path as the deployed model.

Word list: pysentiment2's LM() class, which bundles the canonical
Loughran-McDonald Master Dictionary word lists (MIT-licensed data files, no
manual download). Score = (positive_count - negative_count) / total_token_count
on the same extracted document text the micro layer reads
(run_meta.extracted_text_path in each outputs/<issuer>/results/<document_id>.json,
same resolution pattern as experiments/quote_verification_screen.py).

Dev/eval split (new - this repo had no such split before): sort all N=268
events by report_date, earliest ~20% (~54 events) = dev, remaining ~214 =
eval. Two thresholds (upper/lower -> BUY/HOLD/SELL) are grid-searched for
best accuracy on dev only, then frozen and applied unchanged to eval - never
fit on the events being scored, per the spec's own explicit trap warning.

Comparison is against the deployed model's OWN accuracy on the same eval
subset (not the full-N 36.2% figure elsewhere in this project) and against
a majority-class baseline on that same subset, so all three numbers answer
the identical question over the identical events.

Run: python -m experiments.lm_baseline
"""
from __future__ import annotations

import csv
import itertools
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pysentiment2 as ps

from backtest import OUTPUTS_DIR

PHASE2_CALIBRATION_CSV = OUTPUTS_DIR / "global" / "summary" / "global_outcome_calibration_phase2.csv"
THRESHOLDS_JSON = OUTPUTS_DIR / "global" / "summary" / "lm_baseline_dev_thresholds.json"
EVAL_CSV = OUTPUTS_DIR / "global" / "summary" / "lm_baseline_eval_results.csv"

DEV_FRACTION = 0.20

_LM = ps.LM()


def result_json_path(issuer: str, document_id: str) -> Path:
    return OUTPUTS_DIR / issuer / "results" / f"{document_id}.json"


def lm_score(text: str) -> tuple[float, int, int, int]:
    """Returns (score, pos_count, neg_count, total_tokens).
    score = (pos - neg) / total_tokens, 0.0 if no tokens."""
    tokens = _LM.tokenize(text)
    scored = _LM.get_score(tokens)
    pos, neg = scored["Positive"], scored["Negative"]
    total = len(tokens)
    score = (pos - neg) / total if total else 0.0
    return score, pos, neg, total


def load_events(path: Path = PHASE2_CALIBRATION_CSV) -> list[dict]:
    events = []
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if not r["micro_score"]:
                continue
            events.append(r)
    return events


def attach_lm_scores(events: list[dict]) -> list[dict]:
    out = []
    skipped = 0
    for r in events:
        json_path = result_json_path(r["issuer"], r["document_id"])
        if not json_path.exists():
            skipped += 1
            continue
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        text_path = payload.get("run_meta", {}).get("extracted_text_path")
        if not text_path or not Path(text_path).exists():
            skipped += 1
            continue
        text = Path(text_path).read_text(encoding="utf-8", errors="replace")
        score, pos, neg, total = lm_score(text)
        out.append({
            "document_id": r["document_id"], "ticker": r["ticker"],
            "report_date": r["report_date"], "outcome_label": r["outcome_label"],
            "blend_correct_default": r["blend_correct_default"],
            "lm_score": score, "lm_pos": pos, "lm_neg": neg, "lm_total_tokens": total,
        })
    if skipped:
        print(f"Skipped {skipped} events (missing result JSON or extracted text)")
    return out


def split_dev_eval(events: list[dict], dev_fraction: float = DEV_FRACTION) -> tuple[list[dict], list[dict]]:
    events_sorted = sorted(events, key=lambda e: e["report_date"])
    n_dev = round(len(events_sorted) * dev_fraction)
    return events_sorted[:n_dev], events_sorted[n_dev:]


def predict(score: float, upper: float, lower: float) -> str:
    if score > upper:
        return "BUY"
    if score < lower:
        return "SELL"
    return "HOLD"


def accuracy(events: list[dict], upper: float, lower: float) -> float:
    if not events:
        return 0.0
    correct = sum(1 for e in events if predict(e["lm_score"], upper, lower) == e["outcome_label"])
    return correct / len(events)


def fit_thresholds(dev_events: list[dict]) -> tuple[float, float, float]:
    """Grid search over candidate thresholds (dev score distribution's own
    percentiles) for the (upper, lower) pair maximizing dev accuracy.
    Returns (best_upper, best_lower, best_dev_accuracy)."""
    scores = sorted(e["lm_score"] for e in dev_events)
    candidates = sorted(set(np.percentile(scores, np.linspace(0, 100, 41))))

    best = (candidates[-1], candidates[0], -1.0)
    for upper in candidates:
        for lower in candidates:
            if lower > upper:
                continue
            acc = accuracy(dev_events, upper, lower)
            if acc > best[2]:
                best = (upper, lower, acc)
    return best


def majority_baseline_accuracy(events: list[dict]) -> tuple[str, float]:
    counts = Counter(e["outcome_label"] for e in events)
    majority_label, majority_count = counts.most_common(1)[0]
    return majority_label, majority_count / len(events)


def write_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows -> {path}")


def main() -> int:
    events = load_events()
    print(f"Loaded {len(events)} events from calibration CSV")
    events = attach_lm_scores(events)
    print(f"Attached LM scores to {len(events)} events")

    dev, eval_set = split_dev_eval(events)
    print(f"Dev split: {len(dev)} events (earliest {DEV_FRACTION:.0%} by report_date), "
          f"eval split: {len(eval_set)} events")
    print(f"Dev date range: {dev[0]['report_date']} to {dev[-1]['report_date']}")
    print(f"Eval date range: {eval_set[0]['report_date']} to {eval_set[-1]['report_date']}")

    upper, lower, dev_acc = fit_thresholds(dev)
    print(f"\nFitted on dev only: upper={upper:.6f}, lower={lower:.6f}, dev accuracy={dev_acc:.4f}")

    thresholds_out = {
        "dev_n": len(dev), "eval_n": len(eval_set),
        "dev_fraction": DEV_FRACTION,
        "dev_date_range": [dev[0]["report_date"], dev[-1]["report_date"]],
        "eval_date_range": [eval_set[0]["report_date"], eval_set[-1]["report_date"]],
        "fitted_upper": upper, "fitted_lower": lower, "dev_accuracy": round(dev_acc, 4),
        "note": "Thresholds fit on dev split only (earliest 20% by report_date), applied "
                "frozen to eval split - never fit on the events they are scored on.",
    }
    THRESHOLDS_JSON.parent.mkdir(parents=True, exist_ok=True)
    THRESHOLDS_JSON.write_text(json.dumps(thresholds_out, indent=2), encoding="utf-8")
    print(f"Wrote thresholds -> {THRESHOLDS_JSON}")

    eval_rows = []
    lm_correct = 0
    model_correct = 0
    for e in eval_set:
        lm_pred = predict(e["lm_score"], upper, lower)
        is_lm_correct = int(lm_pred == e["outcome_label"])
        is_model_correct = int(e["blend_correct_default"] == "True")
        lm_correct += is_lm_correct
        model_correct += is_model_correct
        eval_rows.append({
            "document_id": e["document_id"], "ticker": e["ticker"], "report_date": e["report_date"],
            "outcome_label": e["outcome_label"], "lm_score": round(e["lm_score"], 6),
            "lm_predicted_signal": lm_pred, "lm_correct": is_lm_correct,
            "model_correct_default": is_model_correct,
        })
    write_csv(EVAL_CSV, eval_rows)

    lm_eval_acc = lm_correct / len(eval_set)
    model_eval_acc = model_correct / len(eval_set)
    majority_label, majority_acc = majority_baseline_accuracy(eval_set)

    print(f"\nOn eval split (n={len(eval_set)}), same events for all three:")
    print(f"  LM baseline accuracy:        {lm_eval_acc:.4f}")
    print(f"  Deployed model accuracy:     {model_eval_acc:.4f}")
    print(f"  Majority-class ({majority_label:4}) baseline: {majority_acc:.4f}")

    if lm_eval_acc >= model_eval_acc:
        print("\n  Result: LM baseline matches or beats the deployed model on this eval subset - "
              "report this plainly, do not smooth it into a model-favorable framing.")
    else:
        print("\n  Result: deployed model beats the LM baseline on this eval subset.")
    if max(lm_eval_acc, model_eval_acc) <= majority_acc:
        print("  Caveat: the majority-class baseline still beats both predictors on this subset - "
              "same honest-limitation shape as the existing rq16_surprise_control finding.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
