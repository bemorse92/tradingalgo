"""Success criteria, declared as data and graded mechanically.

Hand-grading a result against a prose pre-registration is where goalpost drift
gets in: the metrics are right there, the criteria are a paragraph away, and the
comparison happens in the researcher's head. Declaring criteria as data on the
strategy means the harness returns a verdict the researcher did not choose.

Thresholds are fractions, not percentage points: 0.10 means ten percentage points
of drawdown, and -0.02 means "no more than two points of CAGR below benchmark".
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:  # pragma: no cover
    from .runner import TrialResult

#: Metrics resolved against the benchmark rather than in absolute terms. A
#: `_vs_benchmark` suffix on any summarised metric yields (strategy - benchmark).
BENCHMARK_SUFFIX = "_vs_benchmark"

#: Metrics derived from the per-event attribution table rather than from one
#: trial's summary. These only make sense for the reported best trial.
ATTRIBUTION_METRICS = frozenset({"positive_protection_events", "largest_protection_share"})

#: Boundaries are inclusive by intent, so comparisons carry a tolerance. Without
#: it, "no more than 2pp below" fails at exactly 2pp below, because 0.0615-0.0815
#: is -0.020000000000000004 in binary floating point. A verdict must not hinge on
#: the sixteenth decimal place.
_BOUNDARY_TOLERANCE = 1e-9

COMPARISONS = {
    "at_least": lambda value, threshold: value >= threshold - _BOUNDARY_TOLERANCE,
    "at_most": lambda value, threshold: value <= threshold + _BOUNDARY_TOLERANCE,
}

SCOPES = frozenset({"best", "all_trials"})


class CriterionError(ValueError):
    """Raised when a criterion is declared in a form the harness cannot grade."""


@dataclass(frozen=True)
class Criterion:
    """One pre-registered pass/fail test.

    `scope="all_trials"` requires every point in the parameter grid to satisfy the
    test, which is how a plateau requirement is expressed: an improvement that
    appears at only one parameter value is fitted to noise.
    """

    name: str
    metric: str
    threshold: float
    comparison: str = "at_least"
    scope: str = "best"

    def __post_init__(self) -> None:
        if self.comparison not in COMPARISONS:
            raise CriterionError(
                f"{self.name!r}: unknown comparison {self.comparison!r}; "
                f"expected one of {sorted(COMPARISONS)}"
            )
        if self.scope not in SCOPES:
            raise CriterionError(
                f"{self.name!r}: unknown scope {self.scope!r}; expected one of {sorted(SCOPES)}"
            )
        if self.scope == "all_trials" and self.metric in ATTRIBUTION_METRICS:
            raise CriterionError(
                f"{self.name!r}: {self.metric!r} is derived from the attribution table, "
                "which is built for the reported trial only, so scope must be 'best'."
            )


@dataclass(frozen=True)
class CriterionResult:
    """How one criterion actually came out."""

    criterion: Criterion
    value: float
    passed: bool

    @property
    def name(self) -> str:
        return self.criterion.name


def _attribution_value(metric: str, attribution: pd.DataFrame) -> float:
    if attribution.empty:
        return 0.0
    protection = attribution["protection"]
    if metric == "positive_protection_events":
        return float((protection > 0).sum())
    # Share of total protection contributed by the single largest event. High
    # values mean the edge is one event wearing a costume.
    positive = protection[protection > 0]
    total = float(positive.sum())
    return float(positive.max() / total) if total > 0 else 0.0


def _trial_value(metric: str, trial: TrialResult, benchmark: dict[str, float]) -> float:
    if metric.endswith(BENCHMARK_SUFFIX):
        base = metric[: -len(BENCHMARK_SUFFIX)]
        if base not in trial.metrics:
            raise CriterionError(f"Unknown metric {base!r}; have {sorted(trial.metrics)}")
        return float(trial.metrics[base] - benchmark[base])
    if metric not in trial.metrics:
        raise CriterionError(f"Unknown metric {metric!r}; have {sorted(trial.metrics)}")
    return float(trial.metrics[metric])


def evaluate(
    criteria: Sequence[Criterion],
    trials: Sequence[TrialResult],
    best: TrialResult,
    benchmark_metrics: dict[str, float],
    attribution: pd.DataFrame,
) -> list[CriterionResult]:
    """Grade every declared criterion. No criterion may be skipped."""
    results: list[CriterionResult] = []
    for criterion in criteria:
        passes = COMPARISONS[criterion.comparison]

        if criterion.metric in ATTRIBUTION_METRICS:
            value = _attribution_value(criterion.metric, attribution)
        elif criterion.scope == "all_trials":
            # Report the weakest trial: if the worst point in the grid clears the
            # bar, every point does.
            values = [_trial_value(criterion.metric, t, benchmark_metrics) for t in trials]
            value = min(values) if criterion.comparison == "at_least" else max(values)
        else:
            value = _trial_value(criterion.metric, best, benchmark_metrics)

        results.append(
            CriterionResult(
                criterion=criterion,
                value=value,
                passed=bool(passes(value, criterion.threshold)),
            )
        )
    return results


def verdict(results: Sequence[CriterionResult]) -> str:
    """PASS only if every criterion passes. Partial credit is not a thing here."""
    if not results:
        return "UNGRADED"
    return "PASS" if all(r.passed for r in results) else "FAIL"


def describe(criterion: Criterion) -> str:
    """Human-readable restatement of the test, for the report."""
    direction = "at least" if criterion.comparison == "at_least" else "at most"
    scope = " (every trial)" if criterion.scope == "all_trials" else ""
    return f"{criterion.metric} {direction} {criterion.threshold:g}{scope}"


def as_dict(results: Sequence[CriterionResult]) -> dict[str, Any]:
    """Flat form for the ledger."""
    return {r.name: r.passed for r in results}
