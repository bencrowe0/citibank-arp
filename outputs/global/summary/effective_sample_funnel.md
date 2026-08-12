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

## Effective N must accompany every accuracy figure

Any accuracy figure quoted from this study rests on the 67 graded events (or
a subset thereof for arm/subgroup comparisons). This N must appear alongside
the figure. An accuracy of 70.8% on "24 directionally graded events" carries
a very different evidential weight than the same percentage on "132 events".

## Subgroup results are underpowered, not null

The pre_market vs after_hours accuracy difference of +5.7pp (p=0.632) is
computed on 24 vs 43 events. At this sample size, the minimum detectable
effect (two-proportion z-test, 80% power, α=0.10 one-sided) is approximately
±25pp. Any subgroup difference smaller than ~25pp is untestable at this N,
not absent. This applies to every subgroup cut in the study, including
Item C's section ablation arms.
