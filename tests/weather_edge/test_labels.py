from datetime import date

import duckdb

import weather_edge.labels as pl


def test_daily_truth_uses_local_day_and_tenths(tmp_path):
    con = duckdb.connect(str(tmp_path / "r.duckdb"))
    con.execute(
        "CREATE TABLE observations (station VARCHAR, obs_time_utc TIMESTAMP, raw VARCHAR, temp_c_whole INTEGER, temp_c_tenths DOUBLE, tmpf_iem DOUBLE)"
    )
    rows = []
    for h in range(24):  # 2026-09-20 local day in New York (EDT): 04:00Z 09-20 to 04:00Z 09-21
        rows.append(("KLGA", f"2026-09-20 {h:02d}:51", "x", 20, 20.4 if h != 19 else 23.4, None))
    rows.append(("KLGA", "2026-09-21 03:51", "x", 21, 21.0, None))  # 23:51 local on 09-20
    rows.append(("KLGA", "2026-09-21 04:51", "x", 30, 30.0, None))  # 00:51 local on 09-21: next day
    con.executemany("INSERT INTO observations VALUES (?, ?, ?, ?, ?, ?)", rows)
    assert pl.build_daily_truth(con) >= 1
    d = con.execute(
        "SELECT day, max_c, n_obs FROM daily_truth WHERE day = DATE '2026-09-20'"
    ).fetchone()
    assert d == (
        date(2026, 9, 20),
        23.4,
        21,
    )  # 04Z..23Z of 09-20 (20 reports) plus the 03:51Z report
    con.close()
