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
   its largest contributing drawdown event. *(Since H4, such a pre-registration must
   also name the benchmark it is graded against; see the second addendum below.)*
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

---

## Addendum: the benchmark is now a declared choice

*Added 2026-08-28. Implements [path_to_trading.md](path_to_trading.md) H4.*

The addendum above ends by saying the next pre-registration should declare its
benchmark. It now must.

`Strategy` carries a `benchmark` field with no default, validated at import
against a fixed vocabulary (`buy_and_hold`, `vol_matched`, `exposure_matched`,
`sixty_forty`, `equal_weight`, `inverse_vol`, `cash`). A strategy that does not
name its bar does not import. The declared benchmark is checked before the sweep
logs a trial, and then resolves every `*_vs_benchmark` criterion, the per-event
attribution and the regret bundle. The report prints it beside the verdict.

**Nothing above is re-graded, and nothing above moved.** Both strategies are
recorded as declaring `buy_and_hold`, which is what their pre-registrations
actually said. Re-run through the new machinery they reproduce exactly:

| Criterion | sma_trend | dual_momentum |
|---|---|---|
| drawdown cut ≥ 0.10 | 0.3436 PASS | 0.2147 PASS |
| CAGR within −0.02 | 0.0017 PASS | 0.0021 PASS |
| protected in ≥ 3 events | 3 PASS | **2 FAIL** |
| plateau (every trial) | 0.3309 PASS | 0.2147 PASS |
| **Verdict** | **PASS** | **FAIL** |

Identical to the machine-graded table earlier in this document. That is the
result worth recording: the mechanism changed and no committed number did.

**What it changes is prospective.** The matched mix stops being a table nobody
has to answer to. A future strategy can declare `vol_matched` and then *fail*
against a portfolio that needs no signal, no timing and no discipline — which,
on the evidence of the previous addendum, is a bar neither existing strategy
would clear post-2008.

One honest limitation, stated here rather than discovered later: the two matched
mixes are constructed from the strategy's own realised volatility and exposure,
so declaring one pre-commits the *method*, not a fixed portfolio. It is fixed in
advance and cannot be swapped afterwards, but it is a weaker commitment than
naming `sixty_forty` outright. The report says so on any run that uses one.

### Ledger state

147 trials, 15 of them `search`. Holdout: **unconsumed.**

The six new trials are the two strategies re-run to confirm the verdicts above,
logged as `robustness`: re-runs of already-declared configurations under new
reporting, which is what that tag means. No search budget was spent, and the
deflation is unchanged.

---

## Addendum: the harness reproduces a published result

*Added 2026-08-28. Implements [path_to_trading.md](path_to_trading.md) G2.*

Everything above assumes the machinery is correct. Until now that assumption
rested on unit tests written by the same person who wrote the code. This addendum
checks it against someone else's numbers, published before this project existed.

Faber's 10-month timing rule was re-implemented and run through **the same engine,
the same single `.shift(1)` and the same statistics** as any strategy here, then
compared to his 2013 update. Run it with `python -m backtest.cli reproduce`.

| Check | Published | Ours | Gap |
|---|---|---|---|
| buy & hold, compound return 1901–2012 | 9.32% | 9.49% | +0.17pp |
| buy & hold, mean annual return | 11.26% | 11.33% | +0.07pp |
| buy & hold, drawdown in the 1929–32 bear | −83.66% | −81.76% | 1.90pp |
| timing, drawdown in the 1929–32 bear | −42.24% | −43.77% | 1.53pp |
| timing, share of months invested | ~70% | 69.79% | 0.21pp |
| buy & hold, drawdown of the 2008–09 bear (SPY) | −50.95% | −50.78% | 0.17pp |
| timing exits during October 2000 | yes | yes | exact |
| timing out of the market by January 2008 | yes | yes | exact |
| timing, compound return 1901–2012 | 10.18% | 11.29% | **+1.11pp** |

