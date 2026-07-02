"""
eval/outcomes.py
Fetches actual stock price outcomes via yfinance and buckets them into a
ground-truth BUY/HOLD/SELL label - the label the pipeline's predictions are
scored against.

Two distinct threshold concepts exist in this project and must never be
confused:
  - hold_upper / hold_lower (report_pipeline.py, run_reports.py, blend.py):
    thresholds on the LLM's -1..+1 SENTIMENT SCORE, used to derive a
    prediction (BUY/HOLD/SELL) from what the model said about a document.
  - outcome_upper / outcome_lower (this module): thresholds on the stock's
    actual forward RETURN, used to derive the ground-truth label the
    prediction is checked against. This module always uses the outcome_*
    names - never hold_upper/hold_lower - so the two can't be confused by a
    reader grepping the codebase.

Entry price is the next trading-day CLOSE on/after report_date (conservative:
avoids assuming same-day intraday reaction is fully captured, since some
reports release after market close).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yfinance as yf

OUTCOME_UPPER_DEFAULT = 0.03
OUTCOME_LOWER_DEFAULT = -0.03
DEFAULT_WINDOW_TRADING_DAYS = 5


@dataclass(frozen=True)
class ForwardReturn:
    document_id: str
    ticker: str
    report_date: str
    window_trading_days: int
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    forward_return: float
    outcome_label: str


def bucket_outcome(
    forward_return: float,
    outcome_upper: float = OUTCOME_UPPER_DEFAULT,
    outcome_lower: float = OUTCOME_LOWER_DEFAULT,
) -> str:
    if forward_return > outcome_upper:
        return "BUY"
    if forward_return < outcome_lower:
        return "SELL"
    return "HOLD"


def fetch_forward_return(
    document_id: str,
    ticker: str,
    report_date: str,
    window_trading_days: int = DEFAULT_WINDOW_TRADING_DAYS,
    outcome_upper: float = OUTCOME_UPPER_DEFAULT,
    outcome_lower: float = OUTCOME_LOWER_DEFAULT,
) -> ForwardReturn | None:
    report_dt = datetime.strptime(report_date, "%Y-%m-%d")
    # Pull a wide-enough window to guarantee window_trading_days of trading
    # sessions exist after report_date even across long weekends/holidays.
    start = report_dt.strftime("%Y-%m-%d")
    end = (report_dt + timedelta(days=window_trading_days * 3 + 10)).strftime("%Y-%m-%d")

    history = yf.Ticker(ticker).history(start=start, end=end)
    if history.empty or len(history) < window_trading_days + 1:
        return None

    entry_row = history.iloc[0]
    exit_row = history.iloc[window_trading_days]
    entry_price = float(entry_row["Close"])
    exit_price = float(exit_row["Close"])
    forward_return = (exit_price - entry_price) / entry_price

    return ForwardReturn(
        document_id=document_id,
        ticker=ticker,
        report_date=report_date,
        window_trading_days=window_trading_days,
        entry_date=str(history.index[0].date()),
        entry_price=round(entry_price, 4),
        exit_date=str(history.index[window_trading_days].date()),
        exit_price=round(exit_price, 4),
        forward_return=round(forward_return, 6),
        outcome_label=bucket_outcome(forward_return, outcome_upper, outcome_lower),
    )


def collect_outcomes_for_issuer(
    issuer: str,
    results_dir: Path,
    window_trading_days: int = DEFAULT_WINDOW_TRADING_DAYS,
    outcome_upper: float = OUTCOME_UPPER_DEFAULT,
    outcome_lower: float = OUTCOME_LOWER_DEFAULT,
) -> list[ForwardReturn]:
    outcomes: list[ForwardReturn] = []
    for result_path in sorted(results_dir.glob("*.json")):
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        metadata = payload.get("report_metadata", {})
        ticker = metadata.get("ticker")
        report_date = metadata.get("report_date")
        document_id = payload.get("document_id")
        if not ticker or not report_date:
            print(f"  Skipping {result_path.name}: missing ticker/report_date in report_metadata")
            continue

        outcome = fetch_forward_return(
            document_id, ticker, report_date, window_trading_days, outcome_upper, outcome_lower
        )
        if outcome is None:
            print(f"  Skipping {document_id}: no price data available for {ticker} around {report_date}")
            continue
        outcomes.append(outcome)

    return outcomes
