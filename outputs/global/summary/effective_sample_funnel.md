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

## The measured cost of the pre-registered HOLD band

Of the 75 events where the model traded but the return fell inside the ±2%
band, **46 (61.3%) were directionally correct** — the sign of the return
matched the call.

| Group | Sign correct | N | Rate | 90% CI | Binomial p (H0: 50%) |
|---|---|---|---|---|---|
| All ungraded | 46 | 75 | 61.3% | [51.2%, 70.8%] | **0.064** |
| Pre_market | 36 | 56 | 64.3% | [52.5%, 74.9%] | **0.044** |
| After_hours | 10 | 19 | 52.6% | [32.0%, 72.6%] | 1.000 |

The band was fixed in advance to avoid grading noise, and it is doing that.
But it is also discarding events where the model was directionally right
significantly more often than chance (p=0.064 pooled, p=0.044 pre_market).
This is a limitation with a number attached rather than a generic caveat.

**The mechanism fits**: the discarded signal concentrates in pre_market at
64.3% against 52.6% after_hours — exactly where the band swallows most
events. A pre-market release is partly priced before the open, so the
direction survives while the magnitude is compressed below the band. This is
the same mechanism as the pre_market power gap (see `pre_market_power_gap.md`),
now visible from a second direction: the model reads the direction correctly,
but the overnight gap is too small to register it as a graded outcome.

The after_hours cell (10/19) is too small to say anything (p=1.0, CI spans
32-73%).

**Caveat**: median return magnitude is 0.61% and P75 is 1.17%, both within
normal daily variation. Any single correct sign is weak evidence. This is not
an accuracy claim and must not be combined with the graded accuracy figure.

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
