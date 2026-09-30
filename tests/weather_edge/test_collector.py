"""Known-answer checks for the collector's parsers, storage and loop."""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

import weather_edge.collector as c

FIXTURE = Path(__file__).parent / "fixtures" / "gamma_events_sample.jsonl"
T = datetime(2026, 9, 30, 8, 0, 0)


def test_market_rows_and_rules_history():
    ev = [json.loads(line) for line in FIXTURE.read_text().splitlines()][2]  # NYC 2026-09-02
    rows = c.market_rows(ev, T)
    assert len(rows) == 11 and rows[0]["station"] == "KLGA" and rows[0]["token_yes"]
    state = {}
    first = c.rules_rows(rows, state)
    assert len(first) == 11 and c.rules_rows(rows, state) == []  # unchanged hashes: no new rows
    rows[0]["rules_hash"] = "changed"
    assert len(c.rules_rows(rows, state)) == 1


def test_book_rows_dedupe_by_hash():
    books = [
        {
            "asset_id": "t1",
            "hash": "h1",
            "timestamp": "1790754506435",
            "bids": [{"price": "0.02", "size": "22"}, {"price": "0.01", "size": "15"}],
            "asks": [{"price": "0.99", "size": "3503"}, {"price": "0.98", "size": "138"}],
            "last_trade_price": "0.63",
            "min_order_size": "5",
            "tick_size": "0.01",
        }
    ]
    state = {}
    rows = c.book_rows(books, {"t1": "m1"}, T, state)
    assert len(rows) == 1
    r = rows[0]
    assert (r["market_id"], r["best_bid"], r["best_ask"]) == ("m1", 0.02, 0.98)
    assert r["book_ts"] == datetime(2026, 9, 30, 7, 48, 26, 435000) and json.loads(r["bids"])[
        -1
    ] == [0.02, 22.0]
    assert c.book_rows(books, {"t1": "m1"}, T, state) == []  # same hash: nothing new
    books[0]["hash"] = "h2"
    assert len(c.book_rows(books, {"t1": "m1"}, T, state)) == 1


def test_metar_rows_keep_tenths_and_dedupe():
    reports = [
        {
            "icaoId": "KLGA",
            "obsTime": 1790751060,
            "reportTime": "2026-09-30T07:00:00.000Z",
            "receiptTime": "2026-09-30T06:54:10.393Z",
            "temp": 17.8,
            "dewp": 13.9,
            "rawOb": "METAR KLGA 300651Z ... T01780139",
            "metarType": "METAR",
        }
    ]
    state = {}
    rows = c.metar_rows(reports, T, state)
    assert (
        len(rows) == 1
        and rows[0]["temp_c"] == 17.8
        and rows[0]["receipt_time"] == datetime(2026, 9, 30, 6, 54, 10, 393000)
    )
    assert rows[0]["obs_time"] == datetime(2026, 9, 30, 6, 51)
    assert c.metar_rows(reports, T, state) == []
    speci = dict(reports[0], rawOb="SPECI KLGA 300655Z ...", metarType="SPECI", obsTime=1790751300)
    assert len(c.metar_rows([speci], T, state)) == 1


def test_hko_rows_convert_hkt_to_utc():
    text = (
        "Date time,Automatic Weather Station,Air Temperature(degree Celsius)\n"
        "202609301500,HK Observatory,33.1\n202609301500,King's Park,32.4\n"
    )
    state = {}
    rows = c.hko_rows(text, T, state)
    assert (
        len(rows) == 1
        and rows[0]["temp_c"] == 33.1
        and rows[0]["obs_time"] == datetime(2026, 9, 30, 7, 0)
    )
    assert c.hko_rows(text, T, state) == []


def test_forecast_rows_per_model():
    payload = {
        "hourly": {
            "time": ["2026-09-30T00:00", "2026-09-30T01:00"],
            "temperature_2m_gfs_seamless": [17.1, 16.9],
            "temperature_2m_ecmwf_ifs025": [17.5, None],
        }
    }
    rows = c.forecast_rows(payload, "KLGA", T)
    assert len(rows) == 3 and {r["model"] for r in rows} == {"gfs_seamless", "ecmwf_ifs025"}
    assert rows[0] == {
        "available_time": T,
        "station": "KLGA",
        "model": "gfs_seamless",
        "valid_time": datetime(2026, 9, 30, 0, 0),
        "temp_c": 17.1,
    }


def test_store_flush_writes_parquet_and_state(tmp_path):
    st = c.Store(tmp_path / "out")
    st.add("books", [{"a": 1, "fetched_at": T}])
    st.add("observations", [])
    written = st.flush(when=datetime(2026, 9, 30, 8, 15, 0))
    assert [str(w.relative_to(tmp_path / "out")) for w in written] == [
        "books/2026-09-30/081500.parquet"
    ]
    assert pd.read_parquet(written[0])["a"].tolist() == [1]
    assert (
        json.loads((tmp_path / "out" / "state.json").read_text())["pending_uploads"] == []
    )  # no bucket


class _Resp:
    def __init__(self, data, status=200, text=""):
        self._d, self.status_code, self.text = data, status, text or json.dumps(data)

    def json(self):
        return self._d

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class _Session:
    """Serves one live event from the fixture, one book per token, one METAR, one forecast."""

    headers = {}

    def __init__(self):
        self.ev = [json.loads(line) for line in FIXTURE.read_text().splitlines()][2]
        self.ev["eventDate"] = "2026-09-30"
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append(url)
        if "events/keyset" in url:
            return _Resp({"events": [self.ev], "next_cursor": None})
        if "stationinfo" in url:
            return _Resp([{"icaoId": "KLGA", "lat": 40.78, "lon": -73.88}])
        if "metar" in url:
            return _Resp(
                [
                    {
                        "icaoId": "KLGA",
                        "obsTime": 1790751060,
                        "temp": 17.8,
                        "rawOb": "x",
                        "metarType": "METAR",
                    }
                ]
            )
        if "open-meteo" in url:
            return _Resp(
                {"hourly": {"time": ["2026-09-30T00:00"], "temperature_2m_gfs_seamless": [17.0]}}
            )
        raise AssertionError(url)

    def post(self, url, json=None, timeout=None):
        self.calls.append(url)
        return _Resp(
            [
                {
                    "asset_id": x["token_id"],
                    "hash": "h",
                    "timestamp": "1790754506435",
                    "bids": [],
                    "asks": [],
                }
                for x in json
            ]
        )


def test_one_cycle_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(c.time, "sleep", lambda _s: None)
    st = c.Store(tmp_path / "out")
    col = c.Collector(st, session=_Session())
    col.run(once=True)
    tables = sorted(p.name for p in (tmp_path / "out").iterdir() if p.is_dir())
    assert tables == ["books", "forecasts", "markets_live", "observations", "rules_history"]
    books = pd.read_parquet(next((tmp_path / "out" / "books").rglob("*.parquet")))
    assert len(books) == 11 and books["market_id"].notna().all()
    assert (tmp_path / "out" / "heartbeat").exists()
    # a second cycle with unchanged books and reports adds no book or observation rows
    col.run(once=True)
    assert len(list((tmp_path / "out" / "books").rglob("*.parquet"))) == 1
