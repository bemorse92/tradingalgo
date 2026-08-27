"""Command line entry point.

    python -m backtest.cli snapshot            # pin a fresh data pull
    python -m backtest.cli snapshots           # list pinned snapshots
    python -m backtest.cli ledger              # show the trial ledger
    python -m backtest.cli run <strategy>      # sweep a strategy's grid
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import sys

from . import data, engine, ledger, report
from .runner import RunReport, run_strategy
from .strategy import Strategy


def _load_strategy(name: str) -> type[Strategy]:
    """Import strategies.<name> and return the Strategy subclass it defines."""
    try:
        module = importlib.import_module(f"strategies.{name}")
    except ModuleNotFoundError as exc:
        raise SystemExit(f"No strategy module 'strategies/{name}.py' ({exc}).") from exc

    candidates = [
        obj
        for _, obj in inspect.getmembers(module, inspect.isclass)
        if issubclass(obj, Strategy) and obj is not Strategy and not obj.__abstractmethods__
    ]
    if not candidates:
        raise SystemExit(f"strategies/{name}.py defines no concrete Strategy subclass.")
    if len(candidates) > 1:
        raise SystemExit(
            f"strategies/{name}.py defines several strategies: "
            f"{[c.__name__ for c in candidates]}. Keep one per module."
        )
    return candidates[0]


def _print_report(rep: RunReport) -> None:
    print(report.section(f"{rep.strategy_name}"))
    print(
        report.provenance(
            snapshot_id=rep.snapshot.id,
            start=rep.sample_start,
            end=rep.sample_end,
            declared_n=rep.declared_n,
            trials_total=rep.trials_total,
            used_holdout=rep.used_holdout,
        )
    )

    best = rep.best_by_drawdown
    print(report.section("Best by drawdown vs buy & hold"))
    print(report.comparison(best.metrics, rep.benchmark_metrics, rep.strategy_name))
    if best.params:
        shown = ", ".join(f"{k}={v}" for k, v in sorted(best.params.items()))
        print(f"\n  at {shown}")

    print(report.section("Parameter plateau"))
    rows = []
    for trial in rep.trials:
        row = {k: v for k, v in trial.params.items()} or {"params": "(none)"}
        row["cagr"] = report.pct(trial.metrics["cagr"])
        row["max_dd"] = report.pct(trial.metrics["max_drawdown"])
        row["sharpe"] = f"{trial.metrics['sharpe']:.3f}"
        row["deflated"] = f"{trial.deflated_sharpe:.3f}"
        rows.append(row)
    print(report.plateau(rows))
    print(
        "\n  'deflated' is the probability the Sharpe survives the whole search to date.\n"
        "  Look for a flat neighbourhood, not a peak."
    )

    print(report.section("Per-event attribution (benchmark drawdowns > 10%)"))
    print(report.attribution(rep.attribution))
    print(
        "\n  If protection comes from one event, the edge is that event, not the rule."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="backtest", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    snap = sub.add_parser("snapshot", help="pull and pin a fresh data snapshot")
    snap.add_argument("--tickers", nargs="+", default=list(data.DEFAULT_TICKERS))
    snap.add_argument("--start", default=data.DEFAULT_START)
    snap.add_argument("--end", default=None)

    sub.add_parser("snapshots", help="list pinned snapshots")
    sub.add_parser("ledger", help="show the trial ledger")

    run = sub.add_parser("run", help="sweep a strategy's declared grid")
    run.add_argument("strategy", help="module name under strategies/")
    run.add_argument("--snapshot", default=None, help="snapshot id (default: latest)")
    run.add_argument("--cost-bps", type=float, default=engine.DEFAULT_COST_BPS)
    run.add_argument("--benchmark", default="SPY")
    run.add_argument("--note", default="")
    run.add_argument(
        "--allow-holdout",
        action="store_true",
        help="consume the reserved period. Recorded in the ledger.",
    )

    args = parser.parse_args(argv)

    if args.command == "snapshot":
        snapshot = data.create_snapshot(tuple(args.tickers), args.start, args.end)
        print(f"Created snapshot {snapshot.id}")
        print(f"  {', '.join(snapshot.tickers)}  {snapshot.start}..{snapshot.end}  "
              f"{snapshot.rows} rows  checksum {snapshot.checksum}")
        return 0

    if args.command == "snapshots":
        rows = [
            {
                "id": s.id,
                "tickers": ",".join(s.tickers),
                "start": s.start,
                "end": s.end,
                "rows": s.rows,
            }
            for s in data.list_snapshots()
        ]
        print(report.table(rows) if rows else "  (no snapshots yet)")
        return 0

    if args.command == "ledger":
        frame = ledger.read()
        if frame.empty:
            print("  (no trials yet)")
            return 0
        print(frame.to_string(index=False))
        print(f"\n  {len(frame)} trials logged.")
        return 0

    prices, snapshot = data.load(args.snapshot)
    strategy_cls = _load_strategy(args.strategy)
    rep = run_strategy(
        strategy_cls,
        prices,
        snapshot,
        cost_bps=args.cost_bps,
        benchmark_ticker=args.benchmark,
        allow_holdout=args.allow_holdout,
        note=args.note,
    )
    _print_report(rep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
