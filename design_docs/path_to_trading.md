# Path to Placing Trades

Working backwards from the end state Ben actually wants, to the platform
capabilities that have to exist first. These are **objectives, not tasks** — each
describes a capability the framework must have, why it is needed, and what "done"
looks like. Sequencing matters more than sizing.

Written 2026-08-28. Assumes familiarity with [findings.md](findings.md) and
[research_guardrails.md](research_guardrails.md).

**Progress.** Objectives are marked **Built** inline as they land, with what the
result actually was — an objective completed without recording what it changed is
half a record. Done so far: **H1** and **H3** (2026-08-28). Everything else below
is open.

---

## The end state

On a defined morning, Ben opens the tool and it tells him: *here is what you should
be holding, here is what you actually hold, here is the difference, place these
trades.* He places them manually, records what actually filled, and the tool keeps
score. If the strategy ever breaks its own rules, the tool says so before he has to
notice.

Everything below is what stands between here and that.

---

## What already exists

The research half is built and working: pinned data, a simulator that cannot see the
future, pre-registration, an automatic trial log, mechanically graded criteria, a
guarded one-shot holdout, and reports that surface per-event dependence, whipsaw, and
robustness. Two strategies have been through it end to end.

Since 2026-08-28 it also compares every strategy against a slate of portfolios that
need no signal to follow — including static mixes matched to the strategy's own
realised volatility and equity exposure (H1, H3). That comparison did not overturn
the existing findings but it shrank them substantially on both sides, and it is
what a result now has to survive to mean anything. Since H4, which of those
comparisons grades a strategy is declared on the strategy itself and checked before
the run, so the harder bar is binding rather than merely printed.

**None of it produces an instruction.** The framework can currently tell you what
*would have* happened. It has no concept of today, of what Ben holds, or of a trade.
That gap is the bulk of the work below.

---

## A. Close the search before selecting

**A1. Comparison on equal terms.**
Every result's honesty penalty is calculated against the trial count *at the moment
it ran*, so a strategy tested early looks better than an identical one tested late.
Comparing candidates today would compare accidents of timing.

*Needed:* the ability to re-grade every candidate against the final, complete trial
record, so they are ranked on the same footing.

*Done when:* one command produces a ranked slate of every strategy ever tested,
scored against the total search, and re-running it does not change the ranking.

**A2. A declared end to searching.**
Selection is only meaningful once fishing has stopped. While new ideas are still
being tried, any "best" is provisional.

*Needed:* an explicit, recorded moment where the candidate set is frozen. After it,
new ideas start a new round rather than quietly joining this one.

*Done when:* the slate from A1 is committed and dated, and the tool can tell whether
a given result predates or postdates the freeze.

**A3. Permission to conclude "none of them."**
This is a real and reasonably likely outcome. The evidence so far is that drawdown
protection is real but costs 3–5 points of annual return — a trade, not an edge.
H1 has since narrowed this further: measured against a same-risk static mix rather
than 100% SPY, the post-2008 protection is 1.6–4.0pp at approximately no return
cost. Smaller on both sides, and well inside the noise.

*Needed:* the decision gate must accept "do not trade" as a valid, recorded endpoint
rather than an embarrassing dead end.

*Done when:* the framework has a way to record a strategy as retired-without-trading,
with the reasoning, so it is not silently re-litigated later.

---

## B. Confirm, once

**B1. A holdout protocol written before the holdout is opened.**
The sealed 2023+ data can be used once. Right now there is no rule for what its
result *means* — and deciding that after seeing it is exactly the failure the whole
project is built against.

*Needed:* a pre-committed statement of what holdout result constitutes go, what
constitutes stop, and what constitutes inconclusive.

*Done when:* the protocol is committed, and it names thresholds, not adjectives.

**B2. The release itself.**
*Done when:* the holdout has been consumed exactly once for the chosen candidate, the
result is recorded, and B1's protocol has been applied without amendment.

---

## C. Turn research into an instruction

This is the largest gap and the one that most changes what the framework *is*.

**C1. Current-signal generation.**
The framework must answer "what should be held *today*" from the most recent data,
not "what would have been held historically."

*Needed:* a run mode that takes fresh data and emits a target allocation for now.

