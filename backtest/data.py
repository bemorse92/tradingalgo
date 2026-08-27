"""Market data: fetch, cache, and pin.

yfinance silently restates adjusted prices over time, so a backtest run twice can
produce different numbers for no visible reason. Every result in this project is
therefore tied to a *snapshot id*: an immutable on-disk copy of the raw pull plus a
checksum. Loading a snapshot never touches the network.

See design_docs/research_guardrails.md, Tier 1 item 6.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_DIR = DATA_DIR / "cache"
REGISTRY = DATA_DIR / "snapshots.json"

#: The fixed basket. SPY is the growth sleeve; TLT/GLD are the defensive sleeves.
DEFAULT_TICKERS = ("SPY", "TLT", "GLD")

#: Common history across the basket starts here (TLT lists 2002, GLD 2004).
DEFAULT_START = "2004-11-18"


class SnapshotError(RuntimeError):
    """Raised when a snapshot is missing or fails its checksum."""


@dataclass(frozen=True)
class Snapshot:
    """Metadata for one pinned data pull."""

    id: str
    created: str
    tickers: tuple[str, ...]
    start: str
    end: str
    rows: int
    checksum: str

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["tickers"] = list(self.tickers)
        return d


def _checksum(prices: pd.DataFrame) -> str:
    """Stable digest of a price frame. Parquet bytes are not reproducible; CSV is."""
    payload = prices.to_csv(float_format="%.10f").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _read_registry() -> dict:
    if not REGISTRY.exists():
        return {}
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def _write_registry(registry: dict) -> None:
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8")


def _total_return_close(raw: pd.DataFrame, tickers: tuple[str, ...]) -> pd.DataFrame:
    """Extract the adjusted (total-return) close from a yfinance frame.

    yfinance's column layout differs between versions and between single- and
    multi-ticker pulls, so normalise defensively.
    """
    if isinstance(raw.columns, pd.MultiIndex):
        levels = raw.columns.get_level_values(0)
        field = "Close" if "Close" in levels else "Adj Close"
        close = raw.xs(field, axis=1, level=0)
    elif "Close" in raw.columns:
        close = raw[["Close"]]
        close.columns = list(tickers[:1])
    else:  # pragma: no cover - defensive
        raise SnapshotError(f"Unrecognised yfinance columns: {list(raw.columns)}")

    close = close.reindex(columns=list(tickers))
    close.index = pd.to_datetime(close.index).tz_localize(None).normalize()
    close.index.name = "date"
    return close.sort_index().dropna(how="any")


def create_snapshot(
    tickers: tuple[str, ...] = DEFAULT_TICKERS,
    start: str = DEFAULT_START,
    end: str | None = None,
) -> Snapshot:
    """Pull from yfinance, write an immutable snapshot, and register it.

    This is the only function in the project that touches the network.
    """
    import yfinance as yf  # noqa: PLC0415 - lazy, so offline runs never need it

    end = end or datetime.now(UTC).date().isoformat()
    raw = yf.download(
        list(tickers),
        start=start,
        end=end,
        auto_adjust=True,  # total return: dividends and splits folded into Close
        progress=False,
        group_by="column",
    )
    if raw is None or raw.empty:
        raise SnapshotError(f"yfinance returned no data for {tickers} {start}..{end}")

    prices = _total_return_close(raw, tuple(tickers))
    checksum = _checksum(prices)
    snapshot_id = f"{datetime.now(UTC).date().isoformat()}-{checksum[:8]}"

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    prices.to_parquet(CACHE_DIR / f"{snapshot_id}.parquet")

    snap = Snapshot(
        id=snapshot_id,
        created=pd.Timestamp.utcnow().isoformat(),
        tickers=tuple(tickers),
        start=str(prices.index[0].date()),
        end=str(prices.index[-1].date()),
        rows=len(prices),
        checksum=checksum,
    )
    registry = _read_registry()
    registry[snapshot_id] = snap.to_dict()
    _write_registry(registry)
    return snap


def load(snapshot_id: str | None = None) -> tuple[pd.DataFrame, Snapshot]:
    """Load a pinned snapshot and verify its checksum. Never hits the network."""
    registry = _read_registry()
    if not registry:
        raise SnapshotError("No snapshots exist. Run: python -m backtest.cli snapshot")

    snapshot_id = snapshot_id or max(registry)
    if snapshot_id not in registry:
        raise SnapshotError(f"Unknown snapshot {snapshot_id!r}. Have: {sorted(registry)}")

    path = CACHE_DIR / f"{snapshot_id}.parquet"
    if not path.exists():
        raise SnapshotError(f"Snapshot {snapshot_id} is registered but {path} is missing.")

    prices = pd.read_parquet(path)
    snap = Snapshot(**{**registry[snapshot_id], "tickers": tuple(registry[snapshot_id]["tickers"])})
    actual = _checksum(prices)
    if actual != snap.checksum:
        raise SnapshotError(
            f"Snapshot {snapshot_id} failed checksum: expected {snap.checksum}, got {actual}. "
            "The cached file has been modified; results from it are not reproducible."
        )
    return prices, snap


def list_snapshots() -> list[Snapshot]:
    return [
        Snapshot(**{**meta, "tickers": tuple(meta["tickers"])})
        for _, meta in sorted(_read_registry().items())
    ]
