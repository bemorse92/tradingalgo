# tradingalgo

## Overview

This project will create strategies and backtest strategies around stock trading. Ben (owner of this repo) will perform manual placement of trades recommended. 


## Design Goals

- Use out-of-the-box, deterministic software whenever possible.
- Nondeterminism (ML models, LLMs, etc.) is a last resort — reach for it only when deterministic approaches genuinely don't work.

## Working Principles (for Claude)

- The best code is the least code that does the job.
- Standards are standards for a reason — they work, otherwise they wouldn't be standard. Prefer conventional, well-trodden approaches over clever ones.
- Predictable and boring is the goal.
- Research and follow the data — back decisions with evidence, not intuition.
- **One-way vs. two-way doors**: two-way (reversible) decisions can be made and crossed without asking. One-way (hard-to-reverse) decisions need Ben's guidance first. An expensive-to-reverse two-way door should be treated as a one-way door.

## Stack

Python. Purpose-built pandas harness — **no backtesting framework** (see
[scaffolding.md](design_docs/scaffolding.md) for why). Runtime deps: `pandas`, `numpy`,
`scipy`, `yfinance`, `pyarrow`. Dev: `pytest`, `ruff`, plus `ffn`/`quantstats` used only as a
statistics oracle in tests. No broker/execution API — trades are placed manually.

## Architecture

- `backtest/` — the harness: `data` (fetch/cache/pin, total-return series), `engine`
  (weights → equity curve; owns the single `.shift(1)` and the cost model), `stats`
  (CAGR/drawdown/Sharpe/DSR/PSR, per-event attribution), `ledger` (append-only trial log),
  `validate` (future-corruption test, parameter budget, prereg presence, holdout gate),
  `report`, `cli`.
- `strategies/` — one `Strategy` subclass per strategy, each declaring `rationale`, `fixed`,
  and `fitted` params, paired with a `.prereg.md` committed *before* results exist. The
  schema is what enforces the guardrails; see
  [research_guardrails.md](design_docs/research_guardrails.md).
- Strategies return target weights. The engine — not the strategy — applies the lag, so
  look-ahead prevention lives in exactly one place and is unit-testable.

## Setup & Running

TBD — how to install dependencies, configure `.env`, and run backtests/tests locally.

## Conventions

TBD — coding conventions, strategy interface contracts, naming, testing expectations.

## Risk & Safety Rules

Trades are placed manually by Ben — this project does not execute live/paper trades. Beyond that: TBD (position limits, secrets handling, what Claude may run autonomously vs. what needs explicit confirmation).

## Design Docs

See [design_docs/](design_docs/) for deeper write-ups on architecture decisions, strategy designs, and research notes.

- [High Level Strategy](design_docs/high_level_strategy.md)
- [High Level Strategy Research](design_docs/high_level_strategy_research.md) — what the literature says about whether this can work
- [Research Guardrails](design_docs/research_guardrails.md) — the overfitting controls the harness must enforce
- [Scaffolding](design_docs/scaffolding.md) — engine choice, strategy contract, layout, build order
- [Next Steps](design_docs/next_steps.md) — proposed sequence from built harness to a defensible answer
- [Findings](design_docs/findings.md) — results from the first pre-registered runs
