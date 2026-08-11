# Worksheet Leak Triage

run_id: 20260811T191953Z
date: 2026-08-11

## (a) Affected events

53 of 268 extracted text files contain an `=== EARNINGS DOCUMENT ===` section.
Of these 53, **25 are genuine human blind-sentiment worksheets** containing a
human rater's sentiment score, directional signal, correctness verdict, and
realised horizon returns. The other 28 are ordinary press releases or
supplemental filings that happen to carry `doc_type: "Earnings Document"` in the
manifest (no human judgement content).

The 25 human-worksheet events span 9 tickers: AMD (3), AMZN (3), COIN (3),
LLY (3), META (3), NFLX (3), NVDA (4), TSLA (3).

Full event list in `worksheet_leak_flags.csv` (same directory).

## (b) Pipeline path: the worksheet text IS fed to the LLM

The pipeline **does** pass worksheet content to the LLM. The mechanism:

1. Each manifest entry (`manifests/p2_*_reports.json`) lists documents by
   `doc_type`. All 53 affected events include a document with
   `"doc_type": "Earnings Document"`.

2. `report_pipeline.build_bundle_text()` (line 460) iterates over
   `report.documents` -- the manifest's document list -- and for each document
   calls `extract_doc_text()` on its `source_pdf`, then concatenates with a
   section header:

   ```python
   for doc in report.documents:                                      # line 460
       header = BUNDLE_SECTION_HEADERS.get(doc.doc_type, doc.doc_type.upper())  # line 461
       ...
       sections.append(f"=== {header} ===\n\n{extraction.text}")     # line 469
   ```

3. `BUNDLE_SECTION_HEADERS` (lines 43-47) maps only three doc_types:

   ```python
   BUNDLE_SECTION_HEADERS = {
       "Press Release": "PRESS RELEASE",
       "Earnings Presentation": "EARNINGS PRESENTATION",
       "Earnings Call Transcript": "EARNINGS CALL TRANSCRIPT",
   }
   ```

   `"Earnings Document"` is not in this map, so the fallback
   `doc.doc_type.upper()` produces `"EARNINGS DOCUMENT"`.

4. The concatenated text goes straight to `build_user_message()` as
   `report_text`, then into `call_llm()` as the user message content. There is
   **no filtering or section-stripping** between extraction and the LLM call.

5. `run_reports.process_report()` (lines 271-273) shows the flow:

   ```python
   report_text, per_doc_meta, bundle_warnings = build_bundle_text(report)
   extraction_target.write_text(report_text, encoding="utf-8")
   ```

   The same `report_text` is then passed to `build_doc_params()` and onward to
   the LLM. The extracted text file on disk is a faithful record of what the
   model received.

**Conclusion: the LLM saw the full worksheet content, including the human's
score, signal, and -- critically -- the realised price returns.**

## (c) What the worksheets contain

### Example 1: AMD_FQ1_2026 (David Eji, 14 July 2026)

Human sentiment score and directional call (category i -- leakage of human judgement):

> Score:+0.80
> Signal: BUY

Post-event realised returns (category ii -- look-ahead, fatal):

> Score given vs. correct call: signal wasBUY, matching the correct call, so
> the call was CORRECT. Horizon returns (pre-registered) [...] Overnight
> (baseline for the label) +15.26% D+1 close +18.61% D+3 close +28.13%
> D+5 close +26.19%

### Example 2: NVDA_FQ2_2025 (Dragos Macsim, 29 June 2026)

Human sentiment score and signal (category i):

> Sentiment score: +0.35. [...] Directional signal: BUY.

The worksheet also contains realised price data (category ii).

### Example 3: TSLA_FQ4_2025 (David Eji, 16 July 2026)

Human sentiment score and signal (category i):

> Score:+0.60
> Signal: BUY

Realised returns follow the same template (category ii).

All 25 human worksheets follow the same structure: conventions, metadata,
headline financials summary, human-authored analysis, a numeric sentiment score,
a directional signal, a correctness verdict against the realised overnight move,
and a full table of realised horizon returns (overnight through D+20).

**Every one of the 25 human-worksheet events contains both (i) a human
directional judgement and (ii) post-event realised returns.**

## (d) Split figures

### 5-day directional accuracy (blend_correct_default)

| Group | n | Accuracy |
|---|---|---|
| All events | 268 | 36.57% |
| EARNINGS DOCUMENT section (any) | 53 | 41.51% |
| No EARNINGS DOCUMENT | 215 | 35.35% |
| Human-score worksheet | 25 | 44.00% |
| Non-human-score | 243 | 35.80% |

Bootstrap (unpaired) accuracy difference, EARNINGS DOCUMENT vs none:
+6.16pp, 90% CI [-6.09%, +18.82%], p=0.396.

