# Surviving findings after all corrections

Date: 2026-08-13

Six corrections have been applied: stale entry anchor (4 retracted findings),
wrong baseline comparator, and the direction decomposition retraction
(tautological, not a finding). This document lists every result that stands.

## 1. Rank correlation with monotonic decay (strongest)

**Statistic**: Spearman rho = 0.236, p = 0.0003, on all 233 clean events.
Decays monotonically: 0.159 (1d, p=0.015), 0.112 (3d, p=0.089), 0.072
(5d, p=0.276), 0.058 (10d, p=0.380). Bootstrap CI on mean net per trade
crosses zero by 3 days.

**Threshold-dependent?** No. Rho uses the continuous blended score and the
continuous return. No band, no BUY/SELL/HOLD split, no grading threshold.

**Why corrections did not touch it**: rho does not depend on the entry
convention (it uses the same returns_matrix as everything else, which was
rebuilt on the corrected anchor) but it was recomputed on the corrected
matrix and improved from 0.221 to 0.236. It is not sensitive to the HOLD
threshold because it uses all 233 events, not just traded ones.

## 2. Selectivity accuracy (qualified)

**Statistic**: 62/95 = 65.3%, vs 54.7% majority-direction floor,
margin +10.5pp, p=0.024. MDE = ±10.8pp (barely powered to detect).

**Must always be paired with the coverage figure**: 62/147 = 42.2% under
HOLD=wrong, 12.2pp below the 54.4% floor.

**Threshold-dependent?** Yes. The HOLD thresholds (+0.25/-0.05) determine
which 95 of 233 events are graded. Those thresholds were selected by
optimising compounded total return on the full dataset (in-sample,
PSR=0.0). The 95-event denominator is itself a product of in-sample
threshold selection. Item E (walk-forward with out-of-sample threshold
refitting) is therefore the load-bearing robustness test, not a
supplementary one.

**Fragility statement**: the margin is significant but sits at the
detection limit. A modestly smaller true effect would have been
undetectable at N=95.

## 3. Item C: section ablation token ratio

**Statistic**: press release at ~13k tokens achieves 63.3% accuracy
(HOLD-excluded, on its own graded set) vs full bundle at ~30k tokens at
67.7%. Cost per correct call: $0.017 (PR) vs $0.027 (full). Full bundle
wins 6.8pp on the inclusive paired test (p=0.055), driven by 17 events
the PR passes on. Prepared remarks agrees with full bundle on 85.7% of
signals at ~10k tokens.

**Threshold-dependent?** The accuracy figures are threshold-dependent
(same qualification as #2). The token ratio and cost per correct call are
not — they are properties of the documents, not the grading convention.

**Why corrections did not touch it**: Item C was scored and graded on the
corrected returns_matrix. The model version (deepseek-v4-flash) matches
the deployed runs.

## 4. Kappa near-independence (human vs model)

**Statistic**: Cohen's kappa = 0.107, 90% CI [0.027, 0.188]. The human
and LLM arms are close to independent — their directional calls share
barely more structure than two independent classifiers with their
marginals (human BUY 55.7%, LLM BUY 24.0%).

**Threshold-dependent?** No. Kappa compares the BUY/HOLD/SELL calls
directly, not graded outcomes.

**Why corrections did not touch it**: kappa depends on the calls, not the
returns. It was recomputed on the corrected exclusion set (0.107, down
from 0.113 on the stale set) but the change is within the CI.

## 5. Direction-only comparison (human vs model)

**Statistic**: on 76 events where both arms committed, human 57.9%
(44/76) vs LLM 60.5% (46/76), diff +2.6pp, p=0.754. Neither detectably
better. Both above 50% (human: 50.9% BUY at p=0.500, SELL 73.9% at
p=0.017 vs 50%; LLM: BUY 55.6% at p=0.309, SELL 65.0% at p=0.040 vs
50%). Against the overall base rates (43.4% positive, 56.6% negative):
human BUY +7.5pp (p=0.167), human SELL +17.3pp (p=0.069); LLM BUY
+12.1pp (p=0.097), LLM SELL +8.4pp (p=0.181).

**Threshold-dependent?** No. Uses sign accuracy, no band.

**Retracted sub-finding**: the earlier claim that "per-direction accuracy
exactly equals the base rate" was tautological — the per-subset base
rate is the same number as the per-subset accuracy by construction.
The informative comparisons are vs 50% and vs the overall base rate,
and those show marginal evidence of skill in the SELL direction for
both arms (human p=0.017 vs 50%, p=0.069 vs overall neg rate; LLM
p=0.040 vs 50%, p=0.181 vs overall neg rate).

## 6. Supplementary re-score of 25 contaminated events

**Statistic**: 12/25 (48%) changed their directional call once the
worksheet was removed. Re-scored accuracy 66.7% (12/18 graded) resembles
the clean set (65.3%), corroborating the exclusion.

**Threshold-dependent?** Yes (grading uses the HOLD threshold).

## 7. Dev/eval split (directional evidence, not a result)

**Statistic**: dev accuracy 52.6% (10/19), eval 68.4% (52/76). The model
performs better on later events — opposite of overfitting. Eval margin
+14.5pp vs floor (p=0.007). Dev too small (MDE=±24.1pp).

**Not a result**: the difference is not significant (p=0.229). It is
directional evidence that Item E will test properly.

## What did not survive

1. 72.7% band capture → 42.4% (anchor artefact)
2. 61% sign-correct p=0.064 → 56% p=0.480 (anchor artefact)
3. PM 70.8% vs AH 65.1% accuracy divergence → vanished (anchor artefact)
4. +17.3pp agreement filter → -0.3pp (anchor artefact)
5. ~39% baseline → 54.7% majority-direction (comparator error)
6. "Zero per-direction margin" → tautological (not a finding)

## The threshold qualification, stated once

The deployed HOLD thresholds were selected by optimising compounded total
return — a metric the study no longer reports — on the full dataset the
study then scores. PSR=0.0, permutation p=0.150. The thresholds are not
pre-registered. The 95-event graded denominator is itself a product of
in-sample threshold selection.

**Every figure that depends on the HOLD threshold** (selectivity accuracy,
mean net per trade, the graded N, Item C per-arm accuracy) carries this
qualification. Item E is therefore the load-bearing robustness test: it
refits thresholds out of sample and is the only check on whether the
65.3% survives without in-sample selection.

**Rho (finding #1) does not depend on the threshold** and is the only
headline that is clean of this qualification.
