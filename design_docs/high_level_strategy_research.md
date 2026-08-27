# High-Level Strategy Research

What the academic literature and practitioner record say about the specific project
described in [high_level_strategy.md](high_level_strategy.md): a deterministic, daily-bar,
long-only rule over a small ETF basket (SPY/TLT/GLD), aiming to reduce drawdown relative to
buy-and-hold SPY.

Compiled 2026-08-27. Sources at the bottom.

---

## Verdict

**Not a fool's errand — but only because of how the goal was scoped.**

The evidence splits sharply depending on what you are trying to beat:

| Goal | Verdict |
|---|---|
| Higher *absolute return* than buy-and-hold SPY | Near-hopeless. Overwhelming evidence against. |
| Higher *risk-adjusted return* (Sharpe) | Weak, contested, mostly vanishes out-of-sample. |
| **Materially lower drawdown at comparable return** | **Plausible. The best-supported claim in the space.** |
| Learning to build and evaluate strategies rigorously | Unambiguously worthwhile regardless of outcome. |

The drawdown objective already chosen is, by a wide margin, the most defensible target
available. It should not be quietly widened later — "while we're here, can it also beat SPY
on return?" is the exact drift that turns this project into the failure mode below.

---

## The Case For

**1. Trend-following crash protection is real and has survived out-of-sample.**
Faber's 2007 paper — 200-day moving average, exit when price is below it — is the canonical
version of this project. In-sample (1972–2005) it produced Sharpe 0.81, CAGR 11.7%.
Out-of-sample (2006 through early 2025), on data the rule never saw and after publication,
it produced Sharpe 0.68. That is degradation, but it is *survival*, across the GFC, 2018,
2020, and 2022. Very few published anomalies do that well.

**2. The mechanism is understood, not just fitted.** Trend-following's benefit comes from
volatility clustering and the fact that large drawdowns are typically slow, serially
correlated grinds rather than instantaneous gaps. Managed-futures research calls this
"crisis alpha." A strategy with a plausible economic mechanism is far less likely to be a
data-mining artifact than one that merely fits.

**3. The benefit shows up as drawdown reduction, not return enhancement.** This is exactly
what the research reports — trend strategies exhibit lower correlation to equities in
stress, shorter drawdown durations, and positive skew, while *not* reliably adding return.
Aligning the success bar with where the effect actually lives is the biggest single
advantage of the current design.

**4. This project avoids the frictions that killed the commercial versions.** See below.

---

## The Case Against

**1. Faber's headline results are contaminated by data-mining.** Zakamulin's work targets
this directly: the reported performance of Faber-style moving-average timing contains
substantial data-mining bias and ignores real frictions, and once tested out-of-sample with
realistic costs across an 80-year sample, prior studies had *overestimated* these rules. The
200-day window is not a law of nature; it is one of many that could have been chosen, and it
was chosen with hindsight.

**2. In practice, tactical allocation funds have been a graveyard.** Morningstar found ~70%
of tactical asset allocation funds underperformed a passive balanced index fund, with
average underperformance around 2.6 percentage points per year; over the 15 years through
2018 the average TAA fund lagged Vanguard Balanced Index by ~3.2pp annually at similar risk.
Faber's *own* GTAA ETF returned roughly zero over its first three years while buy-and-hold
gained 20%+. A rule working on paper and a product working in the world are demonstrably
different things.

**3. Published edges decay, sharply.** McLean & Pontiff studied 97 documented return
predictors: returns were 26% lower out-of-sample and **58% lower post-publication**. They
attribute roughly the 26% to data mining and the remaining ~32% to arbitrage once public.
Every strategy this project can find by reading is, by construction, already published.

**4. Dual momentum is the cautionary tale.** Antonacci's GEM backtested at ~17% CAGR with
~22% max drawdown (1974–2013). Post-publication it lagged both 60/40 and buy-and-hold, and
analyses concluded its drawdown edge was substantially *a 2008 story* — one event doing most
of the work across a 40-year backtest.

**5. The sample-size problem is severe and cannot be engineered away.** A crash-protection
strategy is validated by crashes, and there have been perhaps 4–6 genuine equity bear
markets in the available sample (which, per the design doc, starts ~2004 for the full
basket). The standard quant guidance of 100–200 trades for significance is irrelevant here:
the effective number of *independent observations of the thing you care about* is closer to
four. No amount of daily bars changes that. **This is the hardest limitation in the project
and no clever methodology fixes it.**

**6. The defensive sleeves are not reliably defensive.** 2022 saw SPY, TLT, and GLD fall
together. Rotating into TLT/GLD rather than T-bills adds a second bet — that the defensive
asset rises when equities fall — which has held on average and failed exactly when inflation
drove the selloff.