*Done when:* one command prints today's target holding, and the same code path that
produced the backtest produces it — so the thing being traded is the thing that was
tested, not a re-implementation.

**C2. Knowledge of what is actually held.**
The framework currently has no concept of a portfolio. Without knowing current
holdings it can state a target but cannot state a *change*.

*Needed:* a record of actual positions and account value, maintained by hand, that
the tool reads.

*Done when:* the tool can show current holdings alongside the target and flag drift
between them.

**C3. Trade instructions, not allocations.**
"Hold 100% BIL" is not something Ben can act on. "Sell 143 SPY, buy 1,190 BIL" is.

*Needed:* translation from target weights to concrete orders — whole shares, current
prices, account value — plus a minimum-change threshold so the tool never asks for a
trade too small to be worth placing.

*Done when:* the output is a short list of orders Ben can execute without doing any
arithmetic himself.

**C4. A decision calendar, and a rule for missing it.**
The tested strategies rebalance at month end. Real life means some month ends get
missed.

*Needed:* a defined decision date, and a pre-committed rule for what to do when a
decision is late — act anyway, or skip to the next date.

*Done when:* the rule is written down and the tool applies it rather than leaving it
to judgement in the moment. A late decision handled ad hoc is an untested strategy.

---

## D. Record what actually happened

**D1. A trade journal.**
Manual execution means intended and actual will diverge — different prices, wrong
day, fat fingers, forgot.

*Needed:* a record of what was instructed versus what actually filled, with dates and
prices.

*Done when:* every instruction has a recorded outcome, including "not placed."

**D2. Friction tracking.**
The backtests assume 5 bps of slippage. Nobody knows whether that is right.

*Needed:* comparison of assumed cost against what trades actually cost.

*Done when:* the tool can report realised versus assumed cost, so the assumption
becomes a measurement.

---

## E. Monitor, and know when to stop

**E1. Live versus expected tracking.**
With the honest caveat established earlier: live results **cannot** confirm the
strategy works — that would take roughly 57 years. What they *can* do is detect that
something is broken: a mis-implemented signal, a data problem, costs far above
assumption, or behaviour the backtest never produced.

*Needed:* an ongoing comparison of realised results against what the backtest said to
expect over the same window.

*Done when:* the tool distinguishes "this is a normal bad stretch" from "this is not
behaving like the thing that was tested" — and is explicit that only the second is
informative.

**E2. Kill criteria, evaluated automatically.**
Framed as model invalidation, not loss limits: *the strategy did something the
backtest said was near-impossible.* The literature's anchors are a drawdown 1.5× worse
than anything backtested, or a recovery taking 3× longer than any in the record.

*Needed:* these written into the pre-registration before any money moves, and checked
by the tool on every run rather than remembered.

*Done when:* a breach produces a loud, unambiguous output — not a number Ben has to
notice.

**E3. A fixed review cadence.**
The most common way people lose money with a working rule is abandoning it during a
normal bad stretch. The defence is deciding *when* you will reconsider, before you
have any reason to want to.

*Needed:* a scheduled review with a defined scope, so continuation is never decided in
the middle of a drawdown.

*Done when:* the cadence is written down and the tool reports on that schedule.

---

## F. Operational trust

**F1. A freshness and integrity gate.**
The single worst outcome is placing a real trade based on stale or broken data.

*Needed:* the tool refuses to issue instructions if the data is out of date, fails its
checksum, or is missing recent days.

*Done when:* the failure mode is a refusal with a clear reason, never a plausible-
looking instruction.

**F2. One repeatable routine that either completes or clearly fails.**
Decision day should be a single command that runs everything — refresh, verify,
signal, compare, instruct — with no half-finished states.

*Done when:* the routine is one step, and a partial run is impossible to mistake for a
successful one.

---

## G. Know whether the evaluation itself is good enough

Everything so far assumes the way results are judged is sound. That assumption has
not been tested against anything external.

**G1. Gap analysis against established evaluation methods.**
The harness implements a specific subset of what the literature offers, and some
omissions were deliberate while others are simply unexamined. Known candidates not
built: probability-of-backtest-overfitting via combinatorial cross-validation,
White's Reality Check and Hansen's SPA test (bootstrap methods for testing a whole
universe of rules at once — directly relevant if strategy generation is automated),
drawdown-focused metrics beyond maximum (Ulcer index, time-under-water distribution,
Calmar), and factor attribution to check whether an apparent edge is just market
exposure timing in disguise.

