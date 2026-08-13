# Workbook Correction Log — 2026-08-13

**Scope**: `data/workbook/Master_Data_CORRECTED_2026-08-13.xlsx` and
`data/workbook/Master_Data_LOCKED_2026-08-13.xlsx`.  
**Author**: automated correction pass, 2026-08-13.  
**Audience**: group members who have not followed this session; passages are
intended to be lifted into a dissertation or team message verbatim. Every
figure carries its N, its definition, and its source file.

---

## (a) What the workbook looked like before

### Main pricing window (columns M–P)

The Human_Data_Entry sheet computed each rater's return from four cells:

| Column | Label | Content |
|--------|-------|---------|
| M | Prior Closing Date | The closing date used as the entry |
| N | Prior Close ($) | The closing price on that date |
| O | Next Opening Date | The date of the exit open |
| P | Next Day Open ($) | The opening price on that date |

Columns Q (Actual % Change), R (Actual Direction), S (Prediction Correct?),
T (Position), and U (Net P&L) were all formula-driven from M–P. The Summary,
Charts, and Efficiency sheets read from those same formula results. In the
original workbook, M was populated with the **close of report_date** and P
with the **next open after report_date**, uniformly for every event, regardless
of when the company actually released.

### The re-pricing block (columns AB–AK)

A second pricing block occupied columns AB–AK. Column AB recorded the rater's
stated basis for their price choice (for example, "release date + stated time",
"price signal — only this window shows an abnormal move"). Columns AC–AK held
the rater's re-derived dates and prices. **No formula in the sheet read this
block.** Q through U and every summary tab continued to read M–P. The re-priced
values were recorded and never applied.

### Extent of the mismatch

A cross-check comparing the corrected EDGAR closing dates against the live
column M found that **only 287 of 420 Human_Data_Entry rows agreed** on the
prior-close date. The remaining 133 rows were using a different session as
their entry.

---

## (b) What was wrong — two distinct problems

### Problem 1: Uniform window, wrong for pre-market reporters

The original scheme entered at the close of report_date and exited at the next
open. For **after-hours reporters** (company releases after 4 pm on report_date)
this is the correct window: the news becomes public after the close, so the
close of report_date is the last price before the announcement. For
**pre-market reporters** (company releases before 9:30 am on report_date) the
window is wrong: the close of report_date is already several hours *after* the
news was out. The correct entry for a pre-market release is the close of the
session *before* report_date — the last trade that occurred without knowledge
of the results.

Using the close of the release day for pre-market events overstates the
magnitude of the measured move and biases the return in an unpredictable
direction depending on how the stock traded during the day.

### Problem 2: Price-signal re-pricing selects on the outcome

Approximately 175 of the 420 re-priced rows (across all passes and raters)
used a basis of "price signal — only this window shows an abnormal move" or
a close variant. This selects the pricing window by observing which window
produced the larger or more abnormal move — an outcome-dependent choice.
Even if each individual row selects the mechanically correct window, the
aggregate procedure is not independent of the return magnitude: events with
large moves are more likely to have one window clearly dominant, and the
re-pricer consistently picks that window. This introduces a selection bias
toward large observed returns, regardless of whether the selected date is
the release date or not.

These two problems are independent. A row can be wrong on Problem 1 (uniform
window misses pre-market timing) and right on Problem 2 (rater used a
stated-time basis, not a price signal). The correction addresses Problem 1
directly and flags Problem 2 as a limitation that cannot be fully corrected
in retrospect.

---

## (c) What was done

### Release dates sourced per event

For each event in the LLM universe (N=268 phase-2 scored events), the EDGAR
8-K Item 2.02 filing date was already embedded in `returns_matrix.csv` as
`entry_date`. This column was established by the anchor correction on
2026-08-12 and serves as the authoritative release date. For non-US issuers
and human-only events not covered by EDGAR, the home-exchange announcement
date was used where documented by the rater.

### Timing rule applied per event

- **Pre-market release**: correct prior close = release_date − 1 business day;
  correct exit open = release_date open.
- **After-hours release**: correct prior close = release_date close;
  correct exit open = release_date + 1 business day open.

### Values written into M–P

The corrected closing date, closing price, opening date, and opening price were
written directly into columns M, N, O, and P so that all downstream formulas
(Q through U, Summary, Charts, Efficiency) would finally read the right window.

