"""Runs quant + macro + micro + news scoring, then blend, for every issuer
with at least one "sourced" gap combo. Thin subprocess wrapper around the
existing per-issuer CLIs, scoped to just the new/updated issuers so this
doesn't redundantly rerun all 40+ existing phase2 issuers. Checkpoints
gap_combos.json's status after each stage per issuer, so a crash partway
through only re-does the issuer it crashed on, not everything before it.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
GAP_COMBOS_PATH = BASE_DIR / "phase2" / "gap_combos.json"


def save(combos: dict) -> None:
    GAP_COMBOS_PATH.write_text(json.dumps(combos, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    combos = json.loads(GAP_COMBOS_PATH.read_text(encoding="utf-8"))
    slugs = sorted({c["slug"] for c in combos.values() if c["status"] == "sourced"})
    if not slugs:
        print("No issuers ready for scoring (need status == sourced - run Task 7 first).")
        return
    print(f"Running quant+macro+micro+news+blend for {len(slugs)} issuers: {slugs}")

    subprocess.run([sys.executable, str(BASE_DIR / "quant_layer.py"), *[f"p2_{s}" for s in slugs]], check=True, cwd=BASE_DIR)
    subprocess.run([sys.executable, str(BASE_DIR / "llm_macro.py")], check=True, cwd=BASE_DIR)

    for slug in slugs:
        manifest = BASE_DIR / "manifests" / f"p2_{slug}_reports.json"
        subprocess.run(
            [sys.executable, str(BASE_DIR / "run_reports.py"), "--issuer", f"p2_{slug}", "--manifest", str(manifest)],
            check=True, cwd=BASE_DIR,
        )
        subprocess.run([sys.executable, str(BASE_DIR / "llm_news.py"), f"p2_{slug}"], check=True, cwd=BASE_DIR)
        for c in combos.values():
            if c["slug"] == slug and c["status"] == "sourced":
                c["status"] = "scored"
        save(combos)

        subprocess.run([sys.executable, str(BASE_DIR / "blend.py"), f"p2_{slug}"], check=True, cwd=BASE_DIR)
        for c in combos.values():
            if c["slug"] == slug and c["status"] == "scored":
                c["status"] = "blended"
        save(combos)

    print(f"Done. {len(slugs)} issuers scored + blended.")


if __name__ == "__main__":
    main()
