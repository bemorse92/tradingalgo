"""Strategy declaration tests: the parameter budget must bite at import time."""

from __future__ import annotations

import pandas as pd
import pytest

from backtest import benchmarks
from backtest.criteria import Criterion
from backtest.strategy import MAX_FITTED_PARAMS, Strategy, StrategyDeclarationError
from tests.conftest import HonestTrend


def _weights_stub(self, prices: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(0.0, index=prices.index, columns=["SPY"])


def test_grid_enumerates_every_combination():
    assert list(HonestTrend.grid()) == [
        {"lookback": 20},
        {"lookback": 40},
        {"lookback": 60},
    ]
    assert HonestTrend.declared_n() == 3


def test_declared_n_multiplies_across_parameters():
    class Two(Strategy):
        name = "two"
        rationale = "test"
        benchmark = benchmarks.BUY_AND_HOLD
        criteria = (Criterion("c", "cagr", 0.0),)
        fitted = {"a": [1, 2, 3], "b": [10, 20]}
        weights = _weights_stub

    assert Two.declared_n() == 6


def test_params_merge_fixed_and_fitted():
    strategy = HonestTrend(lookback=40)
    assert strategy.params == {"defensive": "TLT", "lookback": 40}
    assert strategy.fitted_params() == {"lookback": 40}


def test_fitted_defaults_to_first_grid_value():
    assert HonestTrend().params["lookback"] == 20


def test_too_many_fitted_parameters_is_refused():
    with pytest.raises(StrategyDeclarationError, match=f"cap is {MAX_FITTED_PARAMS}"):

        class Overfit(Strategy):
            name = "overfit"
            rationale = "test"
            benchmark = benchmarks.BUY_AND_HOLD
            criteria = (Criterion("c", "cagr", 0.0),)
            fitted = {"a": [1], "b": [2], "c": [3]}
            weights = _weights_stub


def test_missing_rationale_is_refused():
    with pytest.raises(StrategyDeclarationError, match="ex-ante economic foundation"):

        class NoReason(Strategy):
            name = "no_reason"
            rationale = "   "
            criteria = (Criterion("c", "cagr", 0.0),)
            weights = _weights_stub


def test_missing_name_is_refused():
    with pytest.raises(StrategyDeclarationError, match="must declare a `name`"):

        class Nameless(Strategy):
            rationale = "test"
            benchmark = benchmarks.BUY_AND_HOLD
            criteria = (Criterion("c", "cagr", 0.0),)
            weights = _weights_stub


def test_parameter_declared_both_fixed_and_fitted_is_refused():
    with pytest.raises(StrategyDeclarationError, match="both fixed and fitted"):

        class Confused(Strategy):
            name = "confused"
            rationale = "test"
            benchmark = benchmarks.BUY_AND_HOLD
            criteria = (Criterion("c", "cagr", 0.0),)
            fixed = {"a": 1}
            fitted = {"a": [1, 2]}
            weights = _weights_stub


def test_empty_fitted_grid_is_refused():
    with pytest.raises(StrategyDeclarationError, match="non-empty sequence"):

        class EmptyGrid(Strategy):
            name = "empty_grid"
            rationale = "test"
            benchmark = benchmarks.BUY_AND_HOLD
            criteria = (Criterion("c", "cagr", 0.0),)
            fitted = {"a": []}
            weights = _weights_stub


def test_undeclared_parameter_is_refused():
    with pytest.raises(TypeError, match="undeclared parameters"):
        HonestTrend(nonexistent=1)


def test_missing_benchmark_is_refused():
    """Which alternative a rule must beat is part of the hypothesis.

    Without this a strategy inherits buy-and-hold silently -- the comparison that
    flatters any rule simply holding less equity -- and the matched benchmarks
    stay a table nobody has to answer to.
    """
    with pytest.raises(StrategyDeclarationError, match="must declare a `benchmark`"):

        class NoBar(Strategy):
            name = "no_bar"
            rationale = "a stated mechanism"
            criteria = (Criterion("c", "cagr", 0.0),)
            weights = _weights_stub


def test_unknown_benchmark_is_refused_at_declaration():
    """A typo must fail at import, not silently grade against something else."""
    with pytest.raises(StrategyDeclarationError, match="must declare a `benchmark`"):

        class Typo(Strategy):
            name = "typo"
            rationale = "a stated mechanism"
            benchmark = "vol-matched"  # the display name, not the key
            criteria = (Criterion("c", "cagr", 0.0),)
            weights = _weights_stub


def test_a_harder_benchmark_is_declarable():
    """The point of H4: the matched mix can be the declared bar, not just a table."""

    class Matched(Strategy):
        name = "matched"
        rationale = "a stated mechanism"
        benchmark = benchmarks.VOL_MATCHED
        criteria = (Criterion("c", "cagr_vs_benchmark", 0.0),)
        weights = _weights_stub

    assert Matched.benchmark in benchmarks.KEYS
