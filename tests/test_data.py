"""Snapshot tests. No network: `create_snapshot` is the only function that fetches."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from backtest import data


@pytest.fixture
def snapshot_store(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "DATA_DIR", tmp_path)
    monkeypatch.setattr(data, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(data, "REGISTRY", tmp_path / "snapshots.json")
    (tmp_path / "cache").mkdir()
    return tmp_path


def _write(store, snapshot_id, created, tickers=("SPY",), rows=3):
    frame = pd.DataFrame(
        {t: [1.0, 2.0, 3.0][:rows] for t in tickers},
        index=pd.bdate_range("2020-01-01", periods=rows, name="date"),
    )
    frame.to_parquet(store / "cache" / f"{snapshot_id}.parquet")
    registry = json.loads(data.REGISTRY.read_text()) if data.REGISTRY.exists() else {}
    registry[snapshot_id] = {
        "id": snapshot_id,
        "created": created,
        "tickers": list(tickers),
        "start": "2020-01-01",
        "end": "2020-01-03",
        "rows": rows,
        "checksum": data._checksum(frame),
    }
    data.REGISTRY.write_text(json.dumps(registry), encoding="utf-8")
    return frame


def test_load_picks_the_most_recently_created_not_the_highest_id(snapshot_store):
    """Ids are `date-checksum`; the checksum half sorts arbitrarily.

    Regression test: lexicographic max selected an older snapshot, silently
    running a strategy against a basket missing a ticker it needed.
    """
    _write(snapshot_store, "2026-08-27-e90ccca6", created="2026-08-27T10:00:00", tickers=("SPY",))
    _write(
        snapshot_store,
        "2026-08-27-02dd5081",
        created="2026-08-27T11:00:00",
        tickers=("SPY", "BIL"),
    )

    _, snap = data.load()
    assert snap.id == "2026-08-27-02dd5081"
    assert "BIL" in snap.tickers


def test_load_verifies_the_checksum(snapshot_store):
    _write(snapshot_store, "snap-1", created="2026-01-01T00:00:00")

    tampered = pd.DataFrame(
        {"SPY": [9.9, 9.9, 9.9]},
        index=pd.bdate_range("2020-01-01", periods=3, name="date"),
    )
    tampered.to_parquet(snapshot_store / "cache" / "snap-1.parquet")

    with pytest.raises(data.SnapshotError, match="failed checksum"):
        data.load("snap-1")


def test_load_without_snapshots_explains_how_to_make_one(snapshot_store):
    with pytest.raises(data.SnapshotError, match="No snapshots exist"):
        data.load()


def test_unknown_snapshot_id_is_refused(snapshot_store):
    _write(snapshot_store, "snap-1", created="2026-01-01T00:00:00")
    with pytest.raises(data.SnapshotError, match="Unknown snapshot"):
        data.load("nope")


def test_registered_but_missing_file_is_refused(snapshot_store):
    _write(snapshot_store, "snap-1", created="2026-01-01T00:00:00")
    (snapshot_store / "cache" / "snap-1.parquet").unlink()

    with pytest.raises(data.SnapshotError, match="is missing"):
        data.load("snap-1")
