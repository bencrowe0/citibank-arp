# CLAUDE.md

Citibank Applied Research Project - earnings materials in, DeepSeek-powered structured BUY/HOLD/SELL predictions out, calibrated against actual stock price outcomes.

**Phase2 (`p2_*` issuers) is the only active track.** An earlier 6-issuer pipeline (`jpm`, `bank_of_america`, `boeing`, `disney`, `target`, `netflix`) was used to build and validate this pipeline before phase2 existed; its docs/manifests/outputs are still on disk but are retired - not run by default, not used for comparison, and shouldn't be cited going forward. Every bare CLI invocation below now defaults to the phase2 issuer set; pass an explicit issuer name to touch a retired one.

## Architecture

Four scored layers, blended into one signal, run per-issuer (39 issuers currently registered under `PHASE2_ISSUERS` in `blend.py`/`quant_layer.py`/`llm_news.py`, all `p2_`-prefixed):

- **Micro** (`report_pipeline.py`, `run_reports.py`) - the company's own earnings materials (press release + presentation + transcript, bundled into one LLM call per quarter). Core layer; everything else adjusts it. Scoring anchors to **change in forward guidance vs. the company's own prior guidance**, not absolute quarter quality - a "solid, modest beat, stable guidance" quarter scores ~0.0, not a default +0.5.
- **Macro** (`llm_macro.py`) - FOMC minutes, scored once per meeting, reused across every company/quarter whose `report_date` falls after that meeting (cached under `outputs/macro/results/`).
- **News** (`llm_news.py`) - a **pre-earnings market-expectations digest** per company/quarter, sourced from free outlets (CNBC, Yahoo Finance), stored under `docs/news/<issuer>/<document_id>.txt` with source URLs + dates inline. **Every source article is dated strictly before `report_date`** (hard rule - an earlier version leaked post-earnings reaction language). Scores how stretched/depressed market expectations were heading into the print, not sentiment about results. Not every quarter has a digest yet - see Known gaps.
- **Quant** (`quant_layer.py`) - deterministic, yfinance-only, zero-LLM-cost composite of price momentum, EPS surprise, and a macro-numeric sub-component (`^TNX`, `^IRX`, `^VIX`), plus optional FRED Fed-data ablation (`DFF`, `T10Y2Y`, key-free `fredgraph.csv`, cached to `data/quantitative/fred_cache/`). Never earns blend weight (below).
- **Blend** (`blend.py`) - weighted sum of the four layer scores, then `hold_upper`/`hold_lower` thresholds derive BUY/HOLD/SELL. `DEFAULT_WEIGHTS = (0.8, 0.0, 0.2, 0.0)` (micro/macro/news/quant), `±0.25` thresholds (`eval/calibrate.py`'s `DEFAULT_HOLD_UPPER/LOWER` - **not** `blend.py`'s own `blend_document()` function-default of `±0.15`, a recurring trap - see Known bugs fixed).

Micro/macro/news share one prompt (`prompts/llm_analysis_prompt_template.md`), differing only in `{{REPORT_TYPE}}`/`{{REPORT_TEXT}}`. Quant is pure arithmetic, no LLM call.

## Manifest schema

`manifests/p2_<slug>_reports.json` - each report entry has a `documents` list: `[{"doc_type": "Press Release", "source_pdf": "..."}, ...]`. Composition varies by issuer. `report_pipeline.build_bundle_text()` concatenates a report's documents into one labeled text block per quarter. Every phase2 manifest entry has ≥2 documents except `p2_jpm`'s `JPM_2026_Q1`, which has no usable source document at all and is skipped.

Long filings (10-K/10-Q, annual reports) are excluded by filename pattern (`phase2/build_manifests.py`) - too dense, matches the group's "too financy" feedback.

## Dataset naming convention

Every scored source document lives under **`docs/<issuer>/phase2/CY<FY>-Q<FQ>/`** (the 6 issuers that also have a retired pre-phase2 folder) or **`docs/<issuer>/CY<FY>-Q<FQ>/`** (the 33 phase2-only issuers, no collision risk), where `CY<FY>-Q<FQ>` is the **fiscal period being reported** (from manifest `fiscal_period`, e.g. `FQ1 2026` -> `CY2026-Q1`), NOT the calendar quarter of the release date. Filenames stay issuer-native; only the folder is normalized. Result artifacts: `outputs/p2_<slug>/results/<TICKER>_FQ<Q>_<YEAR>.json`. Any future backfill must follow this scheme.

## Running the pipeline

See [README.md](README.md) for micro-layer run commands. Macro/news/blend/eval/backtest - bare invocations default to the full phase2 issuer set; pass explicit issuer names to touch a retired pre-phase2 issuer:

