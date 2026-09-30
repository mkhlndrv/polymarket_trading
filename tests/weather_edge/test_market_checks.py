"""Known-answer checks for phase1_checks on a two-market synthetic database."""

from datetime import datetime

import duckdb

import weather_edge.market_checks as pc


def _dbs(tmp_path):
    research, prices = tmp_path / "r.duckdb", tmp_path / "p.duckdb"
    con = duckdb.connect(str(research))
    con.execute(
        "CREATE TABLE markets (market_id VARCHAR, event_id VARCHAR, city VARCHAR, station VARCHAR, "
        "date DATE, unit VARCHAR, resolution_source VARCHAR, is_winner BOOLEAN, volume_usd DOUBLE, "
        "bucket_lo INTEGER, bucket_hi INTEGER, closed BOOLEAN, resolved_bucket VARCHAR)"
    )
    # London 2026-02-25 (GMT, local midnight = 2026-02-26 00:00Z): two buckets, the second wins
    con.execute(
        """INSERT INTO markets VALUES
        ('1', 'e', 'London', 'EGLC', DATE '2026-02-25', 'C', 'wunderground', false, 10, NULL, 17, true, '18°C'),
        ('2', 'e', 'London', 'EGLC', DATE '2026-02-25', 'C', 'wunderground', true, 20, 18, 18, true, '18°C')"""
    )
    con.execute(
        "CREATE TABLE trades (ts TIMESTAMP, market_id VARCHAR, maker VARCHAR, taker VARCHAR, "
        "price DOUBLE, token_amount DOUBLE, taker_direction VARCHAR, nonusdc_side VARCHAR)"
    )
    # taker buys YES of the loser at 0.30 (loses 3), taker buys NO of the winner at 0.40
    # (= sells YES at 0.60, loses 0.40 * 10 = 4)
    con.execute(
        """INSERT INTO trades VALUES
        (TIMESTAMP '2026-02-25 10:00', '1', 'mA', 'tA', 0.30, 10, 'BUY', 'token1'),
        (TIMESTAMP '2026-02-25 11:00', '2', 'mA', 'tB', 0.40, 10, 'BUY', 'token2')"""
    )
    con.close()
    p = duckdb.connect(str(prices))
    p.execute("CREATE TABLE prices_history (market_id VARCHAR, ts TIMESTAMP, price DOUBLE)")
    # market 1: 0.30 all day; market 2: 0.50 until 20:00Z then 0.90 (h=3 -> 21:00Z sees 0.90).
    # Points older than 6 hours are ignored, hence the 11:00Z points for h=12.
    p.execute(
        """INSERT INTO prices_history VALUES
        ('1', TIMESTAMP '2026-02-25 00:00', 0.30), ('1', TIMESTAMP '2026-02-25 11:00', 0.30),
        ('1', TIMESTAMP '2026-02-25 20:30', 0.30),
        ('2', TIMESTAMP '2026-02-25 00:00', 0.50), ('2', TIMESTAMP '2026-02-25 11:00', 0.50),
        ('2', TIMESTAMP '2026-02-25 20:00', 0.90)"""
    )
    p.close()
    return str(research), str(prices)


def test_horizon_prices_are_as_of_local_midnight(tmp_path):
    con = pc.connect(*_dbs(tmp_path))
    pc.build_views(con)
    rows = con.execute(
        "SELECT market_id, h, t, price FROM horizon_px ORDER BY market_id, h DESC"
    ).fetchall()
    by = {(m, h): (t, p) for m, h, t, p in rows}
    assert by[("2", 12)] == (datetime(2026, 2, 25, 12), 0.50)  # last point at or before 12:00Z
    assert by[("2", 3)] == (datetime(2026, 2, 25, 21), 0.90)
    assert by[("2", 1)][1] == 0.90 and by[("1", 1)][1] == 0.30
    assert ("2", 30) not in by  # 2026-02-24 18:00Z has no point within 6 hours before it
    cal = pc.t1_calibration(con)
    b3 = cal["brier"].set_index("h").loc[3]
    assert abs(b3["brier_market"] - ((0.30 - 0) ** 2 + (0.90 - 1) ** 2) / 2) < 1e-9
    ext = pc.t2_extremes(con)
    edge = ext[(ext.h == 3) & (ext.bucket_pos == "low_edge")].iloc[0]
    assert edge["hit_rate"] == 0 and abs(edge["return_per_share"] + 0.30) < 1e-9
    s = pc.t3_sum_of_yes(con).set_index("h")
    assert abs(s.loc[3, "mean_sum"] - 1.20) < 1e-9 and abs(s.loc[12, "mean_sum"] - 0.80) < 1e-9


def test_maker_taker_pnl_signs_and_capacity(tmp_path):
    con = pc.connect(*_dbs(tmp_path))
    pc.build_views(con)
    t4 = pc.t4_maker_taker(con)
    o = t4["overall"].iloc[0]
    assert bool(o["complete_month"]) and t4["fill_coverage"].iloc[0]["month"] == "2026-02"
    assert o["n_fills"] == 2 and o["shares"] == 20 and abs(o["taker_pnl_usd"] + 7.0) < 1e-9
    assert abs(o["share_taker_buys_yes"] - 0.5) < 1e-9
    mk = t4["makers"].iloc[0]
    assert mk["maker"] == "mA" and abs(mk["maker_pnl_usd"] - 7.0) < 1e-9
    band = t4["by_band"].set_index("side")
    assert abs(band.loc["taker sells YES", "taker_pnl_per_share"] + 0.40) < 1e-9  # YES at 0.60, won
    cap = pc.t5_capacity(con).iloc[0]
    assert (
        cap["n_days"] == 1
        and cap["mean_shares_per_day"] == 20
        and cap["mean_extreme_shares_per_day"] == 0
    )
    cov = pc.coverage(con).iloc[0]
    assert cov["resolved_markets"] == 2 and cov["markets_with_fills"] == 2
