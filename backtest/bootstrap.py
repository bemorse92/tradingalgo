"""Confidence intervals for results that are currently point estimates.

The project's live claim is that a rule buys a few points of drawdown protection
at roughly no return cost. That is one number from one history containing about
four independent bear markets, and a single number carries no sense of how much of
it is luck. This module attaches an interval to it.

**Why blocks.** The obvious bootstrap -- resample daily returns independently --
is wrong here, and not marginally. These strategies exist because of serial
dependence: volatility clusters, and large drawdowns are slow grinds rather than
gaps. Shuffling returns one at a time destroys exactly the structure under test
and would report a confidence interval for a world the strategy was never claimed
to work in. So blocks of consecutive days are resampled instead, which keeps local
dependence intact.

The scheme is the stationary bootstrap (Politis & Romano, 1994): block lengths are
drawn from a geometric distribution rather than fixed, so the resampled series is
itself stationary and no single block boundary is special.

**Why paired.** The headline claims are *differences* -- this rule against the
benchmark it declared. Resampling the two series independently would add variance
that does not exist, because on any given day both are exposed to the same market.
The same block indices are therefore applied to both, so a resample asks "what if
history had gone differently" rather than "what if these two had been unrelated".

**What this cannot do**, stated plainly because an interval invites more confidence
than it earns:

- A bootstrap quantifies uncertainty in the data you have. It does not manufacture
  new information, and it cannot invent a bear market of a kind never observed.
  Four independent bear markets resampled ten thousand times are still four bear
  markets.
- Drawdown is a *path* statistic, and block resampling chops the long declines that
  produce the worst ones. Level intervals for max drawdown are therefore optimistic
  -- the resampled worst case is usually shallower than the real one. The paired
  *difference* is far less affected, since both series are cut in the same places,
  which is another reason the difference is the number to read.

See design_docs/path_to_trading.md, G4.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import stats

#: Expected block length, in trading days. Fixed a priori at one quarter: long
#: enough to hold a drawdown episode substantially intact, short enough that a
#: fifteen-year sample still contains many independent blocks. Never tuned --
#: `sensitivity` reports the answer across a range instead, because a conclusion
#: that depends on the block length is a conclusion about the block length.
BLOCK_LENGTH = 63

#: Block lengths for the sensitivity report: a month, a quarter, half a year.
SENSITIVITY_BLOCKS = (21, 63, 126)

#: Enough resamples that Monte Carlo noise cannot change a verdict. Measured
#: rather than guessed: across six seeds the endpoints move about 1.8pp at 2,000
#: resamples, 0.6pp at 10,000, and 0.5pp at 20,000. Ten thousand is where the
#: curve flattens, and it runs in about a second. The intervals it produces are
#: ten to forty points wide, so 0.6pp of resampling noise is immaterial to
#: whether one contains zero -- but it is real, and the endpoints should not be
#: read past the first decimal.
RESAMPLES = 10_000

#: Pinned. Randomness is the right tool here, but a result that changes between
#: runs is not a result -- see the design goals in CLAUDE.md.
SEED = 0

#: Two-sided coverage. 90% rather than 95% because the honest message of this
#: module is width, and a 95% interval on four bear markets invites the reader to
#: treat the bounds as real precision.
COVERAGE = 0.90

#: Resamples held in memory at once. The index array is resamples x observations,
#: so the whole run at once would be a few hundred megabytes for no benefit.
_CHUNK = 250


@dataclass(frozen=True)
class Interval:
    """One measured quantity with the range the resampling puts around it."""

    name: str
    point: float
    low: float
    high: float
    #: True when the quantity is a strategy-minus-benchmark difference, where
    #: zero is the value that means "the rule contributed nothing".
    is_difference: bool = False

    @property
    def width(self) -> float:
        return self.high - self.low

    @property
    def straddles_zero(self) -> bool:
        """Whether the interval contains no effect at all."""
        return self.low <= 0.0 <= self.high

    @property
    def verdict(self) -> str:
        """What this interval licenses saying, for a difference.

        Deliberately blunt. An interval spanning zero means the sample cannot
        distinguish the effect from nothing, and saying so in one word is harder
        to read past than a pair of bounds.
        """
        if not self.is_difference:
            return ""
        return "indistinguishable from zero" if self.straddles_zero else "excludes zero"


@dataclass(frozen=True)
class Confidence:
    """Everything one bootstrap produced, with the settings that produced it."""

    block_length: int
    resamples: int
    seed: int
    coverage: float
    intervals: list[Interval] = field(default_factory=list)

    def named(self, name: str) -> Interval | None:
        return next((i for i in self.intervals if i.name == name), None)


# --------------------------------------------------------------------------- #
# Resampling
# --------------------------------------------------------------------------- #


def block_indices(
    observations: int,
    resamples: int,
    block_length: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Stationary-bootstrap index matrix, shape (resamples, observations).

    Each position either continues the current block or starts a new one at a
    random point, with probability 1/block_length. Wrapping at the end of the
    series is what makes the scheme circular, so every observation is equally
    likely to appear regardless of where it sits in the sample.
    """
    if block_length < 1:
        raise ValueError(f"block_length must be at least 1; got {block_length}")

    position = np.arange(observations)
    new_block = rng.random((resamples, observations)) < 1.0 / block_length
    new_block[:, 0] = True  # every resample opens a block

    starts = rng.integers(0, observations, size=(resamples, observations))
    # Index of the most recent block start, carried forward across the row.
    opened_at = np.maximum.accumulate(np.where(new_block, position, -1), axis=1)
    offset = position - opened_at
    return (np.take_along_axis(starts, opened_at, axis=1) + offset) % observations


