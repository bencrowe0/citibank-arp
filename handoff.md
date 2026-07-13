# Handoff

## Goal
Exceed the HOLD/FLAT-majority baseline on the group sheet's **overnight** stock-direction prediction, by legitimate means only (no leakage, no overfitting, pooled across all 6 issuers - no per-company/per-quarter carve-outs).

## Current State
Resolved. Two-part answer, both parts documented in `CLAUDE.md` Round 7.

**Part 1 - the group sheet's true ground truth was pinned down.** The shared Google Sheet's direction formula (`IF(L>Settings!$B$3/100,"UP",IF(L<-Settings!$B$3/100,"DOWN","FLAT"))`) reveals the "overnight move" is a **close-to-OPEN gap**: `(Next Day Open - Prior Close)/Prior Close`, where Prior Close = Close on `report_date` and Next Day Open = Open the next session - exactly `export_sheet_rows.fetch_prices`. This dissolves Round 6's BMO/AMC blocker (the sheet just uses report-date Close -> next-day Open for everyone). The direction threshold is `Settings!B3 = 2%` (integer-tunable). Implemented as a first-class option: `eval/outcomes.fetch_forward_return(exit_on_open=True)`, threaded through to the sweep via `--exit-on-open`.

**Part 2 - raw accuracy provably can't beat the majority baseline; balanced accuracy is the right metric and it wins.** At B3=2 the labels are 19 SELL / 90 FLAT / 22 BUY -> always-FLAT baseline 0.687. Raw accuracy can't clear it (confirmed 4 ways: default 0.550, LOOCV 0.634, widened-grid LOOCV 0.618, no-holdout best 0.657-0.702; signal-strength analysis shows beating 0.687 needs predictor-gap r≈0.45 but the best layer is r≈0.22). No integer B3 gives an honest win. Tuning B3 to the model = label-fitting leakage (refused). **The legitimate win (chosen with the user): balanced accuracy vs the fixed 1/3 floor.** A skew-aware, LOOCV-honest, pooled model scores **balanced accuracy 0.498 vs 0.333 floor, permutation p=0.0012 -> significant**. Selected weights are news-heavy (~0.7), confirming overnight gap is a surprise-vs-expectations phenomenon (micro was tuned for guidance-change, corr with gap only +0.22; news corr +0.22).

## Files in Flight (uncommitted)
- `eval/outcomes.py` - added `exit_on_open` param to `fetch_forward_return` + `collect_outcomes_for_issuer` (close-to-open gap exit price); docstring updated.
- `eval/run_eval.py` - `build_documents_for_issuer` takes/threads `exit_on_open`.
- `experiments/weight_threshold_sweep.py` - `--exit-on-open` flag; `load_pooled(exit_on_open=...)`; `correctness_tensor` now also returns the predictions tensor `P`; `evaluate_variant` returns `loocv_tuned_pred`; `significance_balanced` block now reports BOTH the default- and LOOCV-tuned-model balanced accuracy + permutation p, with the headline keyed to `--optimize-metric`; output filename gains `_gap` suffix when `--exit-on-open`.
- `outputs/global/summary/weight_threshold_sweep_window1_gap_bal.json` - **the headline artifact** (overnight gap, B3=2, balanced accuracy). `significance_balanced.verdict`: "LOOCV-tuned skew-aware balanced_accuracy 0.4979 vs floor 0.3333 - BEATS ... p=0.0012".
- `outputs/global/summary/weight_threshold_sweep.json` - 5-day production artifact, regenerated additively (+29 insertions, 0 deletions; every pre-existing number unchanged - verified).
- `CLAUDE.md` - new Round 7 section + rewritten overnight known-limitations bullet.
- `outputs/global/summary/window1_forward_returns.csv` - by-product (per-doc 1-day close-to-close returns), harmless.

## Superseded
Round 6's `weight_threshold_sweep_window1.json` / `_window1_bal.json` are the close-to-CLOSE approximation; left on disk but no longer the "overnight" answer - the close-to-OPEN gap (`_window1_gap_bal.json`) is the group's real ground truth.

## Failed / rejected this session (all honest negatives)
- Vol-scaled outcome threshold (±1.34% at 1-day close-to-close): tried; the default model beat that window's baseline (0.4427 vs 0.3817) but this was the close-to-close approximation, superseded by Part 1.
- Widening the hold-threshold grid (skew-aware, to ±0.9 asymmetric): in-sample hits 0.702 but LOOCV collapses to 0.618 - overfits, doesn't beat 0.687.
- News/transcript backfill: **gated out before spending budget.** The signal-strength (r) analysis showed even a perfect added news layer (itself r≈0.22) can't lift the combined predictor to the r≈0.45 needed to beat 0.687 on raw accuracy. Not attempted - the data says it wouldn't clear the bar.
- Tuning `Settings!B3` to make the model win: refused as label-definition leakage.

## Next Step
Nothing blocking. If continuing: **commit** the uncommitted changes above on branch `task/task`. Optionally re-derive `Settings!B3` from the sheet's human-rated rows to double-check it's 2 (the discrepancy report flags a couple of internally-inconsistent human direction entries). If the group ever wants raw-accuracy-beats-majority specifically, the only honest lever is a materially stronger signal source (not news/quant as they stand) or a binary move/no-move reframe of the task - both are group decisions, not modelling tweaks.
