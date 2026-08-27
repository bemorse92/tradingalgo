"""Performance and honesty statistics.

Written by hand rather than pulled from a library so every formula is visible and
unit-testable; the test suite cross-checks the conventional metrics against `ffn`
as an oracle.

The second half of this module is the part that matters most. A Sharpe ratio with
no trial count attached is not evidence: after 1,000 independent backtests the
expected maximum Sharpe is 3.26 even when every strategy tested is worthless. The
deflated Sharpe ratio prices that in. See design_docs/research_guardrails.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import norm

TRADING_DAYS = 252
EULER_MASCHERONI = 0.5772156649015329

_MIN_POINTS = 2  # fewest points that define a growth rate
_MIN_OBSERVATIONS = 3  # fewest returns for a usable moment estimate
_MIN_TRIALS = 2  # fewest trials with a definable spread
_EPSILON = 1e-12


# --------------------------------------------------------------------------- #
# Conventional performance metrics
# --------------------------------------------------------------------------- #


def cagr(equity: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    """Compound annual growth rate, on calendar years where dates are available."""
    if len(equity) < _MIN_POINTS:
        return float("nan")
    if isinstance(equity.index, pd.DatetimeIndex):
        years = (equity.index[-1] - equity.index[0]).days / 365.25
    else:
        years = len(equity) / periods_per_year
    if years <= 0:
        return float("nan")
    growth = equity.iloc[-1] / equity.iloc[0]
    return float(growth ** (1.0 / years) - 1.0)


def drawdown_series(equity: pd.Series) -> pd.Series:
    """Fractional drawdown from the running peak, at every date."""
    return equity / equity.cummax() - 1.0


def max_drawdown(equity: pd.Series) -> float:
    """Worst peak-to-trough decline. Negative."""
    return float(drawdown_series(equity).min())


def annual_volatility(returns: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    return float(returns.std(ddof=1) * math.sqrt(periods_per_year))


def sharpe(
    returns: pd.Series,
    risk_free: float = 0.0,
    periods_per_year: int = TRADING_DAYS,
) -> float:
    """Annualised Sharpe ratio. `risk_free` is a per-period rate."""
    excess = returns - risk_free
    sd = excess.std(ddof=1)
    if sd == 0 or np.isnan(sd):
        return float("nan")
    return float(excess.mean() / sd * math.sqrt(periods_per_year))


def sharpe_per_period(returns: pd.Series, risk_free: float = 0.0) -> float:
    """Un-annualised Sharpe. The PSR/DSR formulas below require this convention."""
    excess = returns - risk_free
    sd = excess.std(ddof=1)
    if sd == 0 or np.isnan(sd):
        return float("nan")
    return float(excess.mean() / sd)


# --------------------------------------------------------------------------- #
# Drawdown events and per-event attribution
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class DrawdownEvent:
    """One peak-to-trough-to-recovery episode."""

    peak: pd.Timestamp
    trough: pd.Timestamp
    recovery: pd.Timestamp | None
    depth: float

    @property
    def recovered(self) -> bool:
        return self.recovery is not None


def drawdown_events(equity: pd.Series, threshold: float = -0.10) -> list[DrawdownEvent]:
    """Distinct drawdown episodes at least `threshold` deep, worst first.

    The success bar for this project is drawdown reduction, and the literature's
    clearest warning is that such an edge is often one event in disguise. Reporting
    per-event is how that stays visible.
    """
    dd = drawdown_series(equity)
    underwater = dd < -_EPSILON

    events: list[DrawdownEvent] = []
    start: int | None = None
    for i, wet in enumerate(underwater.to_numpy()):
        if wet and start is None:
            start = i
        elif not wet and start is not None:
            events.append(_build_event(dd, start, i))
            start = None
    if start is not None:
        events.append(_build_event(dd, start, None))

    deep = [e for e in events if e.depth <= threshold]
    return sorted(deep, key=lambda e: e.depth)


def _build_event(dd: pd.Series, start: int, end: int | None) -> DrawdownEvent:
    window = dd.iloc[start:end] if end is not None else dd.iloc[start:]
    peak_idx = max(start - 1, 0)
    return DrawdownEvent(
        peak=dd.index[peak_idx],
        trough=window.idxmin(),
        recovery=dd.index[end] if end is not None else None,
        depth=float(window.min()),
    )


def attribution(
    strategy_equity: pd.Series,
    benchmark_equity: pd.Series,
    events: list[DrawdownEvent],
) -> pd.DataFrame:
    """Compare strategy and benchmark across each *benchmark* drawdown event.

    Events are defined on the benchmark because the claim under test is "this rule
    reduces drawdown relative to buy-and-hold", so the benchmark's bad periods are
    the ones that decide it.
    """
    rows = []
    for event in events:
        window = slice(event.peak, event.trough)
        strat = strategy_equity.loc[window]
        bench = benchmark_equity.loc[window]
        if strat.empty or bench.empty:
            continue
        strat_ret = float(strat.iloc[-1] / strat.iloc[0] - 1.0)
        bench_ret = float(bench.iloc[-1] / bench.iloc[0] - 1.0)
        rows.append(
            {
                "peak": event.peak.date(),
                "trough": event.trough.date(),
                "benchmark_dd": bench_ret,
                "strategy_dd": strat_ret,
                "protection": strat_ret - bench_ret,
                "recovered": event.recovered,
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Multiple-testing corrections
# --------------------------------------------------------------------------- #


def expected_max_sharpe(n_trials: int, sharpe_variance: float) -> float:
    """Expected maximum Sharpe across `n_trials` worthless strategies.

    Bailey & Lopez de Prado. This is the null that a candidate must beat: with
    n=1000 and unit variance across trials it returns ~3.26, meaning a Sharpe of
    3.26 found after a thousand tries is exactly what pure noise predicts.
    """
    if n_trials <= 1 or sharpe_variance <= 0:
        return 0.0
    z1 = norm.ppf(1.0 - 1.0 / n_trials)
    z2 = norm.ppf(1.0 - 1.0 / (n_trials * math.e))
    spread = math.sqrt(sharpe_variance)
    return float(spread * ((1.0 - EULER_MASCHERONI) * z1 + EULER_MASCHERONI * z2))


def probabilistic_sharpe_ratio(returns: pd.Series, benchmark_sharpe: float = 0.0) -> float:
    """Probability the true (per-period) Sharpe exceeds `benchmark_sharpe`.

    Corrects for track-record length, skewness and fat tails -- all three of which
    inflate a naive Sharpe.
    """
    n = len(returns)
    if n < _MIN_OBSERVATIONS:
        return float("nan")
    sr = sharpe_per_period(returns)
    if math.isnan(sr):
        return float("nan")
    skew = float(returns.skew())
    kurt = float(returns.kurtosis()) + 3.0  # pandas reports excess kurtosis
    denom = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr**2
    if denom <= 0:
        return float("nan")
    return float(norm.cdf((sr - benchmark_sharpe) * math.sqrt(n - 1) / math.sqrt(denom)))


def deflated_sharpe_ratio(returns: pd.Series, trial_sharpes: list[float] | np.ndarray) -> float:
    """Probability the strategy is genuinely better than nothing, given the search.

    `trial_sharpes` should be every *annualised* Sharpe produced while searching --
    which is exactly what the trial ledger records. Both the number of trials and
    their spread matter, so this cannot be computed from the winner alone.
    """
    trials = np.asarray([s for s in np.asarray(trial_sharpes, dtype=float) if np.isfinite(s)])
    if trials.size < _MIN_TRIALS:
        return float("nan")
    # Convert the trial distribution to per-period units to match the PSR formula.
    variance = float(np.var(trials, ddof=1)) / TRADING_DAYS
    threshold = expected_max_sharpe(trials.size, variance)
    return probabilistic_sharpe_ratio(returns, benchmark_sharpe=threshold)


def min_track_record_length(
    returns: pd.Series,
    benchmark_sharpe: float = 0.0,
    confidence: float = 0.95,
) -> float:
    """Observations needed to conclude the Sharpe beats `benchmark_sharpe`.

    Routinely returns numbers longer than a human lifetime, which is the honest
    reason live results cannot validate a strategy on any relevant horizon.
    """
    n = len(returns)
    if n < _MIN_OBSERVATIONS:
        return float("nan")
    sr = sharpe_per_period(returns)
    if math.isnan(sr) or sr <= benchmark_sharpe:
        return float("inf")
    skew = float(returns.skew())
    kurt = float(returns.kurtosis()) + 3.0
    numerator = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr**2
    z = norm.ppf(confidence)
    return float(1.0 + numerator * (z / (sr - benchmark_sharpe)) ** 2)


def summarise(result_equity: pd.Series, result_returns: pd.Series) -> dict[str, float]:
    """The standard metric bundle for one run."""
    return {
        "cagr": cagr(result_equity),
        "volatility": annual_volatility(result_returns),
        "sharpe": sharpe(result_returns),
        "max_drawdown": max_drawdown(result_equity),
        "final_equity": float(result_equity.iloc[-1]),
    }
