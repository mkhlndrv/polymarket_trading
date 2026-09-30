"""Known-answer checks for the Phase 4 chain."""

from datetime import date, datetime

import numpy as np
import pandas as pd
import pytest

import weather_edge.pilot_nyc as p4


def test_bucket_probabilities_sum_to_one_and_use_half_integers():
    buckets = [(None, 69), (70, 71), (72, 73), (74, 75), (76, None)]
    ps = [p4.bucket_prob(72.4, 1.5, lo, hi) for lo, hi in buckets]
    assert abs(sum(ps) - 1) < 1e-3
    assert p4.bucket_prob(72.0, 0.3, 72, 72) > 0.9  # sigma floor 0.3, integer displayed value
    assert p4.bucket_prob(72.0, 1.0, 72, 73) == pytest.approx(
        p4.normal_cdf(1.5) - p4.normal_cdf(-0.5), abs=1e-9
    )


def test_point_in_time_mapping():
    # NYC in EDT: 12:00 local on 2026-09-02 is 16:00Z
    assert p4.decision_time_utc(date(2026, 9, 2), 1, "America/New_York") == datetime(2026, 9, 2, 16)
    assert p4.decision_time_utc(date(2026, 9, 2), 2, "America/New_York") == datetime(2026, 9, 1, 16)
    # the last hour of the local day (03:00Z next day) at lead 1 was predicted 24h earlier and public 8h later
    p4.assert_point_in_time(datetime(2026, 9, 3, 3), 1, datetime(2026, 9, 2, 16))
    with pytest.raises(AssertionError):
        p4.assert_point_in_time(
            datetime(2026, 9, 3, 3), 1, datetime(2026, 9, 2, 10)
        )  # 10Z: run not public
    with pytest.raises(AssertionError):
        p4.assert_point_in_time(
            datetime(2026, 9, 2, 20), 0, datetime(2026, 9, 2, 16)
        )  # lead 0 leaks


def test_parse_previous_runs():
    payload = {
        "hourly": {
            "time": ["2026-09-02T00:00", "2026-09-02T01:00"],
            "temperature_2m_previous_day1_gfs_seamless": [20.0, None],
            "temperature_2m_previous_day2_ecmwf_ifs025": [19.5, 19.0],
        }
    }
    df = p4.parse_previous_runs(payload, datetime(2026, 9, 30))
    assert (
        len(df) == 3
        and set(df.model) == {"gfs_seamless", "ecmwf_ifs025"}
        and set(df.lead_days) == {1, 2}
    )


def test_walk_forward_uses_only_past_labels_and_recovers_a_bias():
    days = pd.date_range("2026-01-01", periods=120, freq="D").date
    rng = np.random.default_rng(1)
    model_mean = 60 + 10 * np.sin(np.arange(120) / 10) + rng.normal(0, 1, 120)
    y = pd.Series(model_mean + 2.0 + rng.normal(0, 0.5, 120), index=days)  # label = model + 2F bias
    feats = pd.DataFrame(
        {"day": days, "lead_days": 1, "model_mean": model_mean, "model_spread": 1.0, "n_models": 4}
    )
    wf = p4.walk_forward(feats, y, 1).set_index("day")
    late = wf.loc[days[100]]
    assert abs((late.emos_mu - late.raw_mu) - 2.0) < 0.6  # EMOS learned the bias, raw did not
    assert late.emos_sigma < late.raw_sigma
    assert pd.isna(wf.loc[days[5], "emos_mu"]) and pd.isna(
        wf.loc[days[5], "clim_mu"]
    )  # no history yet
    # leak check: shifting future labels must not change today's fit
    y2 = y.copy()
    y2[days[101:]] += 100
    wf2 = p4.walk_forward(feats, y2, 1).set_index("day")
    assert wf2.loc[days[100], "emos_mu"] == pytest.approx(late.emos_mu)


