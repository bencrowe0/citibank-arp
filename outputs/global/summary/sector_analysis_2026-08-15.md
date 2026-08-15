# Sector Analysis — Earnings Prediction Research Project

**Generated:** 2026-08-15
**Author:** Automated analysis, read-only over frozen scored artifacts

---

## 1. Preamble

### Event sets

| Set | N | Description |
|-----|---|-------------|
| Set A | 233 | Clean phase2 events. 268 scored, 35 excluded: 25 worksheet contamination + 1 SPOT misattribution + 9 timing. Source: `global_outcome_calibration_phase2.csv` joined with `returns_matrix.csv`. |
| Set B | 93 | Extension events (pure eval). Scored after Set A; thresholds frozen from Set A dev split. Source: `global_outcome_calibration_extension_2026_08_13.csv` and `finbert_extension_results.csv`. |

### Sector taxonomy

Sector assignments are sourced from `phase2/build_manifests.py` SECTORS dict (Set A)
and from the ticker-sector mapping in `sector_breakdown_three_sets.csv` notes (Set B).
Fine-grained categories are collapsed to nine broad sectors for adequate cell sizes:
Technology, Consumer, Financials, Industrials, Communication Services, Healthcare,
Energy, Utilities, Materials.

**Mapping discrepancies vs `sector_breakdown_three_sets.csv`:** Two divergences exist; full
detail in Section 2. (1) CVS Health (4 events): old file placed it in Consumer; this analysis
places it in Healthcare per the SECTORS dict entry `Healthcare/Consumer`. (2) LMT (Lockheed
Martin): old file's notes text lists LMT under Healthcare, but its n=14 Healthcare count is
consistent with LMT being counted in Industrials — the notes text is a copy-paste error and
both files effectively agree on Industrials for LMT. This analysis uses the SECTORS dict
throughout; see Section 2 for the authoritative decision record.

### Arm definitions

| Arm | Score (continuous) | Signal | Available in |
|-----|-------------------|--------|--------------|
| LLM | Blended score = 0.55×micro_score + 0.45×macro_score (renormalized when macro is missing: blend = micro_score alone; applies to 19 of 233 Set A events with no macro score) | blend_predicted_signal_default from calibration CSV (hold_upper=0.25, hold_lower=−0.05) | Set A and Set B |
| FinBERT | finbert_score (chunk-averaged ProsusAI/FinBERT sentiment, 0–1 scale) | finbert_predicted_signal (thresholds from Set A dev split, frozen for Set B eval) | Set B only |

### Suppression rule

Cells with n < 10 events are reported as `n=X (suppressed)` for Spearman rho and
BUY/SELL accuracy figures. Mean scores and returns (calibration cut) and dispersion
figures (score_std, hold_rate) are reported regardless of n, as they are not
significance claims.

### Return and grading band

`ret_overnight` = raw overnight gap (prior_close to next_day_open), from `returns_matrix.csv`.
Grading band: |ret_overnight| > 2% (pre-registered). Events inside the band are ungraded.

### What this analysis can and cannot say

All per-sector cell sizes are small (n ≤ 82 for any sector, most < 30). No per-sector
figure is statistically powered. These four cuts are purely descriptive — they show
where the model's continuous score co-varies with returns and where it does not,
and describe calibration/asymmetry patterns for examiners to probe. Do not interpret
any single-sector number as a finding.

---

## 2. Taxonomy Decision (2026-08-15)

The canonical sector taxonomy is the SECTORS dict in `phase2/build_manifests.py`. This is
in code, reproducible, and directly tied to the issuer slugs used throughout the pipeline.
The older taxonomy in `sector_breakdown_three_sets.csv` was hand-assigned from notes and is
not programmatically enforced. `sector_breakdown_three_sets.csv` has not been modified.

### Divergent events

Comparing `sector_breakdown_three_sets.csv` (Set A, N=233) to this file's sector assignments:

