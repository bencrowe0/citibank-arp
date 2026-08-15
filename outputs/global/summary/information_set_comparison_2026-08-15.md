# Information Set Comparison: Human Arm vs Model Arm
**Generated:** 2026-08-15  
**Sources:** `data/workbook/Master_Data_CORRECTED_2026-08-14.xlsx` (Human_Data_Entry); `outputs/global/summary/section_ablation_summary.csv` (model Set A, run 20260812T131110Z); `outputs/global/summary/section_ablation_extension_summary.csv` (model Set B, run 20260813T234207Z); `outputs/global/summary/section_ablation_paired_diffs.csv`; `outputs/global/summary/section_ablation_cost_per_correct.csv`

---

## 1. Background: Item C Model Finding

Item C (section ablation) ran the model against four section arms on two event sets:

**Set A (N=119 events, four-arm):**

| Arm | Events | Trades | Correct | Selectivity accuracy |
|---|---|---|---|---|
| full_bundle | 119 | 87 | 32 | 36.8% |
| press_release | 119 | 66 | 24 | 36.4% |
| prepared_remarks | 119 | 77 | 26 | 33.8% |
| qa_only | 119 | 67 | 26 | 38.8% |

**Set B (N=56 events, four-arm, extension):**

| Arm | Events | Trades | Correct | Selectivity accuracy |
|---|---|---|---|---|
| full_bundle | 56 | 28 | 10 | 35.7% |
| press_release | 56 | 14 | 5 | 35.7% |
| prepared_remarks | 56 | 29 | 11 | 37.9% |
| qa_only | 56 | 25 | 8 | 32.0% |

*Selectivity accuracy = correct / all BUY+SELL calls, including calls where outcome fell within the ±2% flat band. Grading: pre-registered ±2% raw overnight return.*

Across both event sets, the accuracy range across arms is 5pp in Set A (33.8%–38.8%) and 5.9pp in Set B (32.0%–37.9%). Paired bootstrap confidence intervals on the arm differences versus full_bundle are wide: the inclusive paired test on Set A (N=66 pairs) gives a CI of [−12.1pp, −1.5pp] for press_release versus full_bundle at p=0.055, and Set B extension paired tests give CIs of [0, 13.6pp] for prepared_remarks and [0, 15.8pp] for qa_only (both p>0.72). The paired MDE is approximately ±12pp as stated in `section_ablation_paired_diffs.csv`. The key finding in the strict paired test (both arms breach the ±2% band, N=45 pairs): the arms agree on every single event — the accuracy difference lives entirely in whether an arm commits to a trade at all, not in how it scores events it does trade.

Cost variation: prepared_remarks costs $0.021 per correct call versus $0.036 for full_bundle on Set A (42% reduction); press_release costs $0.023 per correct call (36% reduction). Mean tokens per call: full_bundle 30,096; press_release 13,030; prepared_remarks 10,287; qa_only 13,163. Source: `section_ablation_cost_per_correct.csv`.

**Model arm conclusion:** accuracy differences across arms fall within the paired MDE of ±12pp; the model's signal is essentially arm-invariant conditional on committing to a trade.

---

## 2. Counts per Information Set (Human Arm)

The human arm has 420 rows across seven information sets. Note that section-level reads (all rows except "full") are a separate experiment from full-document reads: they cover different events, different reading sessions, and were not paired against full-document reads of the same event by the same rater.

| Information set | n_readings | % of total |
|---|---|---|
| full | 190 | 45.2% |
| transcript only | 94 | 22.4% |
| financials | 32 | 7.6% |
| qanda | 33 | 7.9% |
| guidance | 29 | 6.9% |
| presentation only | 23 | 5.5% |
| press release document only | 19 | 4.5% |
| **Total** | **420** | **100%** |

The six section-level sets together total 230 rows, versus 190 rows for full-document reads.

---

## 3. Reading Time by Information Set

Returns used for the "actual return" in all calculations are the re-priced (release-date-anchored) values where available (295 of 420 rows corrected on 2026-08-13); the remaining 125 rows use the original human-typed prices.

