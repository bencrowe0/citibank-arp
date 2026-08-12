# Item E Handoff — Walk-Forward Validation

Status: **Not started. User go-ahead required before beginning.**

## Anchor correction (2026-08-12)

`release_date` (EDGAR 8-K filing date) is now the **sole entry anchor** for all
events. `report_date` is retained as a historical label (fiscal period identifier,
manifest key) but no longer drives the entry price. The uniform entry rule is:
- `pre_market` events: open on `release_date`
- `after_hours` events: open on the trading day after `release_date`

This correction affected ~42 pre_market events and is a prerequisite for any
walk-forward that trains on returns. Four findings from the old anchor are
retracted; see `retracted_findings_2026-08-12.md`.

## Exclusion set (N=233 clean universe)

35 events excluded from the graded universe:

| Reason | Count |
|---|---|
| Worksheet events (pending re-score decision) | 25 |
| SPOT (single-event outlier excluded by consensus) | 1 |
| Timing unresolved (9 non-US issuers) | 9 |
| **Total excluded** | **35** |

Remaining: **233 clean events**, of which **146 are traded** (BUY or SELL signal)
and **95 are graded** (traded + outcome resolved).

LMT was initially set to null pending manual verification, then resolved as
`pre_market` (press release confirmed pre-open) and **recovered into N=233**.
LMT cannot join Item C (section ablation) because its documents were not
bundled into the section-level variant set.

## Corrected performance figures (post anchor correction, N=233)

These supersede all figures quoted before 2026-08-12.

| Metric | Value |
|---|---|
| Clean events | 233 |
| Traded | 146 |
| Graded (traded + resolved) | 95 |
| Accuracy (graded) | **65.3%** (62/95) |
| Majority-direction floor (graded) | 54.7% (always-DOWN, 52/95) |
| Mean net per trade | **+1.862%** |
| Summed total return (146 trades) | **+271.81%** |
| t-statistic (mean / pstdev × √N, N=146) | **3.43** |
| Info ratio per trade | **0.284** |
| Spearman rho (overnight, all 233 events) | **0.236** |
| Spearman p-value | **0.0003** |

Note: the "t = 3.43" figure is a t-statistic computed as
`mean_net / pstdev(nets) * sqrt(N_traded)`, not a Sharpe ratio. Do not label
it Sharpe in any write-up.

## What Items B and C concluded

### Item B — horizon decay

Monotonic decay from overnight to 10-day window. The bootstrap CI crosses zero
by day 3. This validates the overnight window as the correct primary horizon and
supports using it as the walk-forward's test metric.

### Item C — section ablation (document composition)

Full bundle marginally outperforms press-release-only on signal accuracy
(6.8 pp gap, p = 0.055 — not significant at 0.05 but directionally consistent).
Full bundle costs approximately 2.3× the tokens of press-release-only.

Cost-efficiency framing:
- Press release only: **$0.017 per correct prediction**
- Full bundle: **$0.027 per correct prediction**

Prepared remarks agrees with the full bundle on **85.7%** of signals — the
marginal contribution of adding the transcript/Q&A is small. Report as a
borderline, cost-efficiency-unfavourable result for full bundle, not a clean win.

LMT cannot join Item C (see Exclusion set above).

## Human comparison

Direction-only comparison on **76 events** (events where a human rater
submitted a direction):

| Rater | Accuracy | N |
|---|---|---|
| Human | 57.9% | 76 |
| LLM | 60.5% | 76 |
| Always-BUY baseline | 43.4% | 76 |

Gap: +2.6 pp in favour of LLM. **Not significant** (p = 0.754). Both beat the
always-BUY baseline. Do not claim LLM superiority from this result.

## Recalibrated longer-horizon bands

Longer-horizon (3d, 5d, 10d) bands were recalibrated after the anchor
correction. These are **secondary and not pre-registered** — they exist for
descriptive completeness only. The overnight window remains the primary
pre-registered metric.

## Retracted findings

Four findings from the pre-anchor-correction analysis are formally retracted.
See `outputs/global/summary/retracted_findings_2026-08-12.md` for the full
list with original values and the reason each was retracted.

## Threshold selection criterion (critical for Item E)

The deployed thresholds `hold_upper=+0.25` / `hold_lower=-0.05` were selected
by `experiments/phase2_pnl_weight_threshold_sweep.py`, objective = **total
return** (in-sample), from a 113,344-combo grid. The sweep measured PSR=0.0
and permutation p=0.150 — the combo **failed the project's own overfitting
checks** and was promoted on 2026-08-05 by explicit user decision overriding
the validity gates.

**Not pre-registered.** All events were scored before the sweep was run.
The freeze note (`ext1_freeze_note.md`, dated 2026-08-10) is explicitly
labelled "retrospective not pre-registered".

