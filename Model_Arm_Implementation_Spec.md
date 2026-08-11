# Model Arm Implementation Spec

## Context

This is the working spec for the model arm of an MSc Applied Research Project run in partnership with Citibank, titled "Can AI Read the Markets? LLMs for Predictive Financial Intelligence". The pipeline reads earnings materials and Federal Reserve minutes and produces directional BUY, HOLD and SELL calls with evidence quotes and a confidence label attached, and those calls have been calibrated against real forward stock returns and backtested net of transaction costs. The full quantitative analysis across 120 paired events, covering 2024 through mid 2026, has already been run and seen. The work splits into a human arm, where team members score the same documents by hand, and this model arm, which one person owns. The deadline is 1 September 2026 and today is 5 August 2026, so there are three weeks of build and one week of writing. The artefacts that already exist are `Master_Data_NEW.xlsx` as the master event and results store, `p2_[company]/summary/*.csv` as per-company scored outputs, the event manifest carrying report dates and the release-timing rule per event, `eval/outcomes.py` which currently returns one overnight return per event, `LLM_vs_Human_Trader_Metrics.xlsx` holding the human comparison and cost accounting, and an API cost ledger with tokens and spend per document. This spec covers eight items, one already answered and needing only a write-up, two pieces of plumbing both arms depend on, and five analyses on outputs that mostly exist. Work through the items in the sequencing order at the end, and check each item's dependency line first, because several can start today while others wait on the human arm's reading sessions.

## Locked conventions

Every item below inherits these. Do not reinterpret them silently.

- HOLD band. Plus or minus 2 percent at the overnight horizon. At 3, 5 and 10 days the band is set so the share of HOLD events matches the overnight share, rather than staying flat at 2 percent, because the 2 percent figure was chosen against an earnings jump and does not travel to a longer window. Report the implied band in percent alongside every horizon.
- Horizons. Overnight, 3, 5 and 10 trading days. Multi-day horizons run from the release-day open, so the overnight gap and the subsequent drift stay separable.
- Anchor date. Pre-market reporters anchor on the release day itself. After-hours reporters roll to the next session. The rule is already recorded in the manifest and must be applied from there, never reimplemented elsewhere.
- Returns are computed both raw and excess over SPY across the identical window.
- Price pulls use `auto_adjust=False` and step forward on the NYSE calendar through `pandas_market_calendars`, so a public holiday does not silently turn a five-day horizon into seven.
- The assumed round-trip trading cost is an input rather than a result, so nothing computes it. Every net return reported so far used a number sitting in the backtest, and the existing result is described as holding at five times the assumed costs, which cannot be true unless that number exists. What is missing is anywhere stating what it is. Grep the backtest for a cost, fee, bps, commission or slippage variable, check the results workbook for an assumptions tab, otherwise ask whoever wrote the net profit line. Cross-check while looking, break-even is roughly 113 basis points for the model arm (already computed), so if the result survived five times the assumption then the assumption is around 20 basis points or below. If nobody ever chose it, choose 20 basis points, minute it with today's date, and state in the write-up that it is an assumption rather than a measurement. This blocks nothing, since it only enters at the final subtraction that turns gross returns into net ones.
- Signal to position mapping and position size are already implicit in the benchmarking workbook. Confirm and record them rather than deciding fresh, and note explicitly whether SELL is a short or simply staying flat, because a long-only desk cannot short and the answer changes every profit and loss figure.
- Every run writes a `run_id` into every output row, so two runs can never be silently mixed in the results store.

## Numbers already computed, quote them, never recompute

- Break-even round-trip transaction cost, roughly 113 basis points for the model arm and 127 for the human arm. Already computed.
- Mean token cost, around half a cent per event, against roughly 37 minutes of human analyst time per event. Already computed.
- Agreement-conditional accuracy, 0.561 on the 57 events where both arms agree, against 0.429 where they disagree. Already computed.
- Reading speed, around 16 seconds per document against roughly 35 minutes of analyst time. Already computed.
- Macro weighting, accuracy fell from roughly 0.466 to 0.443 when macro weight was forced on, and the weight search settled at zero. Already computed.
- A permutation test on the blend weights. Already run.
- Profit and loss is concentrated in roughly ten events out of the 120. Already computed.

