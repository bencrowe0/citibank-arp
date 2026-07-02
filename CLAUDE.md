# CLAUDE.md

Citibank Applied Research Project - earnings materials in, DeepSeek-powered structured BUY/HOLD/SELL predictions out, calibrated against actual stock price outcomes.

## Architecture

Three scored layers, blended into one signal:

- **Micro** (`report_pipeline.py`, `run_reports.py`) - the company's own earnings materials (press release + presentation + transcript, bundled into one LLM call per quarter). This is the core layer; everything else adjusts it.
- **Macro** (`llm_macro.py`) - FOMC minutes, scored once per meeting and reused across every company/quarter whose `report_date` falls after that meeting's release (entity-agnostic, cached under `outputs/macro/results/`).
- **News** (`llm_news.py`) - a **pre-earnings market-expectations digest** per company/quarter (`REPORT_TYPE = "Pre-Earnings Market Expectations Digest"`), sourced from free outlets (CNBC, Yahoo Finance) via web search, stored as plain text under `docs/news/<issuer>/<document_id>.txt` with source URLs + publish dates recorded inline for auditability. **Every source article is dated strictly before `report_date`** - this is a hard rule, not a convenience: an earlier version of this layer used an "earnings date and following days" window and leaked actual post-earnings stock-reaction language into the digest text (see "Data leakage fix" below). The layer now scores how stretched or depressed market expectations were heading into the print, not sentiment about results that don't exist yet in the source text.
- **Blend** (`blend.py`) - weighted sum of the three layer scores into one blended sentiment score, then the same `hold_upper`/`hold_lower` threshold mechanism derives BUY/HOLD/SELL.

All three layers share the same prompt (`prompts/llm_analysis_prompt_template.md`), just with a different `{{REPORT_TYPE}}` and `{{REPORT_TEXT}}`.

## Manifest schema

`manifests/<issuer>_reports.json` - each report entry has a `documents` list (not a single `source_pdf`): `[{"doc_type": "Press Release", "source_pdf": "..."}, ...]`. Single-document issuers (Netflix) just have a list of length 1. `report_pipeline.build_bundle_text()` concatenates a report's documents into one labeled text block per quarter.

Long filings (10-K/10-Q, and for JPMC the earnings release financial supplement) are downloaded and stored under `docs/<issuer>/filings/` but are **intentionally excluded** from every layer's default input - too long/dense, matches the group's "too financy" feedback on the source documents.

## Running the pipeline

See [README.md](README.md) for the micro-layer run commands. For the macro/news/blend/eval pieces:

```powershell
python llm_macro.py                        # score all 2025 FOMC minutes (cached, idempotent)
python llm_news.py                          # score all pre-fetched news digests (cached, idempotent)
python blend.py <issuer>                    # blend micro+macro+news for one issuer's quarters
python -m eval.run_eval                     # calibrate threshold + blend weights, pooled across ALL issuers
```

## Two distinct threshold concepts - do not conflate

- `hold_upper` / `hold_lower` - thresholds on the LLM's **sentiment score** (-1..+1), used to derive a prediction.
- `outcome_upper` / `outcome_lower` (`eval/outcomes.py`) - thresholds on the stock's **actual forward return**, used to derive the ground-truth label a prediction is checked against.

Never reuse the `hold_*` names for the outcome-side threshold or vice versa.

## Known limitations

- **Small-N calibration.** `eval/run_eval.py` pools all issuers before running leave-one-out cross-validation (N=12 documents, not 4/issuer) so the tuned threshold/weights are one shared answer rather than three separately overfit ones - but N=12 is still small, and a "tuned" value is a per-fold choice, not a single validated answer.
- **News layer source bias.** Digests are pulled from a small set of free outlets (CNBC, Yahoo Finance) in a fixed pre-report date window. This is auditable (source URLs + publish dates are recorded) but not a guarantee against selection or outlet bias.
- **Blend does not currently beat micro alone.** As of the round-2 fix below, pooled LOOCV shows the micro-only threshold prediction (6/12) outperforming every blend-weight variant tested, including the "tuned" one (which LOOCV shows does not generalize - see round 2). `DEFAULT_WEIGHTS` in `blend.py` is left unchanged (0.6/0.2/0.2) rather than hand-fit to this finding, consistent with the project's "don't tune to outcomes" discipline - but it's an honest result to present: macro/news add conceptual value (context beyond the document) but have not yet been shown to add predictive value at N=12.
- **Long filings excluded by design.** 10-K/10-Q filings and JPMC's financial supplement are stored but never fed to any layer. If a future phase wants deeper regulatory/financial-statement context, this is the obvious extension point.

## Prediction-accuracy fix (2026-07-02)

First pooled eval run scored **2/12 (16.7%)** - worse than naive always-SELL (50%) or always-HOLD (41.7%) baselines, with a systematic BUY-bias: 11/12 quarters predicted BUY regardless of actual outcome (actual distribution was 50% SELL / 41.7% HOLD / 8.3% BUY - 2025 was a rough year for Boeing/JPM/Netflix).

**Root cause, diagnosed against the actual data**: the prompt's scoring anchors (`prompts/llm_analysis_prompt_template.md`) mapped "solid results, modest beat, stable guidance" to +0.5 - but that description fits nearly every earnings release, so the micro layer (60% blend weight) floored almost every quarter above zero regardless of whether the stock was actually expected to move. The model was scoring "was this a good quarter in isolation" rather than "did forward guidance change relative to what the company itself had previously signaled." News (20% weight) compounded it; macro (20% weight, itself roughly balanced) was too small a weight to correct it.

