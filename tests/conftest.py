"""Shared fixtures.

Includes a deliberately look-ahead-buggy strategy. A check that has never caught a
bug is not known to work, so the corruption test is validated against a strategy
that really does peek.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest import ledger, validate
from backtest.strategy import Strategy


@pytest.fixture
def prices() -> pd.DataFrame:
    """Deterministic synthetic prices for two tickers."""
    dates = pd.bdate_range("2010-01-04", periods=1200, name="date")
    rng = np.random.default_rng(42)
    spy = 100.0 * np.exp(np.cumsum(rng.normal(0.0004, 0.011, len(dates))))
    tlt = 100.0 * np.exp(np.cumsum(rng.normal(0.0002, 0.008, len(dates))))
    return pd.DataFrame({"SPY": spy, "TLT": tlt}, index=dates)


@pytest.fixture
def jump_prices() -> pd.DataFrame:
    """Flat prices with a single large jump, for testing the engine's lag."""
    dates = pd.bdate_range("2020-01-01", periods=10, name="date")
    spy = np.full(len(dates), 100.0)
    spy[5:] = 200.0  # +100% on the sixth bar
    return pd.DataFrame({"SPY": spy}, index=dates)


class HonestTrend(Strategy):
    """Plain moving-average trend rule. Uses only past and present prices."""

    name = "honest_trend"
    rationale = "Volatility clusters; large drawdowns are slow grinds, not gaps."
    fixed = {"defensive": "TLT"}
    fitted = {"lookback": [20, 40, 60]}

    def weights(self, prices: pd.DataFrame) -> pd.DataFrame:
        ma = prices["SPY"].rolling(self.params["lookback"]).mean()
        risk_on = (prices["SPY"] > ma).fillna(False)
        out = pd.DataFrame(0.0, index=prices.index, columns=["SPY", self.params["defensive"]])
        out.loc[risk_on, "SPY"] = 1.0
        out.loc[~risk_on, self.params["defensive"]] = 1.0
        return out


class PeekingTrend(Strategy):
    """Deliberately broken: centred rolling mean reads future prices.

    Exists only so the corruption test can be shown to catch something.
    """

    name = "peeking_trend"
    rationale = "Intentionally invalid; used to verify the look-ahead check bites."
    fixed = {}
    fitted = {"lookback": [20]}

    def weights(self, prices: pd.DataFrame) -> pd.DataFrame:
        ma = prices["SPY"].rolling(self.params["lookback"], center=True).mean()
        risk_on = (prices["SPY"] > ma).fillna(False)
        out = pd.DataFrame(0.0, index=prices.index, columns=["SPY"])
        out.loc[risk_on, "SPY"] = 1.0
        return out


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Isolate the ledger and satisfy the pre-registration gate.

    Tests must never write to the real results/trials.csv: the ledger is an audit
    trail, and a test run is not a research trial.
    """
    strategies = tmp_path / "strategies"
    strategies.mkdir()
    (strategies / "honest_trend.prereg.md").write_text("# test prereg", encoding="utf-8")

    monkeypatch.setattr(validate, "STRATEGY_DIR", strategies)
    monkeypatch.setattr(ledger, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "trials.csv")
    return strategies
