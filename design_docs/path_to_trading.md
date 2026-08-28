# Path to Placing Trades

Working backwards from the end state Ben actually wants, to the platform
capabilities that have to exist first. These are **objectives, not tasks** — each
describes a capability the framework must have, why it is needed, and what "done"
looks like. Sequencing matters more than sizing.

Written 2026-08-28. Assumes familiarity with [findings.md](findings.md) and
[research_guardrails.md](research_guardrails.md).

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

## Rough sequence

**A → B → C → D → E**, with F running alongside C.

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
