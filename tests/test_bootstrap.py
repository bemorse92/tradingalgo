"""Bootstrap tests.

Two properties carry the weight. The vectorised statistics must agree *exactly*
with `backtest.stats`, or the interval is drawn around a different quantity than
the point estimate printed inside it. And the resampling must preserve serial
dependence, because these strategies exist because of serial dependence and an
interval that shuffled it away would price a world they were never claimed to
work in.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest import bootstrap, ledger, stats


@pytest.fixture
def returns() -> tuple[pd.Series, pd.Series]:
    """A trending series and a noisier one, with real dates."""
    index = pd.bdate_range("2010-01-04", periods=1500, name="date")
    rng = np.random.default_rng(7)
    strategy = pd.Series(rng.normal(0.0005, 0.008, len(index)), index=index)
    benchmark = pd.Series(rng.normal(0.0003, 0.013, len(index)), index=index)
    return strategy, benchmark


def test_vectorised_metrics_agree_with_stats_exactly(returns):
    """Not approximately. The interval and its point estimate must be one quantity.

    `stats.cagr` measures growth from `equity.iloc[0]`, which already contains the
    first period's return -- a detail easy to get wrong and invisible afterwards,
    because the result still looks like a plausible CAGR.
    """
    series, _ = returns
    years = (series.index[-1] - series.index[0]).days / 365.25
    measured = bootstrap._metrics(series.to_numpy()[None, :], years, stats.TRADING_DAYS)
    equity = (1.0 + series).cumprod()

    assert measured["cagr"][0] == stats.cagr(equity)
    assert measured["max_drawdown"][0] == stats.max_drawdown(equity)
    assert measured["sharpe"][0] == stats.sharpe(series)


def test_resampling_preserves_serial_dependence(returns):
    """The reason for blocks, as a measurement rather than a claim.

    A series with strong autocorrelation must keep most of it after block
    resampling, and lose essentially all of it when resampled one point at a time.
    If this failed, the intervals would be about an independent world.
    """
    index = pd.bdate_range("2010-01-04", periods=2000)
    rng = np.random.default_rng(3)
    values = np.zeros(len(index))
    for i in range(1, len(values)):  # AR(1): dependence by construction
        values[i] = 0.8 * values[i - 1] + rng.normal(0, 0.01)
    series = pd.Series(values, index=index)

    def autocorrelation(sample: np.ndarray) -> float:
        return float(np.corrcoef(sample[:-1], sample[1:])[0, 1])

    generator = np.random.default_rng(0)
    blocked = bootstrap.block_indices(len(series), 40, bootstrap.BLOCK_LENGTH, generator)
    single = bootstrap.block_indices(len(series), 40, 1, generator)

    original = autocorrelation(series.to_numpy())
    with_blocks = np.mean([autocorrelation(series.to_numpy()[row]) for row in blocked])
    without = np.mean([autocorrelation(series.to_numpy()[row]) for row in single])

    assert original > 0.7
    assert with_blocks > 0.6, "block resampling destroyed the dependence it exists to keep"
    assert abs(without) < 0.1, "single-point resampling should leave no dependence"


def test_indices_stay_inside_the_sample(returns):
    """Wrapping is circular, so no index may fall outside the series."""
    series, _ = returns
    picks = bootstrap.block_indices(
        len(series), 50, bootstrap.BLOCK_LENGTH, np.random.default_rng(0)
    )
    assert picks.shape == (50, len(series))
    assert picks.min() >= 0
    assert picks.max() < len(series)


def test_the_same_seed_gives_the_same_interval(returns):
    """Randomness is fine here; irreproducibility is not."""
    strategy, benchmark = returns
    first = bootstrap.confidence(strategy, benchmark, resamples=200)
    second = bootstrap.confidence(strategy, benchmark, resamples=200)
    assert [i.low for i in first.intervals] == [i.low for i in second.intervals]
    assert [i.high for i in first.intervals] == [i.high for i in second.intervals]


def test_the_seed_cannot_change_a_verdict(returns):
    """Resampling noise is real; it must not be large enough to matter.

    The endpoints do move between seeds -- about 0.6pp at the configured resample
    count, which is why they are not worth reading past the first decimal. What
    must not move is whether the interval contains zero, because that is the only
    thing the table actually claims.
    """
    strategy, benchmark = returns
    for name in ("CAGR vs benchmark", "max drawdown vs benchmark", "Sharpe vs benchmark"):
        a = bootstrap.confidence(strategy, benchmark).named(name)
        b = bootstrap.confidence(strategy, benchmark, seed=99).named(name)
        assert a.verdict == b.verdict, name
        assert a.low == pytest.approx(b.low, abs=0.02), name
        assert a.high == pytest.approx(b.high, abs=0.02), name


def test_the_point_estimate_sits_inside_its_interval(returns):
    strategy, benchmark = returns
    for interval in bootstrap.confidence(strategy, benchmark).intervals:
        assert interval.low <= interval.point <= interval.high, interval.name


def test_pairing_narrows_the_difference():
    """Why the two series share one index matrix.

    A strategy and its benchmark are exposed to the same market on the same days,
    which is why the difference between them is far steadier than either one.
    Keeping them aligned through the resampling preserves that; resampling them
    independently would invent variance the comparison does not have.

    The fixture pair used elsewhere in this file is drawn independently, so it has
    no common exposure for pairing to exploit and would show no effect here. This
    one is built the way a real pair is: shared market, small idiosyncratic
    difference.
    """
    index = pd.bdate_range("2010-01-04", periods=1500)
    rng = np.random.default_rng(11)
    market = rng.normal(0.0003, 0.011, len(index))
    benchmark = pd.Series(market, index=index)
    strategy = pd.Series(0.6 * market + rng.normal(0.0002, 0.002, len(index)), index=index)

    paired = bootstrap.confidence(strategy, benchmark).named("CAGR vs benchmark")

    # Break the alignment while leaving both series otherwise untouched.
    misaligned = pd.Series(np.roll(benchmark.to_numpy(), 500), index=index)
    unpaired = bootstrap.confidence(strategy, misaligned).named("CAGR vs benchmark")

    assert paired.width < unpaired.width


def test_a_difference_that_spans_zero_says_so(returns):
    """The verdict wording is the point of the table, so it is asserted."""
    strategy, _ = returns
    identical = bootstrap.confidence(strategy, strategy.copy())
    difference = identical.named("CAGR vs benchmark")

    assert difference.point == pytest.approx(0.0, abs=1e-12)
    assert difference.straddles_zero
    assert difference.verdict == "indistinguishable from zero"


def test_levels_carry_no_verdict(returns):
    """Only differences have a zero that means 'contributed nothing'."""
    strategy, benchmark = returns
    assert bootstrap.confidence(strategy, benchmark).named("CAGR").verdict == ""


def test_block_length_must_be_usable():
    with pytest.raises(ValueError, match="block_length must be at least 1"):
        bootstrap.block_indices(100, 5, 0, np.random.default_rng(0))


def test_sensitivity_reports_one_bundle_per_block_length(returns):
    strategy, benchmark = returns
    bundles = bootstrap.sensitivity(strategy, benchmark, resamples=200)
    assert [b.block_length for b in bundles] == list(bootstrap.SENSITIVITY_BLOCKS)


def test_non_overlapping_series_are_refused(returns):
    """Silently intersecting to nothing would produce an interval about nothing."""
    strategy, _ = returns
    elsewhere = pd.Series([0.01, 0.02], index=pd.to_datetime(["1990-01-02", "1990-01-03"]))
    with pytest.raises(ValueError, match="do not overlap"):
        bootstrap.confidence(strategy, elsewhere)


def test_bootstrapping_logs_no_trials(sandbox, returns):
    """A confidence interval measures a result. It is not a new configuration."""
    strategy, benchmark = returns
    bootstrap.confidence(strategy, benchmark, resamples=100)
    assert ledger.trial_count() == 0
