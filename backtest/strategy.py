"""The strategy contract.

Parameters are declared as data, split into `fixed` (set a priori, never swept --
statistically nearly free) and `fitted` (chosen by looking at results -- capped,
because with roughly four independent bear markets in the sample there is no honest
way to fit many things).

Declaring them this way is what lets the harness enforce the budget, price the
search space into the deflated Sharpe, log every trial, and report parameter
plateaus, without the researcher having to remember to do any of it.

See design_docs/research_guardrails.md, Tier 1 item 3.
"""

from __future__ import annotations

import itertools
from abc import ABC, abstractmethod
from collections.abc import Iterator, Mapping, Sequence
from typing import Any, ClassVar

import pandas as pd

from .criteria import Criterion

#: Hard cap on parameters chosen by looking at results.
MAX_FITTED_PARAMS = 2


class StrategyDeclarationError(TypeError):
    """Raised at import time when a strategy violates the parameter budget."""


class Strategy(ABC):
    """Base class for all strategies.

    Subclasses declare::

        name     = "sma_trend"
        rationale = "Volatility clusters; large drawdowns are slow grinds, not gaps."
        fixed    = {"rebalance": "month_end"}       # a priori, never swept
        fitted   = {"lookback": [150, 200, 250]}    # searched -- max 2 keys
        criteria = (Criterion("drawdown cut", "max_drawdown_vs_benchmark", 0.10),)

    and implement `weights()`. Do not lag inside `weights()`; the engine owns the
    only shift in the project.
    """

    name: ClassVar[str] = ""
    rationale: ClassVar[str] = ""
    fixed: ClassVar[Mapping[str, Any]] = {}
    fitted: ClassVar[Mapping[str, Sequence[Any]]] = {}
    criteria: ClassVar[Sequence[Criterion]] = ()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Validate the declaration when the module is imported, not when it runs."""
        super().__init_subclass__(**kwargs)
        if getattr(cls, "__abstractmethods__", None):
            return  # still abstract; nothing to validate yet

        if not cls.name:
            raise StrategyDeclarationError(f"{cls.__qualname__} must declare a `name`.")
        if not cls.rationale.strip():
            raise StrategyDeclarationError(
                f"{cls.__qualname__} must declare a `rationale`: an ex-ante economic "
                "foundation, stated before searching. This is protocol item #1 "
                "(Arnott, Harvey & Markowitz)."
            )
        if not cls.criteria:
            raise StrategyDeclarationError(
                f"{cls.__qualname__} must declare `criteria`: the bar this must clear, "
                "fixed before results exist. A strategy with no declared bar can be "
                "graded on whichever metric happens to flatter it."
            )
        if len(cls.fitted) > MAX_FITTED_PARAMS:
            raise StrategyDeclarationError(
                f"{cls.__qualname__} declares {len(cls.fitted)} fitted parameters "
                f"({sorted(cls.fitted)}); the cap is {MAX_FITTED_PARAMS}. Parameters set "
                "a priori and never swept belong in `fixed` and cost nothing."
            )
        overlap = set(cls.fixed) & set(cls.fitted)
        if overlap:
            raise StrategyDeclarationError(
                f"{cls.__qualname__}: {sorted(overlap)} declared both fixed and fitted."
            )
        for key, grid in cls.fitted.items():
            if isinstance(grid, (str, bytes)) or not isinstance(grid, Sequence) or not grid:
                raise StrategyDeclarationError(
                    f"{cls.__qualname__}: fitted parameter {key!r} must be a non-empty "
                    "sequence of candidate values."
                )

    def __init__(self, **overrides: Any) -> None:
        params = dict(self.fixed)
        for key, grid in self.fitted.items():
            params[key] = overrides.pop(key, grid[0])
        unknown = set(overrides) - set(params)
        if unknown:
            raise TypeError(f"{type(self).__qualname__}: undeclared parameters {sorted(unknown)}")
        params.update(overrides)
        self.params = params

    def __repr__(self) -> str:
        shown = ", ".join(f"{k}={v!r}" for k, v in sorted(self.fitted_params().items()))
        return f"{type(self).__name__}({shown})"

    def fitted_params(self) -> dict[str, Any]:
        """Just the searched parameters, for logging and plateau reporting."""
        return {k: self.params[k] for k in self.fitted}

    @classmethod
    def grid(cls) -> Iterator[dict[str, Any]]:
        """Every combination of fitted parameter values."""
        if not cls.fitted:
            yield {}
            return
        keys = list(cls.fitted)
        for combo in itertools.product(*(cls.fitted[k] for k in keys)):
            yield dict(zip(keys, combo, strict=True))

    @classmethod
    def declared_n(cls) -> int:
        """Size of the declared search space -- the N that deflates the Sharpe.

        If this disagrees with the ledger's actual run count, the declared N is
        wrong and the deflated Sharpe is flattering.
        """
        n = 1
        for grid in cls.fitted.values():
            n *= len(grid)
        return n

    @abstractmethod
    def weights(self, prices: pd.DataFrame) -> pd.DataFrame:
        """Target weights per date, columns = tickers.

        Long-only and unlevered: values in [0, 1], rows summing to at most 1.
        Decided at each date's close; the engine shifts them forward one bar.
        """
