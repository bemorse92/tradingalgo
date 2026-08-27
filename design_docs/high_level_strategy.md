# High Level Strategy

## Purpose

Determine whether a simple, deterministic rule can improve on buy-and-hold SPY —
primarily by reducing drawdown — and to be able to conclude honestly that it cannot.

The project is a **research bench**, not a signal service. Its output is evidence about
strategies, not daily trade recommendations. Live signal generation is out of scope for now.

## Null Hypothesis

The Bogle prior is the default position: **active deviation from buy-and-hold underperforms.**
Strategies are guilty until proven innocent. A run that concludes "no edge" is a successful
run. The harness must be built to disconfirm, not to search until something looks good.

## Scope

Building and backtesting stock trading strategies. Trade execution is manual (Ben places
recommended trades) — this project does not connect to a broker for live/paper execution.

## Approach

- Prefer deterministic, off-the-shelf tools and well-established methods over custom or
  nondeterministic ones.
- Nondeterministic approaches (ML/LLM-based signals, etc.) are only introduced when
  deterministic methods have been tried and don't work.

## Instruments & Markets

- **Universe:** a small fixed basket of liquid US ETFs — SPY as the growth sleeve, TLT and
  GLD as defensive sleeves. (IWM, QQQ available if needed.)
- **Timeframe:** daily bars; multi-day to multi-week holding periods.
- **Direction:** long-only. No shorting, no leverage, no options.
- **Structure:** hold SPY by default; a rule may rotate into a defensive sleeve. This is a
  small portfolio with weights, not a binary in/out flag.

Because the basket is fixed and hand-chosen, there is no point-in-time universe or
delisting problem — but the ETFs were selected with hindsight, and that selection bias
is not detectable by any backtest. Treat it as a known, unfixable caveat.

## Data Sources

Free daily OHLCV (yfinance / Stooq) is sufficient for this universe.

Required properties:
- **Total-return series** (dividends included). SPY yields ~1–2%; a price-only series
  understates buy-and-hold and flatters every timing rule tested against it.
- **Cached raw pulls.** yfinance silently restates adjusted prices over time; without a
  local cache, backtest results change between runs for no visible reason.

TLT history starts 2002 and GLD 2004, so the common sample across the basket begins ~2004.
The 2000–2002 drawdown is not testable with all three sleeves.

## Strategy Types Under Consideration

TBD — trend/moving-average filters and defensive rotation are the natural first candidates
given the drawdown objective, but no commitment yet.

## Backtesting Approach

- **Benchmark:** buy-and-hold SPY, total return. Every strategy is reported against it.
- **Costs:** $0 commission. Bid/ask spread / slippage is the only friction modeled —
  a fixed bps assumption on liquid ETFs.
- **Taxes:** not modeled. Assumes a tax-advantaged account, so turnover carries no tax cost.
- **Fills:** TBD — default proposal is signal on today's close, filled at tomorrow's open.
- **Framework:** TBD.

## Evaluation Criteria

Primary bar: **materially smaller maximum drawdown at comparable return** to buy-and-hold SPY.

Not absolute return — that bar is realistically only cleared by overfitting on a sample
this small. Trend filters have historically cut drawdowns more reliably than they have
added return, so drawdown is where a real effect is most plausible.

2022 is a required stress case: SPY, TLT, and GLD all fell together, breaking the
defensive-sleeve assumption. No strategy passes without being examined in that window.

## Open Questions

- **Overfitting controls — RESOLVED.** See [research_guardrails.md](research_guardrails.md)
  for the Tier 1 requirements the harness must enforce: pre-registration committed before
  results, an automatic trial ledger, a two-tier parameter budget (unlimited fixed, max 2
  fitted, declared search grid priced into the deflated Sharpe), plateau reporting over peak
  selection, structural look-ahead prevention, pinned data snapshots, a start-date sweep,
  deflated/probabilistic Sharpe, and pre-committed kill criteria.
- **Run ergonomics.** What a "run" is: command invoked, and whether output is a terminal
  stats table, an equity-curve plot, or an HTML report.
- **Strategy definition format.** Config files vs. Python classes.
- **Fill assumption.** Confirm close-signal / next-open-fill.