def _equity(returns: np.ndarray) -> np.ndarray:
    """Equity curves for a matrix of return paths, one path per row."""
    return np.cumprod(1.0 + returns, axis=1)


def _cagr(equity: np.ndarray, years: float) -> np.ndarray:
    # Divided by the first point, not by 1.0: `stats.cagr` measures growth from
    # `equity.iloc[0]`, which already contains the first period's return. Getting
    # this wrong puts the interval around a slightly different quantity than the
    # point estimate printed inside it.
    return (equity[:, -1] / equity[:, 0]) ** (1.0 / years) - 1.0


def _max_drawdown(equity: np.ndarray) -> np.ndarray:
    return (equity / np.maximum.accumulate(equity, axis=1) - 1.0).min(axis=1)


def _sharpe(returns: np.ndarray, periods_per_year: int) -> np.ndarray:
    spread = returns.std(axis=1, ddof=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return returns.mean(axis=1) / spread * np.sqrt(periods_per_year)


def _metrics(returns: np.ndarray, years: float, periods_per_year: int) -> dict[str, np.ndarray]:
    """The three headline statistics, computed the way `stats` computes them.

    Kept as array maths rather than looping over `stats` because two thousand
    resamples of two series is six thousand calls. `tests/test_bootstrap.py`
    asserts these agree with `stats` exactly, so the speed costs no consistency.
    """
    equity = _equity(returns)
    return {
        "cagr": _cagr(equity, years),
        "max_drawdown": _max_drawdown(equity),
        "sharpe": _sharpe(returns, periods_per_year),
    }


def _calendar_years(index: pd.Index, observations: int, periods_per_year: int) -> float:
    """Sample length in years, matching `stats.cagr`'s own convention.

    A resample has the same number of observations as the original and no dates of
    its own, so it inherits the original's calendar span. Without this the interval
    would be built on a slightly different definition of CAGR than the point
    estimate sitting inside it.
    """
    if isinstance(index, pd.DatetimeIndex) and len(index) > 1:
        return (index[-1] - index[0]).days / 365.25
    return observations / periods_per_year


# --------------------------------------------------------------------------- #
# The intervals
# --------------------------------------------------------------------------- #

#: Statistics reported for the strategy alone, and as a difference against the
#: benchmark. The differences are the ones the project's claims are made of.
_METRIC_LABELS = {
    "cagr": "CAGR",
    "max_drawdown": "max drawdown",
    "sharpe": "Sharpe",
}


def confidence(
    strategy_returns: pd.Series,
    benchmark_returns: pd.Series,
    block_length: int = BLOCK_LENGTH,
    resamples: int = RESAMPLES,
    seed: int = SEED,
    coverage: float = COVERAGE,
    periods_per_year: int = stats.TRADING_DAYS,
) -> Confidence:
    """Percentile intervals for the strategy's statistics and its edge over the bar.

    Percentile rather than bias-corrected: the question here is whether an effect
    is distinguishable from zero at all, which is a question about width, and the
    extra machinery would imply a precision the sample cannot support.
    """
    # Inner join, and columns named here rather than inherited: two engine results
    # usually carry the same (or no) name, and duplicate labels would make a later
    # lookup return a frame instead of a series.
    aligned = pd.concat(
        [strategy_returns.rename("strategy"), benchmark_returns.rename("benchmark")],
        axis=1,
        join="inner",
    ).dropna()
    if aligned.empty:
        raise ValueError("Strategy and benchmark returns do not overlap.")

    strategy = aligned["strategy"].to_numpy(dtype=float)
    benchmark = aligned["benchmark"].to_numpy(dtype=float)
    observations = len(strategy)
    years = _calendar_years(aligned.index, observations, periods_per_year)

    rng = np.random.default_rng(seed)
    collected: dict[str, list[np.ndarray]] = {}

    drawn = 0
    while drawn < resamples:
        size = min(_CHUNK, resamples - drawn)
        # One index matrix, applied to both series: the pairing is the point.
        picks = block_indices(observations, size, block_length, rng)
        strategy_metrics = _metrics(strategy[picks], years, periods_per_year)
        benchmark_metrics = _metrics(benchmark[picks], years, periods_per_year)

        for metric, values in strategy_metrics.items():
            collected.setdefault(metric, []).append(values)
            collected.setdefault(f"{metric}_vs_benchmark", []).append(
                values - benchmark_metrics[metric]
            )
        drawn += size

    tail = (1.0 - coverage) / 2.0
    point = _point_estimates(aligned, periods_per_year, years)

    intervals = []
    for metric, label in _METRIC_LABELS.items():
        for key, name, difference in (
            (metric, label, False),
            (f"{metric}_vs_benchmark", f"{label} vs benchmark", True),
        ):
            draws = np.concatenate(collected[key])
            low, high = np.quantile(draws, [tail, 1.0 - tail])
            intervals.append(
                Interval(
                    name=name,
                    point=point[key],
                    low=float(low),
                    high=float(high),
                    is_difference=difference,
                )
            )

    return Confidence(
        block_length=block_length,
        resamples=resamples,
        seed=seed,
        coverage=coverage,
        intervals=intervals,
    )


def _point_estimates(
    aligned: pd.DataFrame, periods_per_year: int, years: float
) -> dict[str, float]:
    """The measured values the intervals are drawn around.

    Taken from `stats`, not recomputed, so the number in the middle of an interval
    is the same number the rest of the report prints.
    """
    out: dict[str, float] = {}
    curves = {}
    for side in ("strategy", "benchmark"):
        returns = aligned[side]
        equity = (1.0 + returns).cumprod()
        curves[side] = {
            "cagr": stats.cagr(equity, periods_per_year),
            "max_drawdown": stats.max_drawdown(equity),
            "sharpe": stats.sharpe(returns, periods_per_year=periods_per_year),
        }
    for metric in _METRIC_LABELS:
        out[metric] = curves["strategy"][metric]
        out[f"{metric}_vs_benchmark"] = curves["strategy"][metric] - curves["benchmark"][metric]
    return out


def sensitivity(
    strategy_returns: pd.Series,
    benchmark_returns: pd.Series,
    blocks: Sequence[int] = SENSITIVITY_BLOCKS,
    **kwargs: object,
) -> list[Confidence]:
    """The same intervals across a range of block lengths.

    Block length is a hidden parameter in exactly the way a start date is, and the
    project's answer to hidden parameters is to show the neighbourhood rather than
    a single point. If the verdict flips between a month and a quarter, the finding
    is about the block length.
    """
    return [
        confidence(strategy_returns, benchmark_returns, block_length=block, **kwargs)  # type: ignore[arg-type]
        for block in blocks
    ]
