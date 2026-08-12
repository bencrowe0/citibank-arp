# Retracted findings — 2026-08-12

Two findings reported on 2026-08-12 were artefacts of the stale entry anchor
(report_date close used uniformly instead of release_date-aware entry). Both
are documented here so the pattern is on the record.

## 1. "72.7% of pre_market events fall inside the ±2% band"

**What was claimed**: 72.7% of pre_market events (96/132) had overnight
returns inside the ±2% HOLD band, against 26.8% (26/97) for after_hours.
This was presented as a 3× structural asymmetry in what the study could
measure, driven by the overnight gap capturing less of the earnings reaction
for BMO reporters.

**Corrected figure**: 42.4% (56/132) for pre_market, 29.9% (29/97) for
after_hours. The asymmetry is real but roughly 1.4×, not 3×.

**Why the artefact arose**: For 82 pre_market events where release_date =
report_date, the old convention used report_date close as entry — which was
already post-announcement for a BMO reporter. The overnight gap from that
close to the next morning's open was residual drift, not the earnings
reaction. The corrected anchor shifts entry to the prior session's close, so
the gap now spans the actual pre-market release and captures most of the
reaction. This moved ~40 events from inside the band to outside it.

## 2. "61% of ungraded trades were directionally correct (p=0.064)"

**What was claimed**: 46 of 75 ungraded trades (events where the model traded
but the overnight return fell inside ±2%) had their directional sign match the
model's call. This was presented as a measured cost of the pre-registered HOLD
band — the band was discarding events where the model had real signal.

**Corrected figure**: 28 of 50 ungraded trades = 56.0%, p=0.480 (not
significant).

**Why the artefact arose**: The 25 events that moved from "flat traded"
(ungraded) to "graded" were disproportionately the ones with correct signs
and larger magnitudes — they sat just below the ±2% boundary under the old
entry and moved above it under the corrected entry. Removing them from the
ungraded pool dropped the rate from 61% to 56% and eliminated the
significance. The band is not discarding signal; the old entry was compressing
returns below the band.

## 3. Accuracy-versus-P&L divergence

**What was claimed in earlier project notes**: accuracy and P&L point in
opposite directions because the HOLD metric rewards hedging while P&L rewards
exposure, with pre_market showing higher accuracy (70.8%) and lower mean net
(+0.723%) than after_hours (65.1%, +2.749%).

**Corrected figures**: pre_market accuracy 64.6% vs after_hours 65.9% — nearly
identical. Mean net +1.149% vs +2.817%. The accuracy divergence has vanished.
Pooled: accuracy 65.2% (60/92), mean net +1.877% — both positive, no
directional divergence.

The earlier divergence was an anchor artefact: the old entry inflated
pre_market accuracy by restricting the graded sample to the 24 most extreme
reactions (70.8% on an easy subset) while deflating mean net by including 56
near-zero flat trades. The corrected anchor doubles the pre_market graded
sample to 48 events, diluting the inflated accuracy and increasing mean net.

## 4. Agreement filter (+17.3pp, p=0.029)

**What was claimed**: LLM correct-direction accuracy on overnight returns
(±2% band) is 32.7% (18/55) where both arms agree, vs 15.4% (8/52) where
they disagree. This was the replacement for the unreproducible 0.561/0.429
headline. It was computed on the stale report_date anchor.

**Corrected figure**: agree 69.0% (20/29), disagree 69.2% (18/26), diff
-0.3pp, p=0.959. **The agreement filter vanishes entirely.**

**Why the artefact arose**: The stale anchor compressed overnight returns
for 82 pre_market events, making most returns fall inside the ±2% band
(graded N was only 55+52=107 out of 167 paired rows). The corrected anchor
produces larger, more accurate overnight returns, raising accuracy across
the board from ~25% to ~69% — but raising it equally for the agree and
disagree groups, eliminating the differential. The filter was not measuring
a real property of agreement; it was measuring which events happened to have
returns large enough to breach the band under the wrong entry.

**Note**: The 0.561/0.429 figures cited in Model_Arm_Implementation_Spec.md
are not reproducible from any script or output in this repository. They are
superseded by this computation regardless of the anchor correction.

## Lesson

All four artefacts trace to the same root cause: using report_date close
uniformly as entry, which was wrong for 82 pre_market events. The corrected
anchor (release_date from EDGAR 8-K Item 2.02) resolves the entry to the
correct session. The structural mechanism — that pre_market gaps are
compressed relative to full-day moves — is real but its magnitude was
overstated by the stale anchor.
