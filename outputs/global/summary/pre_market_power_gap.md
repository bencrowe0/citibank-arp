# Pre-market power gap: a named limitation

Date: 2026-08-12

## Finding

The overnight close-to-open gap is a lower-powered measure of the earnings
reaction for pre-market reporters than for after-hours reporters. This affects
132 of 229 clean events (58%).

## Mechanism

Pre-market reporters release results 1-3 hours before the exchange open. The
pre-market session prices the news partially, but the regular-session open
reflects only a fraction of the full repricing. The remainder is absorbed
during the trading session as the full analyst community reacts. The overnight
gap (prior close → release-date open) captures the pre-market fraction; the
close-to-close move captures both.

Across 136 pre_market events (including excluded ones):
- Mean |overnight gap|: 3.16%
- Mean |close-to-close|: 4.02%
- Ratio: 1.27x (close-to-close is 27% larger on average)
- The close-to-close move is larger in 60% of events

## Impact on grading

On the 229 clean events, graded against the pre-registered ±2% raw overnight
band:

| | Pre_market (N=132) | After_hours (N=97) |
|---|---|---|
| Inside ±2% band (graded HOLD) | **72.7%** (96/132) | **26.8%** (26/97) |
| Traded (BUY or SELL called) | 80 | 62 |
| Dir. accuracy (among traded) | 70.8% (17/24) | 65.1% (28/43) |
| Mean net per trade | +0.723% | +2.749% |
| Accuracy diff (bootstrap) | +5.7pp, 90% CI [-13.8%, +24.3%], p=0.632 |
| Net/trade diff (bootstrap) | -2.0pp, 90% CI [-3.9%, -0.1%], p=0.079 |

The pre_market group shows:
1. **3× the HOLD rate** (72.7% vs 26.8%) — the gap is too small to breach the
   ±2% band in most cases, so the model's directional calls are not tested.
2. **Higher directional accuracy but lower net per trade** — the 24 pre_market
   events that do breach the band are the largest reactions, biasing accuracy
   upward. But the mean net per trade is +0.723% vs +2.749% for after_hours,
   because most pre_market trades land inside the band and contribute ~0% net.
3. **The accuracy difference is not significant** (p=0.632) — the pre_market
   accuracy of 70.8% comes from a small denominator (24 directional events out
   of 132 total). The net/trade difference is marginally significant (p=0.079).

## Implication

The overnight gap convention grades pre_market reporters on a truncated
version of the earnings reaction. 72.7% of pre_market events produce a gap
inside the ±2% band and are graded HOLD regardless of the model's call —
they contribute nothing to accuracy and ~0 to net P&L. The effective sample
for directional testing is not 229 but roughly 229 - 96 = 133 traded events.

The 5-day horizon in `returns_matrix.csv` is available as a secondary check:
it captures the full multi-day repricing and has a wider implied HOLD band
(±3.38%) calibrated to the same HOLD share as the overnight band.

## The accuracy-versus-P&L divergence, now measured

The pre_market group shows 70.8% directional accuracy (on 24 graded events)
but only +0.723% mean net per trade, while after_hours shows 65.1% accuracy
(on 43 graded events) at +2.749% mean net per trade. This divergence was
previously recorded in the project as an observation; it is now explained by
the power gap:

The ±2% HOLD band rewards the lower-powered measure on accuracy (because only
the largest, most directionally obvious reactions breach the band — 24 out of
80 traded pre_market events — inflating the accuracy denominator with
easy-to-grade extremes) while penalising it on P&L (because the 56 flat
pre_market trades contribute ~0% net each, dragging the mean down). This is a
measurement artefact of the band interacting with the gap convention, not a
difference in the model's skill between BMO and AMC events.

## Pre-registered convention retained

The ±2% raw overnight band is pre-registered and stays. This limitation is
stated, not corrected.
