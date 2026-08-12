# Human vs LLM comparison — corrected release_date anchor

Date: 2026-08-12

## Subset definition

Source: `data/human/human_decisions_export_2026-08-12.csv`
Filters: `section == "All"`, `first_rater_for_event == YES`,
`in_llm_universe == YES`, 39-event exclusion set applied.
N = 171 paired events.

Grading: pre-registered ±2% raw overnight band on `returns_matrix.csv`
(release_date anchor). Accuracy = correct-direction rate among events
where the arm traded (BUY or SELL) and |ret_overnight| > 2%.

## Pooled comparison (all repricing classes, N=171)

|  | Human | LLM |
|---|---|---|
| BUY calls | 96 (56.1%) | 42 (24.6%) |
| HOLD calls | 40 (23.4%) | 69 (40.4%) |
| SELL calls | 35 (20.5%) | 60 (35.1%) |
| **HOLD rate** | **23.4%** | **40.4%** |
| Traded | 131 | 102 |
| Graded (traded + |ret|>2%) | 79 | 58 |
| Correct direction | 45 | 40 |
| **Accuracy** | **57.0%** (45/79) | **69.0%** (40/58) |

Always-BUY baseline: 39.4% (39/99 events with |ret|>2%).

### Paired comparison (both arms traded + |ret|>2%): N=48

|  | LLM | Human |
|---|---|---|
| Correct | 31/48 (64.6%) | 28/48 (58.3%) |

LLM − Human: +6.3pp, 90% CI [−8.3pp, +20.8pp], p=0.533.
**Paired MDE at N=48: ~±30pp.** The comparison is underpowered. Any
difference smaller than ~30pp is untestable at this sample size.

### Context on the HOLD rate difference

The LLM holds on 40.4% of events; the human arm on 23.4%. A model
that holds more will have fewer graded events (58 vs 79) and those
graded events will be the ones where it was most confident, inflating
its accuracy relative to an arm that trades more freely. The 69.0% vs
57.0% accuracy difference is confounded by this trade-frequency
asymmetry and should not be read as the LLM being "more accurate" —
it is more selective.

The fair comparison is on the 48 events where both arms committed,
which shows +6.3pp (not significant, p=0.533).

## Fact-based repricing (N=34)

| | Human | LLM |
|---|---|---|
| Graded | 12 | 9 |
| Accuracy | 41.7% (5/12) | 88.9% (8/9) |

Paired (both graded): N=7. LLM 85.7% vs Human 42.9%, diff +42.9pp,
p=0.203. **MDE ~±77pp — completely untestable at N=7.**

## Price-based repricing (N=64, reported separately, never pooled)

| | Human | LLM |
|---|---|---|
| Graded | 39 | 29 |
| Accuracy | 69.2% (27/39) | 55.2% (16/29) |

Paired (both graded): N=27. Human 66.7% vs LLM 55.6%, diff −11.1pp,
p=0.322. **MDE ~±39pp — untestable.**

Note: the human arm outperforms the LLM on price-based rows. This is
expected — price-based repricing selected the measurement window to
show a move, and the human arm's directionally optimistic profile
(56% BUY) is rewarded when moves are guaranteed to be large.
