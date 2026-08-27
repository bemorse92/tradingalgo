"""CLI tests: report rendering must not crash, and strategy loading must fail loudly."""

from __future__ import annotations

import pytest

from backtest import cli, runner
from tests.conftest import HonestTrend
from tests.test_runner import SNAPSHOT


def test_report_renders_every_section(sandbox, prices, capsys):
    report = runner.run_strategy(HonestTrend, prices, SNAPSHOT)
    cli._print_report(report)

    out = capsys.readouterr().out
    assert "honest_trend" in out
    assert "snapshot" in out and SNAPSHOT.id in out
    assert "Parameter plateau" in out
    assert "Per-event attribution" in out
    # Provenance is not optional: a result without these numbers is not a result.
    assert "declared N" in out
    assert "trials to date" in out


def test_report_shows_every_grid_point(sandbox, prices, capsys):
    """Seeing the peak alone must be impossible."""
    report = runner.run_strategy(HonestTrend, prices, SNAPSHOT)
    cli._print_report(report)

    out = capsys.readouterr().out
    for lookback in HonestTrend.fitted["lookback"]:
        assert str(lookback) in out


def test_report_flags_declared_n_disagreeing_with_the_ledger(sandbox, prices, capsys):
    """Running twice doubles the ledger count while declared N stays put."""
    runner.run_strategy(HonestTrend, prices, SNAPSHOT)
    report = runner.run_strategy(HonestTrend, prices, SNAPSHOT)
    cli._print_report(report)

    out = capsys.readouterr().out
    assert report.declared_n == 3
    assert report.trials_total == 6
    assert "differ" in out


def test_unknown_strategy_module_fails_clearly():
    with pytest.raises(SystemExit, match="No strategy module"):
        cli._load_strategy("does_not_exist")


def test_snapshots_command_runs(capsys):
    assert cli.main(["snapshots"]) == 0
    assert capsys.readouterr().out.strip() != ""
