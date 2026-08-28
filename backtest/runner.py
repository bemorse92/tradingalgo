"""Orchestration: pre-flight checks, sweep the declared grid, log every trial.

Nothing here is optional or skippable from a strategy's side. A run either passes
validation and is recorded, or it does not happen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from . import benchmarks as benchmarks_mod
from . import criteria as criteria_mod
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
    #: The benchmark the strategy declared, resolved out of the slate below. Every
    #: `_vs_benchmark` criterion, the per-event attribution and the regret bundle
    #: are all measured against this one -- and it was named in the strategy's
    #: pre-registration, before any of these numbers existed.
    graded_benchmark: benchmarks_mod.Benchmark
    #: The full slate (buy & hold, exposure-matched, 60/40, cash, ...). The rest
    #: are diagnostic: they say what else the rule could have lost to, but only
    #: the declared one can produce a FAIL.
    benchmarks: list[benchmarks_mod.Benchmark] = field(default_factory=list)
    trials: list[TrialResult] = field(default_factory=list)
    attribution: pd.DataFrame = field(default_factory=pd.DataFrame)
    regret: dict[str, float] = field(default_factory=dict)
    criteria: list[criteria_mod.CriterionResult] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        """PASS only if every pre-registered criterion passes."""
        return criteria_mod.verdict(self.criteria)

    @property
    def benchmark(self) -> engine.Result:
        return self.graded_benchmark.result

    @property
    def benchmark_metrics(self) -> dict[str, float]:
        return self.graded_benchmark.metrics

    @property
    def vol_matched(self) -> benchmarks_mod.Benchmark | None:
        """The static mix carrying the same risk with no signal.

        Section H's claim is that this, not buy-and-hold, is the bar that decides
        whether the rule contributed anything.
        """
        return next((b for b in self.benchmarks if b.key == benchmarks_mod.VOL_MATCHED), None)

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
    risk_asset: str = "SPY",
    kind: str = "search",
    allow_holdout: bool = False,
    force_holdout: bool = False,
    note: str = "",
) -> RunReport:
    """Validate, sweep the grid, log every trial, and return the report."""
    # Pre-flight on a representative instance: pre-registration must exist, the
    # holdout is truncated unless explicitly requested, and the strategy must
    # demonstrably not read ahead.
    probe = strategy_cls()
    usable = validate.prepare(
        probe, prices, allow_holdout=allow_holdout, force_holdout=force_holdout
    )
    # The declared benchmark is checked here rather than after the sweep: a run
    # that discovers its own bar is unbuildable has already spent ledger entries.
    benchmarks_mod.require(usable, strategy_cls.benchmark, risk_asset=risk_asset)

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

    best = max(trials, key=lambda t: (t.metrics["max_drawdown"], t.metrics["cagr"]))

    # The slate is built after the sweep because two of its members are matched to
    # the strategy's own realised risk and exposure. The declared benchmark is then
    # picked out of it by key -- never chosen by looking at which one it beats.
    slate = benchmarks_mod.build(usable, best.result, cost_bps=cost_bps, risk_asset=risk_asset)
    graded = benchmarks_mod.resolve(slate, strategy_cls.benchmark)

    events = stats.drawdown_events(graded.result.equity, threshold=-0.10)
    attribution = stats.attribution(best.result.equity, graded.result.equity, events)

    return RunReport(
        strategy_name=strategy_cls.name,
        snapshot=snapshot,
        sample_start=str(usable.index[0].date()),
        sample_end=str(usable.index[-1].date()),
        declared_n=strategy_cls.declared_n(),
        trials_total=ledger.trial_count(),
        used_holdout=allow_holdout,
        graded_benchmark=graded,
        benchmarks=slate,
        trials=trials,
        regret=stats.regret(best.result.equity, graded.result.equity),
        attribution=attribution,
        criteria=criteria_mod.evaluate(
            strategy_cls.criteria, trials, best, graded.metrics, attribution
        ),
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