**Seven match; two are explained.** The buy-and-hold rows carry the most weight
because they involve no signal, no cash and no parameters — they isolate data →
engine → statistics and nothing else, and they land within 0.17pp on a 112-year
compound return.

The timing model's *return* runs about a point hot. The cause is that Faber's
series is Global Financial Data's month-end closes, which is paywalled, while
ours is Shiller's — whose prices are *monthly averages of daily closes*. For a
trend rule that is not cosmetic: it changes which months the signal is invested.
Rather than assert that, it was measured. Both conventions were built from one
daily SPY series and the same rule run on each: **monthly averaging alone moves
the timing compound return by +0.20pp over twenty years, in the same direction.**
Direction confirmed, magnitude of the right order, residual attributed but not
fully accounted for. Those rows are recorded as EXPLAINED, which is deliberately
a weaker claim than MATCH.

### What this does and does not license

- **It does not make any strategy result more likely to be right.** It removes one
  competing explanation for them being wrong. `sma_trend` is still roughly neutral
  against a same-risk static mix post-2008, and G2 says that finding is not a
  measurement error.
- **It raises the value of G4.** A 1.6–4.0pp effect measured by a corroborated
  pipeline deserves a confidence interval; the same effect from an unverified
  pipeline deserved a bug hunt first. That ordering is now settled.
- **It costs no trials.** Reproducing a published result is a check on the
  machinery, not a search for a strategy. The ledger is untouched at 147.

### An error worth recording

The first comparison showed the timing model's max drawdown at −47.45% against
Faber's −42.24% — a 5.2pp gap that looked like a real problem. It was not. Our
figure was the model's worst drawdown *of the century*, which occurs in **1941**;
Faber's is the drawdown during the **1929–32** bear he was describing. Measured on
the same episode the gap is 1.53pp.

Two different events, compared as though they were one. The lesson generalises
past this check: a drawdown figure is meaningless without the window it was
measured over, and that applies to every drawdown number in this document.

### It is now a test, not an event

`tests/test_reproduce.py` runs the reproduction on every test run and asserts no
check fails without a stated explanation. The reference data is committed and its
checksums asserted, because a reproduction that re-downloads its inputs is not
one. And following the same principle as the look-ahead fixture — a check that has
never caught anything is not known to work — one test deliberately breaks the lag
and requires the reproduction to *stop* agreeing with Faber.

### Ledger state

147 trials, 15 of them `search`. Holdout: **unconsumed.**

---

## Addendum: what survives a confidence interval

*Added 2026-08-29. Implements [path_to_trading.md](path_to_trading.md) G4.*

Every number in this document has been a point estimate drawn from one history
containing about four independent bear markets. G2 established that those numbers
are not a pipeline bug. This addendum asks the remaining question: are they
distinguishable from luck?

Intervals come from a paired stationary block bootstrap — blocks of consecutive
days, because these rules exist *because* of serial dependence and shuffling it
away would price a world they were never claimed to work in; paired, because the
claims are differences and the two series meet the same market on the same days.
10,000 resamples, mean block 63 trading days, seed pinned, 90% coverage.

### The differences, with their intervals

Point estimate, then the 90% interval. **Bold** marks the only rows that exclude
zero.

**`sma_trend`**

| From | Against | Δ CAGR | Δ max drawdown | Δ Sharpe |
|---|---|---|---|---|
| 2007-05-30 | buy & hold | +0.17pp [−5.66, +6.45] | **+34.36pp [+0.97, +42.01]** | +0.22 [−0.14, +0.58] |
| 2007-05-30 | vol-matched mix | +2.67pp [−1.33, +6.78] | +15.32pp [−11.22, +20.84] | +0.20 [−0.16, +0.56] |
| 2010-01-04 | buy & hold | −3.18pp [−7.22, +0.53] | +12.89pp [−3.51, +20.20] | +0.00 [−0.27, +0.25] |
| 2010-01-04 | vol-matched mix | −0.09pp [−3.42, +3.10] | +4.01pp [−10.83, +10.05] | −0.01 [−0.28, +0.24] |