| Document ID | Ticker | Old sector (sector_breakdown_three_sets.csv) | New sector (SECTORS dict) | Canonical decision |
|------------|--------|---------------------------------------------|--------------------------|-------------------|
| CVS_FQ1_2026 | CVS | Consumer | Healthcare | Healthcare — SECTORS dict: `Healthcare/Consumer`; primary sector is Healthcare |
| CVS_FQ2_2025 | CVS | Consumer | Healthcare | Healthcare — same |
| CVS_FQ3_2025 | CVS | Consumer | Healthcare | Healthcare — same |
| CVS_FQ4_2025 | CVS | Consumer | Healthcare | Healthcare — same |

These 4 events account for the entire discrepancy: Consumer −4 (86→82) and Healthcare +4 (14→18).

**Note on LMT:** `sector_breakdown_three_sets.csv` lists LMT in its Healthcare *notes text*, but
its actual n=14 count for Healthcare is consistent with LMT being counted in Industrials (both
files show Industrials n=26). The notes text is a copy-paste error in the old file; the counts
themselves are internally consistent. LMT is in Industrials in both files.

**No other sector divergences exist** for Set A: Technology (36), Financials (49), Industrials (26),
Communication Services (19), and Materials (3) all agree across both files.

---

## 3. Event Counts Per Sector

n_graded = events with |ret_overnight| > 2%. These determine what is estimable.

| Sector | Set | n_events | n_graded | Note |
|--------|-----|----------|----------|------|
| Communication Services | Set A | 19 | 18 | CMCSA, DIS, GOOGL, META(excl), NFLX(excl), PINS, SPOT(excl) |
| Consumer | Set A | 82 | 47 | Largest sector; 26 tickers including ABNB, BKNG, CMG, F, GIS, HLT, KHC, KO, LOW, LULU, MAR, MC.PA, MCD, NKE, PEP, PUM.DE, SBUX, TGT, WMT |
| Consumer | Set B | 26 | 11 | CL, COST, EBAY, HD, HEIA.AS, NSRGY, RMSP.XC |
| Energy | Set B | 21 | 1 | CVX, XOM, SHEL — very few graded events (1 of 21) |
| Financials | Set A | 49 | 22 | ALV.DE, BAC, BCS, C, COIN(excl), GS, HOOD, JPM, MET, PYPL, SCHW, STAN.L, UNH, V |
| Financials | Set B | 8 | 2 | AXP, MA — n=8, suppressed for rho ← small n |
| Healthcare | Set A | 18 | 12 | CVS, JNJ, NVO, PFE, UNH (LLY excluded/worksheet); LMT placed in Industrials here |
| Industrials | Set A | 26 | 17 | AMKBY(timing excl), BA, CAT, DAL, FDX, LMT, SIE.DE, UAL |
| Industrials | Set B | 4 | 0 | UNP — n=4, suppressed ← small n |
| Materials | Set A | 3 | 0 | LIN only; n=3, suppressed ← small n |
| Materials | Set B | 3 | 2 | FCX — n=3, suppressed ← small n |
| Technology | Set A | 36 | 31 | AAPL, AMD(excl), AVGO, CRM, DELL, GOOGL, IBM, LNVGY(timing excl), MU, MSFT, NVDA(excl), ORCL, PLTR, UBER, WDAY |
| Technology | Set B | 18 | 15 | ADBE, DDOG, INTC, SHOP, SONY |
| Utilities | Set B | 13 | 0 | DUK only — 0 graded events |

**Supportable cuts by sector and set:**

- Set A Technology (n=36, n_graded=31): all 4 cuts reportable
- Set A Consumer (n=82, n_graded=47): all 4 cuts reportable
- Set A Financials (n=49, n_graded=22): all 4 cuts reportable
- Set A Industrials (n=26, n_graded=17): rho reportable; BUY/SELL accuracy partially suppressed
- Set A Communication Services (n=19, n_graded=18): rho reportable; BUY/SELL partially suppressed
- Set A Healthcare (n=18, n_graded=12): rho reportable
- Set B Technology (n=18, n_graded=15): rho reportable
- Set B Consumer (n=26, n_graded=11): rho reportable
- Set B Energy (n=21, n_graded=1): rho reportable; 1 graded event — not informative
- Set B Utilities (n=13, n_graded=0): rho reportable on continuous score; 0 graded events
- Set A Materials (n=3), Set B Financials (n=8), Set B Industrials (n=4), Set B Materials (n=3): all rho suppressed