## What the human arm supplies, and what it does not

The human predictions are the one input the model arm cannot produce for itself. Everything else, the prices, the horizons, the costs and the aggregation, is sourced or computed on this side.

| The human arm supplies | The model arm supplies |
|---|---|
| `event_id`, matching the manifest exactly | `anchor_date`, from the release-timing rule |
| `report_date` | `ret_overnight`, `ret_3d`, `ret_5d`, `ret_10d` |
| `human_score` and `human_signal` | The excess-over-market version of each return |
| `information_set` and pass number | The implied HOLD band at each horizon |
| `minutes`, peeked flag and notes | The backtest script and every aggregation |
| Their verdicts on the evidence items | The screened evidence items they judge |

The join runs on `event_id`, so that column must match the manifest exactly and must not be retyped by hand. Report dates matter too, because the walk-forward splits the sample on them.

Three consequences to carry through everything below.

- The human reading is the critical path, not the code. Every extension can be written, tested and run against the model signals before a single human sheet exists, and the same code then produces the human line with the score column swapped in. The code is never waiting on data it could fetch, it is waiting on people reading documents.
- Take partial deliveries. Join and run whatever human scores exist rather than waiting for all six raters to finish all four quarters, and update the numbers as more arrive. That surfaces a column mismatch or a mistyped event id in week one rather than week three.
- Three things are owed to the human arm and two of them block it. The screened evidence items, which their review cannot start without. The return matrix filtered per ticker as a read-only reference so they can sanity check their own company. And the implied HOLD bands at 3, 5 and 10 days, which fall out of the matrix. Their overnight scoring can begin before any of it exists.

---

## Item 1. Macro and policy context, already answered

**Runs without Human Arm Results.**

**Main topic.** Whether macro and policy context improves the model's read of a company document.

**What it does and the goal.** This consolidates two earlier research questions, the Federal Reserve arm and the macro context injection arm, into one finished question. Federal Reserve material and news context have both been injected into the pipeline and the weight search settled on zero, meaning the pipeline reads company documents best with no macro context attached, and the earlier numerical weighting work pointed the same way with accuracy falling from roughly 0.466 to 0.443 once macro weight was forced on (already computed). This is a negative result on something the supervisor asked directly, and it is worth reporting as one, because it says the document itself is the information at this horizon. Roughly half a day, all reporting rather than running.

**Inputs.** The stored weight search results, the per-event scored outputs in `p2_[company]/summary/*.csv`, and the sector labels for the per-sector split.

**Steps.**

1. Report the weight search itself, as a curve of accuracy against macro weight with zero marked on it, rather than only stating the conclusion. A curve is far more convincing than a sentence saying zero was best.
2. Put a paired interval on the comparison. It is the same events scored twice, once with context and once without, so bootstrap the difference per event directly rather than showing two overlapping group intervals. The paired form is much more powerful at this sample size because event-to-event variation cancels out. Use the bootstrap helper from Item 2.
3. Add a per-sector split. The original expectation was that a bank would be more macro-sensitive than a streaming company, so test it rather than asserting it. If the split shows nothing either, report that, because a uniform null is a stronger statement than an average null.
4. State the point-in-time discipline explicitly, meaning no injected brief post-dates the event it was attached to, and say in one sentence how it was enforced. The trap is that Federal Reserve minutes publish three weeks after the meeting they describe, and this is the first thing a marker checks on any macro claim.
5. If the Federal Reserve statements were also scored on their own against a market instrument, report that as a separate table. Reading policy language is a different claim from using policy language as context, and folding them together weakens both.

**Outputs.** `macro_weight_curve.png` with zero marked, `macro_paired_interval.csv` holding the bootstrapped difference, `macro_sector_split.csv`, and a short methods paragraph on point-in-time enforcement, plus `fed_standalone_table.csv` if the separate scoring exists.

**Acceptance checks.**

