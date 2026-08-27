# Research Guardrails

Operational answer to the deferred overfitting question in
[high_level_strategy.md](high_level_strategy.md). This document is not background reading —
each Tier 1 item is a requirement the harness must enforce, because every source agrees on
one thing: **guardrails that depend on the researcher's good intentions do not work.**

Compiled 2026-08-27. Sources at the bottom.

---

## The number that should govern everything

> After 1,000 independent backtests, the expected maximum Sharpe ratio is **3.26 — even when
> the true Sharpe of every strategy tested is exactly zero.**
> — López de Prado

This single result reframes the whole project. A reported Sharpe is meaningless without the
number of trials that produced it. "I found a rule with Sharpe 1.2" is not a finding; "I
found a rule with Sharpe 1.2 **on the 4th configuration I tested**" is a finding, and "…on
the 400th" is noise. Harvey & Liu make the same point from the other side: practitioners
routinely haircut backtest Sharpes by an arbitrary 50%, and the statistically correct
haircut is non-linear — marginal Sharpes get penalized far harder than exceptional ones.

Everything below exists to make the trial count visible and the haircut principled.

---

## The protocol this is based on

Arnott, Harvey & Markowitz, *A Backtesting Protocol in the Era of Machine Learning* (Journal
of Financial Data Science, 2019) is the most directly applicable published guidance. Its
categories, in their order:

1. **Research motivation** — start from an investment idea with an *ex-ante economic
   foundation*. Strategies found by search rather than hypothesis tend to fail live.
2. **Multiple testing and statistical methods** — track model specifications, penalize
   results for the number of tests, and measure correlation between the strategies tried.
3. **Sample choice and data** — *justify the test sample before running the test*, and
   ensure data quality.
4. **Cross-validation** — apply cautiously; only live trading is truly out-of-sample.
5. **Research culture** — value rigor over favorable results; accept that most experiments
   fail.

Note item 5 is a *culture* item in a statistics paper. That is deliberate, and it's the one
that most often decides the outcome.

---

## Tier 1 — Must have. Cheap, high value, enforced in code.

These are all small amounts of code. None of them require a statistics library.

### 1. Pre-registration file, committed before results exist

One markdown file per strategy, written and **git-committed before the first backtest runs**,
stating: the economic rationale, the exact rule, the parameter values, the sample period, the
success criteria, and the prediction. Git history is the enforcement mechanism — a
pre-registration whose commit timestamp postdates the result is not a pre-registration.

Harvey's list of "soft misconduct" is precisely the set of choices this locks down: sample
selection, outlier exclusion, variable transformation, choice of control, and selective
reporting of results.

### 2. A trial ledger

An append-only log of **every** backtest configuration ever run, written automatically by the
harness — not by hand, because the ones you forget to log are exactly the ones that inflate
the count. Report the running total alongside every result.

This is the cheapest high-value guardrail available and almost nobody builds it. Note how
fast the count grows without anyone intending it: 5 lookback windows × 3 assets × 2 defensive
sleeves × 2 rebalance frequencies = **60 trials** before a single "idea" has been had.

### 3. Parameter budget: cap what you *search*, price what you *declare*

The quantity that predicts overfitting is not how many arguments a strategy function takes —
it's how many decision points were **searched over**. quantstrat's `degrees.of.freedom`
debits one for each indicator, signal process, rule, parameter set, and constraint; by that
accounting an entirely boring trend rule is already at 4–6 (lookback, rebalance frequency,
defensive sleeve, whipsaw buffer, confirmation lag) before anyone gets clever. A flat cap
would force out things like a whipsaw buffer, which is a known structural feature rather than
a curve-fit, and removing it makes the strategy *more* fragile. So the budget is two-tiered:

**Fixed parameters — unlimited, but declared.** Set a priori from convention or published
precedent (e.g. month-end rebalancing, per Faber), recorded in the pre-registration with a
one-line rationale, and **never swept**. These cost essentially nothing statistically.
Tuning one later converts it to fitted and consumes budget — the ledger makes that visible.

