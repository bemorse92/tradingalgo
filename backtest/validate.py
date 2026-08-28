"""Structural checks that run before a strategy is allowed to produce a result.

The premise of this project is that guardrails depending on the researcher's good
intentions do not work. Everything here is mechanical.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import ledger
from .strategy import Strategy

STRATEGY_DIR = Path(__file__).resolve().parent.parent / "strategies"

#: Date from which data is reserved and must not inform strategy development.
#: Reserves 2023 onward (~17% of the sample). In-sample keeps 2008, 2015, 2018,
#: 2020 and 2022 to develop against; the holdout keeps the 2025 drawdown unseen.
HOLDOUT_START: str | None = "2023-01-01"

_TOLERANCE = 1e-12


class LookAheadError(AssertionError):
    """Raised when a strategy's past decisions depend on future prices."""


class PreRegistrationError(FileNotFoundError):
    """Raised when a strategy has no committed pre-registration."""


def assert_no_lookahead(
    strategy: Strategy,
    prices: pd.DataFrame,
    cut_fractions: tuple[float, ...] = (0.4, 0.6, 0.8),
    seed: int = 0,
) -> None:
    """Prove the strategy cannot see the future.

    Corrupt every price after a cut date and re-run. Weights on or before the cut
    must be bit-identical: they were decided using only data that existed then. If
    they move, the strategy is reading ahead.

    This is cheap because it runs once per strategy, not once per backtest.
    """
    rng = np.random.default_rng(seed)
    baseline = strategy.weights(prices)

    for fraction in cut_fractions:
        cut_pos = int(len(prices) * fraction)
        cut_date = prices.index[cut_pos]

        corrupted = prices.copy()
        tail = corrupted.iloc[cut_pos + 1 :]
        noise = rng.uniform(0.5, 1.5, size=tail.shape)
        corrupted.iloc[cut_pos + 1 :] = tail.to_numpy() * noise

        after = strategy.weights(corrupted)
        left = baseline.loc[:cut_date].fillna(0.0)
        right = after.reindex_like(baseline).loc[:cut_date].fillna(0.0)

        if not np.allclose(left.to_numpy(), right.to_numpy(), rtol=0, atol=_TOLERANCE):
            diff = (left - right).abs().sum(axis=1)
            first = diff[diff > _TOLERANCE].index[0]
            raise LookAheadError(
                f"{strategy!r} leaks future data: corrupting prices after "
                f"{cut_date.date()} changed the weights held on {first.date()}. "
                "Weights must depend only on prices up to and including their own date."
            )


def require_prereg(strategy: Strategy) -> Path:
    """A strategy may not produce a result without a pre-registration on disk.

    Git history is what makes this meaningful: a pre-registration whose commit
    postdates the result is not a pre-registration.
    """
    path = STRATEGY_DIR / f"{strategy.name}.prereg.md"
    if not path.exists():
        raise PreRegistrationError(
            f"No pre-registration for {strategy.name!r} at {path}. Write and commit it "
            "before the first backtest: rationale, rule, parameters, sample, success "
            "criteria, prediction."
        )
    return path


def apply_holdout(prices: pd.DataFrame, allow_holdout: bool = False) -> pd.DataFrame:
    """Truncate the reserved period unless it is explicitly requested.

    Every deliberate access is logged by the caller, because a holdout consulted
    three times is not a holdout.
    """
    if HOLDOUT_START is None or allow_holdout:
        return prices
    return prices.loc[prices.index < pd.Timestamp(HOLDOUT_START)]


def prepare(
    strategy: Strategy,
    prices: pd.DataFrame,
    allow_holdout: bool = False,
    force_holdout: bool = False,
    check_lookahead: bool = True,
) -> pd.DataFrame:
    """Run every pre-flight check and return the price frame the run may use."""
    guard_holdout(type(strategy).name, allow_holdout, force=force_holdout)
    require_prereg(strategy)
    usable = apply_holdout(prices, allow_holdout=allow_holdout)
    if check_lookahead:
        assert_no_lookahead(strategy, usable)
    return usable


class HoldoutExhaustedError(RuntimeError):
    """Raised when a strategy's holdout has already been consumed."""


def guard_holdout(strategy_name: str, allow_holdout: bool, force: bool = False) -> None:
    """Refuse a second look at the reserved period.

    A holdout consulted twice is not a holdout, and there is no second one. Until
    now this depended entirely on the researcher remembering -- which is exactly
    the kind of guardrail the project's own research says does not hold.
    """
    if not allow_holdout:
        return

    prior = ledger.holdout_uses(strategy_name)
    if prior.empty or force:
        return

    when = prior["timestamp"].iloc[0]
    raise HoldoutExhaustedError(
        f"The holdout for {strategy_name!r} was already consumed on {when} "
        f"({len(prior)} prior access(es)). A second look does not produce a second "
        "out-of-sample test -- it produces an in-sample one you have not admitted to. "
        "If you genuinely intend to override this, pass --force-holdout; the access "
        "is recorded in the ledger either way."
    )