- The curve shows the full weight sweep with the zero point visibly marked and the 0.466 to 0.443 figures reproduced from the store, not recomputed.
- The interval on the difference is paired, computed per event then aggregated, not two separate arm intervals.
- The write-up contains one sentence naming the enforcement mechanism for the point-in-time rule.

**What we are testing and what to expect.** Already known. Expect the write-up to land on the argument that the binding constraint is document-level signal quality rather than missing context, the same conclusion the cost work reaches from a different direction. Expect the per-sector split to show nothing, and report that plainly if so.

---

## Item 2. Shared plumbing, the return matrix and the bootstrap helper

**Runs without Human Arm Results,** except that the difference-between-arms bootstrap variant needs human scores before it can produce a number, and the finished return matrix is owed to the human arm filtered per ticker.

**Main topic.** Two pieces built once that everything downstream reads, a multi-horizon return matrix and a bootstrap interval function.

**What it does and the goal.** Six of the later items need returns at multiple horizons, and without one cached matrix each would call the price API separately, slowly, rate-limited, and with subtly different numbers wherever an implementation detail differs. The bootstrap helper exists because 120 events makes every headline figure one draw from a noisy process, and bootstrap intervals were dropped from the group's item list, so they are reinstated here as plumbing, since without them every figure this arm produces is a bare point estimate. Half a day each.

**Inputs.** The event manifest for `event_id`, ticker, report date and the release-timing rule, `eval/outcomes.py` as the module to extend, and yfinance for prices.

**Steps, the return matrix.**

1. Extend `eval/outcomes.py` so it returns a labelled vector per event rather than one overnight number.
2. For each event, resolve `anchor_date` from the release-timing rule in the manifest. The trap is that getting the rule backwards inverts the return on half the events for a given name and the result still looks plausible, which is why the rule is applied here and nowhere else.
3. Pull one price series per ticker covering release minus 5 sessions to release plus 25, wide enough that no horizon runs off the end, with `auto_adjust=False`, stepping on the NYSE calendar through `pandas_market_calendars`.
4. Compute the overnight return from the close before release to the next open, then the 3, 5 and 10 day returns from the release-day open, stepping in trading days.
5. Download SPY over the same range and add an excess column per horizon, the stock's return minus the market's over the identical window. One extra download, and it answers the objection that a rising market was measured rather than a signal.
6. Derive the implied HOLD band at 3, 5 and 10 days so the share of HOLD events matches the overnight share, and record the implied band in percent per horizon.
7. Cache one tidy CSV, one row per event, with `event_id`, `ticker`, `anchor_date`, then overnight, 3, 5 and 10 day returns in raw and excess form. Everything downstream reads this file rather than touching prices.
8. Hand a copy filtered per ticker to the human arm as a read-only reference.

**Steps, the bootstrap helper.**

1. Write one function taking a list of per-trade net returns and returning point estimates and percentile intervals for total return, mean per trade, hit rate and Sharpe.
2. Draw ten thousand resamples with replacement, and report the 5th and 95th percentiles. Use one resample per draw across all statistics rather than resampling separately per statistic, so total return, hit rate and Sharpe stay internally consistent with one another.
3. Add a variant that bootstraps the difference between two arms directly, because the question people actually ask is whether one arm beats the other, and an interval on the difference answers it where two overlapping intervals do not. This variant needs human scores to produce a number but can be written and tested against two model configurations now.
4. Add a clustered variant that resamples report dates rather than individual trades, because events in the same reporting week share a market factor and are not independent. The clustered interval comes out wider and it is the more honest one to quote.

**Outputs.** `returns_matrix.csv`, per-ticker filtered copies for the human arm, `implied_hold_bands.csv`, and `bootstrap.py` exposing the plain, difference and clustered variants.

**Acceptance checks.**

- Two events verified by hand against a price chart, one pre-market reporter and one after-hours reporter, confirming the anchor date behaved differently for each. This single check catches the most damaging silent error available in this project.
- The matrix has exactly one row per manifest event with no missing horizon cells, and every horizon's implied band is recorded in percent.
- The bootstrap returns consistent joint statistics from a single resample stream, and the clustered interval is at least as wide as the plain one on a test input.