| Information set | n | Mean (mins) | Median (mins) | Total (mins) |
|---|---|---|---|---|
| full | 190 | 29.8 | 25.0 | 5,668 |
| transcript only | 94 | **33.5** | 30.0 | 3,145 |
| qanda | 33 | 29.4 | 30.0 | 971 |
| financials | 32 | 20.3 | 21.5 | 651 |
| presentation only | 23 | 19.8 | 22.0 | 456 |
| guidance | 29 | 18.7 | 20.0 | 542 |
| press release document only | 19 | **15.0** | 14.0 | 285 |

**Transcript-only anomaly:** Transcript-only reads averaged 33.5 minutes against 29.8 minutes for full-document reads, confirmed from the data. These figures match the numbers stated by the user. The direction is counter-intuitive: readers given only the transcript took longer on average than readers given the full bundle (press release + presentation + transcript). One plausible explanation is that the transcript is the longest single document in the bundle and readers working from it alone lack the press release's executive summary as an orientation anchor, requiring more time to navigate. However, the data do not record the reason, so this remains speculative.

Relationship to accuracy: transcript-only coverage accuracy (43.1%, n_graded=65) is marginally higher than full-document coverage accuracy (40.2%, n_graded=97). The accuracy pattern does not suggest any clear relationship to the time anomaly; both sets are within a few percentage points of each other and of the majority-class floor.

---

## 4. Accuracy by Information Set

Two accuracy definitions used throughout:

- **Coverage accuracy** = n_correct / n_graded, where n_graded = rows with |overnight return| > 2%, and n_correct = rows where the decision was BUY and outcome was UP (ret > 2%), or SELL and outcome was DOWN (ret < −2%). This measures accuracy over the subset of events that had a large enough move to grade.
- **Selectivity accuracy** = n_correct / n_calls, where n_calls = all BUY or SELL decisions (including events where the outcome fell within the ±2% flat band). This measures how often a human's non-HOLD calls were directionally correct on graded events.

The coverage_floor and selectivity_floor are the majority-class baselines: the fraction of the respective denominator made up by the more common of the two graded outcomes.

Suppression: coverage suppressed where n_graded < 10; selectivity suppressed where n_calls < 10. Both n_graded and n_calls exceed 10 for all seven information sets in this dataset.

### Coverage accuracy (correct / n_graded)

| Information set | n_graded | n_correct | Coverage accuracy | Majority floor |
|---|---|---|---|---|
| full | 97 | 39 | 40.2% | 56.7% |
| transcript only | 65 | 28 | 43.1% | 56.9% |
| financials | 21 | 7 | 33.3% | 61.9% |
| guidance | 20 | 3 | **15.0%** | 55.0% |
| qanda | 22 | 8 | 36.4% | 59.1% |
| presentation only | 14 | 9 | 64.3% | 57.1% |
| press release document only | 15 | 7 | 46.7% | 53.3% |

*Note: presentation only has n_graded=14 (borderline); interpret with caution. Guidance has n_graded=20 but the very low accuracy (15%) is notable — it is well below the majority-class floor of 55%.*

### Selectivity accuracy (correct / n_calls BUY+SELL)

| Information set | n_calls | n_correct | Selectivity accuracy | Majority floor |
|---|---|---|---|---|
| full | 136 | 39 | 28.7% | 56.6% |
| transcript only | 72 | 28 | 38.9% | 59.7% |
| financials | 24 | 7 | 29.2% | 58.3% |
| guidance | 21 | 3 | 14.3% | 57.1% |
| qanda | 20 | 8 | 40.0% | 65.0% |
| presentation only | 22 | 9 | 40.9% | 63.6% |
| press release document only | 11 | 7 | 63.6% | 63.6% |

*Note: press release document only has n_calls=11 (borderline); interpret with caution.*

All information sets fall below the majority-class floor on coverage accuracy (i.e., below the accuracy achievable by always picking the more common direction). On selectivity accuracy, the pattern is similar: all sets are well below their respective floors. This is consistent with the model arm finding.

---

## 5. Decision Mix by Information Set

| Information set | n | BUY% | HOLD% | SELL% |
|---|---|---|---|---|
| full | 190 | 59.5% | 28.4% | 12.1% |
| transcript only | 94 | 59.6% | 23.4% | 17.0% |
| financials | 32 | 53.1% | 25.0% | 21.9% |
| guidance | 29 | 51.7% | 27.6% | 20.7% |
| qanda | 33 | 36.4% | 39.4% | 24.2% |
| presentation only | 23 | 78.3% | 4.3% | 17.4% |
| press release document only | 19 | 36.8% | 42.1% | 21.1% |