```powershell
python llm_macro.py                         # score all FOMC minutes (cached, idempotent)
python llm_news.py                          # score all phase2 pre-fetched news digests (cached, idempotent)
python quant_layer.py                       # score all phase2 quarters' quant composite (free, cached, idempotent)
python blend.py <issuer>                    # blend micro+macro+news+quant for one issuer's quarters
python -m eval.run_eval                     # calibrate threshold + blend weights, pooled across every phase2 issuer (same as --phase2-all)
python -m eval.run_eval --output-suffix phase2   # writes global_outcome_calibration_phase2.csv (the canonical phase2 output)
python -m experiments.phase2_pnl_weight_threshold_sweep   # phase2-scoped weight/threshold grid, TOTAL-RETURN objective + LOOCV + DSR
python -m experiments.rq16_surprise_control   # does the blend score add value beyond public EPS surprise%; also computes legacy production/pooled numbers against retired data (ignore those) - only outputs/global/summary/rq16_surprise_control_phase2.json matters
python build_cost_ledger.py                 # rebuild outputs/global/summary/api_cost_ledger.csv from existing phase2 artifacts (no API calls)
python backtest.py --calibration-csv outputs/global/summary/global_outcome_calibration_phase2.csv   # P&L backtest of the LLM's overnight-gap trades, net of costs
python backtest.py --sheet export.csv       # score every HUMAN rater from a group-sheet CSV export on the identical strategy
```

`run_reports.py` also takes `--prompt <file>` (test an alternate prompt without touching the default), `--ensemble N` (average N repeat runs per document), and `--variant <label>` (writes to `outputs/<issuer>_<label>/`, never overwrites canonical). `eval.run_eval --issuers <issuer>_<label>,...` evaluates a variant folder. `compare_runs.py <a> <b>` diffs two results folders, optionally against ground truth.

## Two distinct threshold concepts - do not conflate

- `hold_upper` / `hold_lower` - thresholds on the LLM's **sentiment score** (-1..+1), used to derive a prediction.
- `outcome_upper` / `outcome_lower` (`eval/outcomes.py`) - thresholds on the stock's **actual forward return**, used to derive the ground-truth label a prediction is checked against.

Never reuse the `hold_*` names for the outcome-side threshold or vice versa.

## Two distinct performance metrics - do not conflate (this bit us: a memory check answered "5-day" for phase2 when the real answer is overnight)

