"""Orchestration: pre-flight checks, sweep the declared grid, log every trial.

Nothing here is optional or skippable from a strategy's side. A run either passes
validation and is recorded, or it does not happen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from . import engine, ledger, stats, validate
from .data import Snapshot
from .strategy import Strategy

#: Shortest window worth reporting on: fewer than a year says nothing.
MIN_WINDOW_DAYS = 260


@dataclass
class TrialResult:
    """One point in the parameter grid."""

    params: dict[str, Any]
    result: engine.Result
    metrics: dict[str, float]
    deflated_sharpe: float = float("nan")


@dataclass
class RunReport:
    """Everything one invocation produced."""

    strategy_name: str
    snapshot: Snapshot
    sample_start: str
    sample_end: str
    declared_n: int
    trials_total: int
    used_holdout: bool
    benchmark: engine.Result
    benchmark_metrics: dict[str, float]
    trials: list[TrialResult] = field(default_factory=list)
    attribution: pd.DataFrame = field(default_factory=pd.DataFrame)
    regret: dict[str, float] = field(default_factory=dict)

    @property
    def best_by_drawdown(self) -> TrialResult:
        """Shallowest drawdown -- the project's stated bar, not the best return.

        Ties break on CAGR. Without a deterministic tie-break, strategies whose
        variants share an identical drawdown (common when they all sit through the
        same crash) report an arbitrary variant, which makes sweeps look
        non-monotonic for no real reason.
        """
        return max(self.trials, key=lambda t: (t.metrics["max_drawdown"], t.metrics["cagr"]))


def run_strategy(
    strategy_cls: type[Strategy],
    prices: pd.DataFrame,
    snapshot: Snapshot,
    cost_bps: float = engine.DEFAULT_COST_BPS,
    benchmark_ticker: str = "SPY",
    kind: str = "search",
    allow_holdout: bool = False,
    note: str = "",
) -> RunReport:
    """Validate, sweep the grid, log every trial, and return the report."""
    # Pre-flight on a representative instance: pre-registration must exist, the
    # holdout is truncated unless explicitly requested, and the strategy must
    # demonstrably not read ahead.
    probe = strategy_cls()
    usable = validate.prepare(probe, prices, allow_holdout=allow_holdout)

    benchmark = engine.buy_and_hold(usable, ticker=benchmark_ticker, cost_bps=cost_bps)
    benchmark_metrics = stats.summarise(benchmark.equity, benchmark.returns)

    trials: list[TrialResult] = []
    for params in strategy_cls.grid():
        strategy = strategy_cls(**params)
        weights = strategy.weights(usable)
        result = engine.run(usable, weights, cost_bps=cost_bps)
        metrics = stats.summarise(result.equity, result.returns)

        ledger.log_trial(
            strategy_name=strategy_cls.name,
            params=strategy.params,
            snapshot_id=snapshot.id,
            start=str(usable.index[0].date()),
            end=str(usable.index[-1].date()),
            cost_bps=cost_bps,
            declared_n=strategy_cls.declared_n(),
            metrics=metrics,
            kind=kind,
            used_holdout=allow_holdout,
            note=note,
        )
        trials.append(TrialResult(params=params, result=result, metrics=metrics))

    # Deflate only after logging, so the correction accounts for the trials this
    # run just consumed. Sharpes span every strategy ever run, because the
    # multiple-testing problem is a property of the whole search.
    all_sharpes = ledger.sharpes(kind="search")
    for trial in trials:
        trial.deflated_sharpe = stats.deflated_sharpe_ratio(trial.result.returns, all_sharpes)

    events = stats.drawdown_events(benchmark.equity, threshold=-0.10)
    best = max(trials, key=lambda t: (t.metrics["max_drawdown"], t.metrics["cagr"]))
    attribution = stats.attribution(best.result.equity, benchmark.equity, events)

    return RunReport(
        strategy_name=strategy_cls.name,
        snapshot=snapshot,
        sample_start=str(usable.index[0].date()),
        sample_end=str(usable.index[-1].date()),
        declared_n=strategy_cls.declared_n(),
        trials_total=ledger.trial_count(),
        used_holdout=allow_holdout,
        benchmark=benchmark,
        benchmark_metrics=benchmark_metrics,
        trials=trials,
        regret=stats.regret(best.result.equity, benchmark.equity),
        attribution=attribution,
    )


def start_date_sweep(
    strategy_cls: type[Strategy],
    prices: pd.DataFrame,
    snapshot: Snapshot,
    start_dates: tuple[str, ...],
    **kwargs: Any,
) -> list[tuple[str, RunReport]]:
    """Re-run from several start dates.

    A single start date is a hidden parameter. If the conclusion depends on
    beginning before 2008, the finding is "2008 happened", not "the rule works".
    """
    kwargs.setdefault("kind", "robustness")  # re-runs of one rule, not a new search
    reports = []
    for start in start_dates:
        window = prices.loc[prices.index >= pd.Timestamp(start)]
        if len(window) < MIN_WINDOW_DAYS:
            continue
        reports.append((start, run_strategy(strategy_cls, window, snapshot, **kwargs)))
    return reports


def cost_sweep(
    strategy_cls: type[Strategy],
    prices: pd.DataFrame,
    snapshot: Snapshot,
    cost_options: tuple[float, ...] = (1.0, 5.0, 10.0, 20.0),
    **kwargs: Any,
) -> list[tuple[float, RunReport]]:
    """Re-run across a range of slippage assumptions.

    A result that dies at 20 bps on liquid ETFs was never real. Tagged as
    robustness: this is one rule under different conditions, not a search.
    """
    kwargs.setdefault("kind", "robustness")
    return [
        (bps, run_strategy(strategy_cls, prices, snapshot, cost_bps=bps, **kwargs))
        for bps in cost_options
    ]