**Fitted parameters — hard cap of 2.** Anything whose value was chosen by looking at
results. This is where the tight limit genuinely belongs, and the binding constraint is
sample size, not taste: with ~4 independent bear markets in the sample, there is no honest
way to fit many things against the phenomenon the project actually cares about.

**Declare the grid; it becomes your N.** The search space size feeds directly into the
Deflated Sharpe (item 8), so additional fitted parameters are *priced* rather than banned —
a parameter never swept costs N=1, one swept over 10 values multiplies N by up to 10 (less
when configurations are correlated). The ledger's actual run count is the enforcement: if
declared N and logged runs disagree, the declared N is wrong and the DSR is flattering.

### 4. Plateau test, not peak selection

Any parameter must be tested at its neighbors and the result reported as a curve, never a
point. A rule that works at 150/200/250 days is credible; one that works only at 200 is
fitted to noise. **The harness should report the neighborhood automatically** so that seeing
the peak alone is impossible.

### 5. Structural look-ahead prevention

Not a convention — a property of the code:

- Signals computed from data through close of day *t* produce a position effective at the
  open of *t+1*. Enforce with an explicit shift in one place, and unit-test it with a
  synthetic series where the answer is known (e.g. a price series that jumps on a known date;
  if the strategy captures the jump, the shift is broken).
- **Adjusted-close is a look-ahead trap.** Adjusted prices are retroactively restated for
  later dividends and splits, so a moving average of adjusted close at time *t* incorporates
  factors that were not knowable at *t*. The effect on an SMA signal is small, but the
  restatement problem is not: it makes results silently irreproducible between runs.
- Benchmark and strategy must use the same total-return convention. Comparing a total-return
  strategy against a price-only SPY is a fabricated edge of ~1–2%/yr.

### 6. Pinned data snapshots

Raw pulls cached to disk, committed or checksummed, with a dated snapshot id recorded in
every result. Without this, yfinance's silent restatements mean a result cannot be
reproduced — and an irreproducible result cannot be validated or refuted.

### 7. Start-date robustness

A single start date is a hidden parameter. Report results across a sweep of start dates
(2004, 2005, 2007, 2010…). If the conclusion depends on starting before 2008, the finding is
"2008 happened," not "the rule works." This is the specific failure mode that Antonacci's GEM
turned out to have.

### 8. Deflated Sharpe Ratio and Probabilistic Sharpe Ratio

Both are closed-form — a few dozen lines, no dependencies beyond scipy. DSR corrects a
Sharpe for the number of trials, sample length, skewness and kurtosis. PSR gives the
probability the true Sharpe exceeds a threshold. Feed DSR the trial count from the ledger
(item 2) and the whole stack becomes self-consistent.

### 9. Pre-committed kill criteria, defined as model invalidation

Written into the pre-registration, before any capital is involved. The literature's concrete
anchors: pause at **1.5× the backtest's maximum drawdown**, or López de Prado's **Triple
Penance Rule** — halt if recovery time exceeds 3× the formation period.

The framing matters more than the number. Research across three decades and dozens of ETFs
found mechanical drawdown stops usually *hurt*: tight stops get triggered by noise, wide ones
don't protect. So the kill criterion should answer **"is my model falsified?"** — the
strategy did something the backtest said was essentially impossible — and not "am I down too
much?" Those are different questions with different correct answers.

---

## Tier 2 — Worth building if cheap, skip if not

- **Block bootstrap confidence intervals.** Resample blocks of returns to generate
  alternative histories and produce an interval around the drawdown-reduction estimate. This
  partially addresses the tiny-sample problem — but be honest about what it does: **a
  bootstrap quantifies uncertainty in the data you have; it does not manufacture new
  information.** It cannot invent a bear market of a type never observed, and block length
  must preserve the serial correlation that trend-following depends on, or it will destroy
  the very effect being measured.
- **Walk-forward analysis** (rolling, not anchored — the guidance is rolling for
  regime-sensitive strategies like trend-following, and the variant must be **chosen before
  seeing results**, never picked for the better number). Caveat specific to this project: if
  the parameter is pre-committed and never re-optimized, walk-forward adds little, because
  there is no optimization to walk forward. It earns its cost only if parameters are ever
  fit.
