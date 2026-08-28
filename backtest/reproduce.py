"""Reproducing a published result, to test the harness rather than a strategy.

Everything else in this project checks a *strategy*. This module checks the
*machinery*: it re-implements Faber's 10-month timing rule, runs it through the
same engine, the same lag and the same statistics as any strategy here, and
compares the output to the figures printed in his paper.

The reasoning is that our statistics are unit-tested against known values but no
end-to-end result has ever been checked against an outside source. Since H1 made
the matched benchmark do real work, a bug anywhere in data -> weights -> lag ->
equity -> statistics would quietly invalidate every finding. If our numbers land
on Faber's, that whole path is corroborated at once. If they do not, something is
wrong and the existing results are suspect.

Reference:

    Mebane T. Faber, "A Quantitative Approach to Tactical Asset Allocation",
    Journal of Wealth Management (2007), February 2013 update.
    https://papers.ssrn.com/sol3/papers.cfm?abstract_id=962461

His stated method, transcribed from pages 21-22 of the 2013 update:

    BUY  when monthly price > 10-month SMA
    SELL to cash otherwise
    - entry and exit at the close on the day of the signal
    - the model is updated once a month, on the last day of the month
    - all series are total return series including dividends
    - cash earns 90-day Treasury bills
    - taxes, commissions and slippage excluded

That maps onto this harness exactly: monthly bars, weights decided at a month-end
close, and the engine's single `.shift(1)` carrying them into the following month.
Costs are set to zero here because Faber excludes them -- the point is to match
his construction, not to model reality.

**Two known departures**, both from data we cannot obtain rather than choices:

1. Faber's series is Global Financial Data's S&P 500 total return, which is
   paywalled. We substitute Shiller's dataset, whose pre-1926 figures come from
   the same Cowles Commission source Faber names -- but whose prices are *monthly
   averages of daily closes*, not month-end closes. That difference is not
   cosmetic for a trend rule: it changes which months the signal is in the market.
   `sampling_sensitivity()` measures how much, on data where both conventions can
   be built from the same underlying prices.
2. Faber's cash is 90-day T-bills. The longest free series is Ken French's
   one-month bill, which starts 1926-07. Before that the reproduction is run twice
   -- cash at 0% and at 3.5%/yr -- and the timing return is reported as the
   bracket, rather than pretending to a number we cannot source.

See design_docs/path_to_trading.md, G2.
"""

from __future__ import annotations

import hashlib
import io
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from . import engine, stats

REFERENCE_DIR = Path(__file__).resolve().parent.parent / "data" / "reference"
SHILLER_CSV = REFERENCE_DIR / "shiller_sp500_monthly.csv"
SPY_CSV = REFERENCE_DIR / "spy_monthly.csv"

SHILLER_URL = "http://www.econ.yale.edu/~shiller/data/ie_data.xls"
FRENCH_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_CSV.zip"
)

#: Faber's rule. Fixed by the paper, not by us, and never swept.
LOOKBACK_MONTHS = 10

#: The reproduction window. Faber reports 1901-2012; the series starts ten months
#: earlier so the first signal of 1901 has its full lookback.
WARMUP_START = "1900-01-31"
SAMPLE_START = "1901-01-31"
SAMPLE_END = "2012-12-31"

#: Ken French's factor file is five comma-separated columns, of which the last is
#: RF, and its monthly block is keyed YYYYMM. Named so the parser reads as intent.
_FRENCH_COLUMNS = 5
_FRENCH_RF_COLUMN = 4
_FRENCH_STAMP_WIDTH = 6

#: Ken French's one-month bill begins here; before it, cash is bracketed.
CASH_STARTS = "1926-07-31"
CASH_BRACKET = (0.0, 0.035)

MONTHS_PER_YEAR = 12

#: SPY exists from 1993 and is a genuine month-end total return series, so it can
#: be sampled the way Faber samples. Used for the modern cross-check.
SPY_START = "1993-01-01"


class ReferenceDataError(RuntimeError):
    """Raised when the pinned reference data is missing or fails its checksum."""


