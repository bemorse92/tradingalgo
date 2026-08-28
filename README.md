# tradingalgo

A research bench for one question: **can a simple, deterministic rule reduce drawdown
relative to buy-and-hold SPY?** Trades, if any are ever placed, are placed manually.

The default position is that it cannot — see
[design_docs/high_level_strategy_research.md](design_docs/high_level_strategy_research.md).
The harness is built to be able to conclude that.

## Setup

```bash
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

Pin a data snapshot (the only command that touches the network):

```bash
python -m backtest.cli snapshot
```

Run a strategy across its declared parameter grid:

```bash
python -m backtest.cli run <strategy_name>
```

Sweep it across start dates and cost assumptions, and against the signal-free
benchmarks:

```bash
python -m backtest.cli robustness <strategy_name>
```

Check the harness itself against a published result:

```bash
python -m backtest.cli reproduce
```

This re-implements Faber's 10-month timing rule on committed reference data and
compares the output to the figures in his paper. It is the only check here that can
catch a mistake shared by the code and its own unit tests. It logs no trials.

Other commands: `snapshots` (list pinned data), `ledger` (every trial ever run).

Re-running a settled strategy to see new reporting is not a new search, and should
say so — `run --kind robustness` logs the trials without deflating anyone's Sharpe.
Choosing among results is `search` whatever it is called.

## Layout

- `backtest/` — the harness. `data` (fetch/cache/pin), `engine` (weights → equity curve;
  owns the only lag in the project), `stats` (performance plus deflated/probabilistic
  Sharpe), `benchmarks` (the signal-free portfolios a strategy has to beat, including
  static mixes matched to its own volatility and equity exposure; which one grades a
  strategy is declared on it in advance), `criteria`
  (pre-registered bars, graded mechanically), `ledger` (append-only trial log),
  `validate` (look-ahead detection, pre-registration gate, holdout gate), `reproduce`
  (the harness checked against externally published results), `runner`, `report`, `cli`.
- `strategies/` — one `Strategy` subclass per module, each paired with a `.prereg.md`
  committed *before* its first result exists.
- `data/` — `snapshots.json` is the committed registry; `cache/` holds the pinned pulls
  and is gitignored.
- `data/reference/` — pinned inputs for the published-result reproduction. Committed:
  a reproduction that re-downloads its own inputs is not one.
- `results/trials.csv` — the trial ledger. Committed: it is the audit trail.
- `tests/`

## Working rules

Three things the harness enforces mechanically, because the research says intentions
don't hold (see [design_docs/research_guardrails.md](design_docs/research_guardrails.md)):

1. **No result without a pre-registration.** Rationale, rule, parameters, benchmark,
   sample, and success criteria are committed before the first backtest runs. Which
   signal-free alternative a strategy must beat is part of the hypothesis: buy & hold
   flatters any rule that simply holds less equity, so it has to be a choice rather
   than a default.
2. **Every trial is logged.** A Sharpe found on the 4th configuration is a finding; the
   same number on the 400th is noise, and only the ledger knows which you have.
3. **Strategies must prove they cannot see the future.** Prices after a cut date are
   corrupted and the earlier weights must not move.

```bash
python -m pytest
```
