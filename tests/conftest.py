"""Shared fixtures.

Includes a deliberately look-ahead-buggy strategy. A check that has never caught a
bug is not known to work, so the corruption test is validated against a strategy
that really does peek.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest import benchmarks, ledger, validate
from backtest.criteria import Criterion
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
def basket(prices) -> pd.DataFrame:
    """The two-ticker fixture plus a near-riskless cash sleeve.

    A cash sleeve is what makes the matched benchmarks constructible, so any test
    about declared benchmarks needs this rather than the bare `prices` fixture.
    """
    frame = prices.copy()
    frame["BIL"] = 100.0 * np.exp(np.arange(len(frame)) * 0.00008)  # ~2%/yr, no vol
    return frame


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
    benchmark = benchmarks.BUY_AND_HOLD
    fixed = {"defensive": "TLT"}
    fitted = {"lookback": [20, 40, 60]}
    criteria = (Criterion("drawdown cut", "max_drawdown_vs_benchmark", 0.05),)

    def weights(self, prices: pd.DataFrame) -> pd.DataFrame:
        ma = prices["SPY"].rolling(self.params["lookback"]).mean()
        risk_on = (prices["SPY"] > ma).fillna(False)
        out = pd.DataFrame(0.0, index=prices.index, columns=["SPY", self.params["defensive"]])
        out.loc[risk_on, "SPY"] = 1.0
        out.loc[~risk_on, self.params["defensive"]] = 1.0
        return out


class MatchedTrend(HonestTrend):
    """The same rule as HonestTrend, declared against the vol-matched mix.

    Exists so the declared benchmark can be shown to change the verdict rather
    than merely being recorded next to it.
    """

    name = "matched_trend"
    benchmark = benchmarks.VOL_MATCHED


class PeekingTrend(Strategy):
    """Deliberately broken: centred rolling mean reads future prices.

    Exists only so the corruption test can be shown to catch something.
    """

    name = "peeking_trend"
    rationale = "Intentionally invalid; used to verify the look-ahead check bites."
    benchmark = benchmarks.BUY_AND_HOLD
    fixed = {}
    fitted = {"lookback": [20]}
    criteria = (Criterion("drawdown cut", "max_drawdown_vs_benchmark", 0.05),)

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
    for name in ("honest_trend", "matched_trend"):
        (strategies / f"{name}.prereg.md").write_text("# test prereg", encoding="utf-8")

    monkeypatch.setattr(validate, "STRATEGY_DIR", strategies)
    monkeypatch.setattr(ledger, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "trials.csv")
    return strategies
