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
   real and persistent (~13pp post-2008); it costs 3–5 points of annual return. That
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
