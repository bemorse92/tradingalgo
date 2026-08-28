"""Look-ahead detection tests.

The second test here is the one that matters: it proves the check actually catches
peeking, rather than passing everything it is ever shown.
"""

from __future__ import annotations

import pandas as pd
import pytest

from backtest import ledger, validate
from tests.conftest import HonestTrend, PeekingTrend


def test_honest_strategy_passes(prices):
    validate.assert_no_lookahead(HonestTrend(lookback=40), prices)


def test_peeking_strategy_is_caught(prices):
    """A centred rolling mean reads forward. The check must refuse it."""
    with pytest.raises(validate.LookAheadError, match="leaks future data"):
        validate.assert_no_lookahead(PeekingTrend(), prices)


def test_missing_prereg_blocks_the_run(prices):
    with pytest.raises(validate.PreRegistrationError, match="No pre-registration"):
        validate.require_prereg(HonestTrend())


def test_holdout_is_armed(prices):
    """The gate is live: 2023 onward is reserved and must not leak into a run."""
    assert validate.HOLDOUT_START == "2023-01-01"

    withheld = validate.apply_holdout(prices)
    assert withheld.index.max() < pd.Timestamp(validate.HOLDOUT_START)


def test_holdout_is_inert_when_unset(prices, monkeypatch):
    monkeypatch.setattr(validate, "HOLDOUT_START", None)
    assert len(validate.apply_holdout(prices)) == len(prices)


def test_holdout_truncates_when_configured(prices, monkeypatch):
    cut = prices.index[500]
    monkeypatch.setattr(validate, "HOLDOUT_START", str(cut.date()))

    withheld = validate.apply_holdout(prices)
    assert withheld.index[-1] < cut
    assert len(validate.apply_holdout(prices, allow_holdout=True)) == len(prices)


def test_holdout_guard_allows_the_first_consumption(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "trials.csv")
    validate.guard_holdout("sma_trend", allow_holdout=True)  # no prior use: fine


def test_holdout_guard_refuses_a_second_look(tmp_path, monkeypatch):
    """A holdout consulted twice is not a holdout, and there is no second one."""
    monkeypatch.setattr(ledger, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "trials.csv")
    ledger.log_trial(
        strategy_name="sma_trend",
        params={},
        snapshot_id="s",
        start="2007-05-30",
        end="2026-08-26",
        cost_bps=5.0,
        declared_n=3,
        metrics={"sharpe": 1.0, "cagr": 0.08, "max_drawdown": -0.2},
        used_holdout=True,
    )

    with pytest.raises(validate.HoldoutExhaustedError, match="already consumed"):
        validate.guard_holdout("sma_trend", allow_holdout=True)

    # A different strategy has its own holdout and is unaffected.
    validate.guard_holdout("dual_momentum", allow_holdout=True)
    # And the guard is inert when the holdout is not being consumed at all.
    validate.guard_holdout("sma_trend", allow_holdout=False)
    # An explicit override is permitted, and is itself recorded by the caller.
    validate.guard_holdout("sma_trend", allow_holdout=True, force=True)
