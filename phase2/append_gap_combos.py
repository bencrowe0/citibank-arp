"""One-time-per-batch migration: append gap_combos.json's combos into
triage_docs.TARGET_COMBOS/TICKER_TO_SLUG, build_manifests.py's
COMPANY_NAMES/SECTORS, and PHASE2_ISSUERS in blend.py/llm_news.py/quant_layer.py.

Idempotent via gap_combos.json's "appended" flag - safe to rerun after adding
more combos to gap_combos.json; already-appended combos are skipped.

Aborts with no changes written if any anchor string this script splices
around has moved since this script was written - never silently corrupts a
file. If that happens, re-locate the anchor by hand and update the constant
below.
"""
from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
GAP_COMBOS_PATH = BASE_DIR / "phase2" / "gap_combos.json"
TRIAGE_DOCS_PATH = BASE_DIR / "phase2" / "triage_docs.py"
BUILD_MANIFESTS_PATH = BASE_DIR / "phase2" / "build_manifests.py"
PHASE2_ISSUERS_FILES = [BASE_DIR / "blend.py", BASE_DIR / "llm_news.py", BASE_DIR / "quant_layer.py"]


def splice_before(text: str, anchor: str, insertion: str, label: str) -> str:
    count = text.count(anchor)
    if count != 1:
        raise SystemExit(f"Aborting: expected exactly 1 occurrence of the {label} anchor, found {count}.")
    return text.replace(anchor, insertion + anchor, 1)


def block_between(text: str, start_marker: str, end_marker: str) -> str:
    return text.split(start_marker, 1)[1].split(end_marker, 1)[0]


def main() -> None:
    combos = json.loads(GAP_COMBOS_PATH.read_text(encoding="utf-8"))
    pending = {k: v for k, v in combos.items() if not v.get("appended") and v.get("slug")}
    if not pending:
        print("Nothing to append (all resolved combos already appended, or none have a slug yet - run resolve_gap_tickers.py first).")
        return

    # 1+2. triage_docs.py: TARGET_COMBOS (every pending combo) + TICKER_TO_SLUG (new tickers only).
    triage_text = TRIAGE_DOCS_PATH.read_text(encoding="utf-8")

    combo_lines = "\n".join(
        f'    ("{c["company"]}", "{c["ticker"]}", {int(c["year"])}, "{c["quarter"]}"),'
        for c in sorted(pending.values(), key=lambda c: (c["ticker"], c["year"], c["quarter"]))
    )
    batch_comment = (
        "    # Fourth batch - human/LLM gap-fill onboarding (see\n"
        "    # docs/superpowers/specs/2026-08-05-phase2-gap-onboarding-design.md).\n"
        "    # Docs hand-sourced via EDGAR/IR lookup + background subagent web search,\n"
        "    # not from an OneDrive drop - see phase2/gap_combos.json for provenance.\n"
    )
    triage_text = splice_before(triage_text, "]\n\nTICKER_TO_FOLDER = {", batch_comment + combo_lines + "\n", "TARGET_COMBOS")

    existing_slug_block = block_between(triage_text, "TICKER_TO_SLUG = {", "}\n\n# The 6 tickers above")
    new_ticker_combos = {c["ticker"]: c for c in pending.values() if f'"{c["ticker"]}":' not in existing_slug_block}
    if new_ticker_combos:
        slug_lines = "\n".join(f'    "{t}": "{c["slug"]}",' for t, c in sorted(new_ticker_combos.items()))
        triage_text = splice_before(triage_text, "}\n\n# The 6 tickers above", slug_lines + "\n", "TICKER_TO_SLUG")
    TRIAGE_DOCS_PATH.write_text(triage_text, encoding="utf-8")

    # 3. build_manifests.py: COMPANY_NAMES + SECTORS, new tickers only.
    bm_text = BUILD_MANIFESTS_PATH.read_text(encoding="utf-8")
    if new_ticker_combos:
        company_lines = "\n".join(f'    "{t}": "{c["company"]}",' for t, c in sorted(new_ticker_combos.items()))
        bm_text = splice_before(bm_text, "}\n\nSECTORS = {", company_lines + "\n", "COMPANY_NAMES")
        sector_lines = "\n".join(f'    "{t}": "{c["sector"] or "Unclassified"}",' for t, c in sorted(new_ticker_combos.items()))
        bm_text = splice_before(bm_text, "}\n\nQUARTER_NUM = {", sector_lines + "\n", "SECTORS")
    BUILD_MANIFESTS_PATH.write_text(bm_text, encoding="utf-8")

    # 4. PHASE2_ISSUERS in blend.py / llm_news.py / quant_layer.py - new slugs only.
    new_slugs = sorted({c["slug"] for c in new_ticker_combos.values()})
    if new_slugs:
        for path in PHASE2_ISSUERS_FILES:
            text = path.read_text(encoding="utf-8")
            existing_block = block_between(text, "PHASE2_ISSUERS = [", "\n]\nMANIFESTS.update({")
            missing = [s for s in new_slugs if f'"{s}"' not in existing_block]
            if not missing:
                continue
            lines = "    " + ", ".join(f'"{s}"' for s in missing) + ",\n"
            text = splice_before(text, "]\nMANIFESTS.update({", lines, f"PHASE2_ISSUERS in {path.name}")
            path.write_text(text, encoding="utf-8")

    for key in pending:
        combos[key]["appended"] = True
    GAP_COMBOS_PATH.write_text(json.dumps(combos, indent=2, sort_keys=True), encoding="utf-8")

    print(f"Appended {len(pending)} combos to TARGET_COMBOS ({len(new_ticker_combos)} brand-new tickers: {sorted(new_ticker_combos.keys())})")
    print("Review before committing: git diff phase2/triage_docs.py phase2/build_manifests.py blend.py llm_news.py quant_layer.py")


if __name__ == "__main__":
    main()
