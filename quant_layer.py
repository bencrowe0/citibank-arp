"""
quant_layer.py
Route D quant layer - a deterministic, free (yfinance-only) numeric signal per
company/quarter, scored WITHOUT any LLM call. It exists to add hard-number
signal orthogonal to the three text-sentiment layers (micro/macro/news).

Design principles (mirroring the discipline of the other layers):

  * Free + no API key. Everything comes from yfinance, which eval/outcomes.py
    already depends on.
  * No LLM cost. The score is a fixed, documented arithmetic combination of
    standardized sub-metrics - not a model call - so it adds zero token cost
    and is fully reproducible.
  * Leakage discipline. NO input is dated after report_date:
      - momentum / realized volatility: trailing window ending on the last
        close STRICTLY BEFORE report_date (pre-print).
      - macro numerics (^VIX, ^TNX): last close on/before report_date (public
        market data available at prediction time).
      - EPS surprise: revealed AT the earnings release (== report_date), i.e.
        contemporaneous with the very press release the micro layer reads, and
        the forward-return outcome is measured strictly AFTER that. So it is
        part of the information set at prediction time, not a peek at the
        outcome - the same information class as the micro layer.
  * No sign-fitting to outcomes. Each sub-metric's sign comes from a stated
    economic prior (documented below), and the composite is an equal-weight
    mean of the standardized directional sub-metrics. Normalization constants
    are fixed to typical market scales, NOT tuned against realized returns.
    Whether this layer actually helps is decided by ablation in eval/, not by
    hand-fitting it here.

Sub-metrics and their priors:
  * momentum  (+): trailing ~21-trading-day return into the print. Weak prior
    (short-horizon trend continuation).
  * eps_surprise (+): EPS Surprise(%) vs consensus. Strong prior
    (post-earnings-announcement drift).
  * macro_num (kept as a SEPARATE, toggleable sub-component so eval/ can test
    it on its own): elevated ^VIX -> risk-off (-); rising 10Y yield (^TNX,
    21d change) -> headwind (-).

  realized volatility is computed and stored for audit but is NOT directional,
  so it is deliberately kept OUT of the composite (inventing a sign for it
  would be exactly the outcome-fitting this project avoids).

Availability (probed, free tier): price history and ^VIX/^TNX/^IRX go back
years; EPS Surprise(%) is available via get_earnings_dates (needs lxml).
Revenue surprise, historical options-implied move, and analyst-revision
breadth are NOT freely/historically available and are excluded by design (same
treatment as the long 10-K/10-Q filings).

Interface mirrors llm_news.get_news_score: get_quant_score(issuer, document_id)
returns a payload carrying sentiment.score (the composite), cached idempotently
under outputs/quant/<issuer>/results/<document_id>.json. Raw pulls are cached
under data/quantitative/ for replication.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

from report_pipeline import BASE_DIR, OUTPUTS_DIR, load_manifest

QUANT_RESULTS_DIR = OUTPUTS_DIR / "quant"
DATA_DIR = BASE_DIR / "data" / "quantitative"

MANIFESTS = {
    "boeing": BASE_DIR / "manifests" / "boeing_reports.json",
    "jpm": BASE_DIR / "manifests" / "jpm_reports.json",
    "netflix": BASE_DIR / "manifests" / "netflix_reports.json",
    "bank_of_america": BASE_DIR / "manifests" / "bank_of_america_reports.json",
    "disney": BASE_DIR / "manifests" / "disney_reports.json",
    "target": BASE_DIR / "manifests" / "target_reports.json",
}

# --- Fixed normalization scales (typical market magnitudes, NOT outcome-fit) ---
MOMENTUM_WINDOW_DAYS = 21          # ~1 trading month into the print
MOMENTUM_SCALE = 0.15              # a ~15% monthly move maps to ~tanh(1)
VOL_WINDOW_DAYS = 21
SURPRISE_SCALE = 0.25             # a 25% EPS surprise maps to ~tanh(1)
VIX_CENTER = 19.0                 # long-run-ish median level
VIX_SCALE = 15.0
TNX_CHANGE_WINDOW_DAYS = 21
TNX_CHANGE_SCALE = 0.5           # 0.5 percentage-point 21d move maps to ~tanh(1)
EARNINGS_MATCH_TOLERANCE_DAYS = 5


def _clamp(x: float) -> float:
    return max(-1.0, min(1.0, x))


def _tanh_scale(value: float, scale: float) -> float:
    return _clamp(math.tanh(value / scale))


def _to_naive_date_index(frame: pd.DataFrame) -> pd.DataFrame:
    """yfinance returns a tz-aware DatetimeIndex; drop tz so it compares
    cleanly against a naive report_date."""
    frame = frame.copy()
    frame.index = pd.to_datetime(frame.index).tz_localize(None)
    return frame


def _fetch_price_history(ticker: str, report_date: str, lookback_days: int = 90) -> pd.DataFrame:
    report_dt = datetime.strptime(report_date, "%Y-%m-%d")
    start = (report_dt - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    # +1 day so an on-date close is included when we need on/before semantics.
    end = (report_dt + timedelta(days=1)).strftime("%Y-%m-%d")
    history = yf.Ticker(ticker).history(start=start, end=end)
    if history.empty:
        return history
    return _to_naive_date_index(history)


def _closes_strictly_before(history: pd.DataFrame, report_date: str) -> pd.Series:
    report_dt = pd.Timestamp(report_date)
    return history.loc[history.index < report_dt, "Close"]


def _closes_on_or_before(history: pd.DataFrame, report_date: str) -> pd.Series:
    report_dt = pd.Timestamp(report_date)
    return history.loc[history.index <= report_dt, "Close"]


def compute_momentum(ticker: str, report_date: str) -> dict[str, Any]:
    """Trailing MOMENTUM_WINDOW_DAYS return ending at the last close STRICTLY
    before report_date. Positive prior: trend continuation into the print."""
    history = _fetch_price_history(ticker, report_date)
    closes = _closes_strictly_before(history, report_date)
    if len(closes) < MOMENTUM_WINDOW_DAYS + 1:
        return {"raw_return": None, "score": None, "available": False}
    window = closes.iloc[-(MOMENTUM_WINDOW_DAYS + 1):]
    raw_return = float(window.iloc[-1] / window.iloc[0] - 1.0)
    return {
        "raw_return": round(raw_return, 6),
        "window_start_date": str(window.index[0].date()),
        "window_end_date": str(window.index[-1].date()),
        "score": round(_tanh_scale(raw_return, MOMENTUM_SCALE), 6),
        "available": True,
    }


def compute_volatility(ticker: str, report_date: str) -> dict[str, Any]:
    """Trailing realized daily-return volatility (annualized), audit-only -
    stored but deliberately excluded from the directional composite."""
    history = _fetch_price_history(ticker, report_date)
    closes = _closes_strictly_before(history, report_date)
    if len(closes) < VOL_WINDOW_DAYS + 1:
        return {"annualized_vol": None, "available": False}
    window = closes.iloc[-(VOL_WINDOW_DAYS + 1):]
    daily_returns = window.pct_change().dropna()
    annualized = float(daily_returns.std() * math.sqrt(252))
    return {"annualized_vol": round(annualized, 6), "available": True}


def compute_eps_surprise(ticker: str, report_date: str) -> dict[str, Any]:
    """EPS Surprise(%) for the earnings event matching report_date. Revealed AT
    the print (contemporaneous with the micro layer's press release), so it is
    in the prediction-time information set, not a peek at the forward return.
    Positive prior: post-earnings-announcement drift."""
    report_dt = pd.Timestamp(report_date)
    try:
        earnings = yf.Ticker(ticker).get_earnings_dates(limit=40)
    except Exception as exc:  # noqa: BLE001 - degrade gracefully if lxml/data missing
        return {"surprise_pct": None, "score": None, "available": False, "error": str(exc)}
    if earnings is None or earnings.empty or "Surprise(%)" not in earnings.columns:
        return {"surprise_pct": None, "score": None, "available": False}

    earnings = earnings.copy()
    earnings.index = pd.to_datetime(earnings.index).tz_localize(None)
    deltas = (earnings.index - report_dt).to_series(index=earnings.index).abs()
    nearest_idx = deltas.idxmin()
    if abs((nearest_idx - report_dt).days) > EARNINGS_MATCH_TOLERANCE_DAYS:
        return {"surprise_pct": None, "score": None, "available": False}

    surprise = earnings.loc[nearest_idx, "Surprise(%)"]
    if pd.isna(surprise):
        return {"surprise_pct": None, "score": None, "available": False}
    surprise = float(surprise)
    return {
        "surprise_pct": round(surprise, 4),
        "matched_earnings_date": str(pd.Timestamp(nearest_idx).date()),
        "score": round(_tanh_scale(surprise / 100.0, SURPRISE_SCALE), 6),
        "available": True,
    }


def compute_macro_numeric(report_date: str) -> dict[str, Any]:
    """Elevated ^VIX -> risk-off (-); rising 10Y yield (^TNX 21d change) ->
    headwind (-). Kept separate/toggleable so eval/ can ablate it on its own.
    Uses last close on/before report_date (public market data)."""
    vix_hist = _fetch_price_history("^VIX", report_date)
    tnx_hist = _fetch_price_history("^TNX", report_date)

    vix_closes = _closes_on_or_before(vix_hist, report_date) if not vix_hist.empty else pd.Series(dtype=float)
    tnx_closes = _closes_on_or_before(tnx_hist, report_date) if not tnx_hist.empty else pd.Series(dtype=float)

    if vix_closes.empty or len(tnx_closes) < TNX_CHANGE_WINDOW_DAYS + 1:
        return {"vix_level": None, "tnx_change": None, "score": None, "available": False}

    vix_level = float(vix_closes.iloc[-1])
    vix_score = -_tanh_scale(vix_level - VIX_CENTER, VIX_SCALE)

    tnx_window = tnx_closes.iloc[-(TNX_CHANGE_WINDOW_DAYS + 1):]
    tnx_change = float(tnx_window.iloc[-1] - tnx_window.iloc[0])
    tnx_score = -_tanh_scale(tnx_change, TNX_CHANGE_SCALE)

    macro_score = (vix_score + tnx_score) / 2.0
    return {
        "vix_level": round(vix_level, 4),
        "vix_score": round(vix_score, 6),
        "tnx_change": round(tnx_change, 6),
        "tnx_score": round(tnx_score, 6),
        "score": round(_clamp(macro_score), 6),
        "available": True,
    }


def compute_quant_metrics(ticker: str, report_date: str) -> dict[str, Any]:
    momentum = compute_momentum(ticker, report_date)
    volatility = compute_volatility(ticker, report_date)
    eps_surprise = compute_eps_surprise(ticker, report_date)
    macro_numeric = compute_macro_numeric(report_date)

    # Composite = equal-weight mean of available DIRECTIONAL company sub-scores
    # (momentum, eps_surprise). Macro numeric is stored but kept OUT of the
    # headline composite so it can be ablated as a separate component.
    directional = [m["score"] for m in (momentum, eps_surprise) if m.get("score") is not None]
    company_score = round(sum(directional) / len(directional), 6) if directional else None

    # A second composite that folds the macro sub-score in, for the "with
    # macro-numeric" ablation arm - not the default headline score.
    with_macro = [s for s in (company_score, macro_numeric.get("score")) if s is not None]
    company_plus_macro_score = round(sum(with_macro) / len(with_macro), 6) if with_macro else None

    return {
        "momentum": momentum,
        "volatility": volatility,
        "eps_surprise": eps_surprise,
        "macro_numeric": macro_numeric,
        "quant_score": company_score,
        "quant_score_with_macro": company_plus_macro_score,
    }


def _lookup_report(issuer: str, document_id: str):
    reports = [r for r in load_manifest(MANIFESTS[issuer]) if r.document_id == document_id]
    return reports[0] if reports else None


def score_quant_for_report(issuer: str, document_id: str) -> dict[str, Any] | None:
    report = _lookup_report(issuer, document_id)
    if report is None:
        return None

    results_dir = QUANT_RESULTS_DIR / issuer / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    result_path = results_dir / f"{document_id}.json"
    if result_path.exists():
        return json.loads(result_path.read_text(encoding="utf-8"))

    metrics = compute_quant_metrics(report.ticker, report.report_date)
    payload = {
        "document_id": f"{document_id}_QUANT",
        "base_document_id": document_id,
        "issuer": issuer,
        "ticker": report.ticker,
        "sector": report.sector,
        "report_date": report.report_date,
        # sentiment.score mirrors the other layers' interface so blend/eval can
        # read it uniformly. It carries no cost_log because there is no API call.
        "sentiment": {"score": metrics["quant_score"]},
        "quant_metrics": metrics,
        "cost_log": {"estimated_cost_usd": 0.0, "source": "yfinance", "model": "deterministic"},
    }
    result_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def get_quant_score(issuer: str, document_id: str) -> dict[str, Any] | None:
    return score_quant_for_report(issuer, document_id)


def score_all_quant(issuer: str) -> list[dict[str, Any]]:
    reports = [r for r in load_manifest(MANIFESTS[issuer]) if r.issuer.lower() == issuer.lower()]
    results = []
    for report in reports:
        result = score_quant_for_report(issuer, report.document_id)
        if result is not None:
            results.append(result)
    return results


def main() -> int:
    for issuer in MANIFESTS:
        print(f"\n=== {issuer} ===")
        for result in score_all_quant(issuer):
            m = result["quant_metrics"]
            print(
                f"{result['base_document_id']}: quant={result['sentiment']['score']} "
                f"(mom={m['momentum'].get('score')} eps={m['eps_surprise'].get('score')} "
                f"macro={m['macro_numeric'].get('score')})"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
