"""The trial ledger: an append-only record of every backtest ever run.

The cheapest high-value guardrail available, and almost nobody builds it. A Sharpe
of 1.2 found on the 4th configuration tested is a finding; the same number on the
400th is noise. Without a ledger you genuinely will not know which you have.

Written automatically by the runner. Trials you forget to log are exactly the ones
that inflate the count, so nothing here is meant to be called by hand.
"""

from __future__ import annotations

import csv
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
LEDGER_PATH = RESULTS_DIR / "trials.csv"

FIELDS = (
    "timestamp",
    "strategy",
    "kind",
    "params",
    "snapshot_id",
    "start",
    "end",
    "cost_bps",
    "declared_n",
    "sharpe",
    "cagr",
    "max_drawdown",
    "used_holdout",
    "git_commit",
    "note",
)


def _git_commit() -> str:
    """Current commit, so a result can be traced to the code that produced it."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            cwd=Path(__file__).resolve().parent.parent,
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):  # pragma: no cover - defensive
        return ""


def log_trial(
    strategy_name: str,
    params: dict[str, Any],
    snapshot_id: str,
    start: str,
    end: str,
    cost_bps: float,
    declared_n: int,
    metrics: dict[str, float],
    kind: str = "search",
    used_holdout: bool = False,
    note: str = "",
) -> None:
    """Append one trial. Never rewrites or deduplicates -- that is the point."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    is_new = not LEDGER_PATH.exists()
    row = {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "strategy": strategy_name,
        "kind": kind,
        "params": json.dumps(params, sort_keys=True, default=str),
        "snapshot_id": snapshot_id,
        "start": start,
        "end": end,
        "cost_bps": cost_bps,
        "declared_n": declared_n,
        "sharpe": round(metrics.get("sharpe", float("nan")), 6),
        "cagr": round(metrics.get("cagr", float("nan")), 6),
        "max_drawdown": round(metrics.get("max_drawdown", float("nan")), 6),
        "used_holdout": used_holdout,
        "git_commit": _git_commit(),
        "note": note,
    }
    with LEDGER_PATH.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def read() -> pd.DataFrame:
    """The whole ledger. Empty frame if nothing has been run yet."""
    if not LEDGER_PATH.exists():
        return pd.DataFrame(columns=list(FIELDS))
    return pd.read_csv(LEDGER_PATH)


def trial_count(strategy_name: str | None = None) -> int:
    """Total trials run -- overall, or for one strategy."""
    ledger = read()
    if strategy_name is not None:
        ledger = ledger[ledger["strategy"] == strategy_name]
    return len(ledger)


def sharpes(strategy_name: str | None = None, kind: str | None = "search") -> list[float]:
    """Sharpes for deflating the winner.

    Spans all strategies by default: the multiple-testing correction should
    account for the whole search, not just the branch that succeeded.

    Only `search` trials count by default. N in the deflated Sharpe means
    *configurations selected among*, not re-runs of one configuration under
    different conditions. Counting robustness checks would penalise exactly the
    behaviour the project wants to encourage, identically to p-hacking, which it
    wants to discourage. Pass kind=None to see everything.
    """
    ledger = read()
    if strategy_name is not None:
        ledger = ledger[ledger["strategy"] == strategy_name]
    if kind is not None and "kind" in ledger.columns:
        ledger = ledger[ledger["kind"] == kind]
    if ledger.empty:
        return []
    return [float(s) for s in pd.to_numeric(ledger["sharpe"], errors="coerce").dropna()]


def holdout_uses(strategy_name: str) -> pd.DataFrame:
    """Every prior run that consumed the reserved period, for this strategy.

    The holdout is a one-shot resource; this is what makes "already spent"
    checkable rather than remembered.
    """
    frame = read()
    if frame.empty or "used_holdout" not in frame.columns:
        return frame
    consumed = frame["used_holdout"].astype(str).str.lower() == "true"
    return frame[consumed & (frame["strategy"] == strategy_name)]
