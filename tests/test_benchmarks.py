"""Benchmark tests.

The load-bearing property is symmetry: a benchmark must be produced by the same
engine, with the same lag and the same costs, as the strategy it is compared to.
A benchmark held to a different standard is how backtests flatter themselves.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest import benchmarks, engine, stats


def test_static_mix_pays_the_same_entry_cost_as_buy_and_hold(prices):
    """No asymmetry: a 100% SPY static mix is buy & hold, cost for cost."""
    mix = benchmarks.static(prices, {"SPY": 1.0}, cost_bps=10.0)
    hold = engine.buy_and_hold(prices, ticker="SPY", cost_bps=10.0)
    assert float(mix.equity.iloc[-1]) == pytest.approx(float(hold.equity.iloc[-1]))
    assert mix.total_costs == pytest.approx(hold.total_costs)


def test_static_mix_sits_between_its_sleeves(basket):
    """A blend cannot be more volatile than its most volatile component."""
    mix = benchmarks.static(basket, {"SPY": 0.5, "BIL": 0.5}, cost_bps=0.0)
    spy = benchmarks.static(basket, {"SPY": 1.0}, cost_bps=0.0)
    assert stats.annual_volatility(mix.returns) < stats.annual_volatility(spy.returns)


def test_vol_matched_weight_reproduces_the_target(basket):
    """The solved mix actually has the volatility it was asked for."""
    target = 0.5 * stats.annual_volatility(
        benchmarks.static(basket, {"SPY": 1.0}, cost_bps=0.0).returns
    )
    weight = benchmarks.vol_matched_weight(basket, target, cost_bps=0.0)

    matched = benchmarks.static(basket, {"SPY": weight, "BIL": 1.0 - weight}, cost_bps=0.0)
    assert stats.annual_volatility(matched.returns) == pytest.approx(target, rel=1e-3)
    assert 0.0 < weight < 1.0


def test_vol_matched_weight_clamps_beyond_the_reachable_range(basket):
    """A target no mix can reach saturates rather than failing or extrapolating.

    Leverage is out of scope, so "more volatile than 100% equity" has to resolve
    to all-equity, not to a weight above 1.0.
    """
    assert benchmarks.vol_matched_weight(basket, 10.0, cost_bps=0.0) == 1.0
    assert benchmarks.vol_matched_weight(basket, 0.0, cost_bps=0.0) == 0.0


def test_equity_exposure_is_time_in_market_for_an_all_or_nothing_rule(basket):
    """Half the days in SPY, half in cash -> 50% exposure."""
    weights = pd.DataFrame(0.0, index=basket.index, columns=["SPY", "BIL"])
    weights.iloc[: len(basket) // 2, 0] = 1.0
    weights.iloc[len(basket) // 2 :, 1] = 1.0

    result = engine.run(basket, weights, cost_bps=0.0)
    assert benchmarks.equity_exposure(result, "SPY") == pytest.approx(0.5, abs=0.01)


def test_matched_benchmark_neutralises_a_pure_de_risking_rule(basket):
    """The point of section H, as a test.

    A rule that holds SPY on even days and cash on odd days carries no
    information -- it is just less equity. The exposure-matched benchmark should
    therefore land close to it, where plain buy & hold would not.
    """
    weights = pd.DataFrame(0.0, index=basket.index, columns=["SPY", "BIL"])
    alternating = np.arange(len(basket)) % 2 == 0
    weights.loc[alternating, "SPY"] = 1.0
    weights.loc[~alternating, "BIL"] = 1.0
    result = engine.run(basket, weights, cost_bps=0.0)

    slate = benchmarks.build(basket, result, cost_bps=0.0)
    matched = benchmarks.resolve(slate, benchmarks.EXPOSURE_MATCHED)
    hold = benchmarks.resolve(slate, benchmarks.BUY_AND_HOLD)

    strategy_dd = stats.max_drawdown(result.equity)
    assert abs(strategy_dd - matched.metrics["max_drawdown"]) < abs(
        strategy_dd - hold.metrics["max_drawdown"]
    )


def test_build_skips_benchmarks_whose_tickers_are_missing(prices):
    """No cash sleeve in the snapshot -> no matched mixes, rather than fake ones.

    Modelling an absent sleeve as 0% return is the exact distortion the project's
    BIL sleeve exists to avoid, so a missing ticker must drop the row.
    """
    result = engine.buy_and_hold(prices, ticker="SPY", cost_bps=0.0)
    names = [b.name for b in benchmarks.build(prices, result, cost_bps=0.0)]

    assert any(n.startswith("buy & hold") for n in names)
    assert not any("matched" in n for n in names)
    assert not any("cash" in n for n in names)


def test_inverse_volatility_weights_are_valid_and_favour_the_calm_asset(basket):
    """Weights the engine will accept, tilted toward the lower-volatility sleeve."""
    result = benchmarks.inverse_volatility(basket, ["SPY", "TLT"], cash="BIL", cost_bps=0.0)

    engine.check_weights(result.held)  # long-only, no leverage, no NaN
    settled = result.held.iloc[benchmarks.INVERSE_VOL_LOOKBACK + 25 :]
    assert settled["TLT"].mean() > settled["SPY"].mean()  # TLT is the calmer series
    assert settled["BIL"].max() == pytest.approx(0.0)  # cash only holds the warmup


def test_available_keys_agrees_with_what_build_produces(basket, prices):
    """Pre-flight and the real build must never disagree.

    `require` checks a declared benchmark before the sweep runs; if it said yes
    where `build` then omits the row, a run would log trials and die afterwards.
    """
    for frame in (basket, prices):
        result = engine.buy_and_hold(frame, ticker="SPY", cost_bps=0.0)
        built = [b.key for b in benchmarks.build(frame, result, cost_bps=0.0)]
        assert sorted(built) == sorted(benchmarks.available_keys(frame))


def test_resolve_picks_the_declared_benchmark_by_key(basket):
    """Keys are stable; display names carry weights only known after the run."""
    result = engine.buy_and_hold(basket, ticker="SPY", cost_bps=0.0)
    slate = benchmarks.build(basket, result, cost_bps=0.0)

    matched = benchmarks.resolve(slate, benchmarks.VOL_MATCHED)
    assert matched.key == benchmarks.VOL_MATCHED
    assert matched.name.startswith("vol-matched")


def test_unbuildable_benchmark_is_refused_not_substituted(prices):
    """No cash sleeve -> no matched mix. Falling back would re-grade silently."""
    with pytest.raises(benchmarks.BenchmarkUnavailableError, match="cannot be built"):
        benchmarks.require(prices, benchmarks.VOL_MATCHED)


def test_unknown_benchmark_key_is_refused(basket):
    with pytest.raises(benchmarks.BenchmarkUnavailableError, match="Unknown benchmark"):
        benchmarks.require(basket, "vol-matched")


def test_every_declarable_key_is_actually_buildable(basket):
    """The declared vocabulary and the built slate are the same set.

    A key a strategy may declare but the harness never builds would fail only at
    run time, on a snapshot that has every ticker.
    """
    result = engine.buy_and_hold(basket, ticker="SPY", cost_bps=0.0)
    full = basket.copy()
    full["GLD"] = 100.0  # a second risky sleeve, so the basket rows appear
    built = {b.key for b in benchmarks.build(full, result, cost_bps=0.0)}
    assert built == set(benchmarks.KEYS)