*Needed:* a documented survey of what exists, what this project uses, what it
deliberately skips and why, and what it should adopt.

*Done when:* the choice of evaluation methods is a defended position rather than an
accident of what got built first.

**G2. Validate the harness against published results.**
The statistics are unit-tested against known values, but no *strategy* result has
ever been checked against an external source. If our Faber implementation reproduces
Faber's published figures over the overlapping period, that is strong evidence the
whole pipeline is correct. If it does not, something is wrong and every result so far
is suspect.

*Needed:* at least one strategy reproduced against externally published numbers.

*Done when:* the discrepancy is either negligible or explained.

**G3. Rebalance-timing sensitivity.**
Start-date sensitivity is tested; rebalance-date sensitivity is not. A rule that works
rebalancing on the last trading day of the month but not on the 15th is fitted to a
calendar artifact, not to a market effect.

*Done when:* results are reported across several rebalance offsets, the same way they
are across start dates.

**G4. Confidence intervals around the headline numbers.**
Every result is currently a point estimate. With roughly four independent bear markets
in the sample, the uncertainty is large and invisible.

*Needed:* block bootstrap intervals, with the honest caveat attached — a bootstrap
quantifies uncertainty in the data you have, it does not manufacture new information,
and it cannot invent a bear market of a type never observed.

*Done when:* headline claims carry intervals, and the intervals are wide enough to be
uncomfortable, which they will be.

**G5. Regime-conditional evaluation.**
Aggregate statistics hide that a rule may work in one environment and fail in another.
2022 already showed this: rising rates broke the defensive sleeves.

*Done when:* results can be broken out by regime (rate direction, inflation, equity
trend) rather than only by drawdown event.

---

## H. Benchmarks that make a result defensible

Buy-and-hold SPY is the right primary benchmark, but on its own it is too easy a
comparison, and it flatters any strategy that simply reduces market exposure.

**H1. Exposure-matched benchmarks — the important one.**
`sma_trend` runs at 12.4% volatility against SPY's 20.7%. It is roughly a 60%-exposure
portfolio. The honest question is therefore not "does it beat 100% SPY" but **"does it
beat statically holding 60% SPY and 40% cash?"** — a portfolio requiring no signal, no
timing, and no discipline. If a static mix matches it, the rule contributes nothing and
the entire result is explained by holding less stock.

*Needed:* automatic construction of a static benchmark matched to the strategy's
realised exposure or volatility.

*Done when:* every strategy report shows it, and it is treated as a criterion rather
than a curiosity. **This is the single most likely way the current results get
overturned.**

