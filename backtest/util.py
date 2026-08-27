"""Small helpers shared by strategies.

These live in the harness rather than in each strategy so that common mechanics --
above all rebalance frequency -- are declared as parameters instead of hand-rolled,
which keeps them visible to the parameter budget and the trial ledger.
"""

from __future__ import annotations

import pandas as pd

#: Accepted rebalance frequencies, mapped to pandas period aliases.
REBALANCE_PERIODS = {
    "daily": None,
    "week_end": "W",
    "month_end": "M",
    "quarter_end": "Q",
}


def rebalance(weights: pd.DataFrame, freq: str = "month_end") -> pd.DataFrame:
    """Allow position changes only on the last trading day of each period.

    Faber-style rules trade month-end, not daily, and the difference is material:
    daily checking multiplies whipsaw. Between rebalance dates the previous
    target is carried forward.

    This is not look-ahead. Which day is the last trading day of a month is known
    from the published exchange calendar at the time, not inferred from future
    prices.
    """
    if freq not in REBALANCE_PERIODS:
        raise ValueError(
            f"Unknown rebalance frequency {freq!r}; "
            f"expected one of {sorted(REBALANCE_PERIODS)}"
        )

    period = REBALANCE_PERIODS[freq]
    if period is None:
        return weights

    is_rebalance = ~weights.index.to_period(period).duplicated(keep="last")
    marks = pd.Series(is_rebalance, index=weights.index)
    return weights.where(marks, other=float("nan")).ffill().fillna(0.0)


def above_moving_average(prices: pd.Series, lookback: int) -> pd.Series:
    """True where price is at or above its trailing simple moving average.

    Trailing by construction: `rolling` looks backward only, and the value at
    date t uses prices up to and including t.
    """
    ma = prices.rolling(lookback).mean()
    return (prices >= ma).where(ma.notna(), other=False)


def trailing_return(prices: pd.Series, lookback: int) -> pd.Series:
    """Simple return over the trailing `lookback` bars."""
    return prices.pct_change(lookback, fill_method=None)


def one_hot(index: pd.DatetimeIndex, tickers: list[str], choice: pd.Series) -> pd.DataFrame:
    """Build a fully-invested weight frame from a per-date ticker choice."""
    out = pd.DataFrame(0.0, index=index, columns=tickers)
    for ticker in tickers:
        out.loc[choice == ticker, ticker] = 1.0
    return out
