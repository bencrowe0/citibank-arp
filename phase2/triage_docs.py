"""Phase 2 coverage triage: match the 104 human-evaluated company+quarter combos
against files in OneDrive_2026-07-18/Phase 2/<Company>/**, and report what's
usable, what's thin, and what's missing entirely. Read-only, no LLM calls."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))



MIN_FILE_BYTES = 15_000  # rough proxy for MIN_EXTRACTED_TEXT_CHARS without opening the file


def quick_extract_check(path: Path) -> tuple[bool, int, str | None]:
    """File-size-only proxy for "this doc has real content" - no file open/read
    at all, so it can't be slowed or hung by OneDrive on-demand hydration or by
    parsing huge PDFs. Real extraction (pypdf + pdfplumber fallback, exact char
    counts) happens for real during the actual report_pipeline run (--dry-run
    step) - triage only needs a rough presence/size signal, not exact chars."""
    try:
        size = path.stat().st_size
        return size >= MIN_FILE_BYTES, size, None
    except Exception as exc:  # noqa: BLE001
        return False, 0, str(exc)[:200]

DOCS_ROOT = BASE_DIR / "OneDrive_2026-07-18" / "Phase 2"

# (company_display, ticker, year, quarter) - the 104 combos humans evaluated,
# pulled from Data Entry rows where Type == "Human".
TARGET_COMBOS = [
    ("AMD", "AMD", 2025, "Q2"), ("AMD", "AMD", 2025, "Q4"), ("AMD", "AMD", 2026, "Q1"),
    ("Airbnb", "ABNB", 2025, "Q2"), ("Airbnb", "ABNB", 2025, "Q3"), ("Airbnb", "ABNB", 2025, "Q4"), ("Airbnb", "ABNB", 2026, "Q1"),
    ("Amazon", "AMZN", 2025, "Q3"), ("Amazon", "AMZN", 2025, "Q4"), ("Amazon", "AMZN", 2026, "Q1"),
    ("Apple", "AAPL", 2025, "Q3"), ("Apple", "AAPL", 2025, "Q4"), ("Apple", "AAPL", 2026, "Q1"),
    ("Bank of America", "BAC", 2025, "Q1"), ("Bank of America", "BAC", 2025, "Q2"), ("Bank of America", "BAC", 2025, "Q3"), ("Bank of America", "BAC", 2025, "Q4"),
    ("Boeing", "BA", 2025, "Q1"), ("Boeing", "BA", 2025, "Q2"), ("Boeing", "BA", 2025, "Q3"), ("Boeing", "BA", 2025, "Q4"),
    ("CVS Health", "CVS", 2026, "Q1"),
    ("Charles Schwab", "SCHW", 2025, "Q1"), ("Charles Schwab", "SCHW", 2025, "Q2"), ("Charles Schwab", "SCHW", 2025, "Q3"), ("Charles Schwab", "SCHW", 2025, "Q4"), ("Charles Schwab", "SCHW", 2026, "Q1"),
    ("Citigroup", "C", 2025, "Q1"), ("Citigroup", "C", 2025, "Q2"), ("Citigroup", "C", 2025, "Q3"), ("Citigroup", "C", 2025, "Q4"),
    ("Coca-Cola", "KO", 2025, "Q2"), ("Coca-Cola", "KO", 2025, "Q4"), ("Coca-Cola", "KO", 2026, "Q1"),
    ("Coinbase", "COIN", 2025, "Q3"), ("Coinbase", "COIN", 2025, "Q4"), ("Coinbase", "COIN", 2026, "Q1"),
    ("Disney", "DIS", 2025, "Q1"), ("Disney", "DIS", 2025, "Q3"), ("Disney", "DIS", 2025, "Q4"),
    ("Eli Lilly", "LLY", 2025, "Q3"), ("Eli Lilly", "LLY", 2025, "Q4"), ("Eli Lilly", "LLY", 2026, "Q1"),
    ("Goldman Sachs", "GS", 2025, "Q1"), ("Goldman Sachs", "GS", 2025, "Q2"), ("Goldman Sachs", "GS", 2025, "Q3"), ("Goldman Sachs", "GS", 2025, "Q4"), ("Goldman Sachs", "GS", 2026, "Q1"), ("Goldman Sachs", "GS", 2026, "Q2"),
    ("IBM", "IBM", 2025, "Q2"), ("IBM", "IBM", 2025, "Q4"), ("IBM", "IBM", 2026, "Q1"),
    ("JPMorgan", "JPM", 2025, "Q1"), ("JPMorgan", "JPM", 2025, "Q2"), ("JPMorgan", "JPM", 2025, "Q3"), ("JPMorgan", "JPM", 2025, "Q4"), ("JPMorgan", "JPM", 2026, "Q1"),
    ("Lowe's", "LOW", 2025, "Q1"), ("Lowe's", "LOW", 2025, "Q2"), ("Lowe's", "LOW", 2025, "Q3"), ("Lowe's", "LOW", 2025, "Q4"), ("Lowe's", "LOW", 2026, "Q1"),
    ("Lululemon", "LULU", 2025, "Q3"), ("Lululemon", "LULU", 2025, "Q4"), ("Lululemon", "LULU", 2026, "Q1"),
    ("Maersk", "AMKBY", 2025, "Q1"), ("Maersk", "AMKBY", 2025, "Q2"), ("Maersk", "AMKBY", 2025, "Q3"), ("Maersk", "AMKBY", 2025, "Q4"),
    ("McDonald's", "MCD", 2024, "Q4"), ("McDonald's", "MCD", 2025, "Q4"), ("McDonald's", "MCD", 2026, "Q1"),
    ("Meta", "META", 2025, "Q3"), ("Meta", "META", 2025, "Q4"), ("Meta", "META", 2026, "Q1"),
    ("Netflix", "NFLX", 2024, "Q4"), ("Netflix", "NFLX", 2025, "Q1"), ("Netflix", "NFLX", 2025, "Q2"), ("Netflix", "NFLX", 2025, "Q3"), ("Netflix", "NFLX", 2025, "Q4"), ("Netflix", "NFLX", 2026, "Q1"),
    ("Nike", "NKE", 2025, "Q1"), ("Nike", "NKE", 2025, "Q2"), ("Nike", "NKE", 2025, "Q3"),
    ("Nvidia", "NVDA", 2025, "Q1"), ("Nvidia", "NVDA", 2025, "Q2"), ("Nvidia", "NVDA", 2025, "Q3"), ("Nvidia", "NVDA", 2025, "Q4"),
    ("Target", "TGT", 2025, "Q1"), ("Target", "TGT", 2025, "Q2"), ("Target", "TGT", 2025, "Q3"), ("Target", "TGT", 2026, "Q1"),
    ("Tesla", "TSLA", 2025, "Q3"), ("Tesla", "TSLA", 2025, "Q4"), ("Tesla", "TSLA", 2026, "Q1"),
    ("Uber", "UBER", 2025, "Q1"), ("Uber", "UBER", 2025, "Q2"), ("Uber", "UBER", 2025, "Q4"), ("Uber", "UBER", 2026, "Q1"),
    ("Walmart", "WMT", 2025, "Q1"), ("Walmart", "WMT", 2025, "Q2"), ("Walmart", "WMT", 2025, "Q3"), ("Walmart", "WMT", 2025, "Q4"), ("Walmart", "WMT", 2026, "Q1"),
]

TICKER_TO_FOLDER = {
    "ABNB": "Airbnb", "AMZN": "Amazon", "AMD": "AMD", "AAPL": "Apple",
    "BAC": "bank of america", "BA": "Boeing", "CVS": "CVS Health",
    "SCHW": "Charles Schwab", "C": "Citigroup", "KO": "Coca-Cola",
    "COIN": "Coin Base", "DIS": "Disney", "LLY": "Eli Lilly",
    "GS": "Goldman Sachs", "IBM": "IBM", "JPM": "JPMC Documents",
    "LOW": "Lowe's", "LULU": "Lululemon", "AMKBY": "Maersk",
    "MCD": "McDonald's", "META": "META", "NFLX": "Netflix", "NKE": "Nike",
    "NVDA": "Nvidia", "TGT": "Target", "TSLA": "Tesla", "UBER": "Uber",
    "WMT": "Walmart",
}

TICKER_TO_SLUG = {
    "ABNB": "airbnb", "AMZN": "amazon", "AMD": "amd", "AAPL": "apple",
    "BAC": "bank_of_america", "BA": "boeing", "CVS": "cvs_health",
    "SCHW": "charles_schwab", "C": "citigroup", "KO": "coca_cola",
    "COIN": "coinbase", "DIS": "disney", "LLY": "eli_lilly",
    "GS": "goldman_sachs", "IBM": "ibm", "JPM": "jpm",
    "LOW": "lowes", "LULU": "lululemon", "AMKBY": "maersk",
    "MCD": "mcdonalds", "META": "meta", "NFLX": "netflix", "NKE": "nike",
    "NVDA": "nvidia", "TGT": "target", "TSLA": "tesla", "UBER": "uber",
    "WMT": "walmart",
}

OVERLAP_ISSUERS = {"BAC", "BA", "DIS", "JPM", "NFLX", "TGT"}

EXTRACTABLE_SUFFIXES = {".pdf", ".html"}

# quarter+year patterns seen in these filenames/paths, cascaded most-specific first
QY_PATTERNS = [
    ("qy4", re.compile(r"q([1-4])[\s_-]*(?:fy)?(20\d{2})", re.IGNORECASE)),   # "q1 2026", "Q1-2026", "q1-fy2025"
    ("qy2", re.compile(r"q([1-4])[\s_-]*(?:fy)?(\d{2})(?!\d)", re.IGNORECASE)),  # "q1-25", "q1-fy25"
    ("yq", re.compile(r"([1-4])q[\s_-]*(\d{2})(?!\d)", re.IGNORECASE)),     # "1Q25", "1Q 25"
    ("yq4", re.compile(r"(20\d{2})[\s_-]*q([1-4])", re.IGNORECASE)),       # "2025-Q1", swapped order
]

ISO_DATE_PATTERN = re.compile(r"(20\d{2})[-_](\d{1,2})[-_](\d{1,2})")
MONTH_NAME_DATE_PATTERN = re.compile(
    r"(20\d{2})-([a-zA-Z]+)-(\d{1,2})|(\d{1,2})-([a-zA-Z]+)-(20\d{2})"
)
FOLDER_Q_PATTERN = re.compile(r"(?:^|[\\/])Q([1-4])(?:[\\/]|$)")


def infer_quarter_year(relpath: str) -> tuple[str, int] | None:
    text = relpath.replace("\\", "/")
    for label, pat in QY_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        g1, g2 = m.groups()
        if label in ("qy4", "qy2"):
            q, y = g1, g2
            year = int(y) if len(y) == 4 else 2000 + int(y)
            return f"Q{q}", year
        if label == "yq":
            q, yy = g1, g2
            return f"Q{q}", 2000 + int(yy)
        if label == "yq4":
            y, q = g1, g2
            return f"Q{q}", int(y)

    # bare Q<N> subfolder (e.g. "Q1/2025prqtr1rslt.pdf") - quarter from folder,
    # year from any 4-digit 20xx token anywhere in the path.
    fm = FOLDER_Q_PATTERN.search(text)
    if fm:
        ym = re.search(r"20\d{2}", text)
        if ym:
            return f"Q{fm.group(1)}", int(ym.group(0))
    return None


def infer_iso_date(relpath: str) -> str | None:
    """Best-effort real calendar date extraction, for filenames that carry a
    release date but no explicit quarter token (used as a chronological-order
    fallback, not a primary match)."""
    text = relpath.replace("\\", "/")
    m = ISO_DATE_PATTERN.search(text)
    if m:
        y, mo, d = m.groups()
        try:
            return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
        except ValueError:
            pass
    m = MONTH_NAME_DATE_PATTERN.search(text)
    if m:
        months = {name.lower(): i for i, name in enumerate(
            ["january", "february", "march", "april", "may", "june", "july",
             "august", "september", "october", "november", "december"], start=1)}
        if m.group(1):
            y, mon, d = m.group(1), m.group(2), m.group(3)
        else:
            d, mon, y = m.group(4), m.group(5), m.group(6)
        mon_num = months.get(mon.lower())
        if mon_num:
            try:
                return f"{int(y):04d}-{mon_num:02d}-{int(d):02d}"
            except ValueError:
                pass
    return None


def classify_doc_type(name: str) -> str:
    n = name.lower()
    if "press" in n or "press-release" in n or "prqtr" in n or n.startswith("0000"):
        return "Press Release"
    if "presentation" in n or "psqtr" in n:
        return "Earnings Presentation"
    if "transcript" in n or "call" in n:
        return "Earnings Call Transcript"
    if "supplement" in n or "supp" in n or "fsqtr" in n:
        return "Supplemental Information"
    if "predictions" in n or "summary" in n:
        return "Other (rater notes, not a source doc)"
    return "Unknown"


def main() -> None:
    report: dict[str, dict] = {}
    unmatched_files: dict[str, list[str]] = {}
    date_inferred_notes: list[str] = []

    for ticker, folder in TICKER_TO_FOLDER.items():
        print(f"[{ticker}] scanning {folder} ...", flush=True)
        company_dir = DOCS_ROOT / folder
        by_qy: dict[tuple[str, int], list[Path]] = {}
        dated_leftovers: list[tuple[str, Path]] = []  # (iso_date, file) - quarter unknown
        if not company_dir.exists():
            unmatched_files[ticker] = [f"MISSING FOLDER: {company_dir}"]
            continue
        for f in company_dir.rglob("*"):
            if not f.is_file():
                continue
            relpath = str(f.relative_to(company_dir))
            qy = infer_quarter_year(relpath)
            if qy is None:
                iso = infer_iso_date(relpath)
                if iso and f.suffix.lower() in EXTRACTABLE_SUFFIXES:
                    dated_leftovers.append((iso, f))
                else:
                    unmatched_files.setdefault(ticker, []).append(relpath)
                continue
            by_qy.setdefault(qy, []).append(f)

        # Chronological-order fallback: some filenames carry a real release date
        # but no explicit quarter token (e.g. Target/Lowe's/Uber transcripts named
        # by date only). Sort those leftovers by date and zip them, in order,
        # against this ticker's target combos that regex-matching left empty -
        # both lists are naturally in fiscal-quarter order, so position-matching
        # is a reasonable heuristic. Flagged "date_inferred" for manual spot-check.
        missing_combos_sorted = sorted(
            [(y, q) for c, tk, y, q in TARGET_COMBOS if tk == ticker and (q, y) not in by_qy],
            key=lambda yq: (yq[0], yq[1]),
        )
        dated_leftovers.sort(key=lambda t: t[0])
        inferred_qy_for_file: dict[Path, tuple[str, int]] = {}
        for (year, quarter), (iso, f) in zip(missing_combos_sorted, dated_leftovers):
            inferred_qy_for_file[f] = (quarter, year)
            date_inferred_notes.append(f"{ticker} {year}{quarter} <- {f.name} (dated {iso})")
        for f, qy in inferred_qy_for_file.items():
            by_qy.setdefault(qy, []).append(f)
        leftover_unused = [f for _, f in dated_leftovers if f not in inferred_qy_for_file]
        for f in leftover_unused:
            unmatched_files.setdefault(ticker, []).append(str(f.relative_to(company_dir)) + " (dated, unassigned)")

        for company, tk, year, quarter in [c for c in TARGET_COMBOS if c[1] == ticker]:
            key = f"{ticker}_{year}_{quarter}"
            files = by_qy.get((quarter, year), [])
            entry = {"company": company, "ticker": ticker, "year": year, "quarter": quarter, "docs": []}
            for f in files:
                suffix = f.suffix.lower()
                doc_info = {
                    "path": str(f.relative_to(BASE_DIR)),
                    "doc_type": classify_doc_type(f.name),
                    "extractable": suffix in EXTRACTABLE_SUFFIXES,
                    "date_inferred": f in inferred_qy_for_file,
                }
                if suffix in EXTRACTABLE_SUFFIXES:
                    ok, size, err = quick_extract_check(f)
                    doc_info["file_bytes"] = size
                    doc_info["extract_ok"] = ok
                    if err:
                        doc_info["extract_error"] = err
                entry["docs"].append(doc_info)
            entry["n_docs"] = len(files)
            entry["n_extractable_ok"] = sum(1 for d in entry["docs"] if d.get("extract_ok"))
            entry["status"] = (
                "MISSING" if not files else
                "THIN(1 doc)" if entry["n_extractable_ok"] == 1 else
                "OK" if entry["n_extractable_ok"] >= 2 else
                "UNUSABLE(extraction failed)"
            )
            report[key] = entry

    out_path = BASE_DIR / "phase2" / "coverage_report.json"
    out_path.write_text(json.dumps({
        "combos": report,
        "unmatched_files": unmatched_files,
        "date_inferred_notes": date_inferred_notes,
    }, indent=2), encoding="utf-8")

    statuses = {}
    for v in report.values():
        statuses[v["status"]] = statuses.get(v["status"], 0) + 1
    print(f"Total target combos: {len(report)}")
    for status, count in sorted(statuses.items()):
        print(f"  {status}: {count}")
    print(f"\nDate-inferred (chronological fallback, spot-check these) - {len(date_inferred_notes)}:")
    for note in date_inferred_notes:
        print(f"  {note}")
    print(f"\nFull report: {out_path}")
    print(f"Unmatched (unparsed) files per ticker: {sum(len(v) for v in unmatched_files.values())} total")


if __name__ == "__main__":
    main()