**7. Whipsaw is the standing cost.** Trend rules pay for crash protection with
underperformance in choppy and V-shaped markets. 2020's recovery is the canonical example:
mechanical rules exited near the bottom and re-entered materially higher. The research
framing is blunt — trend following "is rarely the hero in the first act."

**8. The base rate for active retail trading is dismal.** Chague et al. found 97% of
Brazilian futures day traders who persisted beyond 300 days lost money, with no evidence of
learning. Barber & Odean found the most active US retail traders trailed the least active by
~7pp annually. This is a *different* activity from monthly rebalancing on a mechanical rule
— but it is the base rate for "individual decides to actively trade."

---

## The Pattern That Predicts Failure

Across every source, the same decay chain appears:

```
in-sample backtest  →  out-of-sample  →  post-publication  →  live, after costs
    (best)              -26%              -58%                 worse still
```

The consistent finding is not that edges are fake — it's that **each successive layer of
honesty removes roughly half the apparent edge**, and most strategies do not have twice the
edge required to survive that. The Cederburg critique of volatility-managed portfolios is
the cleanest illustration: Moreira & Muir's in-sample Sharpe improvements largely fail
out-of-sample because the underlying regressions are structurally unstable, and Barroso &
Detzel found what remains doesn't survive transaction costs.

**Corollary: any result that looks good should be assumed to be roughly half as good as it
looks, and treated as failing if it can't survive that haircut.**

---

## Patterns Common to Approaches That Survive

1. **Few parameters.** Faber's rule has essentially one. GEM has two. Every additional knob
   multiplies the search space and the overfitting probability. Harvey, Liu & Zhu concluded
   that after accounting for how many factors have been tested, a new claim needs a
   **t-statistic above 3.0**, not the conventional 2.0 — because everyone has been testing
   everything.
2. **A stated economic mechanism, decided before testing.** Volatility clustering is a
   reason. "The 187-day average worked best" is not.
3. **Robustness across neighbors, not a peak.** A rule that works at 150, 200, and 250 days
   is credible. One that works only at 200 is fitted to noise. Parameter *plateaus*, not
   parameter *optima*.
4. **The same rule across all assets.** Per-ticker tuning is overfitting with extra steps.
5. **Simplicity is genuinely protective**, not merely aesthetic. The strategies that
   survived publication are conspicuously the simplest ones.
6. **Low turnover.** Cost assumptions are a top failure mode everywhere; low turnover
   shrinks sensitivity to whatever you assumed wrong.

## Patterns Common to Approaches That Fail

Look-ahead bias (the easiest to introduce accidentally); survivorship bias; curve-fitting to
a parameter optimum; unrealistic fill and cost assumptions; too few independent
observations; iterating until something passes and reporting only that; and — most relevant
here — **changing the success metric after seeing the results.**

---

## Why This Project Is Better Positioned Than the Funds That Failed

This is the strongest argument that the TAA graveyard doesn't fully generalize:

- **No fees.** TAA funds charged 1–1.5%+; a large share of their 2.6pp annual
  underperformance is simply that.
- **No taxes.** Roth IRA — turnover is genuinely free, which is not true for most people
  running these rules, and is a real quantifiable advantage.
- **No career or business risk.** Funds face redemptions after underperformance and drift
  toward discretion; a mechanical rule with no outside capital does not.
- **No capacity or market-impact constraints** at this size in SPY/TLT/GLD.
- **The goal is drawdown, not return** — the one place the effect is best documented.

## Why It Might Still Fail Anyway

- The effect is real but small, and **four bear markets cannot distinguish a small real
  effect from luck.** This is unfixable, and the project may well end genuinely inconclusive
  rather than positive or negative.
- Behavioral risk: mechanical rules only work if followed *through* the whipsaw periods
  where they look stupid. Manual execution makes abandonment easy, and abandoning mid-way
  captures the costs without the benefits — plausibly worse than never starting.
- Whatever is found is already public and already decayed.

---

## Implications for the Design

1. **Set the overfitting controls now** (the deferred open question). The literature makes
   the choices clear: cap parameter count at 1–2, require a parameter *plateau* rather than
   a peak, use one rule across all sleeves, and reserve a genuinely untouched holdout
   period. Enforce in the harness, not by intention.
2. **Count and report strategy iterations.** Multiple testing is the dominant risk and is
   invisible unless the harness tracks how many variants have been tried. A result found on
   attempt 50 is not the same evidence as one found on attempt 2.