**What we are testing and what to expect.** Not a hypothesis, this is infrastructure. Expect the bootstrap intervals downstream to be wide and to frequently cross zero, which is the result rather than a problem with the method, and the write-up should say so before a reader concludes it was hidden.

---

## Item 3. Section ablation

**Runs without Human Arm Results,** their parallel version is a separate experiment and only the comparative write-up needs both.

**Main topic.** Which part of the document carries the signal, measured as accuracy against tokens per section.

**What it does and the goal.** Each earnings event is scored five ways, once per document section and once on the full bundle, to find where the predictive signal sits relative to the token cost. It matters beyond its own finding, because if the press release alone carries most of the signal then the document-gathering effort for the expansion names drops severalfold, which is why it runs early. The model has no memory between calls, so the five arms are genuinely independent reads, which the human version cannot be, and the write-up must say so plainly rather than presenting the two as the same test.

**Inputs.** The stored extracted document text per event, the manifest, the overnight return and band from Item 2's matrix, and the API cost ledger for the token logging convention.

**Steps.**

1. Availability audit first, an afternoon, and it gates everything else. For how many events do we hold the press release, the prepared remarks, the guidance passage and the questions and answers separately. The achieved sample is unknown until this runs, so state it before promising a result to anyone.
2. Agree four section boundaries, one sentence each, written down before splitting anything, so a boundary cannot be quietly adjusted later.
3. Split each document into four files. Regex on headings where transcripts are consistent, by hand where they are not, roughly five minutes each.
4. Run five independent calls per event, one per section plus the full bundle, logging prediction, tokens and cost per arm.
5. Grade all five arms against the same overnight move and the same band, so nothing differs between arms except what went into the prompt.
6. Run only on events where all five arms exist. The trap is that comparing arms drawn from different subsets is not a comparison, it is two different experiments plotted on one chart.

**Outputs.** `section_availability_audit.csv`, the four split files per event, `section_ablation_results.csv` with prediction, tokens and cost per arm per event, and `section_accuracy_vs_tokens.png` with one point per arm, plus a four-row pooled table of accuracy and cost by component with a one-line implication for the expansion.

**Acceptance checks.**

- The results file contains only events where all five arms exist, and the count matches the availability audit.
- Every call logged tokens and cost, and every row carries a `run_id`.
- The written expectation below was recorded before the runs, so it counts as a tested prediction.

**What we are testing and what to expect.** Expect the guidance passage and the press release to carry more than their token share and the prepared remarks to carry least. Write that expectation down before running. Expect per-company results to be uninformative, since each section is tested roughly once per company per quarter, so only the pooled table is a result.

---

## Item 4. Cheap baselines and the cost-accuracy frontier

**Runs without Human Arm Results,** unless the human arm is added to the frontier as a point, which needs their minutes.

**Main topic.** Whether the model's cost buys anything over a method that is effectively free.

**What it does and the goal.** Two cheap scorers, a finance word list and a small sentiment model, are pushed through the identical evaluation as the model arm, then plotted on a frontier of accuracy against cost per document. This is the arm the original three-routes design specified and never built, it answers the brief's cost-efficiency aim directly, and it is the question an examiner asks first about any LLM project.

**Inputs.** The stored extracted text per event, the overnight return and band from the matrix, the development split definition, and the API cost ledger for the model arm's cost point.

**Steps.**

1. Loughran-McDonald first, an afternoon. Count positive words minus negative words over total words on the same extracted text, giving one sentiment number per document with no model involved.
2. Map that ratio to BUY, HOLD and SELL using thresholds fitted on the development split only. The trap is that fitting them on the events being scored hands the cheap arm an advantage the model never had, and it is easy to do without noticing.
3. FinBERT second, through HuggingFace. It has a 512-token input limit, so chunk each document, score each chunk, and average chunk-level sentiment weighted by chunk length, so a two-sentence chunk does not count as much as a full page.
4. Push both baselines through the identical evaluation code as the model arm, so nothing differs but the scorer.
5. Add the cost axis. Tokens and pounds per document for the model arm from the existing ledger, near-zero marginal cost plus local compute time for the baselines. Say plainly that the two cost currencies are not naturally comparable, since any conversion rate is an assumption.
6. Plot accuracy against cost per document, one point per arm, with bootstrap intervals from Item 2.