The decision mix varies substantially. Presentation-only reads show a notably high BUY rate (78.3%) and almost no HOLD (4.3%), which may partly explain the higher nominal accuracy figures for that arm — presentations typically feature forward-looking language and growth narratives. Q&A-only and press release document only reads show higher HOLD rates and lower BUY rates than the full-document group.

---

## 6. Mean Net Per Trade

Mean net P&L per trade (BUY or SELL decisions only), after a 10bps round-trip cost assumption.

Suppression threshold: n_trades < 10. All seven sets exceed this threshold.

| Information set | n_trades | Mean net/trade |
|---|---|---|
| full | 136 | +0.011% |
| transcript only | 72 | +0.437% |
| financials | 24 | −1.085% |
| guidance | 21 | −3.943% |
| qanda | 20 | −0.476% |
| presentation only | 22 | +3.096% |
| press release document only | 11 | +5.553% |

The two highest mean-net figures (presentation only +3.1%, press release document only +5.6%) come from the two smallest sets (n=22 and n=11 trades respectively). These figures have wide sampling uncertainty and should not be interpreted as a reliable performance advantage. Guidance shows the worst mean net per trade (−3.9%) across 21 trades, consistent with its very low accuracy (14.3% coverage, 14.3% selectivity).

---

## 7. Mapping Human Information Sets to Model Arms

The human experiment tested seven information sets. The model arm tested four (full_bundle, press_release, prepared_remarks, qa_only). Direct mappings exist for three:

| Human information set | Model arm | Direct mapping? | Notes |
|---|---|---|---|
| full | full_bundle | Yes (approximate) | Human reads press release + presentation + transcript together; model full_bundle is the same concatenated bundle |
| transcript only | *(none)* | No | Model never ran a transcript-only arm; no comparable model result exists |
| qanda | qa_only | Yes (approximate) | Both restrict to Q&A section of the transcript |
| press release document only | press_release | Yes (approximate) | Both restrict to the press release document |
| financials | *(none)* | No | Mechanically infeasible for the model: the financial tables are embedded in the press release and would require targeted extraction; the model never isolated a financials-only arm |
| guidance | *(none)* | No | Mechanically infeasible: the model cannot isolate a guidance-section-only arm; guidance language is distributed across all documents |
| presentation only | *(none)* | No | Model never ran a presentation-only arm |

The model arm "prepared_remarks" (transcript prepared remarks, excluding Q&A) has no direct human equivalent.

**Critical caveat:** Human and model sessions cover different events, different tickers, and different time periods. The comparison below is of the *pattern* (whether accuracy differentiates across arms) not a direct head-to-head on the same events.

### Side-by-side for mapped pairs

The model accuracy figures are selectivity accuracy (correct / trades from the section ablation files, where flat outcomes count in the denominator). The human figures are selectivity accuracy (correct / n_calls BUY+SELL).

| Human information set | Human selectivity accuracy | Human n_calls | Model arm | Model selectivity (Set A) | Model n_trades (Set A) | Model selectivity (Set B) | Model n_trades (Set B) |
|---|---|---|---|---|---|---|---|
| full | 28.7% (39/136) | 136 | full_bundle | 36.8% (32/87) | 87 | 35.7% (10/28) | 28 |
| qanda | 40.0% (8/20) | 20 | qa_only | 38.8% (26/67) | 67 | 32.0% (8/25) | 25 |
| press release document only | 63.6% (7/11) | 11 | press_release | 36.4% (24/66) | 66 | 35.7% (5/14) | 14 |

*Event sets differ across all rows. n_calls=11 for press release document only is borderline.*

---

## 8. Does the Human Arm Show the Same Flatness?

**Model arm pattern:** Accuracy is approximately flat across all four arms in both event sets. The Set A range is 5pp (33.8%–38.8%); the Set B range is 5.9pp (32.0%–37.9%). Paired confidence intervals span roughly ±12pp, meaning a true difference of that size could not be distinguished from noise in these samples. The key structural finding is that when both arms commit to a trade on the same event, they commit identically — the between-arm difference is driven entirely by trade frequency, not directional signal quality.

