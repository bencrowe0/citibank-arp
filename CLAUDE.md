# CLAUDE.md

Citibank Applied Research Project - earnings materials in, DeepSeek-powered structured BUY/HOLD/SELL predictions out, calibrated against actual stock price outcomes.

## Architecture

Three scored layers, blended into one signal:

- **Micro** (`report_pipeline.py`, `run_reports.py`) - the company's own earnings materials (press release + presentation + transcript, bundled into one LLM call per quarter). This is the core layer; everything else adjusts it.
- **Macro** (`llm_macro.py`) - FOMC minutes, scored once per meeting and reused across every company/quarter whose `report_date` falls after that meeting's release (entity-agnostic, cached under `outputs/macro/results/`).
- **News** (`llm_news.py`) - a coverage digest per company/quarter, sourced from free outlets (CNBC, Yahoo Finance) via web search, stored as plain text under `docs/news/<issuer>/<document_id>.txt` with source URLs recorded inline for auditability.
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
- **News layer source bias.** Digests are pulled from a small set of free outlets (CNBC, Yahoo Finance) in a fixed date window around each report. This is auditable (source URLs are recorded) but not a guarantee against selection or outlet bias.
- **Long filings excluded by design.** 10-K/10-Q filings and JPMC's financial supplement are stored but never fed to any layer. If a future phase wants deeper regulatory/financial-statement context, this is the obvious extension point.

## Prediction-accuracy fix (2026-07-02)

First pooled eval run scored **2/12 (16.7%)** - worse than naive always-SELL (50%) or always-HOLD (41.7%) baselines, with a systematic BUY-bias: 11/12 quarters predicted BUY regardless of actual outcome (actual distribution was 50% SELL / 41.7% HOLD / 8.3% BUY - 2025 was a rough year for Boeing/JPM/Netflix).

**Root cause, diagnosed against the actual data**: the prompt's scoring anchors (`prompts/llm_analysis_prompt_template.md`) mapped "solid results, modest beat, stable guidance" to +0.5 - but that description fits nearly every earnings release, so the micro layer (60% blend weight) floored almost every quarter above zero regardless of whether the stock was actually expected to move. The model was scoring "was this a good quarter in isolation" rather than "did forward guidance change relative to what the company itself had previously signaled." News (20% weight) compounded it; macro (20% weight, itself roughly balanced) was too small a weight to correct it.

**Fix applied**: rewrote the scoring-anchor section to make the score track *change in forward guidance versus the company's own prior guidance* rather than absolute quarter quality, with "in-line, modest beat, guidance reaffirmed" explicitly anchored to 0.0 instead of +0.5, plus two in-prompt calibration examples. Also reduced `eval/calibrate.py`'s `WEIGHT_STEP` from 0.1 to 0.2 (66 -> ~21 weight combinations) to shrink the joint search space's overfitting risk at N=12. All micro/macro/news scores were regenerated under the new prompt (old cached results deleted and re-run).

**Result**: prediction distribution is no longer degenerate (was 11 BUY / 0 HOLD / 1 SELL, now 4 BUY / 6 HOLD / 2 SELL - much closer to the actual 1/5/6 split). Pooled LOOCV: **default-weights accuracy 0.42** (was 0.17), **tuned blend-weight+threshold accuracy 0.58** (was 0.17, and previously tuning made things *worse* than default - 0.08 - which is no longer the case now that the underlying scores are properly calibrated). A supplementary run at a 10-trading-day outcome window (vs. the default 5-day) is saved alongside as `outputs/global/summary/global_outcome_calibration_window10.csv` / `global_calibration_summary_window10.json` - default accuracy is lower at that window (0.17) but tuned blend still recovers to 0.50; the 5-day window remains the default methodology, this is reported as a supplementary robustness check, not a replacement.

Still small-N (12 documents) - this is a real, meaningful improvement, not a fully solved problem, and should be presented to the team as directional evidence that fixing the LLM's scoring calibration (not just tuning thresholds after the fact) is what actually moves accuracy.
