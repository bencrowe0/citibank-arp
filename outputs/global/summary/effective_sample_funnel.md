# Effective sample funnel

Date: 2026-08-12 (corrected on release_date anchor)

## The funnel

| Step | N | Lost | Reason |
|---|---|---|---|
| Total events | 268 | | |
| After worksheet/SPOT exclusion | 242 | 26 | 25 worksheet contamination + 1 misattributed document |
| After timing exclusion | 229 | 13 | ALV.DE (1), AMKBY (4), LNVGY (4), LMT (4) — unknown or null timing |
| LLM called BUY or SELL | 142 | 87 | Model said HOLD — no trade, no directional test |
| Overnight |return| > ±2% band | **92** | 50 | Return inside ±2% band — traded but ungraded ("bet on flat") |

**92 events carry every directional accuracy claim in the study.** The
directional accuracy of 65.2% (60/92) is computed on this base. Of the 50
events lost at the last step, 32 are pre_market reporters and 18 are
after_hours.

**Superseded figure**: the earlier funnel showed 67 graded events (45/67 =
67.2% accuracy). That was computed on the stale report_date anchor, which
used post-announcement close as entry for 82 pre_market events, compressing
their overnight returns below the ±2% band. See
`retracted_findings_2026-08-12.md`.

## Why "traded but ungraded" is a separate category

The grading convention uses the ±2% overnight band to classify outcomes as
BUY-correct, SELL-correct, or flat. When the model calls BUY or SELL but the
overnight return is inside ±2%, the event is **traded** (the model took a
position) but **ungraded** — the outcome is ambiguous and the event
contributes ~0 net P&L. These events are counted in mean-net-per-trade
calculations but not in directional accuracy.

The distinction matters because:
- **Accuracy** is computed on the 92 graded events only: 60 correct / 92 =
  65.2%.
- **Mean net per trade** is computed on all 142 traded events, including the
  50 flat bets, and is +1.877%.

## By release timing

| | Pre_market | After_hours |
|---|---|---|
| Clean events | 132 | 97 |
| Traded | 80 | 62 |
| Inside ±2% band | 56 (42.4%) | 29 (29.9%) |
| Graded (|ret| > 2%) | **48** | **44** |
| Graded share of traded | 60% | 71% |

The pre_market graded share (60%) is lower than after_hours (71%) but no
longer the 3× asymmetry reported on the stale anchor (which showed 30% vs
69%). The corrected anchor resolves most of the pre_market power gap.

## The 50 ungraded trades

28 of 50 ungraded trades (56.0%) had the correct directional sign. This is
not significant (binomial p=0.480, 90% CI [43.4%, 68.0%]). The earlier figure
of 46/75 = 61.3% (p=0.064) was an artefact of the stale anchor — see
`retracted_findings_2026-08-12.md`.

## Minimum detectable effect: the reader's guide to every figure

The minimum detectable effect (MDE) at this sample size determines what the
study can and cannot measure. This belongs in the methodology, not the
limitations, because it tells the reader how to interpret every result.

**Unpaired comparisons** (e.g. pre_market vs after_hours): MDE ≈ ±20pp
(two-proportion z-test, 80% power, α=0.10 one-sided, N=48 vs 44). Any
subgroup difference smaller than ~20pp is untestable, not absent.

**Paired comparisons** (e.g. section arm vs full bundle on the same events):
MDE ≈ ±12pp (McNemar/paired bootstrap, same power/alpha, N=119 paired
events). The within-event correlation eliminates between-event variance,
roughly halving the detectable effect. This is why Item C uses paired
differences.

**Agreement between arms** (on all scored events, no band filter): uses the
full N=119 and does not depend on the ±2% band. This may be the only
adequately powered comparison available for Item C if accuracy cannot
separate the arms.

## Effective N must accompany every accuracy figure

Any accuracy figure quoted from this study rests on the 92 graded events (or
a subset thereof for arm/subgroup comparisons). This N must appear alongside
the figure.
