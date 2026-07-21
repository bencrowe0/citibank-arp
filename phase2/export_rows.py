"""Generate paste-ready Data Entry rows for the Phase 2 (apples-to-apples,
104-combo) LLM run - one row per scoreable combo, in the exact Data Entry
column order (Company, Ticker blank/auto, Year, Quarter, Rater, Type,
Sentiment Score, Decision, Time blank, Prior Close, Next Day Open,
Actual % Change/Actual Direction/Prediction Correct/Position/Net P&L
blank - sheet formulas fill these, Notes).
Company spelling matches the `list` sheet exactly so the XLOOKUP resolves.

No live sheet editing (per project rule) - just writes a CSV for copy-paste.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import blend  # noqa: E402
from export_sheet_rows import fetch_prices, load_notes  # noqa: E402

COMPANY_NAMES = {
    "ABNB": "Airbnb", "AMZN": "Amazon", "AMD": "AMD", "AAPL": "Apple",
    "BAC": "Bank of America", "BA": "Boeing", "CVS": "CVS Health",
    "SCHW": "Charles Schwab", "C": "Citigroup", "KO": "Coca-Cola",
    "COIN": "Coinbase", "DIS": "Disney", "LLY": "Eli Lilly",
    "GS": "Goldman Sachs", "IBM": "IBM", "JPM": "JPMorgan",
    "LOW": "Lowe's", "LULU": "Lululemon", "AMKBY": "Maersk",
    "MCD": "McDonald's", "META": "Meta", "NFLX": "Netflix", "NKE": "Nike",
    "NVDA": "Nvidia", "TGT": "Target", "TSLA": "Tesla", "UBER": "Uber",
    "WMT": "Walmart",
}

QUARTER_NUM = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}


def main() -> None:
    issuers = [l.strip() for l in open(BASE_DIR / "phase2" / "issuers.txt") if l.strip()]

    out_rows = []
    errors = []

    for issuer in issuers:
        manifest = json.loads((BASE_DIR / "manifests" / f"{issuer}_reports.json").read_text(encoding="utf-8"))
        reports = sorted(manifest["reports"], key=lambda r: (r["fiscal_period"].split()[1], int(r["fiscal_period"][2])))
        for r in reports:
            ticker = r["ticker"]
            doc_id = r["document_id"]
            year = r["fiscal_period"].split()[1]
            quarter = f"Q{r['fiscal_period'][2]}"
            report_date = r["report_date"]

            try:
                blend_result = blend.blend_document(issuer, doc_id)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{issuer}/{doc_id}: blend failed: {exc}")
                continue

            try:
                prior_close, next_day_open = fetch_prices(ticker, report_date)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{issuer}/{doc_id}: price fetch failed: {exc}")
                prior_close, next_day_open = "", ""

            notes = load_notes(issuer, doc_id, blend_result.micro_score, blend_result.blended_score,
                                blend_result.news_score is not None)

            out_rows.append({
                "Company": COMPANY_NAMES[ticker],
                "Ticker": "",  # auto via XLOOKUP off Company
                "Year": year,
                "Quarter": quarter,
                "Rater": "Ben/DeepSeek",
                "Type": "LLM",
                "Sentiment Score": f"{blend_result.blended_score:.2f}",
                "Decision": blend_result.signal,
                "Time": "",
                "Prior Close": prior_close,
                "Next Day Open": next_day_open,
                "Actual % Change": "",
                "Actual Direction": "",
                "Prediction Correct": "",
                "Position": "",
                "Net P&L": "",
                "Notes": notes,
            })

    out_path = BASE_DIR / "phase2" / "data_entry_rows.tsv"
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()), delimiter="\t")
        w.writeheader()
        w.writerows(out_rows)

    print(f"Wrote {len(out_rows)} rows -> {out_path}")
    if errors:
        print(f"\n{len(errors)} errors:")
        for e in errors:
            print(" ", e)


if __name__ == "__main__":
    main()