- **Harvey & Liu's haircut Sharpe** — a principled alternative to DSR with a reference
  implementation in R's `quantstrat`. Redundant if DSR is already built.

## Tier 3 — Skip

Deliberately out of scope, consistent with "the best code is the least code that does the
job":

- **PBO via combinatorially symmetric cross-validation** — designed for selecting among many
  configurations. With a 1–2 parameter pre-registered rule there is little selection to
  measure.
- **Purged k-fold CV with embargo** — solves leakage from overlapping labels in ML pipelines.
  No labels here.
- **Generative/synthetic market data (TGAN, agent-based models)** — nondeterministic, heavy,
  and it fabricates the data the conclusion rests on. Directly contrary to the project's
  stated design goals.

---

## Pitfalls specific to *this* project

Generic lists are easy to nod at; these are the ones this design actually exposes:

1. **The trial count explodes invisibly.** Three assets, two defensive sleeves, and a handful
   of lookbacks is already dozens of trials. Without the ledger you will genuinely not know
   whether you're at trial 10 or 300.
2. **One event doing all the work.** The drawdown benefit will likely concentrate in 2008.
   Report per-event contribution, not just aggregate stats — the aggregate hides this
   completely, and it's exactly how GEM's edge evaporated.
3. **Metric drift after seeing results.** The bar is drawdown reduction at comparable return.
   The temptation, once a strategy underwhelms, is to notice it has a nicer Sharpe or Calmar.
   Pre-registration is the only defense.
4. **Defensive sleeve as a second hidden strategy.** Choosing TLT vs GLD vs cash after seeing
   which backtested better is parameter fitting wearing a costume. Pick on rationale, or test
   all three and count all three as trials.
5. **Rebalance frequency as an unlogged parameter.** Daily vs weekly vs month-end changes
   whipsaw materially. Fix it a priori by precedent and it's free; try all three and pick the
   winner and it is a fitted parameter that consumes half the budget and multiplies N by 3.
   The distinction is entirely about whether you looked before choosing.
6. **Benchmark asymmetry.** Any cost, dividend, or fill assumption applied to the strategy but
   not the benchmark manufactures edge.
7. **The holdout gets consumed by accident.** Make it structurally awkward: gate holdout data
   behind an explicit flag that writes to the trial ledger every time it's touched. A holdout
   you've peeked at three times is not a holdout.

---

## The uncomfortable implication

Minimum Track Record Length asks how long a record must be to confirm a Sharpe is genuinely
above a threshold at a given confidence. The answers are brutal — one published worked
example required **1,404 monthly observations, or 117 years**, and found a 179-month record
far too short to conclude anything.

For this project that means: **live results will not validate the strategy within any
relevant horizon.** Running it and watching cannot settle the question, because the noise
swamps the signal for decades. Combined with the ~4 independent bear markets available in
backtest, the honest position is that the evidence bar cannot be cleared by *more data* —
only by *more discipline about the data that exists*. That is precisely why the Tier 1 list
is worth building before any strategy work, and it's the strongest argument against the
instinct to "just start testing ideas and see what looks good."

---

## Behavioral guardrails

The literature is blunt that this is where systematic strategies actually die, and manual
execution with no institutional structure is the highest-risk configuration:

- **Losses are felt roughly twice as strongly as equivalent gains**, which is what turns a
  normal drawdown into an abandonment.
- **Every override is an untested strategy.** The trades most often overridden are
  statistically the exact ones the edge is built on. A rule followed 90% of the time is not
  the rule that was backtested.
- Part of why these strategies persist at all is that **other people abandon them** during
  the whipsaw stretches. The discomfort is not a bug in the strategy; it is plausibly the
  source of whatever edge remains.
- The most common error is quitting during normal variance and persisting through genuine
  regime breaks — which is the argument for defining kill criteria *statistically and in
  advance* rather than in the moment.

On sizing, the Kelly literature's transferable lesson is that **uncertainty in your estimate
should reduce position size, and overbetting accelerates ruin rather than merely slowing
growth** — at 2× Kelly, long-run growth is zero even when every individual bet is positive
expected value. Practitioners typically run quarter- to half-Kelly for exactly this reason.
The decision to cap this at 5% of the account, sized as fully losable, already embodies that
principle; the guardrail is simply not to revisit that cap because a backtest looks good.

