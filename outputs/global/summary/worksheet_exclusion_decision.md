# Worksheet Exclusion Decision

Date: 2026-08-12
Decision: **Exclude** (not re-score)

## Reason

The 25 events listed below had their micro-layer score computed from input
text that included a human rater's blind sentiment worksheet via
`build_bundle_text()`. The worksheets contained:

- The human rater's sentiment score (-1 to +1) and directional signal
  (BUY/HOLD/SELL)
- The realised overnight price move and whether the call was correct
- Realised horizon returns out to D+20

This constitutes both human-judgement leakage and future-information leakage,
making those predictions invalid rather than merely noisy.

## Evidence

- **Pipeline mechanism**: `build_bundle_text()` had no `doc_type` filter.
  `"Earnings Document"` fell through to the fallback header and was
  concatenated into the LLM prompt verbatim. Fixed 2026-08-12 by adding
  `EXCLUDED_DOC_TYPES = {"Earnings Document"}` to `report_pipeline.py`.

- **Agreement contamination**: On fact-based repricing rows, agreement between
  the LLM and human raters is 62.5% (15/24) for the contaminated events vs
  23.5% (8/34) for clean events (bootstrap unpaired difference +39.0pp,
  p=0.0028). Pooled: 60.0% (15/25) vs 38.3% (69/180), +21.7pp, p=0.042.

- **Performance contamination**: Directional accuracy 44.0% vs 35.8%,
  mean net/trade +3.43% vs +1.48% (not significant at n=25, but directionally
  consistent with look-ahead).

## Excluded document_ids (25)

```
AMD_FQ1_2026    AMD_FQ2_2025    AMD_FQ4_2025
AMZN_FQ1_2026   AMZN_FQ3_2025   AMZN_FQ4_2025
COIN_FQ1_2026   COIN_FQ3_2025   COIN_FQ4_2025
LLY_FQ1_2026    LLY_FQ3_2025    LLY_FQ4_2025
META_FQ1_2026   META_FQ3_2025   META_FQ4_2025
NFLX_FQ3_2025   NFLX_FQ4_2024   NFLX_FQ4_2025
NVDA_FQ1_2025   NVDA_FQ2_2025   NVDA_FQ3_2025   NVDA_FQ4_2025
TSLA_FQ1_2026   TSLA_FQ3_2025   TSLA_FQ4_2025
```

Tickers affected: AMD (3), AMZN (3), COIN (3), LLY (3), META (3), NFLX (3),
NVDA (4), TSLA (3).

## Pipeline fix

`report_pipeline.py` now excludes `"Earnings Document"` doc_type from the
bundle text via `EXCLUDED_DOC_TYPES`. All 59 "Earnings Document" entries are
excluded (25 human worksheets + 28 mis-typed press releases that duplicate
content already present under the correct doc_type + 6 other). The exclusion
is logged in `per_doc_meta` and `combined_warnings`.
