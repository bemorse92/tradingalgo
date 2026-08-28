"""Command line entry point.

    python -m backtest.cli snapshot            # pin a fresh data pull
    python -m backtest.cli snapshots           # list pinned snapshots
    python -m backtest.cli ledger              # show the trial ledger
    python -m backtest.cli run <strategy>      # sweep a strategy's grid
    python -m backtest.cli robustness <strat>  # start-date and cost sweeps
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import sys

from . import data, engine, ledger, report, runner, stats, validate
from .runner import RunReport, run_strategy
from .strategy import Strategy

#: Start dates for the robustness sweep. 2010 excludes the GFC entirely, which is
#: the single most informative row: it separates "the rule works" from "2008 happened".
START_DATES = ("2007-05-30", "2010-01-04", "2013-01-02", "2016-01-04")


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

    print(report.section("Pre-registered criteria"))
    print(report.criteria(rep.criteria, rep.verdict))

    print(report.section("Best by drawdown vs buy & hold"))
    print(report.comparison(best.metrics, rep.benchmark_metrics, rep.strategy_name))
    if best.params:
        shown = ", ".join(f"{k}={v}" for k, v in sorted(best.params.items()))
        print(f"\n  at {shown}")

    print(report.section("Against benchmarks that need no signal"))
    print(report.benchmarks(rep.benchmarks, best.metrics, rep.strategy_name))
    print(
        "\n  Buy & hold alone flatters any rule that simply holds less equity. The\n"
        "  matched rows hold the same risk with no signal, no timing and no\n"
        "  discipline: losing to one of those means the rule contributed nothing.\n"
        "  Diagnostic only -- the graded criteria above are the pre-registered ones."
    )

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

    print(report.section("How much this can carry"))
    # Measured against the benchmark's Sharpe, not against zero. "How long to
    # confirm this beats nothing" is a trivial question; "how long to confirm it
    # beats buy-and-hold" is the one the project is actually asking.
    bench_sr = stats.sharpe_per_period(rep.benchmark.returns)
    mintrl = stats.min_track_record_length(best.result.returns, bench_sr) / stats.TRADING_DAYS
    print(report.confidence(mintrl, best.deflated_sharpe))
    print(
        "\n  Live results will not settle this within any relevant horizon; the\n"
        "  evidence has to come from discipline about the sample that exists."
    )

    print(report.section("Followability (whipsaw / regret)"))
    print(report.regret(rep.regret))
    print(
        "\n  A rule only pays if it is followed through the stretches where it looks\n"
        "  stupid. This is what killed the commercial tactical funds."
    )

    print(report.section("Per-event attribution (benchmark drawdowns > 10%)"))
    print(report.attribution(rep.attribution))
    print(
        "\n  If protection comes from one event, the edge is that event, not the rule."
    )


def _print_robustness(strategy_cls, prices, snapshot, cost_bps: float) -> None:
    """Start-date and cost sweeps, both logged as `robustness` rather than search."""
    print(report.section(f"{strategy_cls.name}: start-date sweep"))
    print(
        "  A single start date is a hidden parameter. The post-2008 row is the one\n"
        "  that matters: if the edge needs 2008, the finding is that 2008 happened.\n"
    )
    sweep = runner.start_date_sweep(
        strategy_cls, prices, snapshot, START_DATES, cost_bps=cost_bps
    )
    rows = []
    for start, rep in sweep:
        best = rep.best_by_drawdown
        rows.append(
            {
                "from": start,
                "years": f"{len(rep.benchmark.equity) / 252:.1f}",
                "cagr": report.pct(best.metrics["cagr"]),
                "bench cagr": report.pct(rep.benchmark_metrics["cagr"]),
                "max_dd": report.pct(best.metrics["max_drawdown"]),
                "bench dd": report.pct(rep.benchmark_metrics["max_drawdown"]),
                "dd saved": report.pct(
                    best.metrics["max_drawdown"] - rep.benchmark_metrics["max_drawdown"]
                ),
            }
        )
    print(report.table(rows))

    print(report.section(f"{strategy_cls.name}: vs the vol-matched mix, by start date"))
    print(
        "  The same two questions asked of a portfolio that needs no signal: same\n"
        "  risk, held constantly. Positive deltas mean the timing rule earned its\n"
        "  keep; negative means the result was 'held less stock' all along.\n"
    )
    rows = []
    for start, rep in sweep:
        matched = rep.vol_matched
        if matched is None:
            continue
        best = rep.best_by_drawdown
        rows.append(
            {
                "from": start,
                "mix": matched.name.split()[1],
                "cagr": report.pct(best.metrics["cagr"]),
                "matched cagr": report.pct(matched.metrics["cagr"]),
                "d cagr": report.points(best.metrics["cagr"] - matched.metrics["cagr"]),
                "max_dd": report.pct(best.metrics["max_drawdown"]),
                "matched dd": report.pct(matched.metrics["max_drawdown"]),
                "d max dd": report.points(
                    best.metrics["max_drawdown"] - matched.metrics["max_drawdown"]
                ),
            }
        )
    print(report.table(rows))

    print(report.section(f"{strategy_cls.name}: cost sensitivity"))
    print("  A result that dies at 20 bps on liquid ETFs was never real.\n")
    rows = []
    for bps, rep in runner.cost_sweep(strategy_cls, prices, snapshot):
        best = rep.best_by_drawdown
        rows.append(
            {
                "bps": f"{bps:.0f}",
                "cagr": report.pct(best.metrics["cagr"]),
                "max_dd": report.pct(best.metrics["max_drawdown"]),
                "sharpe": f"{best.metrics['sharpe']:.3f}",
            }
        )
    print(report.table(rows))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="backtest", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    snap = sub.add_parser("snapshot", help="pull and pin a fresh data snapshot")
    snap.add_argument("--tickers", nargs="+", default=list(data.DEFAULT_TICKERS))
    snap.add_argument("--start", default=data.DEFAULT_START)
    snap.add_argument("--end", default=None)

    sub.add_parser("snapshots", help="list pinned snapshots")
    sub.add_parser("ledger", help="show the trial ledger")

    rob = sub.add_parser("robustness", help="start-date and cost sweeps (logged as robustness)")
    rob.add_argument("strategy")
    rob.add_argument("--snapshot", default=None)
    rob.add_argument("--cost-bps", type=float, default=engine.DEFAULT_COST_BPS)

    run = sub.add_parser("run", help="sweep a strategy's declared grid")
    run.add_argument("strategy", help="module name under strategies/")
    run.add_argument("--snapshot", default=None, help="snapshot id (default: latest)")
    run.add_argument("--cost-bps", type=float, default=engine.DEFAULT_COST_BPS)
    run.add_argument("--benchmark", default="SPY")
    run.add_argument("--note", default="")
    run.add_argument(
        "--kind",
        choices=("search", "robustness"),
        default="search",
        help=(
            "how these trials count. `search` deflates the Sharpe (configurations "
            "selected among); `robustness` does not (a re-run of a configuration "
            "already declared). Re-running a settled strategy to see new reporting "
            "is robustness. Choosing among results is search, whatever it is called."
        ),
    )
    run.add_argument(
        "--allow-holdout",
        action="store_true",
        help="consume the reserved period. Recorded in the ledger.",
    )
    run.add_argument(
        "--force-holdout",
        action="store_true",
        help="override the one-shot holdout guard. Recorded in the ledger.",
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
    if args.command == "robustness":
        strategy_cls = _load_strategy(args.strategy)
        usable = validate.apply_holdout(prices)
        _print_robustness(strategy_cls, usable, snapshot, args.cost_bps)
        return 0

    strategy_cls = _load_strategy(args.strategy)
    rep = run_strategy(
        strategy_cls,
        prices,
        snapshot,
        cost_bps=args.cost_bps,
        benchmark_ticker=args.benchmark,
        kind=args.kind,
        allow_holdout=args.allow_holdout,
        force_holdout=args.force_holdout,
        note=args.note,
    )
    _print_report(rep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
