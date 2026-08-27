"""Absolute time-series momentum: hold SPY while it beats cash, else hold cash.

Pre-registration: dual_momentum.prereg.md (committed before the first run).
"""

from __future__ import annotations

import pandas as pd

from backtest.strategy import Strategy
from backtest.util import one_hot, rebalance, trailing_return


class DualMomentum(Strategy):
    name = "dual_momentum"
    rationale = (
        "Time-series momentum: an asset with positive trailing return has historically "
        "been more likely to continue than reverse over intermediate horizons. Compares "
        "SPY against cash over time rather than against a smoothing of its own price."
    )
    fixed = {"defensive": "BIL", "rebalance": "month_end"}
    fitted = {"lookback": [126, 189, 252]}

    def weights(self, prices: pd.DataFrame) -> pd.DataFrame:
        defensive = self.params["defensive"]
        lookback = self.params["lookback"]

        spy = trailing_return(prices["SPY"], lookback)
        cash = trailing_return(prices["BIL"], lookback)
        risk_on = (spy > cash).where(spy.notna() & cash.notna(), other=False)

        choice = pd.Series(defensive, index=prices.index).where(~risk_on, "SPY")
        targets = one_hot(prices.index, ["SPY", defensive], choice)
        return rebalance(targets, self.params["rebalance"])
