# Citibank Applied Research Project — Model Arm

Earnings materials in, DeepSeek-powered structured BUY/HOLD/SELL predictions out, calibrated against actual overnight stock-price outcomes and benchmarked against a parallel human-analyst arm.

Four scored layers are blended into one signal per company-quarter:

- **Micro** — the company's own earnings materials (press release, presentation, transcript), scored on change in forward guidance vs. the company's prior guidance
- **Macro** — FOMC minutes, scored once per meeting and reused across issuers
- **News** — a pre-earnings market-expectations digest per company/quarter (strictly pre-report sources)
- **Quant** — a deterministic, zero-LLM-cost composite of momentum, EPS surprise, and rates/volatility data

The blended score maps to BUY/HOLD/SELL via HOLD-band thresholds, and every prediction is graded against the realised overnight gap, net of transaction costs.

**[CLAUDE.md](CLAUDE.md) is the canonical technical log** — current architecture, headline figures, run commands, audits, and known gaps live there.

## Structure

```text
.
|- report_pipeline.py     # micro layer: bundle documents -> one LLM call per quarter
|- run_reports.py         # micro-layer batch entry point
|- llm_macro.py           # macro layer (FOMC minutes)
|- llm_news.py            # news layer (pre-earnings expectations digests)
|- quant_layer.py         # quant layer (yfinance/FRED, no LLM)
|- blend.py               # weighted blend + BUY/HOLD/SELL thresholds
|- backtest.py            # overnight-gap P&L backtest (model or human raters)
|- export_sheet_rows.py   # rows for the shared Human-vs-LLM workbook
|- bootstrap_stats.py     # shared bootstrap/significance infrastructure
|- build_cost_ledger.py   # API cost ledger from scored artifacts
|- eval/                  # outcome labels, calibration, pooled evaluation
|- phase2/                # active 70+ issuer track: manifests build, sourcing, audits, exports
|- experiments/           # robustness/validity analyses (sweeps, walk-forward, ablations, baselines)
|- docs/                  # source corpus: earnings PDFs, transcripts, news digests
|- manifests/             # per-issuer document manifests
|- outputs/               # scored results; headline artifacts in outputs/global/summary/
|- data/                  # human-arm data, quantitative caches, workbook snapshots
|- prompts/               # shared LLM prompt template
`- tests/
```

## Local setup

```powershell
python -m pip install -r requirements.txt
```

`.env` should contain `DEEPSEEK_API_KEY=...`

## Run

Bare invocations default to the full phase2 issuer set (each layer is cached and idempotent):

```powershell
python llm_macro.py                         # score all FOMC minutes
python llm_news.py                          # score all pre-fetched news digests
python quant_layer.py                       # score all quarters' quant composite (free)
python blend.py <issuer>                    # blend the four layers for one issuer
python -m eval.run_eval --output-suffix phase2   # pooled calibration CSV
```

Micro-layer batch run for one issuer:

```powershell
python run_reports.py --issuer <issuer> --dry-run   # inspect without spending API tokens
python run_reports.py --issuer <issuer>
```

See CLAUDE.md's "Running the pipeline" section for the full command reference.

## Backtest (P&L evaluation)

Evaluates any predictor's calls as an overnight-gap trading strategy (BUY -> long into
the close before the release, exit next open; SELL -> short; HOLD -> no trade), net of
transaction costs. This is the money-based scorecard that complements raw 3-class
accuracy.

```powershell
python backtest.py                       # LLM signal, overnight-gap trades, net of 10 bps round-trip
python backtest.py --sensitivity         # + total return across several cost levels
python backtest.py --sheet export.csv    # add every HUMAN rater from a group-sheet CSV/TSV export
python backtest.py --cost-bps 20 --short-borrow-bps 5   # custom cost assumptions
```

`--sheet` takes any CSV/TSV in the group-sheet schema (columns `Ticker, Year, Quarter,
Rater, Type (Human/LM), Decision (BUY/HOLD/SELL), Prior Close ($), Next Day Open ($)`),
so each human rater is scored on the identical strategy and joins the comparison. Writes
the per-trade equity curve to `outputs/global/summary/backtest_equity.csv`.

## Notes

- PDF text extraction is local and uses `pypdf` with `pdfplumber` fallback
- The batch runner writes extracted text, latest results, logs, and summary files into `outputs/<issuer>/`
- Each batch run is also archived under `outputs/<issuer>/runs/<run_id>/` so later runs do not overwrite prior summaries and result files
- `example_runthrough.py` is a self-contained demo on a fictional transcript, kept for onboarding