---

## 4. Cut 1: Spearman Rho (Score vs Overnight Return)

Spearman rank correlation between continuous arm score and ret_overnight.
Pooled reference: Set A rho = 0.236, p = 0.0003, n = 233 (source: `ext2_holding_curve.csv`).
Pooled Set B reference: rho = 0.272, p = 0.0085, n = 93 (source: `results_three_sets.csv`).
p-values use normal approximation to t-distribution; two-tailed.

### Set A — LLM arm

| Sector | n | rho | p-value |
|--------|---|-----|---------|
| Communication Services | 19 | 0.285 | 0.2205 |
| Consumer | 82 | 0.255 | 0.0182 |
| Financials | 49 | 0.133 | 0.3589 |
| Healthcare | 18 | 0.422 | 0.0624 |
| Industrials | 26 | 0.013 | 0.9492 |
| Materials | 3 | n=3 (suppressed) | — |
| Technology | 36 | 0.268 | 0.1052 |

### Set B — LLM arm

| Sector | n | rho | p-value |
|--------|---|-----|---------|
| Consumer | 26 | 0.119 | 0.5580 |
| Energy | 21 | 0.237 | 0.2868 |
| Financials | 8 | n=8 (suppressed) | — |
| Industrials | 4 | n=4 (suppressed) | — |
| Materials | 3 | n=3 (suppressed) | — |
| Technology | 18 | 0.449 | 0.0447 |
| Utilities | 13 | -0.124 | 0.6786 |

### Set B — FinBERT arm

| Sector | n | rho | p-value |
|--------|---|-----|---------|
| Consumer | 26 | -0.111 | 0.5839 |
| Energy | 21 | -0.110 | 0.6283 |
| Financials | 8 | n=8 (suppressed) | — |
| Industrials | 4 | n=4 (suppressed) | — |
| Materials | 3 | n=3 (suppressed) | — |
| Technology | 18 | -0.051 | 0.8395 |
| Utilities | 13 | -0.560 | 0.0248 |

**Observations (purely descriptive):**

- In Set A, rho is positive across every sector where it is estimable, consistent with the
  pooled positive signal. Healthcare (rho=0.422, n=18) and Communication Services
  (rho=0.285, n=19) show the highest point estimates.

- **Set A Industrials (n=26): rho=0.013 (p=0.950).** This is the only estimable Set A sector
  where the LLM score does not rank overnight returns. The 95% confidence interval for rho
  (Fisher z-transform, two-sided): atanh(0.013) ± 1.96×(1/√23), transformed back, gives
  [−0.376, 0.398]. The pooled Set A rho of 0.236 sits well within this interval, so Industrials
  rho is not distinguishable from the pooled figure given n=26 — the flat estimate could be
  sampling variation rather than a genuine sector difference, and the data cannot resolve it
  either way. Every other estimable Set A sector has rho in [0.133, 0.422]; the Industrials CI
  contains most of those values (Financials 0.133, Consumer 0.255, Communication Services 0.285,
  Technology 0.268, all within [−0.376, 0.398]), with Healthcare's rho of 0.422 falling
  marginally outside the upper bound of 0.398. Industrials is the lowest point estimate across
  Set A sectors, but its CI is too wide to support a claim of genuine sector difference.

- In Set B, LLM rho is positive for Technology (0.449, n=18) and Energy (0.237, n=21),
  consistent with the pooled 0.272. Consumer is weakly positive (0.119). Utilities is
  weakly negative (−0.124, n=13, 0 graded events). All Set B Financials, Industrials,
  and Materials are suppressed.

