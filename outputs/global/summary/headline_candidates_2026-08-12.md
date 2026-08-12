# Headline candidates — corrected figures, ranked by robustness

Date: 2026-08-12 (release_date anchor, N=233)

## 1. Rank correlation: rho = 0.236, p = 0.0003

**Definition**: Spearman rank correlation between the blended score
(micro 0.55 + macro 0.45) and the raw overnight return, computed on
all 233 clean events (not just traded or graded).

**Why strongest**: uses the full N with no band filter, no trade/HOLD
split, and no grading threshold. The p-value is the most significant
single result in the study. It survived the anchor correction (was
0.221 on the old anchor, improved to 0.236 on the corrected one).

**What it means**: the model's sentiment score is positively associated
with the direction and magnitude of the overnight stock move. Higher
scores predict higher returns, across the full range.

## 2. Monotonic decay curve: overnight signal does not persist

**Definition**: mean net per trade at each horizon (overnight, 1d, 3d,
5d, 10d) for the 146 traded events, with the pre-registered ±2% band
on overnight and recalibrated bands on longer horizons.

| Horizon | Mean net/trade | 95% CI | Rho | p(rho) |
|---|---|---|---|---|
| overnight | +1.86% | [+0.98, +2.81] | 0.236 | 0.0003 |
| 1d | +1.21% | [+0.27, +2.19] | 0.153 | 0.021 |
| 3d | +0.99% | [-0.04, +2.05] | 0.106 | 0.111 |
| 5d | +0.86% | [-0.25, +2.02] | 0.072 | 0.279 |
| 10d | +0.66% | [-0.69, +2.04] | 0.051 | 0.439 |

**Why robust**: every metric (mean net, accuracy, rho) decays
monotonically. This validates the overnight window as a measured choice
rather than a convenient assumption. The signal does not persist beyond
1 day (CI crosses zero by 3d).

## 3. Directional accuracy: 65.3% on 95 graded events

**Definition**: correct-direction rate among traded events whose
overnight return exceeds the pre-registered ±2% band. 62/95 = 65.3%.
Mean net per trade: +1.862% on 146 traded events. Summed total:
+271.81% across 146 independent equal-sized trades. t = 3.43
(mean net is 3.4 standard errors above zero).

**Why less robust than rho**: accuracy depends on the ±2% band
(which determines graded N), the trade/HOLD split, and the
release_date anchor. All of these are defensible but each adds a
degree of freedom the rho figure does not require.

## 4. Paired-subset accuracy: ~69% against majority-class ~42.5%

**Definition**: LLM correct-direction accuracy on the subset of events
that have both a human and an LLM score (section=All,
first_rater_for_event=YES, 167 clean paired rows, 55 traded+graded).
Agree 69.0% (20/29), disagree 69.2% (18/26), pooled ~69%.

**Why it matters**: this replaces the retracted agreement filter. The
model reads earnings documents well above the majority-class baseline
regardless of whether the human arm concurs. The agreement filter
(0.561/0.429, then +17.3pp) was an artefact; the underlying accuracy
is the real finding.

**Why weakest as a headline**: small graded N (55 events), and the
paired subset is not representative (covers only companies where both
arms scored the same quarter).

## Summary

| Candidate | Statistic | N | p-value |
|---|---|---|---|
| Rank correlation | rho = 0.236 | 233 | 0.0003 |
| Decay validates window | CI crosses zero by 3d | 146 traded | — |
| Directional accuracy | 65.3% (62/95) | 95 graded | implied by t=3.43 |
| Paired-subset accuracy | ~69% vs ~42.5% baseline | 55 graded | — |

The strongest headline is rho = 0.236 (p = 0.0003), because it uses the
full sample, requires no threshold, and survived the anchor correction.
The decay curve is the strongest methodological validation. Directional
accuracy is the most intuitive metric but rests on the most assumptions.
