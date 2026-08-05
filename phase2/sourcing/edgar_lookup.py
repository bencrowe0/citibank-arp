"""Tier-1 scripted sourcing: for SEC-registered gap tickers, locate the
earnings-release 8-K's EX-99.1 exhibit (the near-universal press-release
exhibit convention) via EDGAR's submissions API, and download it. Zero LLM
tokens - deterministic filing lookup only.

Presentation and transcript documents are NOT reliably on EDGAR (rarely
filed as exhibits, never as full transcripts) - those, the news digest, and
anything this script can't confidently resolve stay Tier-2 (background
subagent web search), regardless of SEC-registrant status.
"""
from __future__ import annotations

import json
import re
import time
import urllib.request
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
GAP_COMBOS_PATH = BASE_DIR / "phase2" / "gap_combos.json"
DOCS_ROOT = BASE_DIR / "docs"

HEADERS = {"User-Agent": "citibank-apr-research bencrowe01@gmail.com"}
EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
QUARTER_NUM = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def find_earnings_8k_index_url(cik: int, report_date: date) -> tuple[str, str] | None:
    """Returns (index_url, filing_date_iso) for the single 8-K (item 2.02,
    Results of Operations) filed within 5 days of report_date. None if zero
    or multiple candidates (ambiguous - leave for Tier 2)."""
    data = fetch_json(EDGAR_SUBMISSIONS_URL.format(cik=cik))
    recent = data["filings"]["recent"]
    candidates = []
    for i, form in enumerate(recent["form"]):
        if form != "8-K":
            continue
        if "2.02" not in recent.get("items", [""])[i]:
            continue
        filed = date.fromisoformat(recent["filingDate"][i])
        if abs((filed - report_date).days) > 5:
            continue
        accno = recent["accessionNumber"][i].replace("-", "")
        candidates.append((f"https://www.sec.gov/Archives/edgar/data/{cik}/{accno}/", filed.isoformat()))
    return candidates[0] if len(candidates) == 1 else None


def download_exhibit_99_1(index_url: str, dest_dir: Path) -> Path | None:
    """Fetches the accession's filing index page, finds the EX-99.1 link,
    downloads it. Returns the saved path, or None if no EX-99.1 found."""
    req = urllib.request.Request(index_url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
    m = re.search(r'href="([^"]*ex-?99[^"]*\.htm[l]?)"', html, re.IGNORECASE)
    if not m:
        return None
    doc_url = index_url + m.group(1).split("/")[-1]
    req = urllib.request.Request(doc_url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = resp.read()
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / "press_release.htm"
    dest_path.write_bytes(content)
    return dest_path


def main() -> None:
    combos = json.loads(GAP_COMBOS_PATH.read_text(encoding="utf-8"))
    targets = {
        k: c for k, c in combos.items()
        if c.get("is_sec_registrant") and c.get("report_date") and c["status"] == "report_date_resolved"
    }
    print(f"{len(targets)} SEC-registered combos with a resolved report_date to try")

    resolved, skipped = 0, []
    for key, combo in sorted(targets.items()):
        report_date = date.fromisoformat(combo["report_date"])
        try:
            found = find_earnings_8k_index_url(combo["cik"], report_date)
        except Exception as exc:  # noqa: BLE001
            skipped.append(f"{key}: EDGAR lookup failed: {exc}")
            continue
        if found is None:
            skipped.append(f"{key}: no unambiguous 8-K (item 2.02) within 5 days of {report_date}")
            continue
        index_url, filing_date = found
        fq = QUARTER_NUM[combo["quarter"]]
        dest_dir = DOCS_ROOT / combo["slug"] / f"CY{combo['year']}-Q{fq}"
        path = download_exhibit_99_1(index_url, dest_dir)
        if path is None:
            skipped.append(f"{key}: 8-K found ({index_url}) but no EX-99.1 exhibit in it")
            continue
        combo.setdefault("documents", []).append({
            "doc_type": "Press Release",
            "source_pdf": str(path.relative_to(BASE_DIR)).replace("\\", "/"),
        })
        combo["notes"] = (combo["notes"] + f" Tier1: press release from {index_url} (filed {filing_date}).").strip()
        resolved += 1
        time.sleep(0.15)  # SEC's fair-use rate-limit guidance

    GAP_COMBOS_PATH.write_text(json.dumps(combos, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Tier-1 resolved press releases for {resolved} combos")
    print(f"{len(skipped)} need Tier-2 (subagent) for at least the press release:")
    for s in skipped:
        print(" ", s)
    print("\nEven Tier-1-resolved combos still need Tier-2 for presentation + transcript + news digest.")


if __name__ == "__main__":
    main()
