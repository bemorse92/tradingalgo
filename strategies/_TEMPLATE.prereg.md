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

## Benchmark

Which signal-free alternative must this beat? Declared here and as `benchmark` on
the strategy class, where the harness resolves every `*_vs_benchmark` criterion
against it. Pick before running, never afterwards from whichever comparison the
result happens to win.

| Key | What it means |
|---|---|
| `buy_and_hold` | 100% of the risk asset. The naive comparison — and it flatters any rule that simply holds less equity. |
| `vol_matched` | Static risk-asset/cash mix at the strategy's realised volatility. |
| `exposure_matched` | Static mix at the strategy's average risk-asset weight. |
| `sixty_forty` | 60/40 risk asset and bonds. |
| `equal_weight` | Equal weight across the risky basket. |
| `inverse_vol` | The risky basket weighted by inverse trailing volatility. |
| `cash` | 100% cash. |

If the rule reduces market exposure — most timing rules do — `buy_and_hold` is the
easy comparison and one of the matched mixes is the honest one. See
[findings.md](../design_docs/findings.md#addendum-benchmarks-that-need-no-signal):
measured against 100% SPY, `sma_trend` looked like it saved 12.9pp of drawdown;
against a mix carrying the same risk, 1.6–4.0pp.

Note that the two matched mixes are built from the strategy's *own realised*
volatility or exposure, so declaring one pre-commits the method of construction
rather than a fixed portfolio. Still fixed in advance and not selectable
afterwards — but a weaker commitment than naming `sixty_forty` outright, and worth
stating which you intended.

**Declared benchmark:** ______

## Sample

Which period, which snapshot, and why that period was chosen — decided before
running, not after.

## Success criteria

The bar this must clear, written now so it cannot drift later. State the metric,
the threshold, and the comparison. Transcribe them into `criteria` on the strategy
class so the harness, not the researcher, produces the verdict.

Metrics ending `_vs_benchmark` resolve against the benchmark declared above, so a
criterion is only as demanding as that choice.

Two failure modes worth designing against, both learned from the first two
pre-registrations:

- **Counting events without weighting them.** "Protected in at least three
  drawdowns" was cleared by a rule whose entire advantage came from 2008. Prefer a
  criterion that must survive *excluding* the largest contributing event, or one
  that requires a post-2008 subsample to pass on its own.
- **A benchmark that flatters.** See the section above.

## Prediction

What you expect to happen. Recording this makes it possible to be wrong, which is
the point.

## What would falsify this

The result that would make you abandon the idea rather than adjust it.

## If this idea came from a generated sweep

Anything surfaced by bulk generation is not a discovery — it is what best-of-N
predicts from worthless inputs. Promotion out of a generated pool is an explicit,
recorded act that carries the full trial count with it, and it needs a stated
mechanism and a fresh pre-registration before it means anything.

**Origin of this idea:** ______
