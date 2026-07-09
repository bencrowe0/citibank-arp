"""
experiments/weight_threshold_sweep.py  (Round 5)

Comprehensive, reproducible pooled weight+threshold optimization - the committed
successor to Round 4's throwaway finer-grid script. Three things the production
grid in eval/calibrate.py does NOT do, kept HERE so the production overfitting
surface stays small:

  1. Finer weight grid (step 0.05 vs production 0.2) over (micro, macro, news, quant).
  2. ASYMMETRIC hold thresholds - production only searches hold_upper == -hold_lower;
     this searches hold_upper and hold_lower independently.
  3. A "does it beat noise" verdict: binomial + permutation significance tests of
     the pooled accuracy against the majority-class baseline.

It also runs the Fed-layer (and macro-numeric) ablation by re-blending with each
quant variant (plain / +macro-numeric / +fred / +macro+fred) and reporting whether
any lifts accuracy.

Vectorized with numpy: a [combo x doc] correctness tensor is built once, so global
best-fit and full LOOCV are both cheap even at N>=131.

Run:  python -m experiments.weight_threshold_sweep
Out:  outputs/global/summary/weight_threshold_sweep.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from report_pipeline import OUTPUTS_DIR
from blend import DEFAULT_WEIGHTS
from eval.calibrate import DEFAULT_HOLD_LOWER, DEFAULT_HOLD_UPPER
from eval.outcomes import DEFAULT_WINDOW_TRADING_DAYS, OUTCOME_LOWER_DEFAULT, OUTCOME_UPPER_DEFAULT
from eval.run_eval import ALL_ISSUERS, build_documents_for_issuer
import quant_layer

LABELS = ("SELL", "HOLD", "BUY")
LABEL_IDX = {l: i for i, l in enumerate(LABELS)}

WEIGHT_STEP = 0.05
THRESH_UPPER = [round(0.05 * k, 2) for k in range(1, 9)]        # 0.05 .. 0.40
THRESH_LOWER = [round(-0.05 * k, 2) for k in range(1, 9)]        # -0.05 .. -0.40
PERMUTATIONS = 5000
RNG_SEED = 20260709

QUANT_VARIANTS = ["quant_score", "quant_score_with_macro", "quant_score_with_fred", "quant_score_with_macro_fred"]


def weight_grid(step: float) -> np.ndarray:
    n = round(1.0 / step)
    combos = []
    for a in range(n + 1):
        for b in range(n + 1 - a):
            for c in range(n + 1 - a - b):
                d = n - a - b - c
                combos.append((a * step, b * step, c * step, d * step))
    return np.array(combos, dtype=float)  # [nw,4] each row sums to 1.0


def load_pooled():
    """Reuse the production loader; also pull the alternative quant variants from
    each quant payload so we can ablate the Fed / macro-numeric sub-components."""
    docs = []
    for issuer in ALL_ISSUERS:
        for outcome, doc in build_documents_for_issuer(
            issuer, DEFAULT_WINDOW_TRADING_DAYS, OUTCOME_UPPER_DEFAULT, OUTCOME_LOWER_DEFAULT
        ):
            qpayload = quant_layer.get_quant_score(issuer, doc.document_id)
            qmetrics = (qpayload or {}).get("quant_metrics", {})
            docs.append({
                "document_id": doc.document_id,
                "issuer": issuer,
                "label": doc.outcome_label,
                "micro": doc.micro_score,
                "macro": doc.macro_score,
                "news": doc.news_score,
                "quant_variants": {v: qmetrics.get(v) for v in QUANT_VARIANTS},
            })
    return docs


def build_layer_matrices(docs, quant_variant):
    """S [ndoc,4] layer scores (0 where missing), M [ndoc,4] presence mask (1/0),
    order = micro, macro, news, quant."""
    n = len(docs)
    S = np.zeros((n, 4))
    M = np.zeros((n, 4))
    for i, d in enumerate(docs):
        for j, key in enumerate(("micro", "macro", "news")):
            v = d[key]
            if v is not None:
                S[i, j] = v; M[i, j] = 1.0
        qv = d["quant_variants"].get(quant_variant)
        if qv is not None:
            S[i, 3] = qv; M[i, 3] = 1.0
    return S, M


def correctness_tensor(S, M, W, labels_idx):
    """Return C [ncombo, ndoc] uint8 correctness and a combo index -> (weights, hu, hl) map.
    Blend uses the same missing-layer redistribution as blend.blend_scores."""
    num = W @ S.T                      # [nw,ndoc]
    den = W @ M.T                      # [nw,ndoc]
    den = np.where(den == 0, np.nan, den)
    blended = num / den                # [nw,ndoc]; NaN only if a doc has zero total weight
    nw, ndoc = blended.shape

    combos_meta = []
    C_blocks = []
    for hu in THRESH_UPPER:
        for hl in THRESH_LOWER:
            pred = np.full((nw, ndoc), LABEL_IDX["HOLD"], dtype=np.int8)
            pred[blended > hu] = LABEL_IDX["BUY"]
            pred[blended < hl] = LABEL_IDX["SELL"]
            correct = (pred == labels_idx[None, :]).astype(np.uint8)
            # a doc with no usable weight (blended NaN) is scored wrong for that combo
            correct[np.isnan(blended)] = 0
            C_blocks.append(correct)
            for wi in range(nw):
                combos_meta.append((wi, hu, hl))
    C = np.concatenate(C_blocks, axis=0)  # [ncombo, ndoc]
    return C, combos_meta


def dist_from_default(w, hu, hl):
    return sum(abs(a - b) for a, b in zip(w, DEFAULT_WEIGHTS)) + abs(hu - DEFAULT_HOLD_UPPER) + abs(hl - DEFAULT_HOLD_LOWER)


def evaluate_variant(docs, quant_variant, W):
    labels_idx = np.array([LABEL_IDX[d["label"]] for d in docs])
    S, M = build_layer_matrices(docs, quant_variant)
    C, meta = correctness_tensor(S, M, W, labels_idx)     # [ncombo,ndoc]
    ncombo, ndoc = C.shape
    per_combo_correct = C.sum(axis=1)                     # [ncombo]

    # --- global best-fit (fit on all docs; tie-break toward the default config) ---
    best_acc = per_combo_correct.max()
    tied = np.where(per_combo_correct == best_acc)[0]
    best_ci = min(tied, key=lambda ci: dist_from_default(W[meta[ci][0]], meta[ci][1], meta[ci][2]))
    bw, bhu, bhl = W[meta[best_ci][0]], meta[best_ci][1], meta[best_ci][2]
    global_best = {
        "accuracy": round(best_acc / ndoc, 4),
        "weights": [round(x, 4) for x in bw.tolist()],
        "hold_upper": bhu, "hold_lower": bhl,
        "n_tied": int(len(tied)),
    }

    # --- LOOCV: for each held-out doc, best combo on the OTHER docs, tie-break to default ---
    default_ci = _default_combo_index(meta, W)
    loocv_tuned_correct = 0
    for i in range(ndoc):
        loo_correct = per_combo_correct - C[:, i]        # correct count without doc i
        m = loo_correct.max()
        tied_i = np.where(loo_correct == m)[0]
        ci = min(tied_i, key=lambda ci: dist_from_default(W[meta[ci][0]], meta[ci][1], meta[ci][2]))
        loocv_tuned_correct += int(C[ci, i])
    loocv_default_correct = int(C[default_ci].sum())

    return {
        "global_best": global_best,
        "loocv_tuned_accuracy": round(loocv_tuned_correct / ndoc, 4),
        "loocv_default_accuracy": round(loocv_default_correct / ndoc, 4),
        "default_correct_vector": C[default_ci].tolist(),
        "labels_idx": labels_idx.tolist(),
        "n": ndoc,
    }


def _default_combo_index(meta, W):
    # find the combo closest to (DEFAULT_WEIGHTS, DEFAULT_HOLD_UPPER, DEFAULT_HOLD_LOWER)
    best, best_d = 0, 1e9
    for ci, (wi, hu, hl) in enumerate(meta):
        d = dist_from_default(W[wi], hu, hl)
        if d < best_d:
            best_d, best = d, ci
    return best


def significance(default_correct_vector, labels_idx, seed=RNG_SEED, perms=PERMUTATIONS):
    """Test the DEFAULT (deployed) model's pooled accuracy against the
    majority-class baseline. Binomial (vs baseline rate) + label-permutation."""
    correct = np.array(default_correct_vector, dtype=np.uint8)
    labels = np.array(labels_idx)
    n = len(labels)
    acc = correct.mean()

    counts = np.bincount(labels, minlength=len(LABELS))
    majority_rate = counts.max() / n
    majority_label = LABELS[int(counts.argmax())]

    # binomial: P(Binom(n, majority_rate) >= observed_correct), one-sided
    k = int(correct.sum())
    from math import comb
    p_binom = sum(comb(n, j) * majority_rate**j * (1 - majority_rate)**(n - j) for j in range(k, n + 1))

    return {
        "accuracy": round(float(acc), 4),
        "n": int(n),
        "majority_label": majority_label,
        "majority_rate": round(float(majority_rate), 4),
        "binomial_p_vs_majority": round(float(p_binom), 5),
    }


def permutation_test(default_pred, labels, seed=RNG_SEED, perms=PERMUTATIONS):
    """Real permutation test: hold the model's predictions FIXED, shuffle the true
    labels `perms` times, and see how often the shuffled accuracy meets/exceeds the
    observed. p = fraction >= observed."""
    rng = np.random.default_rng(seed)
    obs = float((default_pred == labels).mean())
    ge = 0
    for _ in range(perms):
        ge += int((default_pred == rng.permutation(labels)).mean() >= obs)
    return round((ge + 1) / (perms + 1), 5)


def main() -> int:
    print("Loading pooled documents...")
    docs = load_pooled()
    W = weight_grid(WEIGHT_STEP)
    ncombo = W.shape[0] * len(THRESH_UPPER) * len(THRESH_LOWER)
    print(f"N={len(docs)} docs | weight grid={W.shape[0]} x thresholds={len(THRESH_UPPER)*len(THRESH_LOWER)} = {ncombo} combos/variant")

    variants = {}
    for v in QUANT_VARIANTS:
        variants[v] = evaluate_variant(docs, v, W)
        gb = variants[v]["global_best"]
        print(f"  [{v}] global_best acc={gb['accuracy']} w={gb['weights']} thr=({gb['hold_upper']},{gb['hold_lower']}) "
              f"| LOOCV tuned={variants[v]['loocv_tuned_accuracy']} default={variants[v]['loocv_default_accuracy']}")

    # significance on the primary (headline quant) default model
    primary = variants["quant_score"]
    labels_idx = np.array(primary["labels_idx"])
    # reconstruct default predictions from the default correctness vector is lossy;
    # recompute default predictions directly for a clean permutation test:
    default_pred = _default_predictions(docs)
    sig = significance(primary["default_correct_vector"], primary["labels_idx"])
    sig["permutation_p_vs_shuffled_labels"] = permutation_test(default_pred, labels_idx)
    sig["verdict"] = _verdict(sig)
    print(f"\nSignificance (default model): acc={sig['accuracy']} vs majority '{sig['majority_label']}'={sig['majority_rate']} "
          f"| binomial p={sig['binomial_p_vs_majority']} | permutation p={sig['permutation_p_vs_shuffled_labels']}")
    print(f"VERDICT: {sig['verdict']}")

    out = {
        "n_documents": len(docs),
        "weight_step": WEIGHT_STEP,
        "threshold_grid": {"upper": THRESH_UPPER, "lower": THRESH_LOWER, "asymmetric": True},
        "combos_per_variant": ncombo,
        "default_config": {"weights": list(DEFAULT_WEIGHTS), "hold_upper": DEFAULT_HOLD_UPPER, "hold_lower": DEFAULT_HOLD_LOWER},
        "variants": {v: {k: r[k] for k in ("global_best", "loocv_tuned_accuracy", "loocv_default_accuracy", "n")}
                     for v, r in variants.items()},
        "fed_ablation_note": (
            "Compare quant_score (plain) vs quant_score_with_fred / _with_macro / _with_macro_fred. "
            "If none lifts global_best or LOOCV accuracy over plain, the Fed/macro-numeric sub-components "
            "do not earn weight - a stable negative, consistent with macro/news at earlier N."
        ),
        "significance": sig,
    }
    summary_dir = OUTPUTS_DIR / "global" / "summary"
    summary_dir.mkdir(parents=True, exist_ok=True)
    path = summary_dir / "weight_threshold_sweep.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {path}")
    return 0


def _default_predictions(docs) -> np.ndarray:
    """Default-model (DEFAULT_WEIGHTS at DEFAULT thresholds) prediction per doc,
    using blend.blend_scores redistribution semantics."""
    from blend import blend_scores, derive_signal
    preds = []
    for d in docs:
        blended = blend_scores(d["micro"], d["macro"], d["news"], d["quant_variants"]["quant_score"], DEFAULT_WEIGHTS)
        preds.append(LABEL_IDX[derive_signal(blended, DEFAULT_HOLD_UPPER, DEFAULT_HOLD_LOWER)])
    return np.array(preds)


def _verdict(sig) -> str:
    p = max(sig["binomial_p_vs_majority"], sig["permutation_p_vs_shuffled_labels"])
    if p < 0.05:
        return (f"blend {sig['accuracy']} vs majority {sig['majority_rate']} - statistically significant "
                f"(binomial p={sig['binomial_p_vs_majority']}, permutation p={sig['permutation_p_vs_shuffled_labels']}) at N={sig['n']}")
    return (f"blend {sig['accuracy']} vs majority {sig['majority_rate']} - NOT distinguishable from noise "
            f"(binomial p={sig['binomial_p_vs_majority']}, permutation p={sig['permutation_p_vs_shuffled_labels']}) at N={sig['n']}")


if __name__ == "__main__":
    sys.exit(main())