**Fix applied**: rewrote the scoring-anchor section to make the score track *change in forward guidance versus the company's own prior guidance* rather than absolute quarter quality, with "in-line, modest beat, guidance reaffirmed" explicitly anchored to 0.0 instead of +0.5, plus two in-prompt calibration examples. Also reduced `eval/calibrate.py`'s `WEIGHT_STEP` from 0.1 to 0.2 (66 -> ~21 weight combinations) to shrink the joint search space's overfitting risk at N=12. All micro/macro/news scores were regenerated under the new prompt (old cached results deleted and re-run).

**Result**: prediction distribution is no longer degenerate (was 11 BUY / 0 HOLD / 1 SELL, now 4 BUY / 6 HOLD / 2 SELL - much closer to the actual 1/5/6 split). Pooled LOOCV: **default-weights accuracy 0.42** (was 0.17), **tuned blend-weight+threshold accuracy 0.58** (was 0.17, and previously tuning made things *worse* than default - 0.08 - which is no longer the case now that the underlying scores are properly calibrated). A supplementary run at a 10-trading-day outcome window (vs. the default 5-day) is saved alongside as `outputs/global/summary/global_outcome_calibration_window10.csv` / `global_calibration_summary_window10.json` - default accuracy is lower at that window (0.17) but tuned blend still recovers to 0.50; the 5-day window remains the default methodology, this is reported as a supplementary robustness check, not a replacement.

Still small-N (12 documents) - this is a real, meaningful improvement, not a fully solved problem, and should be presented to the team as directional evidence that fixing the LLM's scoring calibration (not just tuning thresholds after the fact) is what actually moves accuracy.

## Round 2: data leakage fix + further calibration (2026-07-02)

Asked to push accuracy further (target 8-9/12), with an explicit constraint: no shortcuts and no data leakage. Two things were found and fixed before any further tuning was attempted.

**Data leakage found and fixed.** The news digests (built under the round-1 fix above) were fetched from an "earnings date and following days" window. 4 of 12 digests turned out to contain explicit post-earnings stock-reaction language - e.g. "Boeing stock fell 4% on the announcement," "shares of JPM tumbled 1.9% after the release," "shares... declining by up to 12% following the announcement." The news layer (20% blend weight) was partially reading the actual outcome, not predicting it. Some of round 1's reported 7/12 (tuned blend) was leakage-inflated.

Fix: all 12 news digests were rebuilt from scratch using only articles dated **strictly before** `report_date` - pre-earnings analyst estimates, valuation framing, and expectations-setting coverage, sourced and date-verified per article. This redefines the news layer's purpose: it now measures how stretched or depressed market expectations were heading into the print, not sentiment about the print itself. A first pass at rescoring these under the *round-1* prompt scored everything ~0.0 (neutral) because the scoring anchors were built around "did guidance change," which doesn't apply to a document that predates the guidance - the model correctly noted "no guidance in this document" and defaulted to neutral, discarding real signal like "priced for perfection" valuation commentary. A second prompt fix added an explicit interpretation rule for pre-earnings digests: score how stretched (bearish) or depressed (bullish) expectations are, not whether guidance changed. After that fix, news scores became genuinely directional (e.g. all 4 Netflix quarters scored negative, correctly flagging the "stock priced for perfection" pattern the pre-earnings coverage kept surfacing).

**Micro-layer prompt further sharpened** (same file, extending round 1's anchors, not replacing them): explicit instructions to (a) read the earnings-call Q&A section for analyst pushback/management hedges as real signal, not just prepared remarks, (b) discount guidance improvements management itself attributes to FX/one-time/deferred items vs. organic performance, (c) weight structural/recurring risks (e.g. Boeing's 777X durability issue, KC-46A charge) above one-time noise, and (d) a new +0.15/+0.3 middle band for genuine operational momentum (e.g. a real loss-to-profit swing) that hasn't yet produced a formal guidance raise - the round-1 anchors were correctly catching the extremes but conflating "real momentum, no raise yet" with "flat quarter, no raise."

**Result, fully corrected for leakage**: pooled LOOCV lands at **6/12 (50%)**, achieved by the micro-layer signal alone (threshold-only prediction) - this is the current best, honestly-arrived-at number, down from round 1's leakage-tainted 7/12 but up from the original 2/12. The corrected blend (weights + threshold jointly tuned via the same LOOCV machinery, untouched) performs *worse* (3/12) - LOOCV folds kept picking a 100%-news weight that fit the calibration set but did not generalize to the held-out document, the textbook overfitting signature at this N. This is reported honestly rather than hidden: **macro and news do not currently add predictive value over micro alone**, even though the news layer is now genuinely informative and leak-free. `blend.py`'s `DEFAULT_WEIGHTS` (0.6/0.2/0.2) is left unchanged rather than hand-fit to this finding.

**Target of 8-9/12 was not reached.** Per the plan agreed before this round, prompt refinements were required to be justified by an articulable document-reading principle, not "whatever flips this specific row" - and weight/threshold tuning was restricted to the existing LOOCV machinery, not manual overrides. Both constraints were honored. The remaining wrong calls (BA_FQ2, BA_FQ4, NFLX_FQ1_2026, NFLX_FQ2, NFLX_FQ3, NFLX_FQ4) were individually reviewed; all six have document-defensible sentiment scores near the HOLD/BUY boundary that the model can't confidently push further one way without inventing a rule that wouldn't apply to any *other* document - i.e. this looks like the genuine ceiling for a document-grounded, non-leaking predictor at N=12, not a gap the team should expect to close with more prompt engineering on this same 12-document set. Growing N (as the rest of the team's companies land) is the most promising remaining lever.