- **FinBERT (Set B): rho is near zero or negative across all Set B sectors.** FinBERT (Set B,
  n=93 events across all sectors) makes essentially zero SELL calls: across every Set B sector,
  SELL n_calls is 0 or 1 (Consumer: 1 SELL call from HEIA.AS; Technology: 1 SELL call from
  SONY; all other sectors: 0). This is a structural property of the baseline rather than a
  directional accuracy failure: FinBERT scores press releases as predominantly positive
  sentiment (mean FinBERT score positive in every sector, ranging from +0.081 in Utilities to
  +0.280 in Financials), and the phase2 dev-fitted thresholds push nearly all scores into BUY.
  As a result, FinBERT traded 71.0% of Set B events (66/93) while the LLM model traded 34.4%
  (32/93). The asymmetry is near-complete: FinBERT can make only 2 SELL calls across 93 events,
  so the SELL half of any BUY/SELL comparison is structurally absent for this baseline. This
  limits the comparability of the two arms on directional accuracy. The negative or near-zero
  FinBERT rho at the sector level is consistent with this over-trading pattern.

---

## 5. Cut 2: Calibration (Mean Score vs Mean Return by Sector)

Mean of the continuous arm score vs mean of ret_overnight per sector.
A positive mean score alongside a negative mean return indicates systematic over-optimism.
A negative mean score alongside a positive mean return indicates systematic under-optimism.
No suppression applied (means are not significance claims).

### Set A — LLM arm

| Sector | n | mean_score | mean_ret_overnight |
|--------|---|------------|-------------------|
| Communication Services | 19 | 0.109 | 0.0035 |
| Consumer | 82 | -0.022 | -0.0113 |
| Financials | 49 | 0.133 | 0.0001 |
| Healthcare | 18 | 0.042 | -0.0041 |
| Industrials | 26 | 0.142 | 0.0134 |
| Materials | 3 | -0.077 | -0.0037 |
| Technology | 36 | 0.270 | 0.0053 |

### Set B — LLM arm

| Sector | n | mean_score | mean_ret_overnight |
|--------|---|------------|-------------------|
| Consumer | 26 | 0.013 | -0.0011 |
| Energy | 21 | 0.180 | 0.0014 |
| Financials | 8 | 0.180 | -0.0003 |
| Industrials | 4 | 0.001 | 0.0009 |
| Materials | 3 | 0.017 | -0.0455 |
| Technology | 18 | 0.171 | 0.0268 |
| Utilities | 13 | 0.140 | 0.0021 |

### Set B — FinBERT arm

| Sector | n | mean_finbert_score | mean_ret_overnight |
|--------|---|-------------------|-------------------|
| Consumer | 26 | 0.169 | -0.0011 |
| Energy | 21 | 0.131 | 0.0014 |
| Financials | 8 | 0.280 | -0.0003 |
| Industrials | 4 | 0.191 | 0.0009 |
| Materials | 3 | 0.130 | -0.0455 |
| Technology | 18 | 0.112 | 0.0268 |
| Utilities | 13 | 0.081 | 0.0021 |

**Observations (purely descriptive):**

- The LLM blend score is positive on average in every Set A sector (mean_score > 0), with
  Consumer being the exception at −0.022. Materials (n=3, Set A) has 0 graded events;
  calibration is not meaningful there.

- **Set A Financials over-optimism pattern.** In the Set A Financials sector (n=49 events),
  the mean LLM blend score is +0.133 while the mean realized overnight return is +0.0001
  (essentially zero). On 15 BUY calls, the model achieved 3 correct (accuracy 20.0%, 95%
  Wilson CI [7.0%, 45.2%]), against a sector BUY base rate of 24.5% (12/49 events had
  overnight return >+2%). Minimum detectable effect at n=15 calls, 80% power, two-sided
  alpha=0.05: approximately 35 percentage points from base rate — so at this call count,
  the difference between 20.0% and 24.5% is entirely within sampling noise and carries no
  inferential weight. The over-optimism pattern (high positive mean score, below-base-rate
  BUY accuracy) is descriptively consistent but cannot be confirmed or refuted at n=15 BUY calls.

