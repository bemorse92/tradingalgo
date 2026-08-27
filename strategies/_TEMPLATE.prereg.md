# Pre-registration: <strategy_name>

> Copy to `<strategy_name>.prereg.md`, fill in, and **commit before the first
> backtest runs**. Git history is the enforcement mechanism: a pre-registration
> whose commit postdates the result is not a pre-registration.

## Economic rationale

Why should this work, stated *before* looking at any result? Name the mechanism.
"Volatility clusters, so large drawdowns are slow grinds rather than instantaneous
gaps" is a mechanism. "The 187-day average tested best" is not.

## The rule

Precisely enough that someone else could implement it from this description alone.

## Parameters

| Parameter | Fixed or fitted | Value / grid | Justification |
|---|---|---|---|
|  |  |  |  |

- **Fixed** parameters are set a priori from convention or published precedent and
  are never swept. They cost essentially nothing statistically.
- **Fitted** parameters are chosen by looking at results. Hard cap of 2.
- Declared N (product of the fitted grids): ______

## Sample

Which period, which snapshot, and why that period was chosen — decided before
running, not after.

## Success criteria

The bar this must clear, written now so it cannot drift later. State the metric,
the threshold, and the comparison.

## Prediction

What you expect to happen. Recording this makes it possible to be wrong, which is
the point.

## What would falsify this

The result that would make you abandon the idea rather than adjust it.