**Human arm pattern:** The human arm shows a wider spread. On coverage accuracy, the range across the seven information sets is 49.3pp (15.0% for guidance to 64.3% for presentation only). On selectivity accuracy, the range is 49.3pp (14.3% for guidance to 63.6% for press release document only). However, these extremes are driven by the two smallest information sets: guidance has n_graded=20 and n_calls=21; press release document only has n_calls=11. Excluding these two small sets, the coverage accuracy range across the five remaining information sets is 30.4pp (33.3% for financials to 43.1% for transcript only), and the selectivity accuracy range is 12.2pp (28.7% for full to 40.9% for presentation only).

The two directly comparable mappings (qanda vs qa_only; full vs full_bundle) are within a few percentage points of each other: qanda 40.0% versus qa_only 38.8%/32.0%; full 28.7% versus full_bundle 36.8%/35.7%. These point estimates are on different events and cannot be treated as a paired comparison.

**Plain statement of what the data show:**

The human arm does not clearly replicate the model's flatness. The nominal range across information sets is substantially wider than the model's 5–6pp range, particularly when guidance (15.0% coverage) and presentation only (64.3% coverage) are included. Whether this reflects a real differentiation effect or is sampling noise driven by small n for the extreme groups cannot be determined from this dataset: guidance has n_graded=20 and presentation only has n_graded=14, both too small for confident estimation.

The qanda and full human arms — the two largest groups — are close to each other (43.1% vs 40.2% coverage; 38.9% vs 28.7% selectivity) and broadly consistent with the model's flatness finding. The transcript only arm (33.5 min mean read time, n=94) is also within a few percentage points of the full arm on coverage accuracy despite taking longer to read, which is consistent with the model's finding that signal quality is not strongly arm-dependent.

The guidance arm stands out as an outlier: coverage accuracy 15.0% and selectivity accuracy 14.3%, well below both the majority-class floor (~55%) and every other information set. This is unexpected and may reflect a genuine information-set effect (forward-looking guidance language is harder to translate into a directional overnight trade), a rater-selection effect (raters assigned to guidance sessions may differ systematically), or noise given n_graded=20. The data do not distinguish these explanations.

---

## 9. Data Availability Verdict

| Cut | Estimable? | Notes |
|---|---|---|
| Coverage accuracy by information set | Yes, all 7 sets | n_graded ≥ 14 for all sets; presentation only (n=14) and guidance (n=20) borderline |
| Selectivity accuracy by information set | Yes, all 7 sets | n_calls ≥ 11 for all sets; press release doc only (n=11) borderline |
| Mean reading time | Yes, all 7 sets | Time column fully populated (420/420 non-None) |
| Mean net per trade | Yes, all 7 sets | n_trades ≥ 10 for all sets (press release doc only n=11, borderline) |
| Paired human accuracy vs model accuracy (same events) | No | Human and model sessions cover different events; paired comparison is not possible |
| Within-human paired analysis (full vs section for same rater-event) | No | Each rater-event appears in at most one information set in this dataset; no paired structure available |
| Rater fixed-effects decomposition | Not pursued | Raters are not balanced across information sets; a rater effect would be confounded with information set assignment |

---

## Notes on Methodology

- **Re-priced returns:** The workbook corrected 295 of 420 rows to use release-date (EDGAR 8-K filing date) price anchors on 2026-08-13. The remaining 125 rows (human-only events not in the LLM universe) retain their original human-typed prices. Re-priced values are used preferentially throughout this analysis.
- **Model selectivity accuracy definition:** The section ablation files define accuracy as correct/trades where trades includes all BUY and SELL calls, including calls where the overnight return fell within the ±2% flat band (labeled "flat" in the grade column). The human selectivity accuracy uses the same denominator (all BUY+SELL calls). They are therefore comparable in structure.
- **Model accuracy metric vs coverage accuracy:** The model's section ablation does not compute a coverage accuracy (correct / graded events regardless of model decision). The model metric is closer to the human selectivity accuracy. The human coverage accuracy table has no direct model analogue.
- **Grading band:** ±2% raw overnight return, pre-registered. Consistent across human and model calculations.
- **Majority-class floors:** All human information sets fall below their respective majority-class floors on both coverage and selectivity accuracy, meaning the directional split of outcomes slightly favors a naive always-DOWN strategy over the human raters' actual calls. This is consistent with the systematic upward bias in human decisions (BUY rates of 51–78% against a roughly 43–57% UP/DOWN split in outcomes across most sets).
