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

---

## Amendment — 2026-08-13 (written after 7-event pilot, before further gathering)

**Pilot status when this amendment was written**: the 7-event pilot (Colgate-Palmolive 4 events,
Costco 3 events) had already been scored. Its outcome was 1 graded event (|ret|>2%), 0 traded
events, no accuracy computable. This outcome could not have informed any of the decisions below:
a single graded event with no trades gives no signal about which items to run or drop.

### Items the extension runs

The extension runs all five items, A through E, on the same basis as the frozen N=233 set.
This is decided now, before gathering begins and before any extension results beyond the 7-event
pilot are known, so that no item can be added or dropped on the basis of what the results show.

- **Item A** (return matrix): overnight and multi-horizon returns, same horizons as the frozen set.
  Release dates must be confirmed before the return matrix can be built; timing-unresolved events
  are excluded exactly as in the frozen set.
- **Item B** (holding-period curve): cumulative P&L curve across the extension traded events.
- **Item C** (four-arm section ablation): see stated limitation below.
- **Item D** (FinBERT and dictionary baselines): applied to the same document set as the model arm.
- **Item E** (walk-forward threshold validation): applied to the extension graded events; if the
  extension graded count is too small for walk-forward to be informative, this will be reported
  as a structural limitation rather than omitted.

### Reporting sets

Results will be reported on three event sets:

1. **FROZEN** (N=233, tagged model-arm-final-2026-08-13): the primary result. Never overwritten.
   All findings in surviving_findings.md refer to this set.
2. **EXTENSION ONLY** (up to 93 events, subject to exclusions): the sector broadening test.
   Reported as a separate descriptive block. The extension tests whether the frozen set's fitted
   thresholds generalise across sectors, not across time (the two date ranges overlap).
3. **COMBINED** (N=233 + extension, after exclusions): the robustness check. Reported alongside
   appropriate qualification that the combined set mixes in-sample-threshold events (frozen) with
   genuinely unseen events (extension).

The frozen set is never modified. The extension and combined sets are additions.

### Prior expectation (recorded before results are known)

Extension accuracy is expected to be **lower** than the frozen set's 65.3% (62/95), for two
reasons that apply before any result is seen:

1. **Threshold selection**: the deployed HOLD thresholds (+0.25/-0.05) were fitted on the frozen
   N=233 events. The extension events are genuinely unseen by that selection step. Any in-sample
   inflation in the frozen figure does not carry to the extension.
2. **Sector character**: the extension adds utilities (Duke Energy, ExxonMobil) and non-US names
   whose earnings dynamics may differ materially from the frozen set's sector mix.

This expectation is recorded so that the result — whether it confirms or contradicts it — can be
read against a stated prior rather than interpreted post hoc.

### Item C stated limitation (recorded before gathering begins)

Item C (four-arm section ablation) requires four separately scoreable document bundles per event:
full bundle, press release only, prepared remarks, and transcript Q&A. A yield analysis of the
93 candidate events from the human arm's workbook data shows:

- **29 of 93 events** had a transcript read by at least one human rater (Document column in
  Human_Data_Entry).
- **64 of 93 events** are press-release-only: the human arm read only the press release or full
  bundle where the bundle is a press release alone.

Item C can only be run on events where a transcript exists and can be sourced. The upper bound
is 29 events, and the actual count depends on which of those 29 transcripts are gatherable.
For the 64 press-release-only events, Item C reduces to a single arm and cannot produce a
meaningful four-arm comparison.

This is recorded as a pre-stated structural limitation of the extension's Item C, not a finding
to be reported after the fact. If fewer than 20 four-arm events are achievable, Item C will be
reported as infeasible for the extension and omitted from the extension-only results block.