**Outputs.** `baseline_lm_scores.csv`, `baseline_finbert_scores.csv`, `frontier.png`, and a three-arm accuracy table with intervals, `frontier_table.csv`.

**Acceptance checks.**

- The baseline thresholds trace to the development split only, verifiable from the split definition logged beside the mapping.
- All three arms were scored by the same evaluation code path on the same events.
- The write-up states that momentum and random baselines were dropped, and that the luck question is answered by the permutation test already run on the blend weights, so the absence is explained rather than left inviting the question.

**What we are testing and what to expect.** Expect the dictionary arm to be poor and FinBERT to come closer than is comfortable. If FinBERT matches on accuracy, the argument shifts to the structured output, the evidence quotes and the ability to read a document the model has never seen a template of, which is a fair argument and should be made explicitly rather than avoided.

---

## Item 5. Contamination audit

**Runs without Human Arm Results.**

**Main topic.** Whether the model is inferring from the document or remembering the outcome from training data.

**What it does and the goal.** Events are split around the model's stated training cutoff and performance compared across the split, backed by a direct recall probe with no document attached. An examiner will raise this whether or not we do, so it is better raised by us with numbers attached.

**Inputs.** The scored outputs per event, the manifest report dates, the model's stated training cutoff (confirm the exact date as the first step if it is not already recorded), and the evidence review outputs for the third probe.

**Steps.**

1. Split events into pre-cutoff and post-cutoff relative to the model's stated training cutoff, compare rank correlation and accuracy across the two groups, and bootstrap the difference. The 2025 and 2026 quarters are the clean set and this is the headline probe.
2. Recall probe. Take around thirty event identifiers and ask the model, with no document attached, what happened to that ticker after that quarter's earnings. Score each answer correct direction, wrong direction, or refused.
3. Log the model's answers verbatim. They are quotable in the write-up and a paraphrase is not.
4. Take the third probe free from the evidence review, since any rationale citing a fact absent from the source document is either invented or leaked, and the review is already catching those.

**Outputs.** `contamination_split_table.csv`, `recall_probe_log.csv` with verbatim responses, and a count of out-of-document facts drawn from the evidence review.

**Acceptance checks.**

- Every event carries a pre or post label traceable to its manifest report date and the recorded cutoff.
- The recall probe log holds the model's exact wording per identifier, not summaries.
- The write-up states the confound plainly, that pre-cutoff quarters are also earlier quarters with a different volatility regime, so the comparison is suggestive rather than clean, with a within-sector comparison added if the sample allows.

**What we are testing and what to expect.** Expect the pre-cutoff group to look mildly better and expect the difference to sit inside its interval. On the recall probe, a high correct-direction rate on old quarters alongside refusals on new ones is the clearest single piece of evidence available in either direction.

---

## Item 6. Asymmetry and conviction

**Runs without Human Arm Results.**

**Main topic.** Whether the model is worse at bad news, and whether the magnitude of its score carries information.

**What it does and the goal.** This formalises the downside blindness already visible in the current numbers into a proper result with a test attached, and it establishes whether the score works as a magnitude before Extension 4 bets on it. It has to run before conviction sizing, because if magnitude carries nothing then a sizing null becomes a predicted outcome rather than a surprising one, which is a much stronger position to write from.

**Inputs.** The scored outputs with signal and score per event, and the realised returns from the matrix.

**Steps.**