3. **Report the effective sample size** — the number of distinct drawdown events the
   strategy was actually evaluated on — alongside every headline stat. This is the number
   most likely to be forgotten and most likely to invalidate a conclusion.
4. **Add a whipsaw/regret statistic** to the standard report: worst underperformance vs.
   buy-and-hold over a rolling window. This determines whether the strategy is actually
   followable, and it is what killed the commercial funds.
5. **Reconsider T-bills as the defensive sleeve**, or test both. The literature's supported
   version of this rule exits to cash; rotating to TLT/GLD is an additional, separately
   fitted bet.
6. **Require 2022 and 2020 as named stress cases** — the inflation regime that broke the
   defensive sleeves, and the V-recovery that punishes trend rules.
7. **Pre-register success criteria** before running strategies, and treat any post-hoc
   metric change as a finding of failure.

---

## Generalizing: Does Any of This Apply to Prediction Markets (Kalshi/Polymarket)?

Short answer: **there is a substantial research literature, but it is a different literature
asking a different question — and the framework in this project does not transfer.** The
*methodology* transfers; the *strategy premise* does not.

### The research exists, but it's about forecasting accuracy, not trading

The foundational work — Wolfers & Zitzewitz's 2004 *Journal of Economic Perspectives*
survey and the NBER *Prediction Markets in Theory and Practice* — asks whether prices are
good probability forecasts, not whether you can systematically profit. The recurring finding
is that these markets are broadly efficient and often beat professional forecasters. That's
a conclusion *against* the existence of easy systematic edges.

Platform-specific work is now appearing. A study of 2,668 settled Kalshi macro contracts
(July 2021 – June 2026) found Fed/interest-rate markets near-perfectly calibrated with no
significant favorite-longshot bias, inflation markets moderately calibrated, and
**employment markets the weakest, with significant systematic mispricing.** That last one is
the closest thing to a documented, researchable opening on Kalshi.

### Four structural reasons the current framework doesn't port over

**1. There is no risk premium, so there is no benchmark.** This is the big one. Equities have
a positive long-run expected return from earnings and productivity; an event contract is
roughly zero-sum — 0% expected return at entry, negative after fees. The entire architecture
of this project is "can a rule improve on buy-and-hold SPY." **In prediction markets there is
nothing to buy and hold.** No benchmark, no drawdown-vs-benchmark comparison, no "comparable
return" clause in the success bar. The success criteria would have to be rebuilt from
scratch, not adapted.

**2. Costs are roughly two orders of magnitude higher.** Kalshi's taker fee is
`7¢ × C × (1−C)` per contract — max 1.75¢ at a 50¢ price, which is **3.5% of a 50¢ stake,
per side**. Maker fees are 25% of that, and extreme prices cost less, but the floor is still
far above the ~1bp round-trip friction on SPY. In a zero-sum game, that fee *is* the house
edge, and it must be overcome before the first dollar of profit. The current project's
"costs are negligible" assumption is one of its biggest advantages and it evaporates here.

**3. There is no continuous price series.** Contracts are created and settle. There's no
multi-decade daily bar series to run a 200-day average over, no equity curve of a
continuously held asset, and no way to run the same backtest shape at all. Every settled
contract is one terminal observation.

**4. Kalshi cannot be held in an IRA.** Event contracts are not available inside IRAs or
401(k)s. The stated funding plan — 5% of a Roth — does not reach Kalshi at all. That's a hard
practical blocker independent of whether any strategy works, and it also removes the
tax-free-turnover advantage that made high turnover cheap in the equity version.

### What *is* documented as a real edge — and why each is a poor fit here

| Edge | Status | Fit for a deterministic daily-bar project |
|---|---|---|
| Favorite-longshot bias | Real and long-documented across racing, sports, political markets | **Poor.** In one 12,084-match sample, betting favorites returned **−3.64%** and longshots **−26.08%** — the bias is real but *both sides lose*. It explains relative pricing; it doesn't produce profit after the vig. |
| Cross-platform arbitrage | Real and large — one study documented **$40M+** extracted from Polymarket (Apr 2024–Apr 2025) across 86M bets | **Very poor.** Opportunities persist seconds to minutes; Polymarket's NBA markets yielded only 7 executable in-game anomalies with a median duration of **3.6 seconds**. This is a latency and infrastructure game, the opposite of deterministic daily-bar research. |
| Intra-market arbitrage (contracts summing above $1) | Documented, mostly on PredictIt circa 2014–15 | Poor — largely competed away on modern venues. |
| Mean reversion on binary contracts | Under active study on Polymarket | Plausible but thin; the same research notes prices are ~90% accurate a month out and ~94% near settlement, so the mispricing window is small. |
| Category-level calibration failures (e.g. Kalshi employment markets) | Documented | **The most defensible fit** — it's slow-moving, research-driven, and doesn't require speed. But it's a forecasting problem, not a price-series problem. |

