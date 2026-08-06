"""Merges a Tier-2 subagent's JSON receipt (see make_wave.py's
RECEIPT_SCHEMA) into gap_combos.json: records documents written, marks the
news digest written, advances status to "sourced" once both are satisfied,
and files any 'unresolved' notes for manual follow-up.

Writes gap_combos.json atomically (temp file + os.replace()), same pattern
as phase2/sourcing/edgar_lookup.py's save() - this is a shared checkpoint
file invoked once per Tier-2 wave receipt (potentially dozens of times
across the plan), so a process kill mid-write must not truncate/corrupt
everything previously on disk.

Usage: python phase2/sourcing/ingest_receipt.py path/to/receipt.json
   or: echo '<receipt json>' | python phase2/sourcing/ingest_receipt.py -
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
GAP_COMBOS_PATH = BASE_DIR / "phase2" / "gap_combos.json"


def save(combos: dict) -> None:
    """Writes gap_combos.json atomically: serialize to a temp file in the
    same directory, flush+close, then os.replace() over the real path."""
    data = json.dumps(combos, indent=2, sort_keys=True)
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=GAP_COMBOS_PATH.parent,
        prefix=GAP_COMBOS_PATH.name + ".",
        suffix=".tmp",
        delete=False,
    )
    try:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
    finally:
        tmp.close()
    os.replace(tmp.name, GAP_COMBOS_PATH)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: ingest_receipt.py <receipt.json | ->")
    raw = sys.stdin.read() if sys.argv[1] == "-" else Path(sys.argv[1]).read_text(encoding="utf-8")
    receipt = json.loads(raw)

    combos = json.loads(GAP_COMBOS_PATH.read_text(encoding="utf-8"))
    ticker = receipt["ticker"]
    updated, unresolved_total = 0, 0

    for entry in receipt["combos"]:
        key = f"{ticker}_{entry['year']}_{entry['quarter']}"
        combo = combos.get(key)
        if combo is None:
            print(f"WARNING: {key} not found in gap_combos.json, skipping", file=sys.stderr)
            continue

        existing_paths = {d["source_pdf"] for d in combo.get("documents", [])}
        for doc in entry.get("documents_written", []):
            path = doc["path"]
            if path in existing_paths:
                continue
            combo.setdefault("documents", []).append({"doc_type": doc["doc_type"], "source_pdf": path})

        if entry.get("news_digest_written"):
            combo["news_document_written"] = True
        if entry.get("unresolved"):
            combo["notes"] = (combo["notes"] + " Tier2 unresolved: " + "; ".join(entry["unresolved"])).strip()
            unresolved_total += 1

        have_types = {d["doc_type"] for d in combo.get("documents", [])}
        if len(have_types) >= 2 and combo.get("news_document_written"):
            combo["status"] = "sourced"
        updated += 1

    save(combos)
    print(f"Ingested receipt for {ticker}: {updated} combos updated, {unresolved_total} flagged unresolved")


if __name__ == "__main__":
    main()
