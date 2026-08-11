# Item E Handoff — Walk-Forward Validation

Status: **Not started. User go-ahead required before beginning.**

## Prerequisites (all must be resolved first)

1. **Anchor correction** — the `release_date` field per event (from EDGAR 8-K
   filing date) must be populated and the uniform entry rule applied before any
   grading can be trusted. Without this, the walk-forward windows would train and
   test on returns computed from the wrong entry for ~42 pre_market events.

2. **Timing map completion** — 9 non-US issuers + LMT (10 issuers, ~40 events)
   are unresolved. These must be either classified or excluded before the
   walk-forward can run on the full dataset.

3. **Worksheet leak decision** — 25 events pending re-score vs exclude. The
   walk-forward must know which events are in the universe.

4. **Task 5 (section ablation)** — independent of walk-forward but must complete
   first per the gap spec's sequencing.

5. **Item D (FinBERT baseline)** — independent, can run in parallel.

## Design notes from the gap spec (Item E)

- One function taking a training cutoff and test span, fitting HOLD thresholds
  only (not weights — PSR near zero at this N means weight search is unstable).
- Rolling: start at ~40% of events by report_date, step forward one calendar
  quarter, refit thresholds on training slice, score next quarter out of sample.
- Two-window headline: fit on events ≤ 2026-08-10, score events after. Currently
  empty (all 268 events predate the freeze) — path must exist and exit cleanly.
- Label everything "retrospective validation", never "pre-registered".
- Per-window log of fitted thresholds, training/test counts, trade counts.
  Assert loudly if any window's trade count collapses (threshold going degenerate).
- Report pooled OOS figures with bootstrap intervals alongside in-sample.

## Dependencies on tonight's work

- The `release_date` field and uniform entry rule directly affect the returns
  the walk-forward trains and tests on. If entry is wrong for pre_market events,
  threshold fitting on training slices will be biased.
- The timing map must be complete (or events excluded) so the walk-forward
  universe is well-defined.

## Timing

Item E is the longest remaining code item (3–4 days per the gap spec). Nothing
new starts after 25 August (writing week). User confirmation required before
beginning.

## Release timing map state (2026-08-11)

| Value | Count | Notes |
|---|---|---|
| `pre_market` | 30 | 29 confirmed + LMT set back to null (see below) |
| `after_hours` | 34 | All confirmed |
| `null` (non-US) | 9 | ALV.DE, BCS, LNVGY, MC.PA, AMKBY, NVO, PUM.DE, SIE.DE, STAN.L |
| `null` (LMT) | 1 | 8-K acceptance 11:31–12:25 ET = mid-session, needs manual check |

LMT was initially classified pre_market based on unnamed "public calendars". All
4 events had 8-K acceptance times during market hours. Set back to null pending
manual verification of the actual press release timestamp.

Price cross-check (audits the map, does not build it): 31/58 pre_market events
show |open_gap| > |overnight|. Disagreements are explained by `report_date`
inconsistency (some manifests use eve-of-earnings, others use morning-of). The
fix is a factual `release_date` per event from the 8-K filing date, not
price-based per-event classification.
