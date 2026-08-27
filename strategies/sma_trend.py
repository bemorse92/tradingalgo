"""Faber-style trend filter: hold SPY above its trailing average, else cash.

Pre-registration: sma_trend.prereg.md (committed before the first run).
"""

from __future__ import annotations

import pandas as pd

from backtest.strategy import Strategy
from backtest.util import above_moving_average, one_hot, rebalance


class SmaTrend(Strategy):
    name = "sma_trend"
    rationale = (
        "Volatility clusters and large equity drawdowns are slow grinds rather than "
        "instantaneous gaps, so price below a long trailing average has historically "
        "been more likely to keep falling. Serial dependence, not a searched pattern."
    )
    fixed = {"defensive": "BIL", "rebalance": "month_end"}
    fitted = {"lookback": [150, 200, 250]}

    def weights(self, prices: pd.DataFrame) -> pd.DataFrame:
        defensive = self.params["defensive"]

        risk_on = above_moving_average(prices["SPY"], self.params["lookback"])
        choice = pd.Series(defensive, index=prices.index).where(~risk_on, "SPY")

        targets = one_hot(prices.index, ["SPY", defensive], choice)
        return rebalance(targets, self.params["rebalance"])
