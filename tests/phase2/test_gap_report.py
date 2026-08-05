import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR / "phase2"))

from gap_report import parse_events, compute_gap  # noqa: E402


def test_parse_events_skips_header_and_incomplete_rows():
    rows = [
        ["Company", "Ticker", "Year", "Quarter"],
        ["Broadcom", "AVGO", "2025", "Q3"],
        ["", "", "", ""],
        ["Costco", "COST", "", ""],
    ]
    events = parse_events(rows)
    assert events == {("AVGO", "2025", "Q3"): "Broadcom"}


def test_compute_gap_returns_human_only_combos():
    human = {("AVGO", "2025", "Q3"): "Broadcom", ("AAPL", "2025", "Q3"): "Apple"}
    llm = {("AAPL", "2025", "Q3"): "Apple"}
    assert compute_gap(human, llm) == {("AVGO", "2025", "Q3"): "Broadcom"}
