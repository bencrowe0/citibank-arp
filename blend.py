"""
blend.py
Combines the three scored layers (micro = company earnings bundle, macro =
nearest already-public FOMC minutes, news = coverage digest) into a single
blended sentiment score and BUY/HOLD/SELL signal.

Weights are NOT hardcoded to one "true" value - eval/calibrate.py sweeps them
per issuer via leave-one-out cross-validation against actual price outcomes.
0.6/0.2/0.2 (micro/macro/news) is the sensible-default baseline reported
alongside any tuned result, never presented as the tuned answer on its own.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple

from report_pipeline import BASE_DIR, OUTPUTS_DIR, load_manifest

DEFAULT_WEIGHTS = (0.6, 0.2, 0.2)  # (micro, macro, news)

MANIFESTS = {
    "boeing": BASE_DIR / "manifests" / "boeing_reports.json",
    "jpm": BASE_DIR / "manifests" / "jpm_reports.json",
    "netflix": BASE_DIR / "manifests" / "netflix_reports.json",
}


class BlendResult(NamedTuple):
    document_id: str
    micro_score: float
    macro_score: float | None
    news_score: float | None
    weights: tuple[float, float, float]
    blended_score: float
    signal: str


def blend_scores(
    micro_score: float,
    macro_score: float | None,
    news_score: float | None,
    weights: tuple[float, float, float] = DEFAULT_WEIGHTS,
) -> float:
    """Weighted sum of the three layer scores. A missing macro/news score
    (e.g. not yet fetched for that quarter) drops out of the sum and its
    weight is redistributed proportionally across the remaining layers,
    rather than silently treating a missing layer as neutral (0.0)."""
    w_micro, w_macro, w_news = weights
    components = [(micro_score, w_micro)]
    if macro_score is not None:
        components.append((macro_score, w_macro))
    if news_score is not None:
        components.append((news_score, w_news))

    total_weight = sum(weight for _, weight in components)
    if total_weight == 0:
        raise ValueError("Total weight across available layers is zero")

    return sum(score * weight for score, weight in components) / total_weight


def derive_signal(blended_score: float, hold_upper: float = 0.15, hold_lower: float = -0.15) -> str:
    if blended_score > hold_upper:
        return "BUY"
    if blended_score < hold_lower:
        return "SELL"
    return "HOLD"


def _load_micro_score(issuer: str, document_id: str) -> float:
    result_path = OUTPUTS_DIR / issuer / "results" / f"{document_id}.json"
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    return payload["sentiment"]["score"]


def blend_document(
    issuer: str,
    document_id: str,
    weights: tuple[float, float, float] = DEFAULT_WEIGHTS,
    hold_upper: float = 0.15,
    hold_lower: float = -0.15,
) -> BlendResult:
    import llm_macro
    import llm_news

    reports = [r for r in load_manifest(MANIFESTS[issuer]) if r.document_id == document_id]
    if not reports:
        raise ValueError(f"No manifest entry for {issuer}/{document_id}")
    report = reports[0]

    micro_score = _load_micro_score(issuer, document_id)

    macro_result = llm_macro.get_macro_score_for_date(report.report_date)
    macro_score = macro_result["sentiment"]["score"] if macro_result else None

    news_result = llm_news.get_news_score(issuer, document_id)
    news_score = news_result["sentiment"]["score"] if news_result else None

    blended = blend_scores(micro_score, macro_score, news_score, weights)
    signal = derive_signal(blended, hold_upper, hold_lower)

    return BlendResult(
        document_id=document_id,
        micro_score=micro_score,
        macro_score=macro_score,
        news_score=news_score,
        weights=weights,
        blended_score=round(blended, 4),
        signal=signal,
    )


def blend_issuer(issuer: str, **kwargs) -> list[BlendResult]:
    reports = [r for r in load_manifest(MANIFESTS[issuer]) if r.issuer.lower() == issuer.lower()]
    return [blend_document(issuer, report.document_id, **kwargs) for report in reports]


if __name__ == "__main__":
    import sys

    # Hand-computed sanity check: micro=0.4, macro=0.2, news=-0.2, weights=0.6/0.2/0.2
    # expected = 0.4*0.6 + 0.2*0.2 + (-0.2)*0.2 = 0.24 + 0.04 - 0.04 = 0.24
    check = blend_scores(0.4, 0.2, -0.2, (0.6, 0.2, 0.2))
    assert abs(check - 0.24) < 1e-9, f"Sanity check failed: got {check}, expected 0.24"
    print(f"Sanity check passed: blend_scores(0.4, 0.2, -0.2) = {check}")

    for issuer in sys.argv[1:] or list(MANIFESTS):
        print(f"\n=== {issuer} ===")
        for result in blend_issuer(issuer):
            print(
                f"{result.document_id}: micro={result.micro_score} macro={result.macro_score} "
                f"news={result.news_score} -> blended={result.blended_score} ({result.signal})"
            )
