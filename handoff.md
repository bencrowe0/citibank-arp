# Handoff

## Goal
Improve the Citibank APR earnings-prediction pipeline: add a free quantitative layer, grow the calibration sample N by backfilling earlier quarters, test per-sector vs pooled calibration, track API cost, and organize data for replication - without overfitting or data leakage.

## Current State - ALL BACKLOG ITEMS DONE, NOTHING COMMITTED YET
- **Quant layer**: `quant_layer.py` built and integrated as 4th blend layer (default weight 0.0, verified byte-identical blend behavior).
- **Backfill complete for all 6 issuers**, 2022-2024, 9 quarters each: jpm, bank_of_america, boeing, disney, target, netflix. N grew **24 -> 78**. Total backfill LLM cost this session: **~$0.47** (BAC $0.165, Boeing $0.081, Disney $0.084, Target $0.089, Netflix $0.052; JPM's $0.087 was prior session).
- **Pooled result at N=78**: threshold-only default=tuned=**0.51**, blend default=tuned=**0.54**. The tuned/default overfitting gap seen at every earlier N has closed - all 78 LOOCV folds independently pick the exact default weights (0.8/0.0/0.2/0.0). Quant still earns 0 weight (same story as macro at earlier N) - reported honestly, not hidden.
- **Per-sector re-check at larger N**: Financials (jpm+bac, N=26) tuned 0.62 vs default 0.54 - real gap, could be genuine or still overfit at N=26. Media/Comms (netflix+disney, N=26) converged, no gap. Industrials (boeing, N=13) and Consumer/Retail (target, N=13) both show tuning hurting badly (0.31 vs 0.46/0.54) - textbook overfit at N=13. Pooled stays the default methodology.
- **Cost ledger built**: `build_cost_ledger.py` (new, read-only, no API calls) aggregates all existing per-call cost logs into `outputs/global/summary/api_cost_ledger.csv`. Total logged cost across the whole project: **~$0.68** (micro $0.557, news $0.065, macro $0.055; quant is free).
- **`data/backfill_provenance.csv` filled**: 122 rows, one per backfilled document, with source URL + verification status.
- **CLAUDE.md refreshed**: Architecture/Manifest/Known-limitations sections updated to 6 issuers/4 layers/N=78, plus a new "Round 4" section documenting everything above in full (methodology, honest negatives, what wasn't done).
- **Nothing committed to git yet** - user must review and approve.

## Files in Flight (new/modified this session)
- `manifests/bank_of_america_reports.json`, `boeing_reports.json`, `disney_reports.json`, `target_reports.json`, `netflix_reports.json` - each grew from 4 to 13 entries (9 backfilled + 4 pre-existing 2025 quarters).
- `docs/bank_of_america/CY202*-Q*/`, `docs/boeing/CY202*-Q*/`, `docs/disney/CY202*-Q*/`, `docs/target/CY202*-Q*/`, `docs/netflix/CY202*-Q*/` - new downloaded source documents (SEC EDGAR + company IR CDNs + Motley Fool/Insider Monkey transcripts), all verified via `report_pipeline.extract_doc_text()`.
- `outputs/<issuer>/{extracted,results,summary,runs}/` for all 6 issuers - new backfilled scoring artifacts.
- `outputs/quant/<issuer>/results/` - quant scores for all quarters, all issuers.
- `outputs/global/summary/global_outcome_calibration.csv`, `global_calibration_summary.json` - refreshed to N=78 pooled (canonical, current state on disk).
- `outputs/global/summary/api_cost_ledger.csv` - new.
- `build_cost_ledger.py` - new, reusable (re-run any time after future scoring runs).
- `data/backfill_provenance.csv` - filled (was header-only).
- `CLAUDE.md` - Architecture/Manifest/Known-limitations refreshed + new Round 4 section appended.
- Target folder rename: `docs/target/CY2023-Q1..Q4` (stray, off-by-one fiscal labeling from a prior failed agent run) renamed to `CY2022-Q4, CY2023-Q1..Q3` to match the fiscal-period-based convention used by every other issuer.
- Boeing correction: one wrong SEC exhibit (`a202407jul318kex991.htm`, a CEO-succession 8-K, not the earnings 8-K) was caught by verification and replaced with the correct one (`a202406jun308kprex991.htm`) before scoring.

## Failed Attempts (historical, still relevant if this work resumes with agents)
- **Background subagents for the backfill (twice, prior session) - do NOT retry this way.** First run did nothing in 6 tool calls (misread task). Second run spawned 6 uncontrolled child subagents against explicit instructions, downloaded PDFs chaotically, then hit the account weekly usage limit before scoring anything. This session's backfill was done entirely inline in the main thread per that lesson, and worked cleanly for all 6 issuers.

## Fine-grid pooled weight/threshold search (follow-up ask, same session)
User asked for the "absolutely optimal" pooled weights. Ran a standalone finer grid (`WEIGHT_STEP=0.05`, 18 threshold candidates, 31,878 combos vs. production's 336 - not committed to `eval/calibrate.py`, exploratory only) both as a global best-fit (no held-out fold) and through LOOCV. Both land on **accuracy 0.5385 (42/78)** at weights **(0.8, 0.0, 0.2, 0.0)**, threshold **±0.25** - exactly the existing hardcoded default, unanimous across all 78 LOOCV folds. Confirms the coarse-grid convergence is real, not a grid-resolution artifact. Written up in CLAUDE.md's Round 4 section.

## Open Backlog - what's left (deliberately deferred, not forgotten)
1. **News digests for the 54 backfilled quarters** - out of scope this round. Backfilled quarters currently blend on micro+quant only (`blend_scores`' missing-layer redistribution handles this). Would need the same leak-free "strictly before report_date" sourcing discipline as the 2025 quarters.
2. **`data/quantitative/` replication layout** - not built. `quant_layer.py` re-fetches from yfinance on every run rather than caching prices/fundamentals/macro series to disk under `data/`.
3. **Financials per-sector gap (tuned 0.62 vs default 0.54, N=26)** - worth re-checking once more Financials quarters are added; currently ambiguous whether it's real or still overfitting.
4. **README.md** - not touched this session (it's a single-issuer example doc, doesn't carry the same stale N/issuer-count claims CLAUDE.md had).

Continuous/finer weight sweep (previously item 3) is DONE - see above.

## Next Step
All requested work is complete and CLAUDE.md is current. Ready to commit: `quant_layer.py`, `build_cost_ledger.py`, modified `blend.py`/`eval/calibrate.py`/`eval/run_eval.py`, all 6 issuers' manifests, all new `docs/` source files, all new `outputs/` artifacts, `data/backfill_provenance.csv`, and `CLAUDE.md`. `docs/`/`outputs/` are already tracked in git history (confirmed via `git ls-files`), so no gitignore decision needed - staying consistent with existing practice.