- **FinBERT calibration:** FinBERT scores are uniformly positive across all Set B sectors
  (ranging from +0.081 in Utilities to +0.280 in Financials), while mean overnight returns
  are near zero or negative in several sectors (Consumer, Financials). This structural
  positive bias in FinBERT scores is consistent with the near-zero or negative rho observed
  across Set B sectors for the FinBERT arm.

---

## 6. Cut 3: Score Dispersion by Sector

Population standard deviation of the continuous arm score (how much the model differentiates
within each sector), alongside HOLD rate (fraction of events with signal == HOLD).
Low dispersion suggests the model assigns similar scores across events in that sector.

### Set A — LLM arm

| Sector | n | score_std (pop) | hold_rate |
|--------|---|-----------------|-----------|
| Communication Services | 19 | 0.177 | 42.1% |
| Consumer | 82 | 0.266 | 36.6% |
| Financials | 49 | 0.184 | 42.9% |
| Healthcare | 18 | 0.237 | 38.9% |
| Industrials | 26 | 0.235 | 34.6% |
| Materials | 3 | 0.127 | 33.3% |
| Technology | 36 | 0.153 | 30.6% |

### Set B — LLM arm

| Sector | n | score_std (pop) | hold_rate |
|--------|---|-----------------|-----------|
| Consumer | 26 | 0.168 | 61.5% |
| Energy | 21 | 0.103 | 85.7% |
| Financials | 8 | 0.155 | 62.5% |
| Industrials | 4 | 0.051 | 75.0% |
| Materials | 3 | 0.302 | 66.7% |
| Technology | 18 | 0.144 | 55.6% |
| Utilities | 13 | 0.166 | 53.8% |

### Set B — FinBERT arm

| Sector | n | score_std (pop) | hold_rate |
|--------|---|-----------------|-----------|
| Consumer | 26 | 0.158 | 38.5% |
| Energy | 21 | 0.050 | 19.0% |
| Financials | 8 | 0.078 | 0.0% |
| Industrials | 4 | 0.077 | 0.0% |
| Materials | 3 | 0.026 | 0.0% |
| Technology | 18 | 0.124 | 33.3% |
| Utilities | 13 | 0.035 | 53.8% |

**Observations (purely descriptive):**

- LLM score dispersion is broadly similar across Set A sectors (std ~0.15–0.27),
  suggesting the model differentiates comparably within each sector. Technology (std=0.153)
  has slightly lower dispersion, while Consumer (0.266) and Healthcare (0.237) are the
  highest. Industrials (0.235) dispersion is mid-range, so the near-zero rho in that sector
  is not an artifact of score bunching.
- HOLD rate varies substantially: Set B Energy has the highest HOLD rate (85.7%), consistent
  with a cautious model on commodity sectors where overnight moves are small. Set A Technology
  has the lowest HOLD rate (30.6%), consistent with the model making more directional calls
  in a sector where it also has a positive rho.
- **FinBERT structural HOLD compression:** FinBERT has zero or near-zero HOLD rate in Energy
  (19.0%), Financials (0.0%), Industrials (0.0%), and Materials (0.0%), because FinBERT has no
  inherent HOLD zone — the thresholds fitted on Set A dev effectively push nearly all positive
  FinBERT scores into BUY. Only Consumer (38.5%) and Utilities (53.8%) show appreciable HOLD
  rates for FinBERT, and those arise from the small number of negative FinBERT scores in those
  sectors. This HOLD compression is the same structural property that produces FinBERT's
  71.0% trade rate (66/93 events traded) versus the LLM model's 34.4% (32/93).

---

## 7. Cut 4: SELL vs BUY Asymmetry by Sector

Accuracy on BUY calls: n_correct / n_calls (where signal==BUY AND outcome==BUY).
Accuracy on SELL calls: n_correct / n_calls (where signal==SELL AND outcome==SELL).
Base rates: fraction of all events in sector with each overnight outcome.
Suppression: accuracy suppressed where n_calls < 10.

### Set A — LLM arm

