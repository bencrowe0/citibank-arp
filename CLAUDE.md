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
python -m eval.run_eval --issuer <issuer>   # calibrate against actual price outcomes
```

## Two distinct threshold concepts - do not conflate

- `hold_upper` / `hold_lower` - thresholds on the LLM's **sentiment score** (-1..+1), used to derive a prediction.
- `outcome_upper` / `outcome_lower` (`eval/outcomes.py`) - thresholds on the stock's **actual forward return**, used to derive the ground-truth label a prediction is checked against.

Never reuse the `hold_*` names for the outcome-side threshold or vice versa.

## Known limitations

- **Small-N calibration.** `eval/calibrate.py` runs leave-one-out cross-validation across 4 quarters/issuer - a "tuned" threshold or weight triple is a per-fold choice, not a single validated answer. Treat calibration results as directional evidence, not a settled parameter.
- **News layer source bias.** Digests are pulled from a small set of free outlets (CNBC, Yahoo Finance) in a fixed date window around each report. This is auditable (source URLs are recorded) but not a guarantee against selection or outlet bias.
- **Long filings excluded by design.** 10-K/10-Q filings and JPMC's financial supplement are stored but never fed to any layer. If a future phase wants deeper regulatory/financial-statement context, this is the obvious extension point.
