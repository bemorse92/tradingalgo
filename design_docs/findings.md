# Findings

First research runs. Snapshot `2026-08-27-02dd5081` (SPY/TLT/GLD/BIL,
2007-05-30 → 2026-08-26). In-sample period 2007-05-30 → 2022-12-30; **the 2023+
holdout has not been consumed.**

Two strategies, each pre-registered before its first run, 5 bps one-way slippage,
month-end rebalancing, exit to BIL.

---

## Summary

| | `sma_trend` | `dual_momentum` |
|---|---|---|
| Pre-registered criteria | **Passed all four** | **Failed** (criterion 3) |
| Max drawdown | −20.83% vs −55.19% | −33.72% vs −55.19% |
| CAGR | 8.32% vs 8.15% | 8.36% vs 8.15% |
| Sharpe | 0.705 vs 0.483 | 0.614 vs 0.483 |
| Post-2008 drawdown saved | +12.9pp | **0.0pp** |
| Post-2008 CAGR vs benchmark | **−3.2pp** | **−5.8pp** |

**Neither result supports spending the holdout.** Details below.

---

## sma_trend

Passed every pre-registered criterion on the pre-registered sample:

1. Max drawdown reduced 34.4pp (−20.83% vs −55.19%) — required ≥10pp. **Pass.**
2. CAGR 8.32% vs 8.15%, *above* benchmark — required within −2pp. **Pass.**
3. Positive protection in 2008 (+57.9pp), 2020 (+21.4pp), 2022 (+11.4pp) — required
   ≥3 events. **Pass, at exactly the minimum.**
4. Drawdown improvement held at all three lookbacks (−22.1%, −22.1%, −20.8%).
   **Pass.**

Costs are not the binding constraint: at 20 bps the CAGR only falls from 8.32% to
7.94%.

### What the criteria failed to capture

**The start-date sweep is the finding.** Criterion 2 passes only because 2008 is in
the sample:

| From | Strategy CAGR | Benchmark CAGR | Drawdown saved |
|---|---|---|---|
| 2007-05-30 | 8.32% | 8.15% | +34.4pp |
| **2010-01-04** | **8.75%** | **11.93%** | +12.9pp |
| 2013-01-02 | 7.06% | 12.17% | +12.9pp |
| 2016-01-04 | 8.29% | 11.63% | +12.9pp |

Drawdown protection survives excluding the GFC — that part is real and worth
noting. But the return cost is 3–5 points a year on every post-2008 window, against
a criterion that allowed 2 points. The rule does not beat buy-and-hold on return; it
matched it once, in a sample containing the worst equity drawdown in seventy years.

**The regret numbers say the same thing from another angle.** Worst cumulative
shortfall versus buy-and-hold: **−59.8%**. Worst single year relative: **−32.0%**.
Longest stretch below a relative peak: **3,479 days — about 13.8 years**, essentially
the whole post-crisis sample.

Read together: the strategy's relative peak was set in March 2009, and it spent the
next fourteen years giving that advantage back. That is precisely the "one event in
disguise" pattern the literature warns about, and criterion 3 — three distinct events
— was too weak to catch it, because it counted events without weighting them.

### Verdict

Passed as written. **Not re-graded** — the criteria were fixed in advance and moving
them after seeing results is the failure mode the whole project is built to prevent.

But promotion to the holdout is a separate decision from passing, and the holdout is
a one-shot resource. The evidence the criteria were meant to establish — that this
rule improves on buy-and-hold at acceptable cost — did not materialise once the
sample dependence was visible. **Recommendation: do not spend the holdout on this.**

---

## dual_momentum

Failed criterion 3, **exactly as its pre-registration predicted**: positive
protection in only two events (2008 +57.9pp, 2022 +11.6pp). It sat through 2020 for
the full −33.72% and gave back −2.3pp in 2015.

The start-date sweep is worse than for `sma_trend`. Post-2008 it delivers **zero**
drawdown protection while giving up 5.8–7.5 points of CAGR a year — strictly
dominated by simply holding SPY.

A clean, recorded negative result. Its entire apparent edge is 2008.

---

## What this says about the process

- **The pre-registration worked.** `dual_momentum`'s prereg predicted its own failure
  mode and was right. That prediction is only meaningful because it was committed
  before the run.
- **The robustness sweep did the real work.** Both strategies looked acceptable on
  headline numbers and both were undermined by one table. This is the argument for
  running robustness before believing anything, not after.
- **Criterion 3 was badly designed.** "Three distinct events" counts events without
  weighting them, so a result dominated by one event can still clear it. A future
  pre-registration should require the conclusion to survive *excluding the largest
  contributing event*, or require a post-2008 subsample to pass independently.
  This is a lesson for the next prereg, not grounds for re-grading this one.
