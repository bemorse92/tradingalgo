# Scaffolding

Concrete build plan. Decisions here are settled unless noted; see
[research_guardrails.md](research_guardrails.md) for *why* the guardrail machinery exists and
[high_level_strategy.md](high_level_strategy.md) for the strategy scope it serves.

---

## Engine: purpose-built pandas harness

No backtesting framework. The rationale, briefly, because this runs against the project's
"prefer standards" principle:

- **The engine is not the hard part.** Long-only, daily bars, 3–5 ETFs, target weights, no
  orders, fills, shorts, leverage, margin, or intraday. That is ~100 lines of pandas.
- **The guardrails are the hard part, and no framework provides them.** Trial ledger,
  pre-registration binding, declared-N → deflated Sharpe, plateau reporting, start-date
  sweeps, holdout gating, snapshot pinning, per-event attribution. Adopting a framework means
  writing all of it anyway, on top of someone else's abstractions.
- **Look-ahead is the one thing that must be verifiable**, and it should not be mediated by a
  third party's internals.
- pandas/numpy *is* the well-trodden tool. The standard being skipped is a framework built to
  solve a problem this project does not have.

Landscape as of 2026, for the record: backtrader frozen since April 2023 (forum closed to new
posts); vectorbt's open-source line in maintenance mode with development behind vectorbt PRO
(~$25/mo); zipline-reloaded requires bundle ingestion and targets dynamic-universe factor
research; `bt` is the closest conceptual fit; backtesting.py is single-asset.

**Where standards still win:** write CAGR / max drawdown / Sharpe by hand so they are
unit-testable, then **test them against `ffn` or `quantstats` as an oracle** in the test
suite. Correctness confidence, no runtime dependency.

---

## Strategy definition: class with a declared parameter schema

```python
class Strategy:
    name: str
    rationale: str          # ex-ante economic foundation — required, non-empty
    fixed: dict             # param -> value. Set a priori, never swept.
    fitted: dict            # param -> sweep grid. Max 2 keys.

    def weights(self, prices: pd.DataFrame) -> pd.DataFrame:
        """Target weights per date, columns = tickers, rows sum to <= 1.
        The engine owns the shift; do not lag inside this method."""
```

This was the better call than a bare function, because **the schema does the enforcing**.
With `fixed` and `fitted` declared as data, the harness can, without the researcher
remembering to do anything:

- refuse to run a strategy declaring more than 2 fitted parameters;
- compute `N = product(len(grid) for grid in fitted.values())` and feed it straight to the
  Deflated Sharpe, so the declared search space is *automatically* priced;
- log every `(strategy, param combination)` to the trial ledger as it runs;
- generate the plateau report from the grid for free — seeing a peak in isolation becomes
  impossible;
- reject an empty `rationale`, enforcing protocol item #1 (economic foundation before search).

A parameter promoted from `fixed` to `fitted` shows up as a diff in version control and a
jump in N. That is exactly the visibility the guardrails need.

---

## Fill assumption: signal at close *t* → position effective close *t* → close *t+1*

**This supersedes the earlier next-open proposal.** Reasons:

- Next-open fills require adjusted *open* prices, which complicates the total-return series
  for no real gain at monthly rebalance frequency.
- Next-close is one full bar of delay — slightly conservative, and structurally simpler: the
  entire look-ahead guarantee reduces to a single `.shift(1)` in one place.
- It matches manual execution honestly. Ben sees the signal after the close and places the
  trade sometime the following day; assuming the day's close is fair, and if anything
  pessimistic relative to acting at the open.

---

## Layout

Extends the existing scaffold rather than restructuring it.

```
backtest/
  data.py        # fetch, cache to parquet, snapshot ids, total-return series
  engine.py      # weights -> equity curve. Owns the shift and the cost model.
  stats.py       # CAGR, max DD, Sharpe, DSR, PSR, per-drawdown-event attribution
  ledger.py      # append-only trial log
  validate.py    # future-corruption test, param budget, prereg presence, holdout gate
  report.py      # terminal tables
  cli.py         # entry point
strategies/
  <name>.py          # the Strategy subclass
  <name>.prereg.md   # committed BEFORE the first result exists
data/
  cache/         # pinned raw pulls (gitignored)
  snapshots.json # snapshot id -> date, tickers, checksum (committed)
results/
  trials.csv     # the ledger (committed)
tests/
```

## Dependencies

Deliberately small: `pandas`, `numpy`, `scipy` (normal CDF for DSR/PSR), `yfinance`,
`pyarrow` (parquet cache). Dev/test only: `pytest`, `ruff`, and `ffn` **or** `quantstats` as
a statistics oracle.

---

## Output: terminal stats tables

Least code, fastest iteration loop, and it costs less than first assumed — the two outputs
that matter most to the success bar are naturally tabular:

- **Plateau report** — parameter value → drawdown reduction, as a small table.
- **Per-event attribution** — each drawdown event → strategy DD vs benchmark DD. This is the
  table that exposes the "one event doing all the work" failure that killed GEM.

Only the equity curve genuinely wants a picture, and it is the least decision-relevant
artifact. If it's ever needed, it can be added without touching the engine.

Every run prints, alongside the headline stats: the **snapshot id**, the **running trial
count**, the **declared N**, and the **deflated Sharpe**. A result reported without those is
not a result.

---

## Build order

Guardrails before strategies — retrofitting them does not work, and the first strategy run is
already a trial that should be logged.

1. ~~`data.py` + cache/snapshot pinning, total-return series, fixture-based test.~~ **Done.**
2. ~~`engine.py` — the shift, the cost model, the equity curve.~~ **Done.**
3. ~~`validate.py` — the future-corruption test, proven against a deliberately
   look-ahead-buggy fixture strategy.~~ **Done.**
4. ~~`stats.py` — hand-written, oracle-tested; DSR/PSR closed forms.~~ **Done.**
5. ~~`ledger.py` + `Strategy` base class enforcement.~~ **Done.**
6. ~~`report.py` + `cli.py`.~~ **Done.**
7. First pre-registered strategy. **Not started** — this is a research decision, not a
   scaffolding one: the rationale, parameters, and success criteria are Ben's to state.

One deviation from the layout above: orchestration lives in `runner.py` rather than inside
`cli.py`, so the sweep-and-log flow is testable without going through argument parsing.

---

## Still open

- **Holdout period.** Which date range stays untouched, and until when. Needs deciding before
  step 7, not before step 1.
- **Slippage assumption.** A fixed bps figure on liquid ETFs; value TBD.
- **Environment tooling.** Current scaffold uses `venv` + `requirements.txt`. `uv` with a
  lockfile is the faster, more reproducible option and is a cheap two-way door either way.