| Sector | n | buy_n_calls | buy_accuracy | buy_base_rate | sell_n_calls | sell_accuracy | sell_base_rate |
|--------|---|-------------|-------------|---------------|-------------|--------------|---------------|
| Communication Services | 19 | 5 | n=5 (suppressed) | 42.1% | 6 | n=6 (suppressed) | 52.6% |
| Consumer | 82 | 13 | 38.5% | 19.5% | 39 | 46.2% | 37.8% |
| Financials | 49 | 15 | 20.0% | 24.5% | 13 | 38.5% | 20.4% |
| Healthcare | 18 | 4 | n=4 (suppressed) | 33.3% | 7 | n=7 (suppressed) | 33.3% |
| Industrials | 26 | 11 | 54.5% | 42.3% | 6 | n=6 (suppressed) | 23.1% |
| Materials | 3 | 0 | n=0 (suppressed) | 0.0% | 2 | n=2 (suppressed) | 0.0% |
| Technology | 36 | 24 | 50.0% | 38.9% | 1 | n=1 (suppressed) | 47.2% |

### Set B — LLM arm

| Sector | n | buy_n_calls | buy_accuracy | buy_base_rate | sell_n_calls | sell_accuracy | sell_base_rate |
|--------|---|-------------|-------------|---------------|-------------|--------------|---------------|
| Consumer | 26 | 1 | n=1 (suppressed) | 23.1% | 9 | n=9 (suppressed) | 19.2% |
| Energy | 21 | 3 | n=3 (suppressed) | 4.8% | 0 | n=0 (suppressed) | 0.0% |
| Financials | 8 | 2 | n=2 (suppressed) | 12.5% | 1 | n=1 (suppressed) | 12.5% |
| Industrials | 4 | 0 | n=0 (suppressed) | 0.0% | 1 | n=1 (suppressed) | 0.0% |
| Materials | 3 | 0 | n=0 (suppressed) | 0.0% | 1 | n=1 (suppressed) | 66.7% |
| Technology | 18 | 7 | n=7 (suppressed) | 44.4% | 1 | n=1 (suppressed) | 38.9% |
| Utilities | 13 | 4 | n=4 (suppressed) | 0.0% | 2 | n=2 (suppressed) | 0.0% |

### Set B — FinBERT arm

| Sector | n | buy_n_calls | buy_accuracy | buy_base_rate | sell_n_calls | sell_accuracy | sell_base_rate |
|--------|---|-------------|-------------|---------------|-------------|--------------|---------------|
| Consumer | 26 | 15 | 20.0% | 23.1% | 1 | n=1 (suppressed) | 19.2% |
| Energy | 21 | 17 | 5.9% | 4.8% | 0 | n=0 (suppressed) | 0.0% |
| Financials | 8 | 8 | n=8 (suppressed) | 12.5% | 0 | n=0 (suppressed) | 12.5% |
| Industrials | 4 | 4 | n=4 (suppressed) | 0.0% | 0 | n=0 (suppressed) | 0.0% |
| Materials | 3 | 3 | n=3 (suppressed) | 0.0% | 0 | n=0 (suppressed) | 66.7% |
| Technology | 18 | 11 | 54.5% | 44.4% | 1 | n=1 (suppressed) | 38.9% |
| Utilities | 13 | 6 | n=6 (suppressed) | 0.0% | 0 | n=0 (suppressed) | 0.0% |

**Observations (purely descriptive):**

- In Set A Consumer (n=82), both BUY (n_calls=13) and SELL (n_calls=39) counts are
  sufficient for accuracy reporting. The sector has a negative mean overnight return (−0.011),
  consistent with the model making many more SELL calls than BUY calls.

- **Set A Financials BUY calls:** The Financials sector (n=49) shows the largest descriptive
  over-optimism pattern. Mean blend score is +0.133 against mean overnight return of +0.0001.
  The model made 15 BUY calls with accuracy 20.0% (3/15, 95% Wilson CI [7.0%, 45.2%]),
  below the sector BUY base rate of 24.5% (12/49 events moved >+2%). At n=15 BUY calls with
  a base rate near 24.5%, the MDE at 80% power, two-sided 5% alpha is approximately 35pp —
  the 4.5pp gap between observed accuracy (20.0%) and base rate (24.5%) is far below the
  detectable threshold and carries no inferential weight. Report this as a descriptive pattern
  only, not as a finding of systematic under-performance.