- **Trial accounting held up.** 78 trials logged, of which only 6 are `search` and
  deflate the Sharpe; the other 72 are robustness re-runs of already-declared
  configurations. Without that distinction, honest robustness testing would have
  penalised these results as heavily as p-hacking.

## Ledger state

78 trials, 6 deflating. Holdout: **unconsumed.**

Search Sharpes to date: 0.805, 0.745, 0.705 (`sma_trend`); 0.542, 0.477, 0.614
(`dual_momentum`).

## Suggested next

1. Do not consume the holdout yet.
2. If continuing: write a third pre-registration with a repaired criterion set —
   post-2008 subsample must pass independently, and the result must survive dropping
   its largest contributing drawdown event.
3. Consider that the honest answer may already be visible. Drawdown protection is
   real and persistent (~13pp post-2008); it costs 3–5 points of annual return.
   *(Both halves of this sentence are revised by the benchmark addendum below:
   measured against a same-risk static mix rather than 100% SPY, the cost is
   roughly zero and the protection is roughly 2–4pp.)* That
   is a *trade*, not an edge, and whether it is worth making is a preference question,
   not one more backtest.

---

## Addendum: machine-graded verdicts

Criteria are now declared as data on each strategy and graded by the harness. The
verdicts it produced independently reproduce the hand-grading above:

| Criterion | sma_trend | dual_momentum |
|---|---|---|
| drawdown cut ≥ 0.10 | 0.3436 PASS | 0.2147 PASS |
| CAGR within −0.02 | 0.0017 PASS | 0.0021 PASS |
| protected in ≥ 3 events | 3 PASS | **2 FAIL** |
| plateau (every trial) | 0.3309 PASS | 0.2147 PASS |
| **Verdict** | **PASS** | **FAIL** |

Agreement between hand and machine is reassuring but is not the point. The point is
that every future verdict is produced by criteria committed before the run, so the
comparison no longer happens in the researcher's head.

Two numbers worth recording from the newly surfaced confidence block, both for
`sma_trend`:

- **Deflated Sharpe 0.974.** Not yet discriminating: at 6 search trials the
  threshold it must clear is only ~0.16 annualised. It rises to ~0.29 at 50 trials
  and ~0.41 at 1,000, so it will start biting on its own as the search widens. A
  high value here should not currently be read as validation.
- **Minimum track record: 57 years.** This is measured against the *benchmark's*
  Sharpe rather than against zero — "how long to confirm this beats buy-and-hold",
  not "how long to confirm it beats nothing". It is the concrete form of the
  earlier conclusion that live results cannot settle this question on any relevant
  horizon.

The holdout remains unconsumed, and is now guarded: a second consumption for the
same strategy is refused unless explicitly forced, and either way is recorded.

---

## Addendum: benchmarks that need no signal

*Added 2026-08-28. Implements [path_to_trading.md](path_to_trading.md) H1 and H3.*

Every number above compares the strategy to **100% SPY**. That comparison flatters
any rule that simply holds less equity — and `sma_trend` holds 12.44% volatility
against SPY's 20.66%. It is, in effect, a 60%-equity portfolio. So the question
the earlier sections actually answered was not "does the timing signal work" but
"does 60% equity behave differently from 100% equity", to which the answer was
never in doubt.

The harness now runs the strategy against a slate of portfolios that require **no
signal, no timing and no discipline**, all through the same engine, same lag, same
costs. Two are matched to the strategy's own realised exposure.

### `sma_trend`, full sample (2007-05-30 → 2022-12-30)

| | CAGR | max dd | vol | Sharpe | Δ CAGR | Δ max dd |
|---|---|---|---|---|---|---|
| **sma_trend** | 8.32% | −20.83% | 12.44% | 0.705 | — | — |
| buy & hold SPY | 8.15% | −55.19% | 20.66% | 0.483 | +0.17pp | +34.36pp |
| **vol-matched 60/40 SPY/BIL** | 5.65% | −36.14% | 12.44% | 0.504 | **+2.67pp** | **+15.32pp** |
| exposure-matched 73/27 SPY/BIL | 6.54% | −42.87% | 15.10% | 0.495 | +1.79pp | +22.04pp |
| 60/40 SPY/TLT | 7.58% | −29.92% | 11.59% | 0.689 | +0.74pp | +9.09pp |
| equal-weight basket | 7.35% | −22.74% | 9.78% | **0.774** | +0.97pp | +1.91pp |
| inverse-volatility basket | 8.04% | −22.14% | 9.11% | **0.895** | +0.28pp | +1.32pp |
| 100% cash (BIL) | 0.65% | −0.78% | 0.52% | 1.250 | +7.67pp | −20.05pp |