@dataclass(frozen=True)
class Check:
    """One published figure, next to what this harness produced.

    `tolerance` is the gap at which the two stop being the same number. It is set
    from the known data departures above, not from what happens to pass: a
    century-old index reconstructed by a different vendor will not agree to the
    basis point, and pretending otherwise would make this check meaningless in
    both directions.

    A check outside tolerance with a stated `explanation` is *explained*, not
    passed. One outside tolerance without an explanation is a failure, and the
    test suite treats it as one.
    """

    name: str
    published: float
    reproduced: float
    tolerance: float
    explanation: str = ""

    @property
    def gap(self) -> float:
        return self.reproduced - self.published

    @property
    def within_tolerance(self) -> bool:
        return abs(self.gap) <= self.tolerance

    @property
    def status(self) -> str:
        if self.within_tolerance:
            return "MATCH"
        return "EXPLAINED" if self.explanation else "FAIL"


@dataclass
class Reproduction:
    """Everything one reproduction produced."""

    source: str
    checks: list[Check] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        if any(c.status == "FAIL" for c in self.checks):
            return "FAIL"
        if all(c.status == "MATCH" for c in self.checks):
            return "MATCH"
        return "MATCH (with explained gaps)"


# --------------------------------------------------------------------------- #
# Pinned reference data
# --------------------------------------------------------------------------- #


def checksum(frame: pd.DataFrame) -> str:
    """Same digest scheme as `data.Snapshot`, for the same reason."""
    return hashlib.sha256(frame.to_csv(float_format="%.10f").encode("utf-8")).hexdigest()[:16]


def _load(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise ReferenceDataError(
            f"Missing pinned reference data at {path}. It is committed to the repo so "
            "the reproduction runs offline and identically forever; rebuild it with "
            "`python -m backtest.cli reproduce --refresh` only when you intend to "
            "change what is being reproduced against."
        )
    frame = pd.read_csv(path, index_col=0, parse_dates=True)
    frame.index.name = "date"
    return frame


def load_shiller() -> pd.DataFrame:
    """Monthly S&P 500 total return index and the one-month bill rate."""
    return _load(SHILLER_CSV)


def load_spy() -> pd.DataFrame:
    """Month-end SPY total return index."""
    return _load(SPY_CSV)


def _shiller_period(value: float) -> pd.Period:
    """Shiller encodes dates as 1901.01 .. 1901.1, where `.1` means October."""
    year, month = f"{float(value):.2f}".split(".")
    return pd.Period(f"{year}-{int(month):02d}", freq="M")


def fetch_shiller() -> pd.DataFrame:
    """Rebuild the pinned Shiller series from source. Needs the network.

    The total return is built the standard way: reinvest one twelfth of the
    annualised dividend each month, since Shiller reports the dividend as an
    annual rate against a monthly price.
    """
    # Imported here, not at module scope: xlrd is needed only to re-pull the
    # reference data, and the pinned path must work without it installed.
    import xlrd  # noqa: F401, PLC0415

    request = urllib.request.Request(SHILLER_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()

    raw = pd.read_excel(io.BytesIO(payload), sheet_name="Data", header=7)
    columns = dict(zip(raw.columns[:3], ["date", "price", "dividend"], strict=False))
    raw = raw.rename(columns=columns)
    raw = raw[["date", "price", "dividend"]].dropna(subset=["date", "price"])
    raw.index = [_shiller_period(v) for v in raw["date"]]

    total_return = (raw["price"] + raw["dividend"].fillna(0.0) / 12.0) / raw["price"].shift(1) - 1.0
    index = (1.0 + total_return.fillna(0.0)).cumprod()

    frame = pd.DataFrame({"sp500_tr": index, "rf": _fetch_french_rf()})
    frame = frame.loc[_shiller_period(1900.01) : _shiller_period(2012.12)]
    frame.index = frame.index.to_timestamp("M")
    frame.index.name = "date"
    return frame


def _fetch_french_rf() -> pd.Series:
    """Ken French's one-month Treasury bill return, monthly, from 1926-07."""
    request = urllib.request.Request(FRENCH_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))

    lines = archive.read(archive.namelist()[0]).decode("latin-1").splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip().startswith(",Mkt-RF"))

    rates: dict[pd.Period, float] = {}
    for line in lines[start + 1 :]:
        fields = line.split(",")
        stamp = fields[0].strip()
        if (
            len(fields) != _FRENCH_COLUMNS
            or not stamp.isdigit()
            or len(stamp) != _FRENCH_STAMP_WIDTH
        ):
            break  # the monthly block ends; an annual block follows
        rate = float(fields[_FRENCH_RF_COLUMN]) / 100.0
        rates[pd.Period(f"{stamp[:4]}-{stamp[4:]}", freq="M")] = rate
    return pd.Series(rates)


