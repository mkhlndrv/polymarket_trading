"""Known-answer checks for the Phase 1 loaders."""

from datetime import UTC, datetime

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

import weather_edge.prices as pp
import weather_edge.trades as pt


def _trades_table(n=6):
    return pa.table(
        {
            "timestamp": pa.array([1_740_000_000 + i for i in range(n)], pa.uint64()),
            "block_number": pa.array([1] * n, pa.uint64()),
            "transaction_hash": [f"h{i}" for i in range(n)],
            "log_index": pa.array(list(range(n)), pa.uint32()),
            "market_id": ["1", "2", "3", "1", "2", "9"][:n],
            "condition_id": ["c"] * n,
            "maker": ["m"] * n,
            "taker": ["t"] * n,
            "price": [0.5] * n,
            "usd_amount": [5.0] * n,
            "token_amount": [10.0] * n,
            "maker_direction": ["SELL"] * n,
            "taker_direction": ["BUY"] * n,
            "nonusdc_side": ["token1"] * n,
            "asset_id": ["a"] * n,
        }
    )


def test_filter_group_keeps_only_inventory_markets():
    out = pt.filter_group(_trades_table(), {"1", "3"})
    assert out["market_id"].to_pylist() == ["1", "3", "1"]


def test_stream_skips_old_groups_and_writes_matches(tmp_path):
    src = tmp_path / "src.parquet"
    pq.write_table(
        _trades_table(), src, row_group_size=3
    )  # two groups: ts ...000-002 and ...003-005
    pf = pq.ParquetFile(src)
    out = tmp_path / "out.parquet"
    groups, rows = pt.stream(pf, {"1", "2"}, out, since_ts=1_740_000_003)
    assert (groups, rows) == (1, 2)  # only the second group is read: market 1 and 2 rows
    assert pq.read_table(out)["market_id"].to_pylist() == ["1", "2"]


def test_load_and_check_against_gamma_volume(tmp_path):
    con = duckdb.connect(str(tmp_path / "t.duckdb"))
    con.execute(
        "CREATE TABLE markets (market_id VARCHAR, closed BOOLEAN, date DATE, volume_usd DOUBLE)"
    )
    con.execute(
        "INSERT INTO markets VALUES ('1', true, DATE '2026-01-01', 20.0), "
        "('2', true, DATE '2026-01-01', 100.0)"
    )
    path = tmp_path / "trades.parquet"
    pq.write_table(_trades_table(), path)
    assert pt.load(con, path) == 6
    assert con.execute("SELECT min(ts) FROM trades").fetchone()[0] == datetime(2025, 2, 19, 21, 20)
    r = pt.check(con, "2026-07-20")
    assert r["markets"] == 2 and r["with_trades"] == 2
    assert r["share_within_1pct"] == 0.5  # market 1: 20 shares = Gamma 20; market 2: 20 vs 100
    con.close()


class _Resp:
    def __init__(self, data, status=200):
        self._d, self.status_code = data, status

    def json(self):
        return self._d


class _Session:
    def __init__(self):
        self.calls = []
        self.fail_once = True

    def get(self, url, params=None, timeout=None):
        self.calls.append(dict(params))
        if self.fail_once:
            self.fail_once = False
            return _Resp(None, 429)
        if params["market"] == "empty":
            return _Resp({"history": []})
        if params["market"] == "bad":
            return _Resp({"error": "invalid filters"}, 400)
        return _Resp(
            {"history": [{"t": params["startTs"] + 60 * k, "p": 0.1 * k} for k in range(3)]}
        )


def test_prices_run_windows_stores_and_skips_done(tmp_path, monkeypatch):
    monkeypatch.setattr(pp.time, "sleep", lambda _s: None)
    con = duckdb.connect(str(tmp_path / "p.duckdb"))
    con.execute(
        "CREATE TABLE markets (market_id VARCHAR, clob_token_yes VARCHAR, created_at TIMESTAMP, "
        "closed_at TIMESTAMP, end_date TIMESTAMP, date DATE)"
    )
    con.execute(
        """INSERT INTO markets VALUES
        ('1', 'tokA', TIMESTAMP '2026-02-24 15:25:10', TIMESTAMP '2026-02-25 17:08:38', NULL,
         DATE '2026-02-25'),
        ('2', 'empty', TIMESTAMP '2026-09-28 10:00:00', NULL, NULL, DATE '2026-09-30'),
        ('3', 'bad', TIMESTAMP '2026-05-18 04:04:25', NULL, TIMESTAMP '2026-05-20 12:00:00',
         DATE '2026-05-20')"""
    )
    s = _Session()
    now = datetime(2026, 9, 29, 12, tzinfo=UTC)
    assert pp.run(con, s, fidelity=5, pause=0, limit=None, now=now) == 5  # 3 pts + 2 markers
    p3 = [c for c in s.calls if c["market"] == "bad"][-1]
    assert p3["endTs"] == int(datetime(2026, 5, 22, 0, 0, tzinfo=UTC).timestamp())  # end_date + 36h
    p1 = [c for c in s.calls if c["market"] == "tokA"][-1]
    assert p1["startTs"] == int(datetime(2026, 2, 24, 14, 25, 10, tzinfo=UTC).timestamp())
    assert p1["endTs"] == int(datetime(2026, 2, 25, 18, 8, 38, tzinfo=UTC).timestamp())
    p2 = [c for c in s.calls if c["market"] == "empty"][-1]
    assert p2["endTs"] == int(now.timestamp())  # open market: window ends now
    rows = con.execute(
        "SELECT market_id, ts, price FROM prices_history ORDER BY market_id, ts"
    ).df()
    assert len(rows) == 5 and rows.iloc[0]["ts"] == pd.Timestamp("2026-02-24 14:25:10")
    assert pp.pending(con).empty  # nothing left, including the empty market
    assert len(s.calls) == 3 + 6  # three markets, one 429 retry, six tries on the bad token
    con.close()