On the full sample the rule survives its matched benchmark: same volatility,
+2.67pp of CAGR, 15pp less drawdown. That is a real result and it was not
guaranteed.

But two static portfolios of the same four tickers — equal-weight and
inverse-volatility, neither of which contains a signal of any kind — **beat it on
Sharpe** (0.774 and 0.895 against 0.705), with comparable drawdowns. Whatever
`sma_trend` is doing, simply spreading across the basket did it better per unit of
risk, and needed no rule to follow.

### The start-date sweep, re-asked against the matched mix

This is where the addendum changes the reading.

**`sma_trend`**

| From | mix | CAGR | matched | Δ CAGR | max dd | matched | Δ max dd |
|---|---|---|---|---|---|---|---|
| 2007-05-30 | 60/40 | 8.32% | 5.65% | +2.67pp | −20.83% | −36.14% | +15.32pp |
| **2010-01-04** | 71/29 | 8.75% | 8.84% | **−0.09pp** | −20.83% | −24.84% | **+4.01pp** |
| 2013-01-02 | 70/30 | 7.06% | 8.89% | −1.83pp | −20.83% | −24.41% | +3.58pp |
| 2016-01-04 | 64/36 | 8.29% | 8.07% | +0.22pp | −20.83% | −22.46% | +1.63pp |

Both halves of the earlier conclusion shrink:

- **The 3–5pp annual "cost" was largely a benchmark artifact.** Against a mix
  carrying the same risk it is −0.09, −1.83 and +0.22 points — call it zero. The
  rule was not giving up 3–5 points a year to time the market; it was giving them
  up to hold less stock, which is a choice, not a cost of the signal.
- **So was most of the protection.** 12.9pp of drawdown saved against buy-and-hold
  becomes **1.6–4.0pp** against the matched mix. The signal contributes something,
  but it is a small fraction of what the headline number suggested.

Post-2008, `sma_trend` is roughly neutral against a portfolio that needs no
discipline to hold: a couple of points of drawdown protection at approximately no
return cost. That is a much weaker claim than either the pass verdict or the
earlier "real but expensive trade" framing, and it sits well inside the noise of a
sample containing about four independent bear markets. As before, the 2007 row is
the outlier, and as before the reason is 2008.

**`dual_momentum`**

| From | mix | CAGR | matched | Δ CAGR | max dd | matched | Δ max dd |
|---|---|---|---|---|---|---|---|
| 2007-05-30 | 72/28 | 8.36% | 6.47% | +1.90pp | −33.72% | −42.34% | +8.62pp |
| 2010-01-04 | 79/21 | 6.09% | 9.70% | −3.61pp | −33.72% | −27.34% | **−6.38pp** |
| 2013-01-02 | 87/13 | 5.95% | 10.78% | −4.83pp | −33.72% | −29.79% | **−3.93pp** |
| 2016-01-04 | 80/20 | 4.09% | 9.71% | −5.62pp | −33.72% | −27.64% | **−6.08pp** |

Post-2008 it is **strictly dominated on both axes** — worse return *and* worse
drawdown than a static mix at the same risk, in every window. The earlier verdict
was that its entire edge is 2008; this is the stronger form of it. Nothing further
is owed to this strategy.

### What this does and does not change

- **No verdict is re-graded.** Both strategies pre-registered against
  buy-and-hold, and their criteria were fixed before the runs. `sma_trend` still
  **PASSES** its pre-registration. Moving the bar after seeing results is the
  failure mode the whole harness exists to prevent, and it does not become
  acceptable because the new bar is a better one.
- **The next pre-registration should declare its benchmark.** That is H4, and
  the exposure-matched mix is the obvious candidate for it. Making a benchmark
  binding is a decision taken *before* a run, never after.
- **The recommendation not to spend the holdout stands**, and is now better
  supported. Promotion is a separate decision from passing, and the evidence the
  criteria were meant to establish is weaker after this addendum, not stronger.
- **Trial accounting.** These are re-runs of already-declared configurations, so
  all 54 were logged as `robustness`. The deflation is unchanged and no search
  budget was spent producing this section.

### Ledger state

141 trials, 15 of them `search`. Holdout: **unconsumed.**

(The `search` count is 15 rather than the 6 recorded earlier in this document: a
re-run of both strategies on 2026-08-28T00:08 was logged as `search`, before the
`--kind` flag existed. It is left as recorded — the ledger is append-only, and a
count that can be edited downward is not a guardrail.)