def fetch_spy() -> pd.DataFrame:
    """SPY total return sampled both ways from one daily series. Needs the network.

    `month_end` is Faber's convention; `month_avg` is Shiller's. Pinning both from
    the same daily closes is what lets `sampling_sensitivity` attribute the whole
    difference to sampling and to nothing else.
    """
    import yfinance  # noqa: PLC0415  -- network-only path, as with xlrd above

    raw = yfinance.download(
        "SPY", start=SPY_START, end="2013-01-01", auto_adjust=True, progress=False
    )
    close = raw["Close"]
    if isinstance(close, pd.DataFrame):
        close = close[close.columns[0]]

    frame = pd.DataFrame(
        {"month_end": close.resample("ME").last(), "month_avg": close.resample("ME").mean()}
    )
    frame.index.name = "date"
    return frame


def refresh() -> dict[str, str]:
    """Re-pull both reference series and rewrite the pinned files."""
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    written = {}
    for path, frame in ((SHILLER_CSV, fetch_shiller()), (SPY_CSV, fetch_spy())):
        frame.to_csv(path, float_format="%.10f")
        written[path.name] = checksum(frame)
    return written


# --------------------------------------------------------------------------- #
# The rule, run through this project's engine
# --------------------------------------------------------------------------- #


def faber_weights(
    prices: pd.DataFrame,
    risk_asset: str,
    cash: str,
    lookback: int = LOOKBACK_MONTHS,
) -> pd.DataFrame:
    """Faber's rule as target weights. No lag here; the engine owns that."""
    average = prices[risk_asset].rolling(lookback).mean()
    risk_on = (prices[risk_asset] > average).where(average.notna(), other=False)

    weights = pd.DataFrame(0.0, index=prices.index, columns=[risk_asset, cash])
    weights.loc[risk_on, risk_asset] = 1.0
    weights.loc[~risk_on, cash] = 1.0
    return weights


def _shiller_prices(pre_1926_cash: float) -> pd.DataFrame:
    """Price frame for the engine: the equity index and a cash index beside it."""
    frame = load_shiller().loc[WARMUP_START:SAMPLE_END]
    rate = frame["rf"].copy()
    rate.loc[: pd.Timestamp(CASH_STARTS)] = rate.loc[: pd.Timestamp(CASH_STARTS)].fillna(
        pre_1926_cash / MONTHS_PER_YEAR
    )
    return pd.DataFrame({"SP500": frame["sp500_tr"], "CASH": (1.0 + rate.fillna(0.0)).cumprod()})


def mean_annual_return(returns: pd.Series) -> float:
    """The average of calendar-year returns.

    Faber reports both this and the compounded return, and the gap between them is
    his illustration of what volatility costs. It is the mean of yearly figures,
    not twelve times the mean monthly one.
    """
    yearly = (1.0 + returns).groupby(returns.index.year).prod() - 1.0
    return float(yearly.mean())


def drawdown_within(equity: pd.Series, start: str, end: str) -> float:
    """Worst drawdown inside one window.

    Faber's 42.24% is the timing model's fall during the 1929-32 bear, which is
    *not* its worst drawdown of the century -- that comes in 1941. Comparing our
    all-time maximum against his episode figure would be comparing two different
    events and calling the difference an error.
    """
    window = equity.loc[start:end]
    return float((window / window.cummax() - 1.0).min())


# --------------------------------------------------------------------------- #
# The reproduction
# --------------------------------------------------------------------------- #

#: The 1929-32 bear market, the episode Faber quotes drawdowns for.
CRASH_WINDOW = ("1929-08-31", "1933-06-30")

_SAMPLING_NOTE = (
    "Shiller's prices are monthly averages of daily closes; Faber's are month-end "
    "closes. That changes which months the signal holds equity, and "
    "`sampling_sensitivity()` shows it moves the timing return in this direction "
    "on identical underlying prices."
)