Bootstrap accuracy difference, human-score worksheet vs none:
+8.20pp, 90% CI [-8.33%, +25.43%], p=0.433.

### Overnight mean net per trade

| Group | Trades | Mean net/trade |
|---|---|---|
| EARNINGS DOCUMENT section | 40 | +2.192% |
| No EARNINGS DOCUMENT | 131 | +1.559% |
| Human-score worksheet | 20 | +3.432% |
| Non-human-score | 151 | +1.479% |

Bootstrap (unpaired) net/trade difference, EARNINGS DOCUMENT vs none:
+0.633pp, 90% CI [-1.222%, +2.442%], p=0.587.

Bootstrap net/trade difference, human-score worksheet vs none:
+1.954pp, 90% CI [-0.887%, +4.644%], p=0.242.

### Agreement rate with human arm

Human-rater directional signals (BUY/HOLD/SELL) were extracted directly from the
worksheet text embedded in each of the 25 affected events' extracted text files
(the same text the LLM received). The human signal was parsed via the
`Signal: <BUY|HOLD|SELL>` or `Directional signal: <BUY|HOLD|SELL>` pattern
present in every worksheet. All 25 events yielded a parseable human signal.

**LLM-human agreement on the 25 worksheet events: 18/25 = 72.0%**

| Metric | Value |
|---|---|
| Agreement rate | 72.0% (18/25) |
| Chance agreement (marginals) | 43.4% |
| Cohen's kappa | 0.506 |
| 90% bootstrap CI on agreement | [56.0%, 84.0%] |
| Permutation p-value (vs chance) | 0.0013 |

Signal distributions (n=25): human BUY=17, HOLD=3, SELL=5; LLM BUY=13, HOLD=5,
SELL=7. The 7 disagreements: AMD_FQ2_2025 (human BUY, LLM HOLD),
COIN_FQ1_2026 (human BUY, LLM SELL), LLY_FQ3_2025 (human SELL, LLM BUY),
META_FQ1_2026 (human BUY, LLM SELL), NVDA_FQ2_2025 (human BUY, LLM HOLD),
TSLA_FQ1_2026 (human HOLD, LLM SELL), TSLA_FQ3_2025 (human BUY, LLM HOLD).

The 72% agreement rate is significantly above the 43.4% chance rate expected from
the marginal signal distributions (permutation p=0.0013). Cohen's kappa of 0.506
indicates moderate-to-good agreement, consistent with the LLM having read and
been influenced by the human's directional call embedded in the input text.

**Comparison to non-worksheet events is not possible from repo data alone.**
Human-rater scores for the remaining 243 events live in an external spreadsheet
(`Master_Data_NEW.ods` on SharePoint, not committed to the repository). Without
that data, we cannot compute a clean-group agreement rate to split by the leak
flag. The 72% figure for the worksheet group stands on its own as evidence of
contamination but cannot be contrasted with a clean baseline.

If the external sheet is made available, the correct analysis would be:
`bootstrap_unpaired_difference` (from `bootstrap_stats.py`) on agreement
indicator arrays (1=agree, 0=disagree) for the 25 worksheet events vs the
non-worksheet events that also have human scores, yielding a CI and p-value on
the agreement-rate difference.

## (e) Conclusion

**This is a real leak, not a potential one.** The pipeline mechanism is
unambiguous: `build_bundle_text()` concatenates every document listed in the
manifest, the manifest lists the worksheet PDF as `"Earnings Document"`, and no
filtering occurs before the text reaches the LLM.

For the 25 human-worksheet events, the model received:
- A human rater's sentiment score (-1 to +1) and directional signal (BUY/HOLD/SELL)
- A human rater's written analysis and evidence reasoning
- The realised overnight price move and whether the human's call was correct
- Realised horizon returns out to D+20

The **look-ahead** component (realised returns baked into the input text) is the
more severe concern: for these 25 events, the model could read the actual
overnight move before producing its own score. This is not merely a human-
judgement contamination issue -- it is a future-information leak.

The directional performance difference (human-worksheet group: 44.0% accuracy,
3.43% mean net/trade vs. clean group: 35.8% accuracy, 1.48% mean net/trade) is
directionally consistent with contamination but not statistically significant at
conventional levels (accuracy p=0.433, net/trade p=0.242 via unpaired
bootstrap). However, with only n=25 affected events, the test has limited power
to detect a real effect.

**Severity**: 25 of 268 events (9.3%) have their micro-layer score compromised
by look-ahead data. Any accuracy or P&L figure computed over the full N=268
dataset is tainted by these events and cannot be cited as clean. The remaining
28 "Earnings Document" sections that are just press releases are benign (no human
judgement or realised returns) -- they add legitimate source material, equivalent
to any other press release section.
