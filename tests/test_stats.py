"""Statistics tests.

Conventional metrics are checked against hand-computed values and cross-checked
against `ffn` as an oracle. The multiple-testing functions are checked against the
published figures they come from.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest import stats


def test_max_drawdown_known_series():
    equity = pd.Series([1.0, 1.5, 0.75, 1.2])  # peak 1.5 -> trough 0.75 is -50%
    assert stats.max_drawdown(equity) == pytest.approx(-0.5)


def test_cagr_doubling_over_two_years():
    index = pd.to_datetime(["2020-01-01", "2022-01-01"])
    equity = pd.Series([1.0, 4.0], index=index)
    # 4x over ~2 years is 100%/yr
    assert stats.cagr(equity) == pytest.approx(1.0, rel=1e-3)


def test_sharpe_hand_computed():
    returns = pd.Series([0.01, -0.01] * 50)
    expected = returns.mean() / returns.std(ddof=1) * np.sqrt(252)
    assert stats.sharpe(returns) == pytest.approx(expected)


def test_metrics_agree_with_ffn_oracle(prices):
    """Cross-check against a third-party implementation.

    CAGR uses a loose tolerance because day-count conventions differ (365.25 here
    vs ffn's); max drawdown has no such ambiguity and is checked tightly.
    """
    ffn = pytest.importorskip("ffn")
    equity = prices["SPY"] / prices["SPY"].iloc[0]

    assert stats.max_drawdown(equity) == pytest.approx(
        float(ffn.core.calc_max_drawdown(equity)), rel=1e-9
    )
    assert stats.cagr(equity) == pytest.approx(float(ffn.core.calc_cagr(equity)), rel=0.02)


def test_expected_max_sharpe_reproduces_published_figure():
    """Bailey & Lopez de Prado: 1,000 trials, unit variance -> ~3.26.

    This is the number the whole guardrail stack exists to respect: a Sharpe of
    3.26 found after a thousand tries is exactly what worthless strategies produce.
    """
    assert stats.expected_max_sharpe(1000, 1.0) == pytest.approx(3.26, abs=0.01)


def test_expected_max_sharpe_grows_with_trials():
    assert stats.expected_max_sharpe(10, 1.0) < stats.expected_max_sharpe(10_000, 1.0)


def test_expected_max_sharpe_degenerate_cases():
    assert stats.expected_max_sharpe(1, 1.0) == 0.0
    assert stats.expected_max_sharpe(100, 0.0) == 0.0


def test_psr_rises_with_track_record_length():
    rng = np.random.default_rng(7)
    short = pd.Series(rng.normal(0.0005, 0.01, 100))
    long = pd.Series(rng.normal(0.0005, 0.01, 5000))
    assert stats.probabilistic_sharpe_ratio(long) > stats.probabilistic_sharpe_ratio(short)


def test_deflated_sharpe_falls_as_the_search_widens():
    """The same returns become less impressive the more strategies were tried."""
    rng = np.random.default_rng(11)
    returns = pd.Series(rng.normal(0.0006, 0.01, 2000))

    narrow = stats.deflated_sharpe_ratio(returns, [0.9, 1.0, 1.1])
    wide = stats.deflated_sharpe_ratio(returns, list(rng.normal(0.5, 1.2, 500)))
    assert wide < narrow


def test_min_track_record_length_is_infinite_without_an_edge():
    rng = np.random.default_rng(3)
    flat = pd.Series(rng.normal(0.0, 0.01, 500))
    assert stats.min_track_record_length(flat, benchmark_sharpe=1.0) == float("inf")


def test_drawdown_events_finds_distinct_episodes():
    equity = pd.Series(
        [1.0, 1.2, 0.9, 1.3, 1.4, 0.7, 1.5],
        index=pd.bdate_range("2020-01-01", periods=7),
    )
    events = stats.drawdown_events(equity, threshold=-0.10)

    assert len(events) == 2
    # Worst first: 1.4 -> 0.7 is -50%, 1.2 -> 0.9 is -25%
    assert events[0].depth == pytest.approx(-0.5)
    assert events[1].depth == pytest.approx(-0.25)
    assert all(e.recovered for e in events)


def test_attribution_reports_protection_per_event():
    index = pd.bdate_range("2020-01-01", periods=7)
    benchmark = pd.Series([1.0, 1.2, 0.9, 1.3, 1.4, 0.7, 1.5], index=index)
    defensive = pd.Series([1.0, 1.1, 1.05, 1.1, 1.15, 1.1, 1.2], index=index)

    events = stats.drawdown_events(benchmark, threshold=-0.10)
    frame = stats.attribution(defensive, benchmark, events)

    assert len(frame) == 2
    assert (frame["protection"] > 0).all()  # defensive curve lost less every time


def test_relative_drawdown_measures_shortfall_against_the_benchmark():
    index = pd.bdate_range("2020-01-01", periods=4)
    benchmark = pd.Series([1.0, 1.0, 2.0, 2.0], index=index)
    strategy = pd.Series([1.0, 1.0, 1.0, 1.0], index=index)
    # Relative curve peaks at 1.0 then halves as the benchmark doubles away.
    assert stats.relative_drawdown(strategy, benchmark) == pytest.approx(-0.5)


def test_relative_drawdown_is_zero_when_never_behind():
    index = pd.bdate_range("2020-01-01", periods=4)
    benchmark = pd.Series([1.0, 1.0, 1.0, 1.0], index=index)
    strategy = pd.Series([1.0, 1.1, 1.2, 1.3], index=index)
    assert stats.relative_drawdown(strategy, benchmark) == pytest.approx(0.0)


def test_longest_underperformance_counts_the_worst_stretch():
    index = pd.bdate_range("2020-01-01", periods=7)
    benchmark = pd.Series([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0], index=index)
    # Behind for three bars, recovers to a new peak, then behind for one.
    strategy = pd.Series([1.0, 0.9, 0.9, 0.9, 1.2, 1.1, 1.3], index=index)
    assert stats.longest_underperformance(strategy, benchmark) == 3


def test_regret_bundle_has_the_followability_numbers():
    index = pd.bdate_range("2020-01-01", periods=300)
    benchmark = pd.Series(1.0, index=index).cumsum() / 300 + 1.0
    strategy = pd.Series(1.0, index=index)
    bundle = stats.regret(strategy, benchmark)

    assert set(bundle) == {
        "relative_drawdown",
        "worst_1y_shortfall",
        "longest_underperformance_days",
    }
    assert bundle["relative_drawdown"] < 0  # flat strategy falls behind a rising benchmark
