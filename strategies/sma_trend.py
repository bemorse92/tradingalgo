"""Faber-style trend filter: hold SPY above its trailing average, else cash.

Pre-registration: sma_trend.prereg.md (committed before the first run).
"""

from __future__ import annotations

import pandas as pd

from backtest import benchmarks
from backtest.criteria import Criterion
from backtest.strategy import Strategy
from backtest.util import above_moving_average, one_hot, rebalance


class SmaTrend(Strategy):
    name = "sma_trend"
    rationale = (
        "Volatility clusters and large equity drawdowns are slow grinds rather than "
        "instantaneous gaps, so price below a long trailing average has historically "
        "been more likely to keep falling. Serial dependence, not a searched pattern."
    )
    # Transcribed from the pre-registration, which named buy & hold. The
    # exposure-matched mix is the harder and better bar (path_to_trading.md H1),
    # but it did not exist when this was declared, and adopting it now would be
    # re-grading a committed result against a bar chosen after the fact.
    benchmark = benchmarks.BUY_AND_HOLD
    fixed = {"defensive": "BIL", "rebalance": "month_end"}
    fitted = {"lookback": [150, 200, 250]}
    # Transcribed verbatim from the pre-registration; the harness grades these,
    # so the verdict is not something the researcher decides after seeing numbers.
    criteria = (
        Criterion("drawdown cut >= 10pp", "max_drawdown_vs_benchmark", 0.10),
        Criterion("CAGR within 2pp", "cagr_vs_benchmark", -0.02),
        Criterion("protected in >= 3 events", "positive_protection_events", 3),
        Criterion(
            "plateau: holds at every lookback",
            "max_drawdown_vs_benchmark",
            0.10,
            scope="all_trials",
        ),
    )

    def weights(self, prices: pd.DataFrame) -> pd.DataFrame:
        defensive = self.params["defensive"]

        risk_on = above_moving_average(prices["SPY"], self.params["lookback"])
        choice = pd.Series(defensive, index=prices.index).where(~risk_on, "SPY")

        targets = one_hot(prices.index, ["SPY", defensive], choice)
        return rebalance(targets, self.params["rebalance"])
