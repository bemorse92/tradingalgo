"""Criteria grading tests.

The point of this module is that a verdict is produced by the harness rather than
by the researcher comparing numbers to a paragraph in their head.
"""

from __future__ import annotations

import pandas as pd
import pytest

from backtest import criteria as crit
from backtest.runner import TrialResult


def _trial(cagr: float, max_dd: float, sharpe: float = 0.5) -> TrialResult:
    return TrialResult(
        params={},
        result=None,
        metrics={"cagr": cagr, "max_drawdown": max_dd, "sharpe": sharpe, "volatility": 0.1},
    )


BENCHMARK = {"cagr": 0.0815, "max_drawdown": -0.5519, "sharpe": 0.483, "volatility": 0.2066}


def _attribution(protections: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "peak": ["2008-01-01"] * len(protections),
            "trough": ["2009-01-01"] * len(protections),
            "benchmark_dd": [-0.3] * len(protections),
            "strategy_dd": [-0.1] * len(protections),
            "protection": protections,
            "recovered": [True] * len(protections),
        }
    )


def test_benchmark_relative_metric_is_a_difference():
    best = _trial(cagr=0.0832, max_dd=-0.2083)
    results = crit.evaluate(
        [crit.Criterion("dd cut", "max_drawdown_vs_benchmark", 0.10)],
        [best],
        best,
        BENCHMARK,
        _attribution([0.5]),
    )
    # -0.2083 - (-0.5519) = 0.3436
    assert results[0].value == pytest.approx(0.3436, abs=1e-4)
    assert results[0].passed


def test_negative_threshold_expresses_an_allowance():
    """"CAGR no more than 2pp below benchmark" is at_least -0.02."""
    best = _trial(cagr=0.0615, max_dd=-0.2)  # 2 points below the benchmark's 8.15%
    results = crit.evaluate(
        [crit.Criterion("cagr floor", "cagr_vs_benchmark", -0.02)],
        [best],
        best,
        BENCHMARK,
        _attribution([0.5]),
    )
    assert results[0].passed

    worse = _trial(cagr=0.05, max_dd=-0.2)  # 3.15 points below: outside the allowance
    results = crit.evaluate(
        [crit.Criterion("cagr floor", "cagr_vs_benchmark", -0.02)],
        [worse],
        worse,
        BENCHMARK,
        _attribution([0.5]),
    )
    assert not results[0].passed


def test_all_trials_scope_reports_the_weakest_trial():
    """A plateau requirement fails if any single grid point fails."""
    trials = [_trial(0.08, -0.20), _trial(0.08, -0.21), _trial(0.08, -0.50)]
    best = trials[0]
    results = crit.evaluate(
        [crit.Criterion("plateau", "max_drawdown_vs_benchmark", 0.10, scope="all_trials")],
        trials,
        best,
        BENCHMARK,
        _attribution([0.5]),
    )
    # The -0.50 trial only improves on the benchmark by 0.0519.
    assert results[0].value == pytest.approx(0.0519, abs=1e-4)
    assert not results[0].passed


def test_event_count_metric_counts_positive_protection():
    best = _trial(0.08, -0.20)
    results = crit.evaluate(
        [crit.Criterion("events", "positive_protection_events", 3)],
        [best],
        best,
        BENCHMARK,
        _attribution([0.6, 0.2, -0.01, 0.0]),  # only two are positive
    )
    assert results[0].value == 2
    assert not results[0].passed


def test_largest_protection_share_exposes_one_event_edges():
    best = _trial(0.08, -0.20)
    results = crit.evaluate(
        [crit.Criterion("not one event", "largest_protection_share", 0.6, comparison="at_most")],
        [best],
        best,
        BENCHMARK,
        _attribution([0.90, 0.05, 0.05]),  # 90% of protection from one event
    )
    assert results[0].value == pytest.approx(0.9)
    assert not results[0].passed


def test_verdict_requires_every_criterion():
    best = _trial(0.08, -0.20)
    results = crit.evaluate(
        [
            crit.Criterion("passes", "max_drawdown_vs_benchmark", 0.10),
            crit.Criterion("fails", "cagr_vs_benchmark", 0.50),
        ],
        [best],
        best,
        BENCHMARK,
        _attribution([0.5]),
    )
    assert crit.verdict(results) == "FAIL"


def test_ungraded_when_nothing_declared():
    assert crit.verdict([]) == "UNGRADED"


def test_unknown_metric_is_refused():
    best = _trial(0.08, -0.20)
    with pytest.raises(crit.CriterionError, match="Unknown metric"):
        crit.evaluate(
            [crit.Criterion("bogus", "sortino", 1.0)], [best], best, BENCHMARK, _attribution([0.5])
        )


def test_unknown_comparison_is_refused_at_declaration():
    with pytest.raises(crit.CriterionError, match="unknown comparison"):
        crit.Criterion("c", "cagr", 0.0, comparison="roughly")


def test_attribution_metric_cannot_use_all_trials_scope():
    with pytest.raises(crit.CriterionError, match="scope must be 'best'"):
        crit.Criterion("c", "positive_protection_events", 3, scope="all_trials")


def test_declared_boundaries_are_inclusive():
    """Exactly at the bar passes. Verdicts must not hinge on binary float error."""
    best = _trial(cagr=0.0615, max_dd=-0.20)  # exactly 2pp below the benchmark
    results = crit.evaluate(
        [crit.Criterion("cagr floor", "cagr_vs_benchmark", -0.02)],
        [best],
        best,
        BENCHMARK,
        _attribution([0.5]),
    )
    assert results[0].passed
