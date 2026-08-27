"""Terminal tables.

Plain text, no dependencies. The two outputs that decide the project's success bar
-- the parameter plateau and the per-drawdown-event attribution -- are naturally
tabular, so this costs less than it looks. Only the equity curve wants a picture,
and it is the least decision-relevant artifact.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import pandas as pd


def table(rows: Sequence[dict[str, Any]], headers: Sequence[str] | None = None) -> str:
    """Render a list of dicts as a fixed-width table."""
    if not rows:
        return "  (no rows)"
    headers = list(headers or rows[0].keys())
    cells = [[_fmt(r.get(h, "")) for h in headers] for r in rows]
    widths = [max(len(h), *(len(row[i]) for row in cells)) for i, h in enumerate(headers)]

    line = "  ".join(h.ljust(w) for h, w in zip(headers, widths, strict=True))
    rule = "  ".join("-" * w for w in widths)
    body = "\n".join(
        "  ".join(c.rjust(w) for c, w in zip(row, widths, strict=True)) for row in cells
    )
    return f"{line}\n{rule}\n{body}"


def _fmt(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        if math.isnan(value):
            return "n/a"
        if value in (float("inf"), float("-inf")):
            return "inf"
        return f"{value:,.4f}"
    return str(value)


def pct(value: float) -> str:
    return "n/a" if math.isnan(value) else f"{value * 100:,.2f}%"


def section(title: str) -> str:
    return f"\n{title}\n{'=' * len(title)}"


def provenance(
    snapshot_id: str,
    start: str,
    end: str,
    declared_n: int,
    trials_total: int,
    used_holdout: bool,
) -> str:
    """Printed with every run. A result without these numbers is not a result."""
    lines = [
        f"  snapshot        {snapshot_id}",
        f"  sample          {start} .. {end}",
        f"  declared N      {declared_n}",
        f"  trials to date  {trials_total}",
    ]
    if declared_n != trials_total:
        lines.append(
            f"  {'':<15} note: declared N and ledger count differ; the deflated"
        )
        lines.append(f"  {'':<15} Sharpe below uses the ledger, which is the honest one.")
    if used_holdout:
        lines.append("  holdout         CONSUMED — this access is recorded in the ledger")
    return "\n".join(lines)


def comparison(strategy: dict[str, float], benchmark: dict[str, float], label: str) -> str:
    """Strategy against buy-and-hold, side by side."""
    rows = [
        {
            "metric": "CAGR",
            label: pct(strategy["cagr"]),
            "buy & hold": pct(benchmark["cagr"]),
        },
        {
            "metric": "max drawdown",
            label: pct(strategy["max_drawdown"]),
            "buy & hold": pct(benchmark["max_drawdown"]),
        },
        {
            "metric": "volatility",
            label: pct(strategy["volatility"]),
            "buy & hold": pct(benchmark["volatility"]),
        },
        {
            "metric": "Sharpe",
            label: f"{strategy['sharpe']:.3f}",
            "buy & hold": f"{benchmark['sharpe']:.3f}",
        },
    ]
    return table(rows, ["metric", label, "buy & hold"])


def plateau(rows: Sequence[dict[str, Any]]) -> str:
    """Parameter neighbourhood, never a single point.

    A rule that works at 150/200/250 is credible; one that works only at 200 is
    fitted to noise. Printing the neighbourhood makes seeing the peak alone
    impossible.
    """
    return table(rows)


def attribution(frame: pd.DataFrame) -> str:
    """Per-event protection. Exposes an edge that is really one event in disguise."""
    if frame.empty:
        return "  (no benchmark drawdown events past the threshold)"
    rows = [
        {
            "peak": str(r["peak"]),
            "trough": str(r["trough"]),
            "benchmark": pct(r["benchmark_dd"]),
            "strategy": pct(r["strategy_dd"]),
            "protection": pct(r["protection"]),
            "recovered": bool(r["recovered"]),
        }
        for _, r in frame.iterrows()
    ]
    return table(rows)
