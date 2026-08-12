# JPM_FQ1_2025: Why price-based window selection fails

## The error

A diagnostic script used price patterns to determine `release_date` for
events where the field had not yet been built. The logic:

```python
open_gap = abs((rdate_open - prior_close) / prior_close)
overnight = abs((next_open - rdate_close) / rdate_close)

if overnight > open_gap * 2:
    release_date = next_trading_day   # "eve" pattern
else:
    release_date = report_date        # "day-of" pattern
```

For JPM_FQ1_2025, this classified the event as "day-of" (release on
2025-04-10) when the actual release was 2025-04-11.

## What happened

JPM_FQ1_2025 has `report_date = 2025-04-10`. JPM actually released Q1 2025
results pre-market on **2025-04-11** (Friday) at approximately 7:00 AM ET.
The EDGAR 8-K Item 2.02 filing is `jpm-20250411.htm` (accession
0000019617-25-000332), filed 2025-04-11.

But on 2025-04-09, the US announced a 90-day tariff pause. The broad market
rallied sharply, and JPM ran from a $212.50 open to a $234.34 close — a
+10.3% intraday move with no company-specific news.

## The price table

```
Date         Open       Close      Note
2025-04-08   $223.52    $216.87
2025-04-09   $212.50    $234.34    Tariff-pause rally (+10.3% intraday)
2025-04-10   $230.00    $227.11    report_date (no JPM news this day)
2025-04-11   $226.31    $236.20    Actual earnings release (pre-market)
```

## Why the classifier failed

The classifier compared:
- `|open_gap|` on 2025-04-10: |(230.00 - 234.34) / 234.34| = 1.85%
- `|overnight|` from 2025-04-10 close to 2025-04-11 open:
  |(226.31 - 227.11) / 227.11| = 0.35%

Since `|open_gap| > |overnight|`, the classifier concluded the earnings
reaction was at the 4/10 open (i.e., report_date was the day-of). In
reality, the open gap on 4/10 was the tariff rally **unwinding** — a
market-wide move, not an earnings reaction — and the actual earnings gap
(4/11 open vs 4/10 close = -0.35%) was suppressed by the same market
turbulence.

## The lesson

The classifier selected the measurement window by checking which window
contained the larger move. This is classification by outcome: it asks "where
did the price move?" and assigns the window accordingly. When a market-wide
event (tariff pause) produces a larger move than the earnings event, the
classifier points at the wrong day.

This failed on JPMorgan Chase, the most canonical pre-market reporter in the
dataset. The correct anchor — `release_date = 2025-04-11` from the EDGAR 8-K
Item 2.02 filing — is a documented fact that does not depend on which window
moved more.

## Resolution

`release_date` is now built from the EDGAR 8-K Item 2.02 filing date for
every US event, with zero price input in the resolution path. The price-based
diagnostic was never committed and no graded output was contaminated.