- Most other sectors have too few BUY or SELL calls to compute accuracy. Communication
  Services and Technology in Set A have sufficient events for rho but not for per-direction
  accuracy breakdown at the sector level.

- **FinBERT SELL calls structural absence (Set B):** FinBERT makes 2 SELL calls across all 93
  Set B events — 1 in Consumer (HEIA.AS FQ3_2025) and 1 in Technology (SONY FQ1_2026) — and
  0 in every other sector. This is a structural property of the baseline: FinBERT's positive
  sentiment bias pushes nearly all scores above the dev-fitted BUY threshold, resulting in
  66/93 events traded as BUY (71.0%) versus 0–1 SELL calls per sector. The LLM model by
  contrast traded 32/93 events (34.4%), with 15 SELL calls and 17 BUY calls across the 93
  events. The near-complete absence of FinBERT SELL calls means that any SELL-direction
  accuracy comparison between the two arms is structurally impossible for this baseline.
  SELL accuracy is suppressed for FinBERT in every sector.

---

## 8. Data Availability Verdict

| Sector | Set | n | rho estimable | buy_acc estimable | sell_acc estimable |
|--------|-----|---|---------------|-------------------|-------------------|
| Communication Services | Set A | 19 | Yes | No | No |
| Consumer | Set A | 82 | Yes | Yes | Yes |
| Consumer | Set B | 26 | Yes | No | No |
| Energy | Set B | 21 | Yes | No | No |
| Financials | Set A | 49 | Yes | Yes | Yes |
| Financials | Set B | 8 | No | No | No |
| Healthcare | Set A | 18 | Yes | No | No |
| Industrials | Set A | 26 | Yes | Yes | No |
| Industrials | Set B | 4 | No | No | No |
| Materials | Set A | 3 | No | No | No |
| Materials | Set B | 3 | No | No | No |
| Technology | Set A | 36 | Yes | Yes | No |
| Technology | Set B | 18 | Yes | No | No |
| Utilities | Set B | 13 | Yes | No | No |

**Summary:**

- Only Set A Consumer, Technology, Financials, and Industrials have sufficient n for
  Spearman rho AND reach the n=10 threshold for at least one directional accuracy estimate.
- Set A Healthcare and Communication Services support rho but not per-direction accuracy.
- Set B Energy and Utilities support rho computation on the full 21/13 events but have
  only 1 and 0 graded events respectively — the rho figure is driven almost entirely by
  ungraded (flat-bet) events and should not be read as a directional accuracy finding.
- Materials in both sets, and Financials/Industrials in Set B, are fully suppressed.
- FinBERT figures are reported for Set B only; most sectors have zero SELL calls,
  making sell_accuracy uniformly suppressed for FinBERT.

---

## 9. Source File Index

| File | Role |
|------|------|
| `outputs/global/summary/global_outcome_calibration_phase2.csv` | Set A per-event scores, signals, outcomes |
| `outputs/global/summary/global_outcome_calibration_extension_2026_08_13.csv` | Set B per-event scores, signals, outcomes |
| `outputs/global/summary/finbert_extension_results.csv` | FinBERT scores and signals for Set B |
| `outputs/global/summary/returns_matrix.csv` | Per-event overnight returns and timing_excluded flag |
| `outputs/global/summary/ext2_holding_curve.csv` | Pooled Set A rho=0.236 reference |
| `outputs/global/summary/results_three_sets.csv` | Pooled Set B rho=0.272 reference |
| `outputs/global/summary/sector_breakdown_three_sets.csv` | Sector taxonomy and n references |
| `phase2/build_manifests.py` | SECTORS dict — authoritative sector assignments |
| `outputs/global/summary/worksheet_exclusion_decision.md` | 25 excluded document IDs |

---

*This file was generated read-only from frozen scored artifacts. No existing file was modified.*