**`dual_momentum`**

| From | Against | Δ CAGR | Δ max drawdown | Δ Sharpe |
|---|---|---|---|---|
| 2007-05-30 | buy & hold | +0.21pp [−5.56, +6.41] | +21.47pp [−2.87, +35.57] | +0.13 [−0.19, +0.50] |
| 2007-05-30 | vol-matched mix | +1.90pp [−2.61, +6.52] | +8.62pp [−12.38, +22.17] | +0.12 [−0.21, +0.49] |
| 2010-01-04 | buy & hold | **−5.84pp [−10.42, −1.83]** | +0.00pp [−10.54, +7.65] | −0.23 [−0.48, +0.03] |
| 2010-01-04 | vol-matched mix | −3.61pp [−7.68, +0.16] | −6.38pp [−17.41, +1.70] | −0.24 [−0.48, +0.03] |

### Reading this

**Two of sixteen differences exclude zero, and one of them is bad news.**

1. `sma_trend`'s full-sample drawdown reduction against buy & hold. Note the
   shape: a point estimate of +34.36pp with a lower bound of **+0.97pp**. The
   interval excludes zero by a hair while spanning forty points. "This reduced
   drawdown by something between one point and forty" is technically a finding
   and practically not one.
2. `dual_momentum`'s post-2008 CAGR against buy & hold, at −5.84pp
   [−10.42, −1.83]. Distinguishable underperformance. That strategy was already
   finished; this is the epitaph.

**Every single comparison against the vol-matched mix straddles zero.** Including
the one the project's live claim rests on: post-2008 drawdown protection of
+4.01pp has an interval of [−10.83, +10.05]. Against a portfolio holding the same
risk with no signal, no timing and no discipline, this sample cannot tell
`sma_trend` apart from doing nothing — on return, on drawdown, or on Sharpe.

The verdicts are stable across block lengths of a month, a quarter and half a
year, so this is not an artifact of the one parameter the method has.

### What this does not say

- **It is not proof the rule does nothing.** A wide interval is ignorance, not
  refutation. The honest statement is that ~15 years containing about four
  independent bear markets cannot resolve an effect of this size, which is a fact
  about the sample as much as about the rule.
- **It does not make the drawdown protection unreal.** `sma_trend` did hold a
  −20.83% drawdown against SPY's −55.19%. What the interval denies is that we can
  attribute the part not explained by holding less equity to the *signal* rather
  than to how this particular history fell out.
- **A bootstrap cannot invent a bear market of a kind never observed.** Four
  resampled bear markets are still four bear markets. If anything this
  understates the uncertainty, since it can only rearrange crises we have seen.
- **Drawdown intervals are optimistic** by construction: resampling chops the long
  declines that produce the worst drawdowns. That biases the *levels*; the paired
  differences are far less affected, because both series are cut in the same
  places. It is another reason to read the difference rows and not the level rows.

### Where this leaves the project

The sequence has now removed the two competing explanations for the headline
result in order. H1 asked whether it was just holding less equity, and most of it
was. G2 asked whether it was a measurement error, and it was not. G4 asks whether
what remains is distinguishable from luck, and it is not.

That is close to an answer. [path_to_trading.md](path_to_trading.md) **A3** exists
precisely so "do not trade" can be a recorded endpoint with reasoning attached
rather than an embarrassment, and the evidence now points there for both
strategies currently on the bench. What it does *not* license is quietly searching
for a third strategy until something clears — the ledger counts, and the bar rises
with it.

### Ledger state

174 trials, 15 of them `search`. Holdout: **unconsumed.**

The bootstrap logs nothing: an interval measures a result that already exists, it
is not a new configuration. The additional trials are re-runs performed to produce
the tables above, all `robustness`.

(The `search` count is 15 rather than the 6 recorded earlier in this document: a
re-run of both strategies on 2026-08-28T00:08 was logged as `search`, before the
`--kind` flag existed. It is left as recorded — the ledger is append-only, and a
count that can be edited downward is not a guardrail.)
