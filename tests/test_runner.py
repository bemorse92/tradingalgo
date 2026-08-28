"""End-to-end tests: validation, sweep, logging, and reporting as one flow."""

from __future__ import annotations

import pytest

from backtest import benchmarks, ledger, runner, validate
from backtest.data import Snapshot
from tests.conftest import HonestTrend, MatchedTrend, PeekingTrend

SNAPSHOT = Snapshot(
    id="test-snapshot",
    created="2026-08-27T00:00:00",
    tickers=("SPY", "TLT"),
    start="2010-01-04",
    end="2014-08-08",
    rows=1200,
    checksum="deadbeefdeadbeef",
)




def test_run_sweeps_the_grid_and_logs_every_trial(sandbox, prices):
    report = runner.run_strategy(HonestTrend, prices, SNAPSHOT, cost_bps=5.0)

    assert len(report.trials) == HonestTrend.declared_n() == 3
    assert ledger.trial_count("honest_trend") == 3
    assert report.trials_total == 3
    assert {t.params["lookback"] for t in report.trials} == {20, 40, 60}


def test_run_reports_benchmark_and_deflated_sharpe(sandbox, prices):
    report = runner.run_strategy(HonestTrend, prices, SNAPSHOT)

    assert report.benchmark_metrics["max_drawdown"] < 0
    for trial in report.trials:
        assert 0.0 <= trial.deflated_sharpe <= 1.0


def test_run_builds_the_benchmark_slate_without_logging_it(sandbox, prices):
    """Benchmarks are yardsticks, not candidates: they must not consume trials.

    A benchmark that inflated the trial count would penalise the strategy for
    being measured honestly, which is exactly backwards.
    """
    report = runner.run_strategy(HonestTrend, prices, SNAPSHOT)

    assert report.benchmarks, "no benchmarks built"
    assert ledger.trial_count() == HonestTrend.declared_n()
    # No cash sleeve in this fixture, so the matched mixes are skipped, not faked.
    assert report.vol_matched is None


def test_best_by_drawdown_picks_the_shallowest_not_the_richest(sandbox, prices):
    report = runner.run_strategy(HonestTrend, prices, SNAPSHOT)
    shallowest = max(t.metrics["max_drawdown"] for t in report.trials)
    assert report.best_by_drawdown.metrics["max_drawdown"] == shallowest


def test_missing_prereg_blocks_the_whole_run(tmp_path, monkeypatch, prices):
    monkeypatch.setattr(validate, "STRATEGY_DIR", tmp_path)
    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "trials.csv")

    with pytest.raises(validate.PreRegistrationError):
        runner.run_strategy(HonestTrend, prices, SNAPSHOT)
    assert ledger.trial_count() == 0  # nothing logged: the run did not happen


def test_peeking_strategy_never_reaches_the_ledger(tmp_path, monkeypatch, prices):
    """Validation runs before any trial is recorded."""
    (tmp_path / "peeking_trend.prereg.md").write_text("# test", encoding="utf-8")
    monkeypatch.setattr(validate, "STRATEGY_DIR", tmp_path)
    monkeypatch.setattr(ledger, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "trials.csv")

    with pytest.raises(validate.LookAheadError):
        runner.run_strategy(PeekingTrend, prices, SNAPSHOT)
    assert ledger.trial_count() == 0


def test_start_date_sweep_produces_one_report_per_window(sandbox, prices):
    reports = runner.start_date_sweep(
        HonestTrend, prices, SNAPSHOT, start_dates=("2010-01-04", "2011-01-03")
    )

    assert [start for start, _ in reports] == ["2010-01-04", "2011-01-03"]
    assert reports[0][1].sample_start != reports[1][1].sample_start
    assert ledger.trial_count() == 6  # both windows logged


def test_best_by_drawdown_breaks_ties_deterministically(sandbox, prices):
    """Variants sharing an identical drawdown must not report an arbitrary winner."""
    report = runner.run_strategy(HonestTrend, prices, SNAPSHOT)
    for trial in report.trials:
        trial.metrics["max_drawdown"] = -0.25  # force an exact tie
    report.trials[0].metrics["cagr"] = 0.01
    report.trials[1].metrics["cagr"] = 0.09
    report.trials[2].metrics["cagr"] = 0.05

    assert report.best_by_drawdown is report.trials[1]


def test_criteria_are_graded_against_the_declared_benchmark(sandbox, basket):
    """H4, as a test: the declared bar decides the numbers, not a hardcoded one.

    Same rule, same data, same criteria -- only the declared benchmark differs.
    If the two runs graded identically, the declaration would be decoration.
    """
    plain = runner.run_strategy(HonestTrend, basket, SNAPSHOT)
    matched = runner.run_strategy(MatchedTrend, basket, SNAPSHOT)

    assert plain.graded_benchmark.key == benchmarks.BUY_AND_HOLD
    assert matched.graded_benchmark.key == benchmarks.VOL_MATCHED
    assert plain.criteria[0].value != pytest.approx(matched.criteria[0].value)

    # And the matched mix is the harder bar: carrying the same risk with no
    # signal, it leaves far less drawdown for the rule to claim credit for.
    assert matched.criteria[0].value < plain.criteria[0].value


def test_regret_is_measured_against_the_declared_benchmark(sandbox, basket):
    """Followability is judged against whatever the researcher would compare to."""
    plain = runner.run_strategy(HonestTrend, basket, SNAPSHOT)
    matched = runner.run_strategy(MatchedTrend, basket, SNAPSHOT)

    assert plain.regret["relative_drawdown"] != pytest.approx(
        matched.regret["relative_drawdown"]
    )


def test_unbuildable_declared_benchmark_blocks_the_run_before_logging(sandbox, prices):
    """The `prices` fixture has no cash sleeve, so the vol-matched mix is impossible.

    The refusal has to come before the sweep: a run that dies afterwards has
    already spent ledger entries against a bar that does not exist.
    """
    with pytest.raises(benchmarks.BenchmarkUnavailableError):
        runner.run_strategy(MatchedTrend, prices, SNAPSHOT)
    assert ledger.trial_count() == 0
