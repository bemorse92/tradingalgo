"""Look-ahead detection tests.

The second test here is the one that matters: it proves the check actually catches
peeking, rather than passing everything it is ever shown.
"""

from __future__ import annotations

import pytest

from backtest import validate
from tests.conftest import HonestTrend, PeekingTrend


def test_honest_strategy_passes(prices):
    validate.assert_no_lookahead(HonestTrend(lookback=40), prices)


def test_peeking_strategy_is_caught(prices):
    """A centred rolling mean reads forward. The check must refuse it."""
    with pytest.raises(validate.LookAheadError, match="leaks future data"):
        validate.assert_no_lookahead(PeekingTrend(), prices)


def test_missing_prereg_blocks_the_run(prices):
    with pytest.raises(validate.PreRegistrationError, match="No pre-registration"):
        validate.require_prereg(HonestTrend())


def test_holdout_is_inert_until_configured(prices):
    """HOLDOUT_START is still undecided; the gate must not silently truncate."""
    assert validate.HOLDOUT_START is None
    assert len(validate.apply_holdout(prices)) == len(prices)


def test_holdout_truncates_when_configured(prices, monkeypatch):
    cut = prices.index[500]
    monkeypatch.setattr(validate, "HOLDOUT_START", str(cut.date()))

    withheld = validate.apply_holdout(prices)
    assert withheld.index[-1] < cut
    assert len(validate.apply_holdout(prices, allow_holdout=True)) == len(prices)
