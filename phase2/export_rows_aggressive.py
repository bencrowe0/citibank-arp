"""One-off: Data Entry-format TSV for the sweep's global_best combo
(micro=0.55, macro=0.45, news=0, quant=0; hold_upper=0.25, hold_lower=-0.05),
99 trades, total_return=167.66% per outputs/global/summary/phase2_pnl_weight_threshold_sweep.json.

NOT PSR/permutation-validated (PSR=0.0, perm p=0.150) - candidate row only, not a
proposal to change blend.py's DEFAULT_WEIGHTS. All columns computed directly (no
blank sheet-formula columns) so the row is paste-ready as literal values.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from blend import blend_scores, derive_signal  # noqa: E402
from export_sheet_rows import fetch_prices  # noqa: E402
from phase2.export_rows import COMPANY_NAMES, parse_document_id  # noqa: E402
import backtest  # noqa: E402

CALIBRATION_CSV = BASE_DIR / "outputs" / "global" / "summary" / "global_outcome_calibration_phase2.csv"
WEIGHTS = (0.55, 0.45, 0.0, 0.0)
HOLD_UPPER, HOLD_LOWER = 0.25, -0.05
COST_BPS, SHORT_BORROW_BPS = 10.0, 0.0
FLAT_BAND = 0.02  # Settings!B3 = 2%
RATER = "Ben/DeepSeek (aggressive: micro.55/macro.45)"


def _num(x):
    if x in (None, "", "None"):
        return None
    return float(x)


def main() -> None:
    with open(CALIBRATION_CSV, newline="", encoding="utf-8") as fh:
        cal_rows = list(csv.DictReader(fh))

    out_rows = []
    errors = []
    check_preds = []

    for row in cal_rows:
        ticker = row["ticker"]
        report_date = row["report_date"]
        doc_id = row["document_id"]
        micro = float(row["micro_score"])
        macro = _num(row["macro_score"])
        news = _num(row["news_score"])
        quant = _num(row["quant_score"])

        blend_score = blend_scores(micro, macro, news, quant, WEIGHTS)
        decision = derive_signal(blend_score, HOLD_UPPER, HOLD_LOWER)
        quarter, year = parse_document_id(doc_id)

        try:
            prior_close, next_day_open = fetch_prices(ticker, report_date)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{doc_id}: price fetch failed: {exc}")
            continue

        pct_change = (next_day_open - prior_close) / prior_close
        if pct_change >= FLAT_BAND:
            direction = "UP"
        elif pct_change <= -FLAT_BAND:
            direction = "DOWN"
        else:
            direction = "FLAT"

        correct = (
            (decision == "BUY" and direction == "UP")
            or (decision == "SELL" and direction == "DOWN")
            or (decision == "HOLD" and direction == "FLAT")
        )

        position = {"BUY": 1, "SELL": -1, "HOLD": 0}[decision]
        if position == 0:
            net_pnl = 0.0
        else:
            cost = COST_BPS / 1e4 + (SHORT_BORROW_BPS / 1e4 if position < 0 else 0.0)
            net_pnl = position * pct_change - cost

        out_rows.append({
            "Company": COMPANY_NAMES.get(ticker, ticker),
            "Ticker": ticker,
            "Year": year,
            "Quarter": quarter,
            "Rater": RATER,
            "Type (Human/LLM)": "LLM",
            "Sentiment Score (-1 to +1)": f"{blend_score:.4f}",
            "Decision (BUY/HOLD/SELL)": decision,
            "Time (mins) Humans only": "",
            "Prior Close ($)": f"{prior_close:.2f}",
            "Next Day Open ($)": f"{next_day_open:.2f}",
            "Actual % Change": f"{pct_change*100:.2f}%",
            "Actual Direction": direction,
            "Prediction Correct?": "YES" if correct else "NO",
            "Position": position,
            "Net P&L": f"{net_pnl*100:.4f}%",
            "Notes / Risks Flagged": f"micro={micro:.2f} macro={'n/a' if macro is None else f'{macro:.2f}'} "
                                      f"w=[0.55,0.45,0,0] thr=(0.25,-0.05) - PSR=0.0/perm_p=0.150, unvalidated",
        })

        check_preds.append(backtest.Prediction(
            rater=RATER, kind="LM", ticker=ticker, report_date=report_date,
            decision=decision, prior_close=prior_close, next_day_open=next_day_open,
        ))

    out_path = BASE_DIR / "phase2" / "data_entry_rows_aggressive.tsv"
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()), delimiter="\t")
        w.writeheader()
        w.writerows(out_rows)

    n_trades = sum(1 for r in out_rows if r["Decision (BUY/HOLD/SELL)"] != "HOLD")
    print(f"Wrote {len(out_rows)} rows ({n_trades} BUY/SELL, {len(out_rows) - n_trades} HOLD) -> {out_path}")
    if errors:
        print(f"\n{len(errors)} price errors:")
        for e in errors:
            print(" ", e)

    stats = backtest.simulate(check_preds, COST_BPS, SHORT_BORROW_BPS)
    print(f"\nSelf-check vs sweep JSON (expect total_return=167.66%, trades=99):")
    print(f"  computed: total_return={stats['total_return_pct']}% trades={stats['n_trades']} "
          f"hit_rate={stats['hit_rate']*100:.1f}% sharpe={stats['sharpe_per_trade']}")


if __name__ == "__main__":
    main()
