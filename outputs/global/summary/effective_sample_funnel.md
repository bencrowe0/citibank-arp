# Effective sample funnel

Date: 2026-08-12

## The funnel

| Step | N | Lost | Reason |
|---|---|---|---|
| Total events | 268 | | |
| After worksheet/SPOT exclusion | 242 | 26 | 25 worksheet contamination + 1 misattributed document |
| After timing exclusion | 229 | 13 | ALV.DE (1), AMKBY (4), LNVGY (4), LMT (4) — unknown or null timing |
| LLM called BUY or SELL | 142 | 87 | Model said HOLD — no trade, no directional test |
| Overnight |return| > ±2% band | **67** | 75 | Return inside ±2% band — traded but ungraded ("bet on flat") |

**67 events carry every directional accuracy claim in the study.** The
directional accuracy of 67.2% (45/67) is computed on this base. Of the 75
events lost at the last step, 56 are pre_market reporters whose overnight gap
fell inside the ±2% band (see pre_market_power_gap.md), and 19 are
after_hours.

## Why "traded but ungraded" is a separate category

The grading convention uses the ±2% overnight band to classify outcomes as
BUY-correct, SELL-correct, or flat. When the model calls BUY or SELL but the
overnight return is inside ±2%, the event is **traded** (the model took a
position) but **ungraded** — the outcome is ambiguous and the event
contributes ~0 net P&L. These events are counted in mean-net-per-trade
calculations but not in directional accuracy.

The distinction matters because:
- **Accuracy** is computed on the 67 graded events only: 45 correct / 67 =
  67.2%.
- **Mean net per trade** is computed on all 142 traded events, including the
  75 flat bets, and is much lower because those 75 contribute approximately
  zero net each.

## By release timing

| | Pre_market | After_hours |
|---|---|---|
| Clean events | 132 | 97 |
| Traded | 80 | 62 |
| Graded (|ret| > 2%) | **24** | **43** |
| Flat (traded, |ret| ≤ 2%) | 56 | 19 |
| Graded share of traded | 30% | 69% |

The pre_market graded share is less than half the after_hours share. This is
the pre_market power gap: 70% of pre_market trades land inside the ±2% band
because the overnight gap captures only a fraction of the earnings reaction
for BMO reporters.

## The 75 ungraded trades carry a directional signal the metric discards

Of the 75 events where the model traded but the return fell inside the ±2%
band, **46 (61%) were directionally correct** — the sign of the return
matched the call. By timing: pre_market 36/56 (64%), after_hours 10/19 (53%).

This is above the 50% chance rate, suggesting the model has signal the
accuracy metric is discarding. However, sub-2% overnight moves are within
normal daily variation (median magnitude 0.61%, P75 1.17%), so a correct sign
there is weak evidence of skill. This figure is descriptive, not an accuracy
claim.

**Accuracy and P&L are computed on different samples** — 67 graded events for
accuracy, 142 traded events for mean net per trade. This is a cleaner
explanation of their divergence than the band alone: accuracy sees only the
extreme reactions (where the model looks good), while P&L sees every trade
including the 75 flat bets that contribute ~0% net each.

## Effective N must accompany every accuracy figure

Any accuracy figure quoted from this study rests on the 67 graded events (or
a subset thereof for arm/subgroup comparisons). This N must appear alongside
the figure. An accuracy of 70.8% on "24 directionally graded events" carries
a very different evidential weight than the same percentage on "132 events".

## Minimum detectable effect: the reader's guide to every figure

The minimum detectable effect (MDE) at this sample size determines what the
study can and cannot measure. This belongs in the methodology, not the
limitations, because it tells the reader how to interpret every result.

**Unpaired comparisons** (e.g. pre_market vs after_hours): MDE ≈ ±25pp
(two-proportion z-test, 80% power, α=0.10 one-sided, N=24 vs 43). Any
subgroup difference smaller than ~25pp is untestable, not absent.

**Paired comparisons** (e.g. section arm vs full bundle on the same events):
MDE ≈ ±12pp (McNemar/paired bootstrap, same power/alpha, N=119 paired
events). The within-event correlation eliminates between-event variance,
roughly halving the detectable effect. This is why Item C uses paired
differences.

**Agreement between arms** (on all scored events, no band filter): uses the
full N=119 and does not depend on the ±2% band. This may be the only
adequately powered comparison available for Item C if accuracy cannot
separate the arms.
