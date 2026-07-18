# Handoff

## Goal
Give Citibank a version of the earnings-prediction tool that beats the always-FLAT baseline on the group's overnight close-to-open gap — then, when that proved impossible on accuracy, shift the scorecard from raw 3-class accuracy to a costs-aware P&L backtest that any rater (LLM or human) can be judged on.

## Current State
- **Proven (again, across all thresholds):** overnight-gap raw accuracy CANNOT beat the always-FLAT baseline. Swept B3 in {1,1.5,2,2.5,3}% × {overnight, 5-day}, LOOCV-honest. Overnight dead at every threshold (default & tuned lose, binom p 0.83→1.0). 5-day WINS and is significant at ±2.5% (0.435 vs 0.351, p=0.029) and ±3% (0.466 vs 0.382, p=0.031); default beats tuned everywhere.
- **New metric shipped:** `backtest.py` — predictor-agnostic overnight-gap P&L backtest (BUY→long, SELL→short, HOLD→flat; P&L = position×gap − costs). Deployed LLM, net 10 bps: 44 trades, 59% hit, **+173% total ($1→$2.73)**, +2.5%/trade, Sharpe/trade 2.48, max DD 6.5%; direction breakdown 11 correct / 29 flat / **only 4 wrong-direction**. Always-long LOSES (−16%, 50.8% DD); always-flat = 0. Robust to 50 bps cost (+129%).
- **Reframe (the headline insight):** accuracy penalizes a bet-on-a-flat the same as a bet-in-the-wrong-direction; P&L doesn't. Same LLM fails the accuracy test (0.55 vs 0.69) but wins the money test.
- **Docs updated:** CLAUDE.md "Round 8" added + run block + Known-Limitations pointer; README.md "Backtest (P&L evaluation)" section added.
- **Shareable deliverable published:** equity-curve report Artifact → https://claude.ai/code/artifact/e88a0810-f670-497e-89c7-d8bce933522e
- **Nothing committed to git yet this session.** Branch: task/task.

## Files in Flight
- `backtest.py` — committed successor: P&L engine + LLM adapter + `--sheet` human adapter + costs + equity curve + direction breakdown. NEW.
- `outputs/global/summary/backtest_equity.csv` — per-trade equity curve output. NEW.
- `CLAUDE.md`, `README.md` — updated with Round 8 / backtest usage.
- `docs/news/jpm/JPM_FQ4_2020.txt` — one leak-free news digest written before the backfill was deprioritized. NEW.
- `~/.claude/plans/this-is-the-current-iterative-hennessy.md` — the approved plan.
- Throwaway diagnostics in session scratchpad (not committed): `b3_window_sweep.py`, `overnight_pnl.py`, `backtest_report.html` (the Artifact source).

## Changed
- Added `backtest.py` (P&L metric, humans + LLM, costs, equity curve).
- Added Round 8 section to CLAUDE.md; added backtest lines to its run block; added P&L pointer to the last Known-Limitations bullet.
- Added "Backtest (P&L evaluation)" section to README.md.
- Wrote `outputs/global/summary/backtest_equity.csv`.
- Wrote one news digest `docs/news/jpm/JPM_FQ4_2020.txt` (backfill then paused).
- Published equity-curve Artifact.

## Failed Attempts
- **107-quarter news backfill (Phase 1 of approved plan)** — started (1 digest), then DEPRIORITIZED: the B3×window diagnostic showed backfill (est ~0.684) cannot clear the 0.687 overnight baseline, so it is not the lever for the overnight goal. Old-quarter web sourcing also came back thin/contaminated (wrong-year, post-earnings) — real leak risk, slow.
- **Options-implied move / analyst-estimate dispersion (Phase 2)** — dropped: yfinance has no as-of-date historical options/estimates, so they can't be backtested on the 131 historical quarters with free data. Could be added as forward/live-only signals.
- **Beating overnight raw accuracy by any tuning** — impossible at every integer/half-integer B3; confirmed 4 ways prior + this round's full sweep.

## Next Step
Get the group sheet exported as CSV (columns `Rater, Type, Ticker, Year, Quarter, Decision, Prior Close, Next Day Open`) and run `python backtest.py --sheet <export.csv>` to score every HUMAN rater on the identical strategy — then optionally build the "common-quarters mode" (score all raters only on prints every rater covered) so human-vs-LLM totals are strictly apples-to-apples. Also decide whether to `git commit` this session's work (backtest.py + doc updates) on branch task/task.