def reproduce_faber() -> Reproduction:
    """Faber's S&P 500 table, 1901-2012, rebuilt through this harness."""
    low, high = (_shiller_prices(cash) for cash in CASH_BRACKET)

    hold = engine.buy_and_hold(low, ticker="SP500", cost_bps=0.0)
    timing_low = engine.run(low, faber_weights(low, "SP500", "CASH"), cost_bps=0.0)
    timing_high = engine.run(high, faber_weights(high, "SP500", "CASH"), cost_bps=0.0)

    def annualised(result: engine.Result) -> float:
        return stats.cagr(result.equity, MONTHS_PER_YEAR)

    # The bracket's midpoint is what gets compared; its width is reported as a note.
    timing_cagr = (annualised(timing_low) + annualised(timing_high)) / 2.0
    timing_mean = (
        mean_annual_return(timing_low.returns) + mean_annual_return(timing_high.returns)
    ) / 2.0

    checks = [
        # Buy and hold needs no cash series and no signal, so it isolates the path
        # from data through the engine to the statistics. It is the cleanest test
        # of the harness in the whole project.
        Check("buy & hold, compound return", 0.0932, annualised(hold), 0.005),
        Check("buy & hold, mean annual return", 0.1126, mean_annual_return(hold.returns), 0.005),
        Check(
            "buy & hold, drawdown in the 1929-32 bear",
            -0.8366,
            drawdown_within(hold.equity, *CRASH_WINDOW),
            0.03,
        ),
        Check(
            "timing, drawdown in the 1929-32 bear",
            -0.4224,
            drawdown_within(timing_low.equity, *CRASH_WINDOW),
            0.03,
        ),
        Check(
            "timing, share of months invested",
            0.70,
            float(timing_low.held["SP500"].loc[SAMPLE_START:].mean()),
            0.02,
        ),
        Check(
            "timing, compound return",
            0.1018,
            timing_cagr,
            0.005,
            explanation=_SAMPLING_NOTE,
        ),
        Check(
            "timing, mean annual return",
            0.1122,
            timing_mean,
            0.005,
            explanation=_SAMPLING_NOTE,
        ),
    ]

    notes = [
        f"Pre-1926 cash bracketed at {CASH_BRACKET[0]:.1%} and {CASH_BRACKET[1]:.1%} a year: "
        f"timing compounds at {annualised(timing_low):.2%} to {annualised(timing_high):.2%}. "
        "Buy & hold is unaffected -- it never holds cash.",
        "Faber excludes costs, so costs are zero here. This reproduces his construction, "
        "not a tradeable result.",
    ]
    return Reproduction(
        source="Faber 2013, S&P 500 1901-2012 (Shiller series)",
        checks=checks,
        notes=notes,
    )


def reproduce_signal_dates() -> list[tuple[str, bool, bool]]:
    """The two exit dates Faber names in the text, which our signal must also find.

    A statistic can match for the wrong reasons; a specific month cannot. These are
    the sharpest single checks available, because they test the signal and the
    month-end convention at one named point rather than in aggregate.
    """
    prices = _shiller_prices(CASH_BRACKET[1])
    weights = faber_weights(prices, "SP500", "CASH")
    invested = weights["SP500"] > 0.0

    return [
        ("exits during October 2000", True, not bool(invested.loc["2000-10-31"])),
        ("out of the market by January 2008", True, not bool(invested.loc["2008-01-31"])),
    ]


def sampling_sensitivity() -> Reproduction:
    """How much the monthly-average convention alone moves the timing result.

    This is what turns "the series is sampled differently" from an excuse into a
    measurement. SPY gives twenty years of real daily closes, so both conventions
    can be built from *the same underlying prices* and the rule run on each. Any
    difference is caused by sampling and nothing else.
    """
    frame = load_spy()

    results = {}
    for label, column in (("month-end", "month_end"), ("monthly-average", "month_avg")):
        series = frame[column]
        # Cash is held flat at 1.0 in both runs, so it cannot contribute to the
        # difference between them.
        prices = pd.DataFrame({"SP500": series, "CASH": pd.Series(1.0, index=series.index)})
        result = engine.run(prices, faber_weights(prices, "SP500", "CASH"), cost_bps=0.0)
        results[label] = stats.cagr(result.equity, MONTHS_PER_YEAR)

    shift = results["monthly-average"] - results["month-end"]
    hold = engine.buy_and_hold(
        pd.DataFrame({"SP500": frame["month_end"]}), ticker="SP500", cost_bps=0.0
    )
    return Reproduction(
        source="SPY 1993-2012, both sampling conventions from one daily series",
        checks=[
            # Faber names this drawdown in the text, and SPY is sampled his way, so
            # this is the one figure here that can be compared without caveat.
            Check(
                "buy & hold, drawdown of the 2008-09 bear",
                -0.5095,
                stats.max_drawdown(hold.equity),
                0.01,
            ),
        ],
        notes=[
            f"Timing compounds at {results['month-end']:.2%} on month-end closes and "
            f"{results['monthly-average']:.2%} on monthly averages of the same prices: "
            f"a {shift * 100:+.2f}pp swing caused by sampling alone.",
        ],
    )