### What *does* transfer: the methodology

Everything in "Patterns Common to Approaches That Survive" applies verbatim, and the
sports-betting literature independently reached the same conclusions: markets are broadly
efficient, obvious errors get competed away, and any edge must be "smaller, faster, and more
systematic." Multiple-testing discipline, parameter caps, untouched holdouts, and honest cost
modeling are, if anything, *more* necessary — the sample sizes are worse, since each market
yields one settled outcome rather than a continuous series.

One genuinely useful import runs the other direction. Sports betting evaluates skill by
**closing line value** — did your price beat the market's final pre-event estimate? — rather
than by realized P&L, precisely because outcome samples are too small to be informative.
That's the same effective-sample-size problem identified above for crash protection, and
it's a better evaluation primitive than backtest P&L whenever observations are scarce. It is
worth borrowing as a concept even if this project never touches a prediction market.

### Bottom line

Prediction markets are not a generalization of this project; they're a different project
sharing only the research hygiene. The documented edges there are either **behavioral but
unprofitable** (longshot bias), **real but latency-bound** (arbitrage), or **forecasting
problems rather than price-series problems** (calibration failures). Combined with fees ~100×
higher, no benchmark to beat, and no IRA access, the equity version is strictly the better
place to spend effort first. If prediction markets are interesting later, the honest framing
is a *forecasting* project — can you produce better-calibrated probabilities than the market
in a specific weak category — which is a different codebase and a different success bar.

---

## Note on Scope

This document summarizes published research and practitioner record to inform how the
software is designed and evaluated. It is not investment advice, and nothing here is a
recommendation to buy or sell anything. The stated funding — 5% of a Roth IRA, sized as
fully losable — is consistent with the evidence above, which supports treating any result
from this project as uncertain even when the backtest looks strong.

---

## Sources