**Built 2026-08-28** (`backtest/benchmarks.py`). Volatility-matched and
exposure-matched SPY/BIL mixes are built for every run and shown in the standard
report and the start-date sweep. Results in
[findings.md](findings.md#addendum-benchmarks-that-need-no-signal): it did not
overturn the findings but it materially shrank them. `sma_trend` clears the matched
bar on the full sample and is roughly neutral against it post-2008 — the 3–5pp
annual "cost" was mostly a benchmark artifact, and so was most of the 12.9pp of
protection. `dual_momentum` is strictly dominated on both axes post-2008.

Reported, not graded: both strategies pre-registered against buy-and-hold, and
making the matched mix binding after seeing results would be exactly the move the
harness exists to prevent. Binding it is H4's job, on the next pre-registration.

**H2. A random-timing benchmark.**
Related but distinct: a rule that enters and exits at random with the *same turnover*
and *same time-in-market* as the strategy. This isolates whether the signal carries
information, or whether being out of the market sometimes is doing all the work.

*Done when:* results are reported against a distribution of random-timing runs, not a
single one, so the strategy's percentile against luck is visible.

**H3. Standard portfolio benchmarks.**
60/40, equal-weight the basket, inverse-volatility weighting, and 100% cash. These are
what a reasonable person would otherwise do, and 60/40 in particular is the comparison
the tactical-fund literature used when it found most such funds underperforming.

**Built 2026-08-28**, alongside H1. Inverse-volatility is restricted to the risky
sleeves: including BIL makes it degenerate, since near-zero volatility would take
essentially the whole portfolio. The unexpected result is that equal-weight and
inverse-volatility static baskets **beat `sma_trend` on Sharpe** over the full
sample (0.774 and 0.895 against 0.705) at comparable drawdowns, with no signal of
any kind. Worth taking seriously: spreading across the basket outperformed timing
it, per unit of risk.

**H4. Benchmark as a declared choice.**
Which benchmark a strategy must beat should be part of its pre-registration, not
selected afterwards from whichever it happens to beat.

*Done when:* benchmark selection is declared data on the strategy, graded like any
other criterion.

**Built 2026-08-28.** H1 built the matched benchmark but deliberately left it
*reported, not graded*: `sma_trend` and `dual_momentum` pre-registered against
buy-and-hold, and binding them to a harder bar after seeing the numbers is the move
the harness exists to prevent. So the matched mix was a table nobody had to answer
to. It no longer is.

`Strategy` now carries a `benchmark` field, validated at import against a fixed
vocabulary of keys (`buy_and_hold`, `vol_matched`, `exposure_matched`,
`sixty_forty`, `equal_weight`, `inverse_vol`, `cash`). There is **no default** — a
strategy that does not name its bar does not import, because inheriting
buy-and-hold silently is the exact failure this closes. The declared benchmark is
checked in pre-flight, before the sweep logs a single trial, and then drives every
`*_vs_benchmark` criterion, the per-event attribution and the regret bundle. The
report names it beside the verdict and marks its row in the slate.

*Keys, not display names, and the distinction is load-bearing.* The two matched
mixes are built from the strategy's own realised volatility and exposure, so their
composition ("vol-matched 60%/40% SPY/BIL") is not knowable until the run is over.
Declaring one therefore pre-commits the *method of construction*, not a fixed
portfolio. That is still a real commitment — fixed in advance, not selectable from
the slate afterwards — but a weaker one than naming `sixty_forty` outright, and the
report says so on every run that uses one.

**Both existing strategies were recorded as declaring `buy_and_hold`**, which is
what their pre-registrations actually said. Their verdicts re-ran identically under
the new machinery — `sma_trend` PASS at 0.3436 / 0.0017 / 3 / 0.3309,
`dual_momentum` FAIL at 0.2147 / 0.0021 / **2** / 0.2147 — matching
[findings.md](findings.md#addendum-machine-graded-verdicts) exactly. Upgrading them
to the matched bar now would be re-grading a committed result against a bar chosen
after the fact, which is the thing this field exists to prevent. The harder bar
applies to the next pre-registration, which is where it belongs.

The pre-registration template now carries a **Benchmark** section with the
vocabulary, the evidence for why buy-and-hold is the easy answer, and a blank to
fill in.

---

## I. LLM-assisted strategy generation

Wanted explicitly, and genuinely useful — but it collides head-on with two things
already established, and the collision is worth designing around rather than
discovering later.

**The tension, stated plainly.** The project's stated design goal is deterministic
tools first, nondeterminism as a last resort. More seriously: automated strategy
generation is a *trial-count multiplier*, and the honesty penalty scales with trials.
Generating and testing 500 strategies raises the bar every candidate must clear from
roughly 0.16 to 0.41 annualised — and retroactively devalues every result produced so
far. Done naively, this is automated p-hacking with a machine that never gets tired.
It also directly violates the protocol item that a strategy should begin from an
economic rationale rather than from search.

None of that makes it a bad idea. It makes the *design* load-bearing.

**I1. Generation as hypothesis assistance, not search.**
The safe and most valuable mode: the model proposes a *mechanism* with a stated
economic rationale, drafts the pre-registration including criteria and a falsification
condition, and implements the rule — but nothing runs until a human reviews and
commits the pre-registration. The tedious half is automated; the declared-hypothesis
half is preserved.

*Done when:* a proposed strategy arrives as a reviewable pre-registration plus
implementation, and the harness still refuses to run it uncommitted.

**I2. Bulk generation as null calibration — the useful repurposing.**
Rather than fighting the trial-count problem, use it. Let the model generate hundreds
of *plausible-sounding* strategies and run them all, deliberately, as noise. The best
of that population tells you empirically what "best of N plausible ideas" looks like
by luck alone — on this data, this universe, this sample length. That is a far better
threshold for a real candidate to beat than a theoretical formula, because it is
calibrated to the actual problem.

This converts the dangerous capability into a measuring instrument: the generator
produces the null distribution, not the candidates.

*Done when:* the empirical best-of-N distribution is available and real candidates are
scored against it.

**I3. Strict isolation in the trial record.**
Bulk-generated runs must be logged under their own kind — neither `search` nor
`robustness` — so they build the null distribution without inflating the penalty on
independently declared human candidates.

**The rule that makes this honest:** isolation holds *only* while the two searches are
genuinely separate. If a human candidate is chosen **because** the bulk sweep surfaced
it, every one of those trials counts toward its penalty. Promotion from the generated
pool to a real candidate must be recorded as exactly that, and re-scored accordingly.

*Done when:* the ledger distinguishes the three kinds, and promotion out of the
generated pool is an explicit, recorded act that carries the full trial count with it.

**I4. The trap, named so it stays named.**
The failure mode is running a large generated sweep, seeing something excellent, and
treating it as a discovery. It will not be one — that is precisely what the
best-of-many calculation predicts from worthless inputs. Anything surfaced this way
must go back through I1: a stated mechanism, a fresh pre-registration, and ideally
confirmation on data the sweep never touched.

*Done when:* this is written into the pre-registration template, not just this
document.

---

## Rough sequence

**G and H come before A**, and are the highest-value remaining research work: they
determine whether the existing results mean anything.

**H1 and H3 are done (2026-08-28), and the sequencing argument held.** H1 was the
item most likely to overturn the findings, and doing it before selecting a candidate
was correct: it changed what the existing results mean. It did not kill `sma_trend`
— the rule clears its matched benchmark on the full sample — but post-2008 it is
roughly neutral against a static mix at the same risk, and both the apparent cost
(3–5pp of CAGR) and the apparent benefit (12.9pp of drawdown protection) were
mostly artifacts of comparing a ~60%-equity portfolio to a 100%-equity one.
`dual_momentum` is now strictly dominated post-2008 and is finished. An unplanned
finding worth chasing: signal-free equal-weight and inverse-volatility baskets beat
`sma_trend` on Sharpe, which points at allocation rather than timing.

**H4 is done (2026-08-28).** It was small, as expected, and it changed no committed
number — by design: both existing strategies declared what they had actually
pre-registered against, and both verdicts reproduced exactly. What it changed is
that the next pre-registration cannot quietly grade itself against the easy
comparison, and the matched mix is now something a strategy can fail.

**What remains in H: H2** (random-timing null with matched turnover and
time-in-market). It separates "the signal carries information" from "being out of
the market sometimes does all the work" — the natural next question given how small
the matched edge turned out to be, and the one H4 makes actionable, since a
strategy can now declare that it must beat the null rather than merely be shown
next to it.

**G is now the larger open block**, and H1's outcome raises the value of two of its
items in particular: **G2** (reproduce Faber's published numbers) because the matched
benchmark is now doing real work and a pipeline bug would be expensive, and **G4**
(block bootstrap intervals) because a 1.6–4.0pp effect is exactly the size where a
point estimate is not an answer. G1, G3 and G5 are unchanged.

**I runs alongside them.** I1 (hypothesis assistance) is available immediately. I2
(null calibration) is most valuable *just before* A, since its output is the threshold
A ranks candidates against.

Then **A → B → C → D → E**, with F running alongside C.

A and B are decisions and small amounts of work; they are also gates — doing C before
them means building execution machinery for a strategy that may not survive
confirmation.

C is the real build and the point where this stops being a research bench and becomes
an operating tool.

D and E only matter once trades are actually being placed, but **E2 (kill criteria)
must be written before the first one**, not after.

## The honest caveat to carry through all of it

Nothing in this plan produces confidence that the strategy works. That is not
available: the calculation says confirming it beats buy-and-hold would take about 57
years of live results. What this plan produces is the ability to *act on a decision
already made*, to notice when something is broken, and to stop for stated reasons
rather than out of discomfort. The evidence for the decision itself came from the
research half, and it is as good as it is going to get.
