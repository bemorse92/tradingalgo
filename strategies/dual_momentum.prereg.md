# Pre-registration: dual_momentum

Committed before the first backtest of this rule.

## Economic rationale

Time-series momentum: an asset whose trailing return is positive has historically
been more likely to continue than to reverse over intermediate horizons. This is a
distinct mechanism from `sma_trend` — it compares an asset against *itself over
time* and against a risk-free alternative, rather than against a smoothed version
of its own price.

Testing it alongside `sma_trend` is deliberate: the two rules share an economic
family but not an implementation, so agreement between them is weak evidence the
effect is structural rather than an artifact of one specific formulation.

Note the prior honestly: Antonacci's published version underperformed 60/40
post-publication, and analyses concluded its drawdown edge was substantially a
2008 story. Expectations are set accordingly.

## The rule

Long-only, one sleeve at a time, evaluated month-end:

- If SPY's trailing `lookback`-day return exceeds BIL's trailing `lookback`-day
  return, hold 100% SPY.
- Otherwise hold 100% of the defensive sleeve.
- Weights are decided at the close and take effect the following bar.

The comparison against BIL rather than against zero is the "absolute momentum"
leg: it asks whether equities beat cash, not merely whether they rose.

## Parameters

| Parameter | Fixed or fitted | Value / grid | Justification |
|---|---|---|---|
| `lookback` | fitted | 126, 189, 252 | ~6, 9 and 12 months. 12 months is the published value; neighbours test for a plateau. |
| `defensive` | fixed | `BIL` | Cash, matching the published rule and `sma_trend` so the two are comparable. |
| `rebalance` | fixed | `month_end` | Published frequency. |

Declared N: **3**

## Sample

2007-05-30 to 2022-12-31, snapshot-pinned. Identical to `sma_trend` so the two are
directly comparable. 2023 onward is reserved as holdout.

## Success criteria

Identical to `sma_trend`, deliberately — using the same bar for both prevents
grading each on whichever metric happens to flatter it:

1. Max drawdown reduced by at least 10 percentage points, and
2. CAGR no more than 2 points below buy-and-hold, and
3. Positive protection in at least three distinct benchmark drawdown events, and
4. The drawdown improvement holds across all three lookbacks.

## Prediction

Weaker than `sma_trend` on the primary criterion. A trailing-return comparison
reacts more slowly than a moving-average crossover, so it should exit later into
declines. Criterion 3 is the one I expect to fail: the published record suggests
its protection concentrates in 2008.

## What would falsify this

Protection concentrated in a single event, or drawdown improvement at only one
lookback. Given the post-publication record, a marginal result here should be read
as failure rather than encouragement.
