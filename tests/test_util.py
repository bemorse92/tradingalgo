"""Helper tests, with emphasis on the rebalance helper not leaking future data."""

from __future__ import annotations

import pandas as pd
import pytest

from backtest import util


def test_daily_rebalance_is_a_passthrough(prices):
    weights = pd.DataFrame(1.0, index=prices.index, columns=["SPY"])
    pd.testing.assert_frame_equal(util.rebalance(weights, "daily"), weights)


def test_month_end_only_changes_on_the_last_trading_day():
    index = pd.bdate_range("2020-01-01", "2020-03-31", name="date")
    weights = pd.DataFrame(0.0, index=index, columns=["SPY"])
    weights.loc[index[5]:, "SPY"] = 1.0  # signal turns on mid-January

    held = util.rebalance(weights, "month_end")

    # Nothing moves until January's last trading day; from then on it is held.
    jan_end = index[index.to_period("M") == pd.Period("2020-01")][-1]
    assert held.loc[index[5], "SPY"] == 0.0
    assert held.loc[jan_end, "SPY"] == 1.0
    assert held.loc[index[-1], "SPY"] == 1.0


def test_month_end_holds_position_between_rebalances():
    index = pd.bdate_range("2020-01-01", "2020-03-31", name="date")
    weights = pd.DataFrame(0.0, index=index, columns=["SPY"])
    weights["SPY"] = 1.0
    weights.loc[index[25], "SPY"] = 0.0  # a one-day blip mid-month

    held = util.rebalance(weights, "month_end")
    assert held.loc[index[25], "SPY"] == 1.0  # blip ignored; not a rebalance date


def test_unknown_frequency_is_refused(prices):
    weights = pd.DataFrame(1.0, index=prices.index, columns=["SPY"])
    with pytest.raises(ValueError, match="Unknown rebalance frequency"):
        util.rebalance(weights, "hourly")


def test_moving_average_is_trailing_not_centred():
    """Index 2 is the discriminating case.

    Series [1, 1, 1, 10, 1] with lookback 3: the trailing mean at index 2 is 1.0,
    so price >= mean is True. A centred window would pull the spike at index 3
    backwards, giving a mean of 4.0 and False. The True is the proof.
    """
    series = pd.Series(
        [1.0, 1.0, 1.0, 10.0, 1.0], index=pd.bdate_range("2020-01-01", periods=5)
    )
    flags = util.above_moving_average(series, lookback=3)

    assert list(flags) == [False, False, True, True, False]


def test_moving_average_is_false_before_enough_history():
    series = pd.Series(range(1, 11), dtype=float, index=pd.bdate_range("2020-01-01", periods=10))
    flags = util.above_moving_average(series, lookback=5)
    assert not flags.iloc[:4].any()


def test_one_hot_builds_fully_invested_weights():
    index = pd.bdate_range("2020-01-01", periods=3)
    choice = pd.Series(["SPY", "BIL", "SPY"], index=index)
    out = util.one_hot(index, ["SPY", "BIL"], choice)

    assert list(out["SPY"]) == [1.0, 0.0, 1.0]
    assert list(out["BIL"]) == [0.0, 1.0, 0.0]
    assert (out.sum(axis=1) == 1.0).all()
