"""Reproduction tests: the harness checked against an outside source.

Every other test in this suite checks a part against our own expectations. These
check the whole path -- data, weights, lag, equity, statistics -- against numbers
someone else published before this project existed. That makes them the only tests
here that can catch a mistake we and our unit tests share.

They also make the reproduction permanent. Running it once proves the harness was
right on the day; running it as a test proves it stays right.
"""

from __future__ import annotations

import pandas as pd
import pytest

from backtest import engine, ledger, reproduce, stats

#: Digests of the pinned reference data as committed. If these move, the data
#: underneath the reproduction moved, and every figure it reports is about a
#: different series than the one the results were recorded against.
SHILLER_CHECKSUM = "6673f39e802653da"
SPY_CHECKSUM = "3986b8e7a49fdd8f"


@pytest.fixture(scope="module")
def faber() -> reproduce.Reproduction:
    return reproduce.reproduce_faber()


def test_no_check_fails_without_an_explanation(faber):
    """The headline assertion: nothing disagrees for a reason we cannot name.

    A gap outside tolerance is only acceptable if the module says why. This is
    what would break if the engine's lag, the equity curve or the drawdown maths
    were changed.
    """
    failures = [c.name for c in faber.checks if c.status == "FAIL"]
    assert not failures, f"unexplained disagreement with published figures: {failures}"


def test_buy_and_hold_reproduces_the_published_century(faber):
    """The cleanest check in the project: no signal, no cash, no parameters.

    Buy and hold over 1901-2012 exercises data loading, the engine and the
    statistics and nothing else, so a match here corroborates that path directly.
    """
    by_name = {c.name: c for c in faber.checks}
    assert by_name["buy & hold, compound return"].status == "MATCH"
    assert by_name["buy & hold, mean annual return"].status == "MATCH"


def test_signal_dates_match_the_ones_faber_names(faber):
    """A statistic can agree for the wrong reasons; a named month cannot."""
    for claim, expected, actual in reproduce.reproduce_signal_dates():
        assert expected == actual, claim


def test_reproduction_logs_no_trials(sandbox, faber):
    """A reproduction is a check on the machinery, not a search for a strategy.

    If it counted as a trial it would deflate every real result for the crime of
    validating the harness.
    """
    reproduce.reproduce_faber()
    reproduce.sampling_sensitivity()
    assert ledger.trial_count() == 0


def test_sampling_alone_moves_the_timing_result():
    """The two EXPLAINED gaps rest on this being a real effect, not an excuse.

    Both conventions are built from one daily SPY series, so the difference
    between them is caused by sampling and by nothing else.
    """
    sensitivity = reproduce.sampling_sensitivity()
    assert sensitivity.verdict == "MATCH"
    assert any("swing caused by sampling alone" in n for n in sensitivity.notes)


def test_the_reproduction_would_catch_a_broken_lag():
    """A check that has never caught anything is not known to work.

    Feed the engine weights that act on the *next* month's signal -- the shape of
    an off-by-one in the lag -- and the reproduction must stop agreeing with
    Faber. If this passes, the checks above are not discriminating and mean
    nothing.
    """
    prices = reproduce._shiller_prices(0.0)
    honest = reproduce.faber_weights(prices, "SP500", "CASH")
    peeking = honest.shift(-1).fillna(0.0)  # tomorrow's decision, taken today

    published = -0.4224
    tolerance = 0.03
    for label, weights in (("honest", honest), ("peeking", peeking)):
        result = engine.run(prices, weights, cost_bps=0.0)
        drawdown = reproduce.drawdown_within(result.equity, *reproduce.CRASH_WINDOW)
        agrees = abs(drawdown - published) <= tolerance
        assert agrees is (label == "honest"), (
            f"{label} run: drawdown {drawdown:.4f} vs published {published}"
        )


def test_pinned_reference_data_has_not_moved():
    """The reproduction must be reproducible, which means the inputs are pinned.

    Shiller and Ken French both revise their files. A reproduction that silently
    re-downloads is not one, so the data is committed and its digest asserted.
    """
    assert reproduce.checksum(reproduce.load_shiller()) == SHILLER_CHECKSUM
    assert reproduce.checksum(reproduce.load_spy()) == SPY_CHECKSUM


def test_the_faber_rule_cannot_see_the_future():
    """The same corruption test every strategy has to pass, applied to the rule.

    The reproduction runs outside the `Strategy` contract, so it does not get the
    validator's look-ahead check for free. It still has to earn it.
    """
    prices = reproduce._shiller_prices(0.0)
    baseline = reproduce.faber_weights(prices, "SP500", "CASH")

    rng = pd.Series(range(len(prices)), index=prices.index)
    cut = len(prices) // 2
    corrupted = prices.copy()
    corrupted.iloc[cut + 1 :] *= 1.0 + (rng.iloc[cut + 1 :].to_numpy()[:, None] % 7) / 10.0

    after = reproduce.faber_weights(corrupted, "SP500", "CASH")
    pd.testing.assert_frame_equal(baseline.iloc[: cut + 1], after.iloc[: cut + 1])


def test_monthly_statistics_are_annualised_by_months_not_days():
    """Twelve, not 252. Getting this wrong would silently rescale every figure."""
    equity = pd.Series(
        [1.0 * 1.01**i for i in range(12 * 10 + 1)],
        index=pd.date_range("2000-01-31", periods=12 * 10 + 1, freq="ME"),
    )
    assert stats.cagr(equity, reproduce.MONTHS_PER_YEAR) == pytest.approx(0.1268, abs=1e-3)