1. Split events by realised direction and compute accuracy, recall and precision within each side.
2. Report the HOLD rate inside each direction split alongside the accuracy figures. The trap is that an uneven HOLD rate manufactures apparent asymmetry, because an arm that declines to call more often on one side looks more accurate there, and this check is easy to omit.
3. Bin events by absolute realised move, under 1 percent, 1 to 3, 3 to 5 and over 5, and report hit rate per bin per direction.
4. Rank-correlate absolute score against absolute return across all events, then fit accuracy against absolute score in bins to see whether high-conviction calls are actually better calls. The trap is the score scale, conviction means distance from neutral rather than the raw number, so establish where neutral sits before computing anything, because treating neutral as the bottom of the range turns every SELL into an apparently low-conviction call and manufactures the finding out of an arithmetic error.
5. Run a two-proportion z-test on the negative versus positive recall gap so the asymmetry carries a p-value rather than a shrug.

**Outputs.** `asymmetry_by_direction.csv`, `hit_rate_by_move_bin.csv`, `conviction_curve.png`, and the recall gap with its p-value in `asymmetry_test.csv`.

**Acceptance checks.**

- The direction table includes the HOLD rate per side beside every accuracy figure.
- Neutral on the score scale is stated in the output and the conviction computation measures distance from it.
- The z-test inputs, the two recall proportions and their event counts, are reported beside the p-value.

**What we are testing and what to expect.** Expect a real gap with the model better on the upside, and expect the conviction curve to be flat or close to it, meaning the score is reliable as a three-way label and not as a magnitude. Both are deployment findings rather than disappointments.

---

## Item 7. The five backtest extensions

**Requires Human Arm Results** for every human line, and every model line runs without them, so all five can be built and run on model signals today and rerun with the human score column swapped in when their sheets land.

**Main topic.** Five robustness and deployment extensions to the backtest, numbers 5, 2, 9, 4 and 1, built once and serving both arms.

**What it does and the goal.** The backtest scores any predictor the same way, so each extension produces a model line and a human line off one build. These convert known weaknesses, concentration, window choice, cost assumptions, score magnitude and threshold tuning, into demonstrated rigour.

**Inputs.** The return matrix and bootstrap helper from Item 2, the scored model outputs, the manifest report dates, the cost assumption from the conventions lookup, and later the human score columns.

### Extension 5. Leave-one-out robustness

**Requires Human Arm Results, for the human line only. The model line runs without them.**

Profit is concentrated in roughly ten events out of 120 (already computed), so anyone reading the result will suspect it rests on a handful of lucky calls, and they are right to. This answers that with a number instead of a reassurance, needs no decision from anybody, and is the highest value per hour on the whole list, so it starts first. One day.

1. Loop over companies, dropping all of each company's trades and recomputing total return, mean per trade and hit rate on what remains, one row per exclusion.
2. Repeat over calendar quarters.
3. Add a leave-one-event-out pass reporting the ten largest single-event contributions with the total recomputed without each.
4. Put the full-sample figures on the top row, sort by absolute impact, and read for whether the total ever changes sign and which exclusions move it most.

Output `ext5_leave_one_out.csv`. Show ten rows plus the full sample in the chapter and put the complete table in an appendix. Expect one or two names to matter a great deal and the total to keep its sign, and if it does not, that is important and gets reported rather than smoothed over.

### Extension 2. Holding-period curve

**Requires Human Arm Results, the two-line figure is the whole point of this one.** The model line still builds and runs first.

The overnight window was chosen early, so somebody will ask whether that choice made the result, and if the information keeps paying for several days then the finding is post-earnings drift, a more interesting and better-documented claim than a one-night gap. One day, after the return matrix.

1. Entry never changes, it stays the close before the reaction window at every horizon.
2. For each trade, take the return at each horizon from the matrix, sign it by the signal, and charge the round trip once regardless of holding period, because you only get in and out once.
3. Average within each horizon and never compound across horizons, since they are alternative versions of the same trade rather than a sequence. The trap is that positions overlap at longer horizons because several companies report in the same fortnight, so a compounded equity curve implies capital the strategy does not have. Report mean net return per trade, and if a total appears anywhere say plainly it is a sum of independent per-trade returns rather than an achievable account balance.
4. Rescale the HOLD band per horizon per the locked convention, since a flat 2 percent band empties the HOLD class at longer horizons and inflates accuracy for reasons unrelated to skill.
5. Add rank correlation per horizon alongside accuracy, because it needs no band and therefore defends the whole curve against anyone picking at the band convention. If the curve has the same shape in both metrics, the band was not driving it.
6. Put a bootstrap interval on every point, and take one quarter all the way through by hand for the write-up, the overnight gap, the position by the Friday, then the following week, because one worked example makes the chart concrete.

