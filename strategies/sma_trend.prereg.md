# Pre-registration: sma_trend

Committed before the first backtest of this rule.

## Economic rationale

Volatility clusters, and large equity drawdowns are historically slow grinds rather
than instantaneous gaps. A price that has fallen below a long trailing average has,
empirically, been more likely to keep falling than a randomly chosen price. That
serial dependence — not a pattern discovered by search — is the mechanism a trend
filter exploits.

This is the canonical version of the question the project exists to ask, published
by Faber in 2007 and unusual in having survived out-of-sample: Sharpe 0.81
in-sample (1972–2005), 0.68 out-of-sample (2006–2025). Testing it first is
deliberate — it is the candidate most likely to be real, so if it fails here the
weaker candidates are not worth pursuing.

## The rule

Long-only, one sleeve at a time:

- If SPY's close is at or above its trailing `lookback`-day simple moving average,
  hold 100% SPY.
- Otherwise hold 100% of the defensive sleeve.
- Positions may change only on the last trading day of the month.
- Weights are decided at the close and take effect the following bar.

## Parameters

| Parameter | Fixed or fitted | Value / grid | Justification |
|---|---|---|---|
| `lookback` | fitted | 150, 200, 250 | Faber's 200-day is the published value; the neighbours test for a plateau rather than a peak. |
| `defensive` | fixed | `BIL` | The literature's supported version exits to **cash**. BIL earns real T-bill yields, so time out of the market is neither flattered nor penalised. |
| `rebalance` | fixed | `month_end` | Faber's published frequency. Daily checking multiplies whipsaw and is not the tested rule. |

Declared N: **3**

Only `lookback` is searched. Choosing `defensive` or `rebalance` by looking at
results would convert them to fitted parameters and consume the budget; both are
set here from published precedent instead.

## Sample

2007-05-30 to 2022-12-31 (snapshot-pinned; BIL's listing date sets the start).
2023 onward is reserved as holdout and is not consulted. The in-sample period
contains the 2008, 2015, 2018 (twice), 2020 and 2022 drawdowns.

## Success criteria

Against buy-and-hold SPY over the same sample, with 5 bps one-way slippage:

1. **Primary:** maximum drawdown reduced by at least 10 percentage points, and
2. **Return floor:** CAGR no more than 2 percentage points below buy-and-hold, and
3. **Not one event:** positive protection in at least three distinct benchmark
   drawdown events, so the result is not 2008 in disguise, and
4. **Plateau:** the drawdown improvement holds across all three lookbacks, not
   only the best one.

All four must hold. Meeting only the first is a fail.

## Prediction

Criteria 1, 3 and 4 will pass; criterion 2 is the one most likely to fail. Trend
filters have historically bought drawdown reduction by giving up return, and this
sample ends in 2022, which excludes the strong 2023–2024 recovery that would have
punished a defensive rule further.

Expected: max drawdown roughly halved versus SPY's ~55%, CAGR 2–4 points lower.

## What would falsify this

Protection concentrated in a single event, or a drawdown improvement that appears
at only one lookback. Either means the result is noise, and no amount of
re-parameterising fixes it — the idea should be abandoned rather than adjusted.
