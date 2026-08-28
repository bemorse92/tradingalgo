"""The benchmarks a strategy has to beat before it has contributed anything.

Buy-and-hold SPY is the right primary comparison, but on its own it is too easy:
it flatters any rule that simply holds less equity. `sma_trend` runs at 12.4%
volatility against SPY's 20.7% -- it is, in effect, a 60%-equity portfolio. So
the honest question is not "does it beat 100% SPY" but "does it beat statically
holding 60% SPY and 40% cash": a portfolio needing no signal, no timing and no
discipline. If a static mix matches the rule, the signal contributed nothing and
the whole result is explained by holding less stock.

Every benchmark here runs through `engine.run`, so it pays the same costs, takes
the same one-bar lag, and is measured by the same statistics as the strategy.
That symmetry is the point; a benchmark held to a different standard is not a
benchmark.

Two honest caveats, both in the conservative direction -- they make the bar for
the strategy harder, not easier:

- The engine models *target weights*, not share counts, so a constant-weight
  benchmark keeps its weights without paying drift-rebalancing costs.
- The matched mixes are built from the strategy's *realised* exposure, which is
  only knowable after the fact. They answer "was the signal worth anything, given
  how much equity it ended up holding", not "what could have been chosen in
  advance".

Which of these a strategy is *graded* against is part of its pre-registration --
declared as a key on the strategy, checked before the run, and never chosen from
this slate after the numbers exist. That is what stops the matched comparison
from being a table nobody has to answer to.

See design_docs/path_to_trading.md, section H.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import pandas as pd
from scipy.optimize import brentq

from . import engine, stats
from .util import rebalance

#: Trailing window for the inverse-volatility benchmark. Fixed a priori and never
#: swept: this is a yardstick, not a candidate, so it gets no search budget.
INVERSE_VOL_LOOKBACK = 60

#: Weight tolerance for the volatility match. Finer than this is false precision:
#: realised volatility is itself a noisy estimate.
_SOLVER_TOLERANCE = 1e-4

#: Stable identifiers a strategy may declare as the benchmark its criteria are
#: graded against.
#:
#: These are keys, not display names, and the distinction is load-bearing: two of
#: the benchmarks below are matched to the strategy's *own realised behaviour*, so
#: their composition ("vol-matched 60%/40% SPY/BIL") is not knowable until the run
#: is over. Declaring one therefore pre-commits the method of construction rather
#: than a fixed portfolio. That is still a real commitment -- the method is fixed
#: in advance and nothing can be chosen from the slate afterwards -- but it is a
#: weaker one than naming 60/40 outright, and the difference is worth knowing when
#: reading a verdict.
BUY_AND_HOLD = "buy_and_hold"
VOL_MATCHED = "vol_matched"
EXPOSURE_MATCHED = "exposure_matched"
SIXTY_FORTY = "sixty_forty"
EQUAL_WEIGHT = "equal_weight"
INVERSE_VOL = "inverse_vol"
CASH = "cash"

#: What declaring each key commits a strategy to being measured against.
KEYS: Mapping[str, str] = {
    BUY_AND_HOLD: "100% of the risk asset -- the naive comparison",
    VOL_MATCHED: "static risk-asset/cash mix at the strategy's realised volatility",
    EXPOSURE_MATCHED: "static mix at the strategy's average risk-asset weight",
    SIXTY_FORTY: "60/40 risk asset and bonds",
    EQUAL_WEIGHT: "equal weight across the risky basket",
    INVERSE_VOL: "the risky basket weighted by inverse trailing volatility",
    CASH: "100% cash -- the cost of never taking the risk at all",
}

#: Keys whose composition is derived from the strategy's own realised behaviour,
#: and so pre-commit a method rather than a portfolio.
MATCHED_KEYS = frozenset({VOL_MATCHED, EXPOSURE_MATCHED})


class BenchmarkUnavailableError(LookupError):
    """Raised when a declared benchmark cannot be built from the snapshot."""


@dataclass(frozen=True)
class Benchmark:
    """One alternative to the strategy, run through the same engine.

    `key` is the stable identifier a strategy declares; `name` is the display
    form, which for the matched mixes carries weights only knowable after the run.
    """

    key: str
    name: str
    meaning: str
    result: engine.Result
    metrics: dict[str, float]


def static(
    prices: pd.DataFrame,
    weights: Mapping[str, float],
    cost_bps: float = engine.DEFAULT_COST_BPS,
) -> engine.Result:
    """A constant-weight portfolio: no signal, no timing, no discipline."""
    frame = pd.DataFrame(0.0, index=prices.index, columns=list(weights))
    for ticker, weight in weights.items():
        frame[ticker] = float(weight)
    return engine.run(prices, frame, cost_bps=cost_bps)


def inverse_volatility(
    prices: pd.DataFrame,
    tickers: Sequence[str],
    cash: str | None = None,
    lookback: int = INVERSE_VOL_LOOKBACK,
    cost_bps: float = engine.DEFAULT_COST_BPS,
) -> engine.Result:
    """Risk-parity-ish weighting: each asset weighted by 1 / trailing volatility.

    Restricted to risky assets. Including a cash sleeve makes this degenerate --
    BIL's near-zero volatility would take essentially the whole portfolio -- so
    cash is used only to hold the warmup window, where trailing volatility does
    not exist yet.
    """
    vol = prices[list(tickers)].pct_change(fill_method=None).rolling(lookback).std()
    inverse = 1.0 / vol.where(vol > 0)
    weights = inverse.div(inverse.sum(axis=1), axis=0)

    warmup = weights.isna().any(axis=1)
    weights = weights.where(~warmup, other=0.0).fillna(0.0)
    if cash is not None:
        weights[cash] = warmup.astype(float)

    return engine.run(prices, rebalance(weights, "month_end"), cost_bps=cost_bps)


def equity_exposure(result: engine.Result, risk_asset: str = "SPY") -> float:
    """Average weight the strategy actually held in the risk asset.

    For an all-or-nothing rule this is simply its time in the market.
    """
    if risk_asset not in result.held.columns:
        return 0.0
    return float(result.held[risk_asset].mean())


def vol_matched_weight(
    prices: pd.DataFrame,
    target_volatility: float,
    risk_asset: str = "SPY",
    cash: str = "BIL",
    cost_bps: float = engine.DEFAULT_COST_BPS,
) -> float:
    """Fraction of `risk_asset` whose realised volatility matches the target.

    Solved by running candidate mixes through the engine rather than by a
    closed-form variance formula, so the matched portfolio's volatility is
    measured exactly the way the strategy's is -- costs, lag and all.
    """

    def gap(weight: float) -> float:
        mix = static(prices, {risk_asset: weight, cash: 1.0 - weight}, cost_bps=cost_bps)
        return stats.annual_volatility(mix.returns) - target_volatility

    if gap(0.0) >= 0.0:  # even all-cash is more volatile than the strategy
        return 0.0
    if gap(1.0) <= 0.0:  # even all-equity is less volatile
        return 1.0
    return float(brentq(gap, 0.0, 1.0, xtol=_SOLVER_TOLERANCE))


def _measure(key: str, name: str, meaning: str, result: engine.Result) -> Benchmark:
    return Benchmark(
        key=key,
        name=name,
        meaning=meaning,
        result=result,
        metrics=stats.summarise(result.equity, result.returns),
    )


def available_keys(
    prices: pd.DataFrame,
    risk_asset: str = "SPY",
    cash: str = "BIL",
    bond: str = "TLT",
) -> list[str]:
    """Which benchmarks this snapshot can support, without building any of them.

    Separated from `build` so a declared benchmark can be checked in pre-flight,
    before the sweep logs a single trial. Discovering after the sweep that the
    declared bar cannot be constructed would mean trials already recorded against
    a benchmark that does not exist.
    """
    available = set(prices.columns)
    basket = [t for t in prices.columns if t != cash]

    keys: list[str] = []
    if risk_asset in available:
        keys.append(BUY_AND_HOLD)
    if {risk_asset, cash} <= available:
        keys += [VOL_MATCHED, EXPOSURE_MATCHED]
    if {risk_asset, bond} <= available:
        keys.append(SIXTY_FORTY)
    if len(basket) > 1:
        keys += [EQUAL_WEIGHT, INVERSE_VOL]
    if cash in available:
        keys.append(CASH)
    return keys


def _unavailable(key: str, available: Sequence[str]) -> BenchmarkUnavailableError:
    return BenchmarkUnavailableError(
        f"Declared benchmark {key!r} cannot be built from this snapshot, which "
        f"supports {sorted(available)}. It needs tickers the snapshot does not "
        "contain. Grading against a different benchmark instead is exactly the "
        "substitution a declared benchmark exists to prevent, so this is a refusal "
        "rather than a fallback."
    )


def require(
    prices: pd.DataFrame,
    key: str,
    risk_asset: str = "SPY",
    cash: str = "BIL",
    bond: str = "TLT",
) -> None:
    """Pre-flight: refuse the run if the declared benchmark is unbuildable."""
    if key not in KEYS:
        raise BenchmarkUnavailableError(
            f"Unknown benchmark {key!r}; expected one of {sorted(KEYS)}."
        )
    keys = available_keys(prices, risk_asset=risk_asset, cash=cash, bond=bond)
    if key not in keys:
        raise _unavailable(key, keys)


def resolve(slate: Sequence[Benchmark], key: str) -> Benchmark:
    """The declared benchmark, picked out of the built slate by key."""
    for benchmark in slate:
        if benchmark.key == key:
            return benchmark
    raise _unavailable(key, [b.key for b in slate])


def build(
    prices: pd.DataFrame,
    strategy_result: engine.Result,
    cost_bps: float = engine.DEFAULT_COST_BPS,
    risk_asset: str = "SPY",
    cash: str = "BIL",
    bond: str = "TLT",
) -> list[Benchmark]:
    """The full slate, ordered by how much losing to each would hurt.

    Benchmarks whose tickers are absent from the snapshot are skipped rather than
    faked, because a missing sleeve modelled as 0% return is the exact distortion
    the project's cash sleeve exists to avoid.
    """
    keys = available_keys(prices, risk_asset=risk_asset, cash=cash, bond=bond)
    out: list[Benchmark] = []

    if BUY_AND_HOLD in keys:
        out.append(
            _measure(
                BUY_AND_HOLD,
                f"buy & hold {risk_asset}",
                "the naive comparison; too easy on its own",
                engine.buy_and_hold(prices, ticker=risk_asset, cost_bps=cost_bps),
            )
        )

    if VOL_MATCHED in keys:
        target_vol = stats.annual_volatility(strategy_result.returns)
        matched = vol_matched_weight(prices, target_vol, risk_asset, cash, cost_bps)
        out.append(
            _measure(
                VOL_MATCHED,
                f"vol-matched {matched:.0%}/{1 - matched:.0%} {risk_asset}/{cash}",
                "same risk, no signal -- the bar that matters",
                static(prices, {risk_asset: matched, cash: 1.0 - matched}, cost_bps=cost_bps),
            )
        )

        held = equity_exposure(strategy_result, risk_asset)
        out.append(
            _measure(
                EXPOSURE_MATCHED,
                f"exposure-matched {held:.0%}/{1 - held:.0%} {risk_asset}/{cash}",
                "same average equity holding, held constantly",
                static(prices, {risk_asset: held, cash: 1.0 - held}, cost_bps=cost_bps),
            )
        )

    if SIXTY_FORTY in keys:
        out.append(
            _measure(
                SIXTY_FORTY,
                f"60/40 {risk_asset}/{bond}",
                "what a reasonable person would otherwise do",
                static(prices, {risk_asset: 0.6, bond: 0.4}, cost_bps=cost_bps),
            )
        )

    if EQUAL_WEIGHT in keys:
        basket = [t for t in prices.columns if t != cash]
        share = 1.0 / len(basket)
        out.append(
            _measure(
                EQUAL_WEIGHT,
                "equal-weight basket",
                "the basket with no view at all",
                static(prices, dict.fromkeys(basket, share), cost_bps=cost_bps),
            )
        )
        out.append(
            _measure(
                INVERSE_VOL,
                "inverse-volatility basket",
                "the basket weighted by risk, not by view",
                inverse_volatility(
                    prices,
                    basket,
                    cash=cash if cash in set(prices.columns) else None,
                    cost_bps=cost_bps,
                ),
            )
        )

    if CASH in keys:
        out.append(
            _measure(
                CASH,
                f"100% cash ({cash})",
                "the cost of never taking the risk at all",
                static(prices, {cash: 1.0}, cost_bps=cost_bps),
            )
        )

    return out