- [Faber, *A Quantitative Approach to Tactical Asset Allocation* (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=962461) · [PDF](https://mebfaber.com/wp-content/uploads/2016/05/SSRN-id962461.pdf) · [Revisited 10 Years Later](https://allocatortraining.com/wp-content/uploads/2023/06/A-Quantitative-Approach-to-Tactical-Asset-Allocation.pdf)
- [Zakamulin, *The Real-Life Performance of Market Timing with Moving Average and Time-Series Momentum Rules*](https://link.springer.com/article/10.1057/jam.2014.25) · [*Market Timing with Moving Averages* (PDF)](https://technicalanalyst-cdn-1.s3.eu-west-2.amazonaws.com/wp-content/uploads/2015/04/13144853/SSRN-moving-average.pdf)
- [Bailey, Borwein, Lopez de Prado & Zhu, *The Probability of Backtest Overfitting*](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253) · [*Statistical Overfitting and Backtest Performance*](https://sdm.lbl.gov/oapapers/ssrn-id2507040-bailey.pdf)
- [Harvey, Liu & Zhu, *. . . and the Cross-Section of Expected Returns* (NBER)](https://www.nber.org/papers/w20592) · [Duke PDF](https://people.duke.edu/~charvey/Research/Published_Papers/P118_and_the_cross.PDF)
- [McLean & Pontiff, *Does Academic Research Destroy Stock Return Predictability?* (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2156623) · [Journal of Finance](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12365)
- [Morningstar, *Why Tactical-Allocation Funds Failed—Again*](https://www.morningstar.com/funds/why-tactical-allocation-funds-failedagain) · [*Tactical Asset Allocation: Don't Try This at Home*](https://www.morningstar.com/funds/tactical-asset-allocation-dont-try-this-home) · [*Do Tactical-Allocation Funds Deliver?*](https://www.morningstar.com/funds/do-tactical-allocation-funds-deliver)
- [Swedroe, *Beware Tactical Asset Allocation* (etf.com)](https://www.etf.com/sections/index-investor-corner/swedroe-beware-tactical-asset-allocation) · [Institutional Investor, *Only One Tactical Allocation Fund Has Managed to Outperform This Decade*](https://www.institutionalinvestor.com/article/2bw3ho98yb7yovg6xgd8g/portfolio/only-one-tactical-allocation-fund-has-managed-to-outperform-this-decade)
- [Antonacci, *Extended Backtest of Global Equities Momentum*](https://medium.com/@garyantonacci_30463/extended-backtest-of-global-equities-momentum-dual-momentum-eb12902612e0) · [Quant for Free, *Dual Momentum out of sample*](https://quant4free.com/analysis/dual-momentum/) · [Resolve, *Global Equity Momentum: A Craftsman's Perspective*](https://investresolve.com/global-equity-momentum-executive-summary/)
- [CFA Institute, *Trend Following with Managed Futures: The Search for Crisis Alpha*](https://rpc.cfainstitute.org/research/financial-analysts-journal/2015/trend-following-with-managed-futures) · [Man Group, *Trend Following: Equity and Bond Crisis Alpha*](https://www.man.com/insights/trend-following-equity-and-bond-crisis-alpha) · [Return Stacked, *Trend Following Through Turmoil*](https://www.returnstacked.com/trend-following-through-turmoil-why-the-best-protection-comes-after-the-first-punch/)
- [DeMiguel et al., *A Multifactor Perspective on Volatility-Managed Portfolios* (J. Finance)](https://onlinelibrary.wiley.com/doi/full/10.1111/jofi.13395) · [*On the performance of volatility-managed portfolios* (JFE)](https://www.sciencedirect.com/science/article/abs/pii/S0304405X2030132X)
- [Chague, De-Losso & Giovannetti, *Day Trading for a Living?*](https://studylib.net/doc/28481997/chague-losso-giovannetti-47wp) · [summary](https://www.tradicted.com/research/chagu-day-2020/)
- [Hedge Fund Alpha, *Backtesting Mistakes That Kill Quant Strategies*](https://hedgefundalpha.com/education/backtesting-mistakes-kill-quant-strategies-guide/) · [Gainium, *Common Backtesting Mistakes*](https://gainium.io/blog/common-backtesting-problems)

### Prediction markets

- [Wolfers & Zitzewitz, *Prediction Markets* (JEP 2004)](https://www.csc2.ncsu.edu/faculty/mpsingh/local/Social/f15/wrap/readings/Wolfers+Zitzewitz-Prediction-Markets.pdf) · [*Prediction Markets in Theory and Practice* (NBER)](https://www.nber.org/system/files/working_papers/w12083/w12083.pdf) · [*Interpreting Prediction Market Prices as Probabilities*](https://www.stat.berkeley.edu/~aldous/157/Papers/InterpretingPredictionMarketPrices.pdf)
- [*Information Efficiency Across Macroeconomic Prediction Markets: Evidence from Kalshi*](https://www.researchgate.net/publication/409472804_Information_Efficiency_Across_Macroeconomic_Prediction_Markets_Evidence_from_Kalshi) · [*The Economics of the Kalshi Prediction Market* (UCD WP2025-19)](https://www.ucd.ie/economics/t4media/WP2025_19.pdf)
- [QuantPedia, *Systematic Edges in Prediction Markets*](https://quantpedia.com/systematic-edges-in-prediction-markets/) · [QuantPedia, *Exploiting Mean-Reversion in Decentralized Prediction Markets: Evidence from Polymarket*](https://quantpedia.com/exploiting-mean-reversion-in-decentralized-prediction-markets-evidence-from-polymarket-binary-contracts/)
- [*Arbitrage Analysis in Polymarket NBA Markets* (arXiv)](https://arxiv.org/pdf/2605.00864)
- [*Market Efficiency and the Favorite-Longshot Bias in Unemployment Prediction Markets*](https://www.researchgate.net/publication/409238145_Market_Efficiency_and_the_Favorite-Longshot_Bias_in_Unemployment_Prediction_Markets)
- [*Beating the House: Identifying Inefficiencies in Sports Betting Markets* (arXiv)](https://arxiv.org/pdf/1910.08858) · [*Weak Form Efficiency in Sports Betting Markets*](https://myweb.ecu.edu/robbinst/PDFs/Weak%20Form%20Efficiency%20in%20Sports%20Betting%20Markets.pdf) · [*Sports Betting Market Efficiency and the Role of the Closing Line*](https://joesaumarez.co.uk/sports-betting-market-efficiency-and-the-closing-line)
- [Morningstar, *Why the SEC Should Reject Prediction-Market ETFs*](https://www.morningstar.com/funds/know-when-fold-em-why-sec-should-reject-prediction-market-etfs) · [CFTC, *Understanding Prediction Markets and Event Contracts*](https://www.cftc.gov/LearnandProtect/PredictionMarkets) · [Fidelity, *What are prediction markets?*](https://www.fidelity.com/learning-center/trading-investing/prediction-markets)
- [pm.wiki, *Kalshi Fees Explained*](https://pm.wiki/learn/kalshi-fees-explained) · [Market Math, *Kalshi Fees Guide 2026*](https://marketmath.io/blog/kalshi-fees-guide-2026)
