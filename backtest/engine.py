"""The backtest engine.

Deliberately small. The engine owns the *only* lag in the project, so look-ahead
prevention lives in one place and is unit-testable:

    weights decided from data through the close of day t
      -> held over day t+1
      -> earn the close-to-close return of day t+1

Strategies must never lag inside their own `weights()`; the engine does it.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

#: One-way cost charged per unit of notional traded. A full switch between two
#: sleeves trades 2.0 notional and so pays twice this.
DEFAULT_COST_BPS = 5.0

_TOLERANCE = 1e-9


class WeightsError(ValueError):
    """Raised when target weights violate the project's long-only constraints."""


@dataclass(frozen=True)
class Result:
    """Outcome of one backtest."""

    equity: pd.Series
    returns: pd.Series
    held: pd.DataFrame
    traded: pd.Series
    costs: pd.Series

    @property
    def total_traded(self) -> float:
        return float(self.traded.sum())

    @property
    def total_costs(self) -> float:
        return float(self.costs.sum())


def check_weights(weights: pd.DataFrame) -> None:
    """Enforce the project's constraints: long-only, no leverage, no NaN.

    These are scope decisions from high_level_strategy.md, not style preferences,
    so the engine refuses to run rather than silently modelling something the
    project has ruled out.
    """
    if weights.isna().any().any():
        raise WeightsError("Target weights contain NaN; use 0.0 for 'not invested'.")
    if (weights < -_TOLERANCE).any().any():
        raise WeightsError("Negative weights: this project is long-only (no shorting).")
    row_sums = weights.sum(axis=1)
    if (row_sums > 1.0 + _TOLERANCE).any():
        worst = row_sums.max()
        raise WeightsError(
            f"Weights sum to {worst:.4f} > 1.0: this project uses no leverage."
        )


def run(
    prices: pd.DataFrame,
    target_weights: pd.DataFrame,
    cost_bps: float = DEFAULT_COST_BPS,
) -> Result:
    """Run one backtest.

    `target_weights` are decided at each date's close; the engine shifts them
    forward one bar before they earn anything.
    """
    unknown = set(target_weights.columns) - set(prices.columns)
    if unknown:
        raise WeightsError(f"Weights reference tickers absent from prices: {sorted(unknown)}")

    target = target_weights.reindex(index=prices.index).fillna(0.0)
    check_weights(target)

    # The one and only lag in the project.
    held = target.shift(1).fillna(0.0)

    returns = prices[held.columns].pct_change(fill_method=None).fillna(0.0)
    gross = (held * returns).sum(axis=1)

    # Notional traded to move into today's holding. With 0/1 weights this is exact;
    # with blended weights it slightly overstates turnover by ignoring intra-period
    # drift, which is the conservative direction.
    traded = (held - held.shift(1).fillna(0.0)).abs().sum(axis=1)
    costs = traded * (cost_bps / 10_000.0)

    net = gross - costs
    equity = (1.0 + net).cumprod()

    return Result(equity=equity, returns=net, held=held, traded=traded, costs=costs)


def buy_and_hold(
    prices: pd.DataFrame,
    ticker: str = "SPY",
    cost_bps: float = DEFAULT_COST_BPS,
) -> Result:
    """The benchmark, run through the same engine as every strategy.

    Using the identical code path is what prevents the benchmark-asymmetry pitfall:
    the benchmark pays the same entry cost and uses the same total-return series, so
    no edge can be manufactured by treating the two differently.
    """
    weights = pd.DataFrame(0.0, index=prices.index, columns=[ticker])
    weights[ticker] = 1.0
    return run(prices, weights, cost_bps=cost_bps)