`-0.05` is the minimum value of the `THRESH_LOWER` grid (0.05 step), not
a principled choice. The sweep found the least-aggressive lower threshold
maximised in-sample total return.

**Consequence**: the deployed HOLD thresholds were selected by optimising a
metric the study no longer reports (compounded total return, retired as
order-dependent), on data the study then scores (in-sample, all events
seen). The 95-event graded denominator is itself a product of in-sample
threshold selection. Every figure that depends on the HOLD threshold
(selectivity accuracy 65.3%, mean net per trade, graded N) carries this
qualification.

**Item E is therefore the load-bearing robustness test, not a supplementary
one.** Refitting thresholds out of sample is the only check on whether the
65.3% survives without in-sample selection. The only headline that is clean
of this qualification is rho = 0.236 (p = 0.0003), which does not depend
on the threshold.

**Item E must refit thresholds on training slices using the same criterion
(total return) that the deployed thresholds were chosen by.** If a different
criterion is used, state it explicitly and note the divergence. Note that
the original criterion was itself the compounded total return, which is
order-dependent — Item E should use the summed total return instead, and
record the change.

## Baseline correction (2026-08-13)

The correct naive floor for FLAT-excluded accuracy is the majority direction
among graded events: **always-DOWN = 54.7% (52/95)**. The previously used
~39% was always-BUY on all events including HOLDs — wrong denominator.

**Both accuracy framings, always reported together:**
- Selectivity: 62/95 = 65.3% (model traded + |ret|>2%). Above 54.7% floor,
  +10.5pp, p=0.024 — significant but at the detection limit (MDE=±10.8pp).
- Coverage: 62/147 = 42.2% (all |ret|>2%). Below 54.4% floor by 12.2pp.

**Direction-only decomposition**: on 76 paired events where both arms
committed, each arm's per-direction accuracy exactly equals the base rate in
its self-selected subset. Zero per-direction margin. Overall sign accuracy
comes from BUY/SELL allocation matching the sample's SELL skew, not from
document reading. See `direction_accuracy_decomposition.md`.

**Dev/eval split (directional evidence for Item E)**: dev accuracy 52.6%
(10/19), eval 68.4% (52/76). The model performs better on later events —
opposite of overfitting. Eval margin +14.5pp vs floor (p=0.007). Dev too
small (MDE=±24.1pp). This is the finding Item E exists to test properly.

## Item D (FinBERT baseline) — complete

Frontier on eval split (119 graded, HOLD=wrong convention):
- Majority-direction: 55.0%
- Deployed model: 43.3% (below floor under HOLD=wrong)
- FinBERT: 34.5%
- Loughran-McDonald: 15.1%

FinBERT narrows the gap to the model (34.5% vs 15.1% for LM) but the model's
advantage is real (8.4pp, non-overlapping CIs). The model's differentiation
is structured output and evidence quotes, not raw accuracy dominance.

## Prerequisites for Item E (walk-forward)

All anchor-correction and exclusion-set work above is now complete. Remaining
prerequisites before Item E can begin:

1. **Task 5 (section ablation)** — completed (Item C above). Unblocked.
2. **Item D (FinBERT baseline)** — independent, can run in parallel with Item E.
3. **User go-ahead** — Item E is the longest remaining code item (3–4 days per
   the gap spec). Nothing new starts after 25 August (writing week).

## Design notes from the gap spec (Item E)

- One function taking a training cutoff and test span, fitting HOLD thresholds
  only (not weights — PSR near zero at this N means weight search is unstable).
- Rolling: start at ~40% of events by `release_date`, step forward one calendar
  quarter, refit thresholds on training slice, score next quarter out of sample.
- Two-window headline: fit on events ≤ 2026-08-10, score events after. Currently
  empty (all 233 clean events predate the freeze) — path must exist and exit
  cleanly.
- Label everything "retrospective validation", never "pre-registered".
- Per-window log of fitted thresholds, training/test counts, trade counts.
  Assert loudly if any window's trade count collapses (threshold going degenerate).
- Report pooled OOS figures with bootstrap intervals alongside in-sample.
- Entry prices must use `release_date` (not `report_date`) consistent with the
  anchor correction above.

## Release timing map state (2026-08-12, post correction)

| Value | Count | Notes |
|---|---|---|
| `pre_market` | 31 | 30 confirmed + LMT resolved pre_market, recovered into N=233 |
| `after_hours` | 34 | All confirmed |
| `null` (non-US, excluded) | 9 | ALV.DE, BCS, LNVGY, MC.PA, AMKBY, NVO, PUM.DE, SIE.DE, STAN.L |