Output `ext2_holding_curve.csv` and `ext2_holding_curve.png`, mean net return per trade against holding period, one line per arm.

### Extension 9. Execution realism

**Requires Human Arm Results, for the human line only. The model grid runs without them.**

A result that only works at zero trading cost is not a result, and this is the cheapest available defence of the entire backtest. One day.

1. Nothing is re-scored. Same trades, same signals, more subtracted.
2. Build a grid of round-trip costs at 10, 20, 30 and 50 basis points crossed with entry slippage at 0, 10 and 20, twelve cells.
3. In each cell recompute every trade as gross minus cost minus slippage, then report the total and mean per trade for that cell.
4. Add the short-borrow charge on SELL trades if SELL is a short, per the position mapping recorded under the conventions.
5. Email the industry contact asking what a realistic all-in overnight cost looks like in a liquid US name, which turns the grid from a guess into a citable anchor.

Output `ext9_cost_grid.csv`. Break-even is already computed at roughly 113 basis points for the model arm, so expect the whole grid to be survived, making this a confirmation rather than a discovery. The honest framing is that cost is not the binding constraint, signal quality is.

### Extension 4. Conviction-weighted sizing

**Requires Human Arm Results, the identical test runs on their score column.** The model book runs first. One day, after Item 6.

If a high-conviction call really is more likely to be right, betting more on it should make more money, and if it does not, the number is decoration, which is itself a deployment finding.

1. Check the spread of absolute scores before running anything, and report the distribution beside the result, because a flat outcome on a bunched score is a different finding from a flat outcome on a well-spread one.
2. Flat sizing is the baseline, every trade at the same notional.
3. For the sized book, size each trade in proportion to absolute score divided by the mean absolute score across the set. The trap is that without the division the conviction book is simply a bigger book and wins on total return by default while telling us nothing, and with it the method is scale-invariant.
4. Compare total return, Sharpe and maximum drawdown against flat sizing.
5. Run the identical test on the human score column when it lands. If the two arms use different score ranges, compare each against its own flat book and do not put the two sized books side by side.
6. Note in the write-up that normalising by a full-sample statistic is itself mild look-ahead, small at this size but stated rather than glossed over. If the continuous version looks unstable, cut absolute scores into three bands with fixed multiples set in advance or from earlier events, never from thirds of the full set.

Output `ext4_conviction_sizing.csv` plus the score distribution figure. Expect a null.

### Extension 1. Walk-forward validation

**Requires Human Arm Results, for the human line only. The model version runs without them.** Three to four days.

Every threshold in use was chosen with the full dataset in view, so the obvious objection is that the settings were tuned to the answer, and walk-forward is the standard reply, fit on the past, test on the future, report only the future.

1. Write one function taking a training cutoff and a test span, filtering events by report date from the manifest, fitting the blend weights and thresholds on training events only, then scoring the test span with those settings frozen. Everything else calls that function rather than reimplementing it.
2. Run it twice for the headline version, once on pre-freeze quarters and once on post-freeze, and report the second number as the result.
3. For the rolling version, start the training window at roughly the first 40 percent of events by date with a floor of 40 events, step forward one calendar quarter, refit, predict the next slice, and stitch the out-of-sample slices into one curve.
4. Refit the thresholds only rather than re-deriving the blend weights each step, since re-deriving both on 40 events is unstable and thresholds alone is the more defensible choice.
5. Log the fitted threshold, training count, test count, hit rate and mean return per window. The trap is that a threshold refitted on a thin slice can go degenerate, so wide that almost everything is classified HOLD and accuracy looks fine because no calls are being made, and a collapsing trade count is how that shows up, invisible unless logged.

