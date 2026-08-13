# Extension Pre-registration Note

**Date:** 2026-08-13  
**Written before any document has been gathered or any event has been scored for the extension.**

---

## Decision

The model arm is being extended to cover companies that the human arm read but the model arm
never scored. As of this date, 20 such companies have been identified from the group workbook
(Master_Data_CORRECTED_2026-08-13.xlsx), with 93 unique events across those companies.

---

## Selection Rule

The selection rule is: **every company where human readings exist in the group workbook but no
model arm scoring exists in the frozen N=233 results.**

This rule is determined entirely by the human arm's existing coverage. No property of the events
themselves — sector, return magnitude, volatility, or model-expected difficulty — was used to
select or de-select any company or quarter. Companies are included because a human read them, not
because anything is known or expected about how the model will perform on them.

---

## Scope of the Extension

93 unique events across 20 companies:

- **15 US issuers**: Adobe (ADBE), American Express (AXP), Chevron (CVX), Colgate-Palmolive (CL),
  Costco (COST), Datadog (DDOG), Duke Energy (DUK), ExxonMobil (XOM), Freeport-McMoRan (FCX),
  Home Depot (HD), Intel (INTC), Mastercard (MA), Shopify (SHOP), Union Pacific (UNP), eBay (EBAY).
- **5 non-US issuers**: Heineken (HEINY/HEIA), Hermes (RMSP.XC/RMS), Nestle (NSRGY/NESN),
  Shell (SHEL), Sony (SONY/6758.T).

The gathering checklist recording the exact event-by-event document paths is at
`outputs/global/summary/extension_gathering_checklist.csv`.

---

## Relationship to the Frozen Primary Results

The extension results **will be reported separately** from the frozen N=233 results. They are not
merged into the primary dataset and do not alter any figure, table, or finding that cites the
frozen state.

- The authoritative frozen state is tagged **model-arm-final-2026-08-13** (commit e8596e2).
- Every document citing that tag — `surviving_findings.md`, `frontier_table.csv`,
  `workbook_correction_log_2026-08-13.md`, `ext9_cost_grid_n233.json`, and all associated
  backing CSVs — remains the primary result and is not modified by this extension.
- Extension outputs will use a distinct output tree and a distinct calibration CSV
  (suffix `ext2026_08_13` or similar), never writing into the frozen results directories.

---

## Exclusion Rules Carried Over Unchanged

The following rules apply to every extension event identically to the primary N=233 universe:

1. **Release timing**: the entry date must be confirmed from a documented public timestamp.
   For US issuers this is the EDGAR 8-K Item 2.02 acceptance timestamp. For non-US issuers
   (Heineken, Hermes, Nestle, Shell, Sony) this must be sourced manually from each company's
   home exchange regulatory filing or IR announcement with a recorded date and time.
   Any event whose release timing cannot be confirmed is timing-excluded and not scored.

2. **Per-section attribution**: every document placed in the pipeline must be verified to
   contain the correct company, correct fiscal period, and correct document type before
   scoring. Documents gathered for this extension were collected through the same manual
   process that previously produced one misattributed transcript (NFLX) and two
   quarter-shifted news digests. Each file must be spot-checked (company name in opening
   text, fiscal period match to folder label) before the manifest entry is created.

3. **No post-decision-point content**: no document may contain information dated after the
   earnings release date. This includes news digests, analyst summaries, or any supplementary
   material. Press releases are sourced from the original EDGAR filing and are inherently safe
   on this criterion; any non-EDGAR document must have its date verified.

4. **Worksheet contamination**: the extension events were selected because the human arm
   read them, which means worksheet files exist for at least some raters. The worksheet leak
   check (`worksheet_leak_flags.csv`) applies unchanged: any event where a human annotated
   a worksheet score that was then visible to a subsequent scorer is excluded from the
   extension graded set.

---

## What This Note Does Not Pre-register

This note pre-registers the selection rule and the exclusion rules. It does not pre-register
a hypothesis about model performance on the extension set. The extension is a coverage
expansion, not a separate pre-registered experiment. Results will be reported descriptively
alongside the qualification that the same in-sample threshold concerns that apply to the
primary N=233 set apply here: the HOLD thresholds (+0.25/-0.05) were fitted on data the
model has already seen, and the extension events add new coverage without re-validating those
thresholds out of sample.
