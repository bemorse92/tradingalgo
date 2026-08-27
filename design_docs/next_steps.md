# Next Steps

Proposed sequence from "harness built" to "the project has produced a defensible answer."
Extends the build order in [scaffolding.md](scaffolding.md), which is complete through step 6.

**Ordering principle:** the trial ledger starts counting at the first real run. Everything
mechanical done before that is free; everything after costs N and deflates every result
that follows. Do the fiddling while it is still free.

Items marked **[decision]** need Ben; the rest are buildable without input.

---

## Phase 0 — Close the record

Nothing here touches real prices, so none of it costs a trial.

**0.1 Commit the scaffolding.** Git timestamps are the enforcement mechanism for
pre-registration. Until the harness is committed, a prereg's commit date proves nothing.
This should happen before anything else.

**0.2 Decide and arm the holdout. [decision]** `HOLDOUT_START` in `backtest/validate.py` is
`None`, so the gate is currently inert — the one Tier 1 guardrail not yet armed. Reserving
roughly the last 3–5 years is conventional, but note the tension specific to this project:
the recent window contains 2020 and 2022, the two regimes most worth testing against. A
holdout that swallows both leaves the in-sample period thin on stress events; one that
excludes them isn't really testing the interesting question. Worth choosing deliberately.

**0.3 Decide the slippage assumption. [decision]** Defaulted to 5 bps one-way. On liquid
ETFs at small size that is defensible-to-conservative. Phase 2.2 tests sensitivity, so this
does not need to be exactly right — only stated in advance.

**0.4 Decide whether cash is a sleeve. [decision]** The engine currently treats uninvested
capital as earning exactly 0%. That is a real modelling choice, and the research flagged it
as a common way timing backtests distort themselves. The literature's supported version of
this rule exits to *cash*, not to TLT/GLD. Testing that variant honestly means adding BIL
(or a T-bill series) to the basket and taking a new snapshot — a small change, but it must
be decided before the prereg, because adding it later is a new trial.

**0.5 Build the remaining harness pieces.** All small, all better done now:

- **Pre-registration template** (`strategies/_TEMPLATE.prereg.md`) — the artifact the whole
  gate depends on should not be improvised at the moment of first use.
- **Whipsaw / regret statistic** — the guardrails doc calls for worst rolling
  underperformance vs buy-and-hold in the standard report, and it is not built. This is the
  number that decides whether a rule is *followable*, and it is what killed the commercial
  tactical funds. Genuine gap.
- **Rebalance-frequency helper** — the literature's version rebalances month-end, not daily.
  A strategy can express that today, but only by hand-rolling it. A helper keeps it out of
  every strategy and makes rebalance frequency a declarable `fixed` parameter instead of
  bespoke code.
- **Trial kind tagging (`search` vs `robustness`)** — this one matters more than it looks.
  A start-date sweep of 5 dates × 4 parameters logs 20 trials, which currently inflates N
  exactly as if you had searched for a winner 20 times. But N in the deflated Sharpe means
  *configurations selected among*, not re-runs of one configuration for robustness. Without
  this distinction the harness penalises robustness testing — which we want to encourage —
  identically to p-hacking, which we want to discourage. Tag them, and deflate on `search`
  trials only.
- `results/.gitkeep` so the ledger's home exists in a fresh clone.

---

## Phase 1 — First pre-registered strategy

**1.1 Choose the rule. [decision]** The literature's obvious first candidate is a
Faber-style trend filter: hold SPY while above a long moving average, rotate to the
defensive sleeve otherwise. It has one fitted parameter, a stated mechanism, and the best
out-of-sample record in the space — which makes it the right *first* test precisely because
it is the one most likely to survive.

**1.2 Write and commit the pre-registration. [decision]** Rationale, exact rule,
`fixed` vs `fitted` split with grids, sample period, success criteria, and a prediction.
Committed before the first run. This is the document the whole harness exists to serve.

**1.3 Run it.** `python -m backtest.cli run <name>`. Milestone: the machine produces a
real, recorded answer.

---

## Phase 2 — Robustness

All mechanical, all logged, all tagged `robustness` once 0.5 lands.

- **2.1 Start-date sweep** (already built). If the conclusion depends on starting before
  2008, the finding is "2008 happened."
- **2.2 Cost sensitivity** — re-run across a range of bps. A result that dies at 15 bps was
  never real.
- **2.3 Defensive sleeve comparison** — cash vs TLT vs GLD. Each counts as a search trial,
  not robustness: choosing among them after seeing results is fitting.
- **2.4 Named stress windows** — 2020 (V-recovery, punishes trend rules) and 2022
  (correlated selloff, breaks the defensive sleeves). Both are required reading per the
  strategy doc; neither is optional.

---

## Phase 3 — Verdict against the pre-registered bar

Compare to the criteria written in 1.2, not to whatever looks best. Three outcomes, all
legitimate:

- **Clears the bar** → proceed to Phase 4.
- **Fails** → record the negative result in the ledger and stop, or iterate with the trial
  count visible and the deflation growing. A recorded failure is a successful run.
- **Inconclusive** → the most likely outcome given ~4 independent bear markets, and the one
  to be honest about rather than resolve by trying harder.

---

## Phase 4 — Holdout release

Only if Phase 3 clears, and only once. `--allow-holdout` records the access in the ledger.
Treat it as one-way: a holdout consulted twice is not a holdout, and there is no second one.

---

## Phase 5 — Operating discipline

Only relevant if Phase 4 clears.

- **Kill criteria, written before any capital.** Framed as model invalidation — "the
  strategy did something the backtest said was near-impossible" — not as a loss limit. The
  literature's anchors: 1.5× backtest max drawdown, or recovery exceeding 3× the formation
  period.
- **Review cadence**, fixed in advance, so the decision to continue is never made in the
  middle of a drawdown.
- **Sizing** is already settled: 5% of the Roth, sized as fully losable. The guardrail is
  simply not revisiting that cap because a backtest looks good.
- Remember that live results will not validate anything on any relevant horizon (see the
  MinTRL discussion in [research_guardrails.md](research_guardrails.md)). Phase 5 is
  execution, not further evidence-gathering.

---

## Deferred

- **Block bootstrap confidence intervals** (Tier 2) — worth building once there is a result
  worth putting an interval around, not before.
- **Walk-forward analysis** — earns its cost only if parameters are ever re-fit. With a
  pre-committed parameter it adds little.
- **`uv` migration** — cheap two-way door, no urgency.