- **Accuracy/calibration numbers** (`eval/run_eval.py`, `global_outcome_calibration_phase2.csv`) use `eval/outcomes.py`'s `fetch_forward_return(window_trading_days=5, exit_on_open=False)` by default - **5-day close-to-close**. This is a calibration/threshold-tuning artifact (accuracy, LOOCV, weight sweeps), not the deliverable metric.
- **P&L/backtest numbers** (`backtest.py`'s `overnight_gap()`/`simulate()`, the group sheet, every "+X% total return" figure quoted anywhere in this doc) compute close→next-open directly from `prior_close`/`next_day_open` (or `fetch_prices`), **always overnight, regardless of what `run_eval` used** - `simulate()` never reads `window_trading_days` or the calibration CSV's `forward_return` column.
- **Rule of thumb: if the number is a total return / Sharpe / trade count / P&L figure, it's overnight. If it's a bare "accuracy" or "balanced accuracy" percentage, it's 5-day (or whatever `--window-trading-days` was passed to that specific `run_eval`/sweep call).** Before answering "is X's performance measure overnight or 5-day," grep the actual code path (`backtest.py` vs `eval/outcomes.py`) rather than pattern-matching this doc's prose.

## Current state (phase2, N=153)

The live group sheet's human raters (Anna, Abdul, Meriem, David, Nigel, Dragos) evaluate 153 company+quarter combos across 39 tickers. This is the LLM's own scored track on exactly those combos.

- **Backtest (`backtest.py`, overnight close-to-open gap, deployed default weights `0.8/0.0/0.2/0.0`, `±0.25` thresholds, untouched/no phase2-specific tuning)**: 77/153 trades, **total return +70.16%**, hit rate 59.7%, Sharpe/trade 1.37, max drawdown 39.56%, Correct/Flat/Wrong = 26/34/17. Beats always-long (-50.57%) and always-flat (0%).
- **Threshold tightening doesn't help** (`experiments/phase2_threshold_sweep.py`) - tested pulling `hold_upper`/`hold_lower` in from `±0.25` to trade more selectively; total return and avg-P&L/trade both get worse the tighter the band goes. `±0.25` is total-return-optimal on phase2's own curve, not just an inherited default.
- **The blend score does not clearly beat the public EPS surprise%** (`experiments/rq16_surprise_control.py`, joins yfinance's `Surprise(%)` onto each calibration row and asks whether `forward_return ~ surprise% + blend_score` explains more than `forward_return ~ surprise%` alone) - re-run on the current N=150 (153 minus 3 missing surprise data): surprise-only accuracy 0.440, LLM-only 0.387, majority baseline 0.460 - **the baseline beats both individual predictors**, and the R² lift from adding the score is not significant (p=0.544). An honest, currently-unresolved limitation, not a hidden one.
- **The blend weights/thresholds are not an overfit** - `experiments/phase2_pnl_weight_threshold_sweep.py` (phase2-scoped 113,344-combo weight-simplex x asymmetric-threshold grid, total-return objective, re-run on the corrected N=153 universe after the `PHASE2_ISSUERS` fix, self-check MATCH against `backtest.py`'s 70.16%) tried to beat the deployed default on phase2's own data and failed the validity gates: the in-sample "best" combo (`[micro=0.35, macro=0.3, news=0.25, quant=0.1]`, thr `0.15/-0.05`, 99 trades) shows total return 177.12% and raw Sharpe 2.537, but **PSR (Deflated Sharpe Ratio) = 0.0** (not real skill) and **permutation p=0.137** (not significant). Its LOOCV total return (36.63%) is positive but far below in-sample (177.12%) and below the deployed default's own 69.94% - a real out-of-sample gap, not the sign-flip seen on the smaller N=101 universe, but still not a win. The deployed default weights (`0.8/0.0/0.2/0.0`, `±0.25`) remain the only defensible choice on phase2.
- **Macro and quant earn zero blend weight.**

## Known gaps / not yet done

- **`PHASE2_ISSUERS` in `llm_news.py` was missing 7 tickers** (pepsico, fedex, lockheed_martin, novo_nordisk, hilton, lvmh, united_airlines) that `blend.py`/`quant_layer.py` already had - found and fixed this round (any script importing `llm_news.PHASE2_ISSUERS` as its issuer universe, e.g. the phase2 P&L sweep, was silently dropping these 7 tickers' ~34 rows). None of the 7 have a sourced news digest yet (`docs/news/p2_<slug>/` is empty for all 7) - a real, now-visible gap.
- **No news digest**: the 7 tickers above, plus Maersk Q1/Q4 2025 (thin free US-financial-media coverage for a Danish-listed shipper) and Netflix Q4 2024 (deprioritized for time).
- **`p2_jpm`'s `JPM_2026_Q1`** - no usable source document at all, skipped.
- **`GS_FQ2_2026`** - reported 2026-07-14; was too recent for a resolved forward-return outcome as of the last run. May be resolvable now given today's date - not yet rechecked.
- **22 phase2 combos** have a genuinely unresolvable `report_date` (mostly single-rater transcription errors with no second rater to cross-check against, e.g. identical prices typed for two different tickers/quarters).
- **4 pre-existing thin JPM 2025 quarters + 1 PepsiCo quarter** with no free transcript found - surfaced but out of scope, not fixed.
- **Live sheet open item**: confirm `Settings!B3` reads 2.0 (not 10.0, from a caught-but-unverified misclick); the guarded `Data Entry!P` formula needs typing once and copying down the full range; confirm `B4`/`B5` populated (10/0).

## Live "Human vs LLM" group sheet (`Human vs LLM results.xlsx`, Nigel's SharePoint)

Every rater (human or LLM) auto-scores on P&L, not just accuracy, as rows are typed. **Never drive this sheet live via computer-use/browser clicks** - two misclicks during earlier live editing overwrote a banner and the `Settings!B3` threshold cell; the user has explicitly ended Claude-driven live edits. All changes now go to the user as formulas to type by hand. **Also never paste a formula copied from chat into the sheet** - Excel Online's clipboard link metadata intermittently rewrites `'Data Entry'!` references into a broken external-URL self-reference; only hand-typing is reliable. Internal same-workbook copy/paste (filling a formula down rows) is safe.

Load-bearing structure (must match exactly if extended):

- **`Data Entry`** (tab name has a space - quote as `'Data Entry'!`). Columns A-N are manual/semi-manual (`Company, Ticker, Year, Quarter, Rater, Type (Human/LLM), SentimentScore, Decision, Time, PriorClose ($), NextDayOpen ($), Actual %Change, ActualDirection, PredictionCorrect`). `O` = Position (+1 BUY/-1 SELL/0 HOLD, derived from H). `P` = Net P&L% = `position * gap% - costs`, costs from `Settings!$B$4`/`$B$5`, guarded against blank future-quarter rows: `=IFERROR(IF(OR(H3="",J3="",K3=""),"",IF(O3=0,0,O3*L3-Settings!$B$4/10000-IF(O3<0,Settings!$B$5/10000,0))),"")`. Mirrors `backtest.py`'s P&L logic exactly - kept in lockstep.
- **`Settings`**: `B3` = HOLD/direction threshold, must be **2.0** (the group's overnight-gap bucketing threshold); `B4` = round-trip cost bps (10); `B5` = short-borrow bps (0). Everything downstream depends on these three cells.
- **`Summary`**: Accuracy-by-Rater (pre-existing, cols A:G) sits beside the new P&L-by-Rater (cols I:Q: `Rater, Type, #Trades, Total Return %, Avg %/Trade, Dir. Hit Rate, Correct, Flat, Wrong`), same 7 raters/rows for side-by-side reading, plus an All-Humans aggregate row. `#Trades` excludes HOLD (why LLM shows 77, not 153). **Avg Net P&L per Trade is the recommended primary judging metric** (fair across raters with different trade counts; Total Return/Accuracy are supporting context only). Accuracy-by-Company and P&L-by-Company are similarly paired, company names pulled by reference so the two blocks can't drift out of sync.

## Known bugs fixed (still worth knowing the failure mode)

- **Report-date resolution**: two compounding bugs in `phase2/resolve_report_dates.py` - (1) nearest-real-earnings-date positional alignment silently breaks whenever the human dataset lags the single most-recent real print, shifting every date forward a whole quarter; (2) matching against yfinance's *adjusted* (dividend/split-adjusted) price history silently fails since adjusted prices drift below what was actually quoted at the time. Fixed by `phase2/fix_report_dates_from_human_prices.py`, which cross-validates against the humans' own typed (Prior Close, Next Day Open) pair using raw (`auto_adjust=False`) price history - two independent price points must both match.
- **`phase2/export_rows.py` threshold trap**: was deriving `Decision` via `blend.blend_document()`, whose own function-default `hold_upper/lower` is `±0.15`, not the canonical `±0.25` used everywhere else (`eval/calibrate.py`, `backtest.py`, the deployed default). Fixed by reading `Decision`/`Sentiment Score` straight from the calibration CSV's `blend_predicted_signal_default` column.
- **`report_pipeline.extract_doc_text()`** only recognized `.html`, not `.htm` (the conventional SEC EDGAR exhibit extension) or `.txt` (used by several web-sourced transcripts) - silently failed extraction on both until widened.
- **`resolve_report_dates.py` fiscal-year `base_year` rule** mis-years any ticker whose Q1 starts in the first half of the calendar year but still belongs to the prior fiscal year (e.g. FedEx, FYE May 31) - fixed with an explicit `FYE_BASE_YEAR_OFFSET` override.
- **NFLX transcript mislabeling**: `NFLX_FQ1_2025`/`NFLX_FQ2_2025`'s transcript documents actually contained the FQ3/FQ4 2025 calls (future-information leakage into the micro layer). Re-sourced the correct transcripts; the real FQ4 2025 transcript found in the process was added to `NFLX_FQ4_2025` as a bonus doc.
- **News digest leakage**: an earlier version of the news-scoring window pulled from "earnings date and following days" and picked up actual post-earnings reaction language. Digests are now rebuilt strictly pre-`report_date`, with an explicit prompt rule to score pre-earnings expectations, not guidance change.
- **`backtest.py --sheet` parsing**: 3 bugs fixed - whitespace/case-insensitive header and rater matching, synthetic date fallback for non-calibration tickers. Committed (`1c420cf`).
- **`PHASE2_ISSUERS` drift**: `llm_news.py`'s copy of the list fell behind `blend.py`'s/`quant_layer.py`'s after a later onboarding round added 7 tickers only to those two files - fixed by syncing all three, and by flipping `blend.py`/`llm_news.py`/`quant_layer.py`/`eval/run_eval.py`/`build_cost_ledger.py`'s bare-CLI defaults from the retired 6 production issuers to the full phase2 set.

## Environment note

`C:\Users\bencr\OneDrive\Personal\Computing\Business Analytics\Citibank APR` (a path used earlier in this project) is a OneDrive-dependent alias that went fully inaccessible mid-session (OneDrive client process not running) - caused hours of apparent "hangs" reading/copying files before the cause was found. The real, stable project path is `C:\Users\bencr\Documents\Citibank APR` (same git repo) - use this one; it has no OneDrive dependency.
