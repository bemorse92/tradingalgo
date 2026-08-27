"""Ledger tests: the trial count must be automatic and append-only."""

from __future__ import annotations

import pytest

from backtest import ledger


@pytest.fixture
def temp_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "trials.csv")
    return tmp_path / "trials.csv"


def _log(name="s", sharpe=1.0, **kwargs):
    ledger.log_trial(
        strategy_name=name,
        params={"lookback": 200},
        snapshot_id="2026-01-01-abcdef12",
        start="2004-11-18",
        end="2026-08-27",
        cost_bps=5.0,
        declared_n=3,
        metrics={"sharpe": sharpe, "cagr": 0.08, "max_drawdown": -0.2},
        **kwargs,
    )


def test_empty_ledger_reads_as_empty_frame(temp_ledger):
    assert ledger.read().empty
    assert ledger.trial_count() == 0
    assert ledger.sharpes() == []


def test_trials_accumulate_and_are_never_deduplicated(temp_ledger):
    for _ in range(3):
        _log(sharpe=1.0)  # identical trials still count separately
    assert ledger.trial_count() == 3
    assert ledger.sharpes() == [1.0, 1.0, 1.0]


def test_trial_count_filters_by_strategy(temp_ledger):
    _log(name="alpha")
    _log(name="beta")
    _log(name="beta")

    assert ledger.trial_count() == 3
    assert ledger.trial_count("beta") == 2


def test_sharpes_span_all_strategies_by_default(temp_ledger):
    """Multiple testing is a property of the whole search, not one branch."""
    _log(name="alpha", sharpe=0.5)
    _log(name="beta", sharpe=1.5)
    assert sorted(ledger.sharpes()) == [0.5, 1.5]
    assert ledger.sharpes("alpha") == [0.5]


def test_holdout_access_is_recorded(temp_ledger):
    _log(used_holdout=True)
    assert bool(ledger.read()["used_holdout"].iloc[0]) is True


def test_robustness_trials_are_logged_but_do_not_deflate(temp_ledger):
    """N means configurations selected among, not re-runs of one configuration.

    Counting robustness checks would penalise the behaviour the project wants to
    encourage identically to p-hacking, which it wants to discourage.
    """
    _log(sharpe=1.0, kind="search")
    for _ in range(20):
        _log(sharpe=0.4, kind="robustness")

    assert ledger.trial_count() == 21  # everything is on the record
    assert ledger.sharpes() == [1.0]  # only the search trial deflates
    assert len(ledger.sharpes(kind=None)) == 21