Output `ext1_walkforward_windows.csv`, the stitched out-of-sample curve, one pooled out-of-sample figure, and a dated freeze note recording the blend weights, HOLD thresholds, cost assumptions and horizon.

The caveat is not optional. All 120 events have already been run and seen, so a freeze declared now cannot be presented as pre-registered. Label this version retrospective validation, and separately freeze the settings in writing today with the date attached, so the expansion companies and any quarter reporting after today form a genuinely blind set by September. Expect thin windows, around eight of a dozen test events each, too thin to read individually, so the stitched curve and pooled figure are the result and the per-window table is a diagnostic.

**Acceptance checks for Item 7 as a whole.**

- Every extension reads returns from the matrix and intervals from the bootstrap helper, with no separate price pulls and no reimplemented anchor logic anywhere.
- Each extension runs end to end on model signals alone, and swapping in a human score column requires no code change beyond the column name.
- The walk-forward freeze note exists, is dated today, and the walk-forward write-up says retrospective validation, not pre-registered.

---

## Item 8. The mechanical quote screen

**Blocks the Human Arm.** Their evidence review cannot start until this exists.

**Main topic.** Automated verification of the model's evidence quotes.

**What it does and the goal.** Every evidence quote the model produced is checked against the stored source text, so fabricated quotes are removed before a person spends time judging them and human review hours go on relevance rather than existence. Half a day, and because it blocks somebody else's work it is more urgent than its effort suggests.

**Inputs.** The stored model outputs holding the evidence items and confidence labels, and the stored extracted source text per document.

**Steps.**

1. Pull every evidence item for the sampled documents from the stored outputs. The sample is around fifteen documents stratified by sector and by realised direction, so it is not all clean beats.
2. Normalise whitespace and quote characters on both sides before comparing. The trap is that a curly apostrophe or a line break otherwise reads as a hallucination.
3. Check whether each quote appears verbatim in the stored extracted text, with a fuzzy fallback at roughly 90 percent similarity to catch truncation.
4. Flag each item exact, near or absent. Absent is a Reject before any human sees it.
5. Hand over only the items that pass, with the model's stated confidence attached to each row, since half the finding is whether HIGH confidence items are actually better.

**Outputs.** `quote_screen_results.csv` with one row per evidence item flagged exact, near or absent, and `quote_screen_handover.csv` holding only the passing items with confidence attached, delivered to the human arm.

**Acceptance checks.**

- The sample covers both directions and multiple sectors, verifiable from the stratification columns in the results file.
- A hand check of a few near flags confirms they are truncations rather than fabrications, so the 90 percent threshold is behaving.
- The handover file contains no item flagged absent.

**What we are testing and what to expect.** Expect the screen to do most of the work, and expect what reaches the reviewers to be judgement calls about whether a real quote supports the claim built on it.

---

## Sequencing

- Now, nothing blocking. Extension 5, the bootstrap helper, the availability audit for the section ablation, the quote screen, and the cost lookup from the conventions.
- Week of 11 August. The return matrix, then Extension 2. Asymmetry and conviction. The cheap baselines. The section ablation runs, since section calls cost pennies.
- Week of 18 August. Extension 4, Extension 9, Extension 1, the contamination audit, and the macro write-up.
- Week of 25 August. Writing only. No new runs.

## Cut order

If something has to go, cut in this order.

1. Extension 1's rolling version first, keeping its two-window headline.
2. Then the thinnest section arm if availability turns out poor.
3. Then Extension 4, since the conviction finding is already carried by Item 6.

## Things not to do

- Do not fit any threshold on the same events it is scored on. This applies to the baseline mappings, the conviction bands and the walk-forward refits alike.
- Do not compare arms drawn from different subsets of events.
- Do not compound returns across horizons or present a long-horizon total as an achievable account balance.
- Do not present the walk-forward as pre-registered.
- Do not recompute a figure that already exists in the workbook. Quote it and put an interval on it.
- Do not reimplement the anchor-date rule anywhere outside the return matrix.