### Coverage

Of 420 Human_Data_Entry rows, **295 were corrected** (column BS = "Price Basis
Corrected" = YES). The remaining **125 rows were left on the original basis**
because no verified release date was available for those events. Each uncorrected
row carries the reason in column BT. The 295 corrected rows and the 125
uncorrected rows are mutually exclusive; the corrected subset is the one to
use for any quantitative human-arm result.

---

## (d) Corroboration result — headline of this log

**Of 128 documented-release-time first-rater rows** (rows where the rater
recorded an explicit release time or a documented public release moment as
their pricing basis, deduplicated to the first rater per event):

| Category | Count |
|----------|-------|
| No EDGAR record — incomparable | 33 |
| With EDGAR record | **95** |
| — of which: agree directly with EDGAR | 89 |
| — of which: European exchange-convention difference | 6 |
| — of which: rater error already corrected (PBC=YES) | 2 |
| — of which: genuine remaining error, fixed this session | **1** |

The **6 European-convention rows** (LVMH|2025|Q2, Lenovo|2026|Q3, Puma|2026|Q1,
Siemens|2025|Q4, Siemens|2026|Q1, Siemens|2026|Q2) show a 1-day offset because
the rater correctly used the European prior-close date while the EDGAR reference
uses the US SEC filing timestamp. These are not pricing errors.

The **2 rater errors already corrected** are Charles Schwab|2025|Q3 and
Charles Schwab|2025|Q4. Schwab releases after-hours. The rater used the session
before the release as their prior close (the pre-market convention, applied
incorrectly to an after-hours event). The main column M had already been corrected
to the release date (the correct prior close for an after-hours event) with
Price Basis Corrected = YES before this session. The Re-priced prior close
date column (AD) retains the rater's original wrong date as documentation.

The **1 genuine error** is described in section (g) below.

**After all corrections: all 95 documented-release-time rows with an EDGAR
baseline are either in direct agreement or a known exchange-convention
difference. The documented-release-time manual re-pricing method is sound
where an explicit release time was recorded and an EDGAR comparison is possible.**

Source: `outputs/global/summary/manual_repricing_reconciliation.csv`
(clean corroboration rate block, appended 2026-08-13).

---

## (e) Multi-session discrepancies found

The repricing cross-check identified four rows where the human prior-close date
was more than one session from the EDGAR-anchored date. All four used a
price-signal basis (Problem 2 above), not a documented-time basis.

| Event | Rater(s) | Human AD date | EDGAR date | Gap | Diagnosis |
|-------|----------|--------------|------------|-----|-----------|
| Bank of America\|2025\|Q2 | Abdul | 2025-07-14 | 2025-07-16 | 2 calendar days | Human prior-close 2 days before EDGAR entry_date; price-signal basis |
| JPMorgan\|2025\|Q1 | Nigel, Abdul | 2025-03-31 | 2025-04-11 | 11 calendar days | Human used fiscal quarter-end (March 31) rather than the actual release date (April 11) |
| Lowe's\|2026\|Q1 | Anna | 2025-05-20 | 2026-05-20 | 365 calendar days | Year typo: rater entered 2025 instead of 2026 |

The JPMorgan error (11-day gap, fiscal quarter-end used as the entry date) is
the most consequential: the fiscal quarter ends on 31 March but JPMorgan
reported Q1 2025 on 11 April 2025. None of these rows are in the 295-row
corrected subset (all have Price Basis Corrected ≠ YES), so they do not affect
any corrected-subset figures. They are flagged here because they represent
errors that were recorded in the re-pricing block but, since no formula read
that block, were never caught before this audit.

Source: `outputs/global/summary/manual_repricing_reconciliation.csv`,
multi-session disagree sections.

---

## (f) The two workbooks

### Master_Data_LOCKED_2026-08-13.xlsx

Holds the **original human prices and dates untouched**. The LLM arm in this
file was reverted to the old report_date anchor so that the entire file
reflects the pre-correction state. This is a historical record. It should not
be used to compute any figure cited in the dissertation; it exists so that the
before-state can be audited.

### Master_Data_CORRECTED_2026-08-13.xlsx

Holds **both arms on verified release dates**. The LLM arm uses the corrected
EDGAR release_date anchor throughout (all 268 events). The human arm has 295
of 420 rows corrected (Price Basis Corrected = YES), with 125 rows flagged as
uncorrected.

**Cross-arm consistency check**: of 289 events present in both sheets with
Price Basis Corrected = YES, **all 289 agree exactly** on both dates and both
prices (prior-close date, prior-close price, opening date, opening price), to
within one cent rounding tolerance. This was not true before the correction.
The human-vs-model comparison is defensible on those 289 events and not
defensible on the 125 uncorrected rows, which remain on the original
report_date basis.

---

## (g) The KHC sentinel — worked example

### What happened

`KHC_FQ1_2025` (Kraft Heinz, fiscal Q4 2025, reported 2026-02-10 pre-market)
had `next_day_open = 0.0` in the corrected LLM workbook export
(`workbook_llm_corrected.csv`). Zero was not a real price; it was a
missing-price sentinel written where the price fetch returned nothing.

The sentinel propagated through every downstream formula:

| Step | Result |
|------|--------|
| `next_day_open = 0.0`, `prior_close = 24.14` (old anchor) | Actual % Change = (0 − 24.14) / 24.14 = −100% |
| −100% return, but cell displayed as `0` in the CORRECTED export | Actual % Change = 0.0% |
| Direction formula on 0.0%  | Direction = FLAT |
| FLAT direction, decision = SELL | Prediction Correct? = NO |
| |ret| = 0% < 2% threshold | KHC excluded from selectivity denominator |

The FLAT direction caused KHC to be excluded from the selectivity formula,
giving 61/94 = 64.9% instead of the authoritative 62/95 = 65.3%.

A second consequence: because `next_day_open = 0.0` with a SELL decision would
produce a computed return of approximately +100% (short a stock that fell to
zero), had any cost-grid script read from the workbook CSV rather than from
`returns_matrix.csv`, it would have treated KHC as a near-100% profit on a
single trade. For N=233 with 146 traded events, that single spurious return
would inflate the mean net per trade by approximately +0.68 percentage points
(100% / 146), raising the implied breakeven transaction cost from 196.17 bps
to approximately 254 bps — an inflation of roughly one third. The cost-grid
script (`experiments/execution_cost_grid_n233.py`) explicitly avoided this by
reading `returns_matrix.csv` directly, but the sentinel remained in the
workbook until this session.

### Corrected values

Source: `returns_matrix.csv`, document_id = `KHC_FQ1_2025`.

| Field | Before (sentinel) | After (corrected) |
|-------|-------------------|-------------------|
| release_date | — | 2026-02-10 (pre-market; from EDGAR 8-K filing date) |
| Prior close date (M / closing_date) | 2026-02-11 (human); blank (LLM) | **2026-02-09** (session before release) |
| Prior close price (N / prior_close) | 24.14 (old anchor); 24.99 (human) | **24.90** (returns_matrix entry_close) |
| Opening date (O / opening_date) | 2026-02-12 (human); blank (LLM) | **2026-02-10** (release date open) |
| Next day open (P / next_day_open) | blank / 0.0 | **23.80** (= 24.9 × (1 − 0.044177)) |
| Actual % change | 0.0% | **−4.4177%** |
| Actual direction | FLAT | **DOWN** |
| Prediction correct? | NO | **YES** (SELL matched DOWN) |
| ret_overnight (returns_matrix) | — | **−0.0442** |

After the fix the LLM sheet formula reproduces **62/95 = 65.3%** exactly,
consistent with the authoritative figure from `item_e_walkforward.json`.
The human arm KHC row (Human_Data_Entry row 193, Meriem) had no decision
recorded (column J = blank), so Prediction Correct? remains blank; only
M, N, O, P, Q, R, and Price Basis Corrected were updated.

---

## (h) Caveats at full strength

### 1. 109 unique human events remain on the original price basis

Approximately 109 unique human events (roughly 121 Human_Data_Entry rows,
including multi-rater passes) remain on the original report_date price basis
because no verified EDGAR release date was sourced. These split into:

- **Human-only US issuers** (~81 rows): MetLife, Duke Energy, ExxonMobil,
  American Express, Chevron, Intel, Mastercard, Costco, Colgate-Palmolive,
  Datadog, eBay, Union Pacific, Home Depot, Adobe, Shopify, Freeport-McMoRan,
  Johnson & Johnson, Booking Holdings, Dell, UnitedHealth, Caterpillar.
  An EDGAR 8-K lookup is feasible for all of these but was not attempted.

- **Non-US issuers** (~20 rows): Shell, Heineken, Hermès, Allianz, Sony, Nestlé.
  No SEC filing exists; the home-exchange announcement date would need to be
  sourced from each exchange individually.

**Human-arm figures must be reported on the corrected 295-row subset, with the
full 420-row figure alongside and clearly labelled.** The 125 uncorrected rows
are knowingly on the original basis; treating them as equivalent to the
corrected rows would reintroduce the systematic timing error described in (b).

### 2. The LLM sheet holds all 268 events; N=233 requires an explicit filter

`LLM_Data_Entry` contains all 268 phase-2 scored events. The clean universe of
N=233 is defined by the **In Clean Universe** column (column BA): 233 rows read
YES, 35 read NO (25 worksheet contamination, 1 SPOT misattribution, 9 timing
unresolved). Any formula or pivot that reads from LLM_Data_Entry without
filtering on In Clean Universe = YES is computing on N=268 and will not
reproduce the N=233 figures quoted throughout the dissertation.

### 3. Formula-driven cells are unverified until opened in Excel and recalculated

The XLSX files were written by openpyxl. LibreOffice Calc does not evaluate
XLOOKUP, which is used in several helper columns (LLM Decision, LLM Correct?
in Human_Data_Entry; cross-tab lookups in Summary). Every formula-driven cell
should be treated as unverified until the file is opened in Microsoft Excel and
recalculated (Ctrl+Alt+F9). Values written as literals (including all M–P
corrections and In Clean Universe flags) are not formula-dependent and are
correct as written.

### 4. No externally-cited realistic desk cost exists in this repository

The only transaction-cost reference point committed to this repository is the
deployed assumption of 10 bps round-trip (CLAUDE.md, Model_Arm_Gap_Spec.md
line 18). The mean-net breakeven for the N=233 clean universe on the corrected
release-date anchor is **196.17 bps** (primary metric; `ext9_cost_grid_n233.json`,
`breakeven_mean_net_per_trade_bps`, source `returns_matrix.csv` ret_overnight).
No figure from Dr Rock or any comparable external cost estimate is committed
here. Any claim that the breakeven exceeds realistic trading costs must be
attributed to an external source supplied explicitly, or dropped.

---

## (i) Full list of changes — cell ranges and counts

### `data/workbook/Master_Data_CORRECTED_2026-08-13.xlsx`

| Sheet | What changed | Rows/cells affected |
|-------|-------------|---------------------|
| LLM_Data_Entry | KHC row 202 corrected: K(closing_date)→2026-02-09, L(prior_close)→24.9, M(opening_date)→2026-02-10, N(next_day_open)→23.80, P(actual_pct)→−4.4177, Q(direction)→DOWN, R(prediction_correct)→YES, T(net_pnl)→0.043177 | Row 202 |
| LLM_Data_Entry | Column BA (In Clean Universe): 233 YES, 35 NO, written as literals | Rows 3–270 (268 data rows) |
| LLM_Data_Entry | Column BB (Exclusion Reason): populated for 35 excluded rows; blank for 233 clean | Rows 3–270 |
| Human_Data_Entry | Column M (Prior Closing Date), N (Prior Close $), O (Next Opening Date), P (Next Day Open $) corrected to verified release-date-anchored values | 295 rows (Price Basis Corrected = YES) |
| Human_Data_Entry | Column BS (Price Basis Corrected): YES or NO for all 420 rows | All data rows |
| Human_Data_Entry | Column BT (Not Corrected Reason): populated for 125 uncorrected rows | 125 rows |
| Human_Data_Entry | KHC row 193 (Meriem, 2025 Q4): M→2026-02-09, N→24.9, O→2026-02-10, P→23.80, Q→−4.4177%, R→DOWN, AN→YES | Row 193 |
| Accuracy_Conventions | Chart floor note added at row 30 | Row 30 |
| Accuracy_Conventions | N=233 static section added (rows 78–89): coverage 62/147 = 42.2%, selectivity 62/95 = 65.3% | Rows 78–89 |
| Accuracy_Conventions | Row 88 reconciliation note: names KHC_FQ1_2025 as the event causing 61/94 vs 62/95, states it is resolved | Row 88 |
| Accuracy_Conventions | Human-arm coverage limitation note (rows 91–92): 109 unique events, 121 rows uncorrected, split by US/non-US | Rows 91–92 |
| Corrections_Log | 3 entries: KHC LLM fix (sentinel); exclusion columns added; KHC human row 193 fix | Rows 2–4 |
| Corrections_Log | Header added | Row 1 |

### `data/workbook/Master_Data_LOCKED_2026-08-13.xlsx`

| Sheet | What changed | Rows/cells affected |
|-------|-------------|---------------------|
| LLM_Data_Entry | KHC row 202 **left at old-anchor values** (L=24.14, N=23.64) as historical record | Row 202 unchanged |
| LLM_Data_Entry | Column BA (In Clean Universe): 233 YES, 35 NO | Rows 3–270 |
| LLM_Data_Entry | Column BB (Exclusion Reason) | Rows 3–270 |
| Accuracy_Conventions | Same chart note and N=233 static section as CORRECTED | Rows 30, 78–89, 91–92 |
| Corrections_Log | Same entries as CORRECTED | Rows 1–4 |

### `outputs/global/summary/workbook_llm_corrected.csv`

KHC_FQ1_2025 row corrected: prior_close 24.14→24.9, closing_date→2026-02-09,
next_day_open 0.0→23.80, opening_date→2026-02-10, actual_pct_change→−4.4177,
actual_direction→DOWN, prediction_correct→YES, net_pnl→0.043177,
release_date→2026-02-10, release_timing→pre_market,
release_date_source→returns_matrix.csv, document_date→2026-02-10.

### `outputs/global/summary/manual_repricing_reconciliation.csv`

New file, created this session. Contains:
- Pass 1 summary (all raters, all rows with AD date populated, N=400):
  243 agree with EDGAR, 37 classifiable disagrees (5+10+4+17+1=37), 121 no EDGAR record.
- Pass 2 summary (first rater per event, N=356):
  217 agree, 104 no EDGAR record, 17 listing/currency, 10 one-session afterhours,
  5 one-session premarket, 3 multi-session.
- Full row-level detail for all 400 rows with AD date populated.
- Multi-session disagree detail (4 rows: BAC, JPM×2, Lowe's).
- Clean corroboration rate block (appended 2026-08-13): 95/95 comparable
  documented-time rows correct or convention difference after corrections.

### `outputs/global/summary/ext9_cost_grid_n233.json`

New file, created this session by `experiments/execution_cost_grid_n233.py`.
Records breakeven transaction costs on corrected release-date anchor:

| Universe | Metric | Breakeven |
|----------|--------|-----------|
| N=268 (corrected anchor) | compounded total return = 0 (retired, order-dependent) | 186.12 bps |
| N=268 (corrected anchor) | mean net per trade = 0 **[PRIMARY]** | 207.34 bps |
| N=233 (clean, corrected anchor) | compounded total return = 0 (retired) | 175.33 bps |
| N=233 (clean, corrected anchor) | mean net per trade = 0 **[PRIMARY]** | **196.17 bps** |

Not in this table (different anchor, different price set, not comparable):
162.81 bps (ext9_cost_grid_summary.json, OLD report_date anchor, N=268,
compounded metric — superseded 2026-08-12).

### Unchanged files — confirmed current

| File | Status |
|------|--------|
| `outputs/global/summary/surviving_findings.md` | Figures unchanged; denominator counts added to several percentages (e.g. "(27/52)", "(96/171)") during today's session for clarity. All nine findings and their statistics are current as of the corrected anchor. |
| `outputs/global/summary/workbook_metrics.csv` | Unmodified since last commit. All figures are on the N=233 clean universe, corrected release-date anchor. Authoritative source: `ext2_holding_curve.csv`, `item_e_walkforward.json`, `returns_matrix.csv`. |
| `outputs/global/summary/frontier_table.csv` | "always-SELL" label corrected to "always-DOWN"; three-figure reconciliation block added. Data rows and numeric values unchanged. |

---

*End of log.*