---

## What this means for scaffolding

Tier 1 is roughly: a pre-registration template, an append-only CSV ledger, a shift-and-test
convention, a data cache with snapshot ids, a start-date sweep loop, and ~50 lines of
DSR/PSR. **None of that requires a backtesting framework** — it argues for a small purpose-built
harness where these properties are structural, rather than adopting vectorbt or backtrader and
bolting the guardrails on top. That tradeoff is the next decision to make.

---

## Sources

- [Arnott, Harvey & Markowitz, *A Backtesting Protocol in the Era of Machine Learning* (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3275654) · [Duke PDF](https://people.duke.edu/~charvey/Research/Published_Papers/P138_A_backtesting_protocol.pdf) · [summary](https://www.lextechinstitute.ch/a-backtesting-protocol-in-the-era-of-machine-learning/?lang=en)
- [Harvey & Liu, *Backtesting* (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2345489) · [Practical Applications summary](https://people.duke.edu/~charvey/Media/2016/Practical_applications_backtesting.pdf) · [`SharpeRatio.haircut` reference implementation](https://rdrr.io/github/braverock/quantstrat/man/SharpeRatio.haircut.html)
- [Harvey, *Replication in Financial Economics* / editorial on soft misconduct](https://people.duke.edu/~charvey/Research/Published_Papers/P142_Replication_in_financial.pdf)
- [Bailey & López de Prado, *The Deflated Sharpe Ratio* (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551) · [PDF](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf) · [Wikipedia](https://en.wikipedia.org/wiki/Deflated_Sharpe_ratio)
- [Bailey & López de Prado, *The Sharpe Ratio Efficient Frontier* (PSR / MinTRL)](https://www.davidhbailey.com/dhbpapers/sharpe-frontier.pdf) · [MinTRL in PerformanceAnalytics](https://search.r-project.org/CRAN/refmans/PerformanceAnalytics/html/MinTrackRecord.html) · [Portfolio Optimizer explainer](https://portfoliooptimizer.io/blog/the-probabilistic-sharpe-ratio-bias-adjustment-confidence-intervals-hypothesis-testing-and-minimum-track-record-length/)
- [López de Prado, *The 7 Reasons Most Machine Learning Funds Fail* (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3031282) · [*The 10 Reasons…* (GARP PDF)](https://www.garp.org/hubfs/Whitepapers/a1Z1W0000054x6lUAA.pdf)
- [Sullivan, Timmermann & White, *Data-Snooping, Technical Trading Rule Performance, and the Bootstrap* (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=65140) · [PDF](https://www.kevinsheppard.com/files/teaching/mfe/advanced-econometrics/Sullivan_Timmermann_White.pdf)
- [Chan, *Quantitative Trading: How to Build Your Own Algorithmic Trading Business* (Wiley)](https://www.wiley.com/en-us/Quantitative+Trading:+How+to+Build+Your+Own+Algorithmic+Trading+Business,+2nd+Edition-p-9781119800064)
- [QuantInsti, *Walk-Forward Optimization*](https://blog.quantinsti.com/walk-forward-optimization-introduction/) · [Anchored vs. Rolling Windows](https://www.susanpotter.net/quant/walk-forward-optimization/)
- [Varma, *The Stop-Loss That Stops Gains*](https://samirvarma.substack.com/p/the-stop-loss-that-stops-gains) · [Monster Trading Systems, *When to Stop Trading a Strategy*](https://www.monstertradingsystems.com/when-to-stop-trading-a-strategy/)
- [Downey, *Why fractional Kelly? Simulations of bet size with uncertainty*](https://matthewdowney.github.io/uncertainty-kelly-criterion-optimal-bet-size.html)
- [*40+ Behavioral Mistakes Systematic Traders Make*](https://setup4alpha.substack.com/p/40-behavioral-mistakes-systematic)
- [Palomar, *Backtesting with Synthetic Data* (Portfolio Optimization book)](https://bookdown.org/palomar/portfoliooptimizationbook/8.5-backtesting-synthetic-data.html)