def test_bootstrap_ci_and_backtest_fill_logic(tmp_path):
    import duckdb

    diff = pd.Series([0.1, 0.1, -0.05, 0.2])
    days = pd.Series([date(2026, 1, 1), date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)])
    lo, hi = p4.bootstrap_ci(diff, days, n=200)
    assert lo <= diff.mean() <= hi
    con = duckdb.connect(str(tmp_path / "x.duckdb"))
    con.execute("ATTACH ':memory:' AS px")
    con.execute("CREATE TABLE px.prices_history (market_id VARCHAR, ts TIMESTAMP, price DOUBLE)")
    con.execute("""INSERT INTO px.prices_history VALUES
        ('w', TIMESTAMP '2026-01-01 17:00', 0.25), ('w', TIMESTAMP '2026-01-01 18:00', 0.19),
        ('l', TIMESTAMP '2026-01-01 17:00', 0.30), ('l', TIMESTAMP '2026-01-01 18:00', 0.10),
        ('n', TIMESTAMP '2026-01-01 17:00', 0.40)""")
    df = pd.DataFrame(
        {
            "day": [date(2026, 1, 1)] * 3,
            "lead": 1,
            "market_id": ["w", "l", "n"],
            "t": [datetime(2026, 1, 1, 16)] * 3,
            "market_p": [0.20, 0.30, 0.40],
            "outcome": [1, 0, 1],
            "p_raw": [0.45, 0.45, 0.42],
        }
    )
    bt = p4.backtest(con, df, "raw", "America/New_York").set_index("market_id")
    assert (
        bool(bt.loc["w", "touched"])
        and bt.loc["w", "filled"] == 0.5
        and bt.loc["w", "pnl"] == pytest.approx(0.5 * (1 - 0.19) * 5)
    )
    assert (
        bool(bt.loc["l", "touched"])
        and bt.loc["l", "filled"] == 1.0
        and bt.loc["l", "pnl"] == pytest.approx(-0.29 * 5)
    )
    assert "n" not in bt.index  # edge 0.02 < 0.10: no order
    s = p4.summarize_backtest(bt.reset_index())
    assert s["orders"] == 2 and s["filled_shares"] == 7.5
    con.close()


def test_open_archive_features_use_only_runs_public_at_decision(tmp_path):
    import duckdb

    con = duckdb.connect(str(tmp_path / "r.duckdb"))
    con.execute(
        "CREATE TABLE markets (station VARCHAR, date DATE, closed BOOLEAN, resolved_bucket VARCHAR)"
    )
    con.execute("INSERT INTO markets VALUES ('KLGA', DATE '2026-09-02', true, 'x')")
    con.execute("ATTACH ':memory:' AS fc")
    con.execute(
        "CREATE TABLE fc.forecasts (station VARCHAR, model VARCHAR, init_time TIMESTAMP, available_time TIMESTAMP, "
        "valid_time TIMESTAMP, lead_h INTEGER, temp_c DOUBLE)"
    )
    rows = []
    # lead-1 decision is 2026-09-02 16:00Z. Run A (09-01 12Z, public 20:00Z) peaks at 30C; run B (09-02 12Z,
    # public 20:37Z, after the decision) peaks at 35C and must be ignored. Lead-2 decision is 09-01 16:00Z,
    # before run A is public, so lead 2 has no feature at all.
    for init, avail, peak in (
        (datetime(2026, 9, 1, 12), datetime(2026, 9, 1, 20), 30.0),
        (datetime(2026, 9, 2, 12), datetime(2026, 9, 2, 20, 37), 35.0),
    ):
        for step in range(0, 73, 3):
            valid = init + pd.Timedelta(hours=step)
            local_hour = (valid - pd.Timedelta(hours=4)).hour
            rows.append(
                (
                    "KLGA",
                    "ecmwf",
                    init,
                    avail + pd.Timedelta(minutes=step),
                    valid,
                    step,
                    peak - abs(local_hour - 15) / 2,
                )
            )  # each step file appears a little later than the previous one, as on the real mirrors
    con.executemany("INSERT INTO fc.forecasts VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    f = p4.daily_model_max_open(con, "America/New_York").set_index(["day", "lead_days"])
    d = pd.Timestamp("2026-09-02")
    assert f.loc[(d, 1), "ecmwf"] == p4.c_to_f(29.5)  # 3-hourly steps: 14:00 local, not 15:00
    assert (d, 2) not in f.index and (d, 3) not in f.index
    con.close()
