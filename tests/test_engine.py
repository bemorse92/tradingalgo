"""Engine tests.

The lag test is the most important test in the project: it is the mechanical proof
that a strategy cannot trade on information it did not have.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest import engine


def test_signal_cannot_capture_its_own_bar(jump_prices):
    """A weight set on the jump day earns the *next* bar, not the jump itself.

    Prices are flat at 100 through bar 5, then 200 from bar 5 onward, so the +100%
    return lands on bar index 5. A strategy that goes long on bar 5 (the day the
    jump is observable at the close) must not capture it.
    """
    weights = pd.DataFrame(0.0, index=jump_prices.index, columns=["SPY"])
    weights.iloc[5:, 0] = 1.0  # decided at the close of the jump bar

    result = engine.run(jump_prices, weights, cost_bps=0.0)

    # The jump return occurs at position 5; we only held from position 6.
    assert result.returns.iloc[5] == pytest.approx(0.0)
    assert float(result.equity.iloc[-1]) == pytest.approx(1.0)


def test_lag_captures_return_the_bar_after_the_signal(jump_prices):
    """Entering one bar before the jump does capture it."""
    weights = pd.DataFrame(0.0, index=jump_prices.index, columns=["SPY"])
    weights.iloc[4:, 0] = 1.0

    result = engine.run(jump_prices, weights, cost_bps=0.0)

    assert result.returns.iloc[5] == pytest.approx(1.0)
    assert float(result.equity.iloc[-1]) == pytest.approx(2.0)


def test_costs_charged_on_notional_traded(jump_prices):
    """A full switch in and out trades 1.0 notional each way."""
    weights = pd.DataFrame(0.0, index=jump_prices.index, columns=["SPY"])
    weights.iloc[2:6, 0] = 1.0

    result = engine.run(jump_prices, weights, cost_bps=10.0)

    assert result.total_traded == pytest.approx(2.0)
    assert result.total_costs == pytest.approx(2.0 * 10.0 / 10_000.0)


def test_buy_and_hold_matches_price_growth(prices):
    """The benchmark reproduces the underlying total return, less entry cost."""
    result = engine.buy_and_hold(prices, ticker="SPY", cost_bps=0.0)
    expected = prices["SPY"].iloc[-1] / prices["SPY"].iloc[0]
    assert float(result.equity.iloc[-1]) == pytest.approx(expected, rel=1e-9)


def test_rejects_short_positions(prices):
    weights = pd.DataFrame(0.0, index=prices.index, columns=["SPY"])
    weights.iloc[10, 0] = -0.5
    with pytest.raises(engine.WeightsError, match="long-only"):
        engine.run(prices, weights)


def test_rejects_leverage(prices):
    weights = pd.DataFrame(0.0, index=prices.index, columns=["SPY", "TLT"])
    weights.iloc[10] = [0.8, 0.8]
    with pytest.raises(engine.WeightsError, match="leverage"):
        engine.run(prices, weights)


def test_rejects_unknown_ticker(prices):
    weights = pd.DataFrame(0.0, index=prices.index, columns=["GLD"])
    with pytest.raises(engine.WeightsError, match="absent from prices"):
        engine.run(prices, weights)


def test_rejects_nan_weights(prices):
    weights = pd.DataFrame(0.0, index=prices.index, columns=["SPY"])
    weights.iloc[5, 0] = np.nan
    with pytest.raises(engine.WeightsError, match="NaN"):
        engine.check_weights(weights)
