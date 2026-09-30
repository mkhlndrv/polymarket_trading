"""Known-answer checks for the EMOS model."""

import math
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

import weather_edge.model as p5
import weather_edge.pilot_nyc as p4


def test_crps_closed_form():
    # CRPS of N(0, 1) at y = 0 is 2 phi(0) - 1/sqrt(pi) = 0.2337; it scales with sigma
    assert p5.crps_normal(np.array([0.0]), np.array([1.0]), np.array([0.0]))[0] == pytest.approx(
        0.23370, abs=1e-4
    )
    assert p5.crps_normal(np.array([0.0]), np.array([2.0]), np.array([0.0]))[0] == pytest.approx(
        0.46740, abs=1e-4
    )
    # far from the forecast CRPS approaches |y - mu|
    assert p5.crps_normal(np.array([0.0]), np.array([0.5]), np.array([10.0]))[0] == pytest.approx(
        10 - 0.5 / math.sqrt(math.pi), abs=1e-3
    )


def test_fit_emos_recovers_bias_slope_and_spread_use():
    rng = np.random.default_rng(0)
    n = 400
    x1 = 20 + 8 * rng.standard_normal(n)
    x2 = x1 + rng.normal(0, 1.0, n)
    spread = rng.uniform(0.5, 3.0, n)
    y = 1.5 + 0.9 * x1 + 0.1 * x2 + rng.normal(0, 1, n) * np.sqrt(0.25 + 1.0 * spread**2)
    theta = p5.fit_emos(np.c_[x1, x2], spread, y)
    assert theta is not None
    mu, sg, nu = p5.predict_emos(theta, np.array([20.0, 20.0]), 2.0)
    assert mu == pytest.approx(1.5 + 20.0, abs=0.6)
    assert sg == pytest.approx(math.sqrt(0.25 + 4.0), rel=0.25)
    assert nu > 15  # normal errors: the fitted t is close to normal
    assert theta[1] + theta[2] == pytest.approx(1.0, abs=0.1)  # slopes sum to one
    assert p5.fit_emos(np.c_[x1[:10], x2[:10]], spread[:10], y[:10]) is None  # too short


def test_unit_conversion_and_walk_forward_leak_check():
    assert p5.to_unit(20.0, 1.0, "F") == (68.0, 1.8) and p5.to_unit(20.0, 1.0, "C") == (20.0, 1.0)
    days = pd.date_range("2026-01-01", periods=150, freq="D")
    rng = np.random.default_rng(2)
    ec = 15 + 8 * np.sin(np.arange(150) / 12) + rng.normal(0, 1, 150)
    feats = pd.DataFrame(
        {
            "day": days,
            "lead": 1,
            "t": days + pd.Timedelta(hours=16),
            "ecmwf": ec,
            "gfs": ec + rng.normal(0.5, 1, 150),
            "gefs_mean": ec + 0.3,
            "gefs_spread": np.full(150, 1.2),
        }
    )
    y = pd.Series(ec + 1.0 + rng.normal(0, 0.7, 150), index=days)
    wf = p5.walk_forward(feats, y, 1).set_index("day")
    late = wf.loc[days[140]]
    assert (
        abs((late.emos_mu - late.raw_mu) - 0.7) < 0.8
    )  # learned most of the +1 C bias net of the raw mean's own offset
    assert late.emos_sigma < late.raw_sigma
    y2 = y.copy()
    y2[days[141:]] += 50
    assert p5.walk_forward(feats, y2, 1).set_index("day").loc[
        days[140], "emos_mu"
    ] == pytest.approx(late.emos_mu)
    cs = p5.continuous_scores(wf.reset_index())
    assert set(cs.model) == {"clim", "raw", "emos"} and (cs.crps > 0).all()


def test_censored_fit_and_floor_probabilities():
    rng = np.random.default_rng(3)
    n = 400
    rest = 25 + rng.normal(0, 4, n)
    last = rest - 3 + rng.normal(0, 1, n)
    z = 1.0 + 0.8 * rest + 0.2 * last + rng.normal(0, 1.2, n)
    floor = rest - 2 + rng.normal(0, 3, n)  # running max, sometimes above the afternoon peak
    y = np.maximum(floor, z)
    assert 0.1 < (y <= floor).mean() < 0.6  # a real share of censored days
    th = p5.fit_censored(np.column_stack([rest, last]), y, floor)
    assert abs(th[1] - 0.8) < 0.1 and abs(th[2] - 0.2) < 0.1 and abs(math.exp(th[3]) - 1.2) < 0.25
    # floor kills everything below the running max and the mass reappears in the bucket holding it
    buckets = [(None, 69), (70, 71), (72, 73), (74, 75), (76, None)]
    ps = [p5.bucket_prob_floor(71.0, 1.5, 72.6, lo, hi) for lo, hi in buckets]
    assert ps[0] < 1e-3 and ps[1] < 1e-3 and abs(sum(ps) - 1) < 1e-3
    assert ps[2] > 0.8  # displayed 73 already reached, only a big afternoon rise moves it
    assert p5.bucket_prob_floor(20.0, 1.0, -math.inf, 19, 21) == pytest.approx(
        p4.bucket_prob(20.0, 1.0, 19, 21)
    )
    assert p5.crps_numeric(20.0, 1.0, 20.5) == pytest.approx(
        float(p5.crps_normal(20.0, 1.0, 20.5)), abs=0.01
    )
    assert (
        p5.crps_numeric(20.0, 1.0, 25.0, floor=25.0) < 0.05
    )  # max already in and known: near-perfect


def test_obs_walk_forward_uses_only_past_days():
    days = pd.date_range("2026-01-01", periods=140, freq="D")
    rng = np.random.default_rng(4)
    rest = 20 + 5 * np.sin(np.arange(140) / 9) + rng.normal(0, 1, 140)
    feats = pd.DataFrame(
        {
            "day": days,
            "lead": 1,
            "t": days,
            "ecmwf": rest + 1,
            "gfs": rest - 1,
            "gefs_mean": np.nan,
            "gefs_spread": np.nan,
            "ecmwf_rest": rest,
            "gfs_rest": rest - 0.5,
            "gefs_mean_rest": np.nan,
        }
    )
    z = rest + 1.5 + rng.normal(0, 0.8, 140)
    run_max = rest - 3 + rng.normal(0, 2, 140)
    y = pd.Series(np.maximum(run_max, z), index=days)
    obs = pd.DataFrame({"run_max": run_max, "last_obs": rest - 4}, index=days)
    wf = p5.walk_forward(feats, y, 1, obs=obs).set_index("day")
    late = wf.loc[days[120]]
    assert abs(late.obs_mu - (rest[120] + 1.5)) < 1.0 and late.obs_floor == run_max[120]
    y2 = y.copy()
    y2[days[121:]] += 50
    wf2 = p5.walk_forward(feats, y2, 1, obs=obs).set_index("day")
    assert wf2.loc[days[120], "obs_mu"] == pytest.approx(late.obs_mu)
    assert "obs_mu" not in p5.walk_forward(feats, y, 2, obs=obs).columns  # same-day model only


def test_features_take_spread_at_the_mean_peak_and_rest_after_decision(tmp_path):
    import duckdb

    con = duckdb.connect(str(tmp_path / "r.duckdb"))
    con.execute("CREATE TABLE daily_truth (station VARCHAR, day DATE, max_c DOUBLE)")
    con.execute("INSERT INTO daily_truth VALUES ('KLGA', DATE '2026-09-02', 30.0)")
    con.execute("ATTACH ':memory:' AS fc")
    con.execute(
        "CREATE TABLE fc.forecasts (station VARCHAR, model VARCHAR, init_time TIMESTAMP, available_time TIMESTAMP, "
        "valid_time TIMESTAMP, lead_h INTEGER, temp_c DOUBLE)"
    )
    init, avail = datetime(2026, 9, 1, 12), datetime(2026, 9, 1, 20)
    rows = []
    for step in range(0, 73, 3):
        valid = init + timedelta(hours=step)
        local_hour = (valid - timedelta(hours=4)).hour
        peak = 30 - abs(local_hour - 14) / 2  # 3-hourly steps: 14:00 local is the peak step
        for model, val in (("ecmwf", peak), ("gefs_mean", peak - 1), ("gefs_spread", step / 10)):
            rows.append(("KLGA", model, init, avail, valid, step, val))
    # NBM: one daytime maximum per run, valid 00Z 09-03 (20:00 local 09-02) = step 36 of the 12Z run
    rows.append(("KLGA", "nbm_tmax", init, avail, init + timedelta(hours=36), 36, 31.5))
    rows.append(("KLGA", "nbm_tmax_spread", init, avail, init + timedelta(hours=36), 36, 1.25))
    con.executemany("INSERT INTO fc.forecasts VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    f = p5.features(con, "KLGA", "America/New_York", 12)
    assert list(f.columns).count("gefs_spread") == 1
    r = f[f.lead == 1].iloc[0]
    # 2026-09-02 14:00 local = 18Z = step 30 of the 09-01 12Z run: spread there is 3.0
    assert r.ecmwf == 30.0 and r.gefs_mean == 29.0 and r.gefs_spread == pytest.approx(3.0)
    assert r.nbm_tmax == 31.5 and r.nbm_tmax_spread == 1.25 and r.nbm_tmax_rest == 31.5
    assert r.ecmwf_rest == 30.0  # at noon the 14:00 step is still ahead
    f15 = p5.features(con, "KLGA", "America/New_York", 15)
    # after a 15:00 decision (19Z) the remaining steps are 17:00, 20:00, 23:00 local: max at 17:00
    assert f15[f15.lead == 1].iloc[0].ecmwf_rest == pytest.approx(28.5)
    assert np.isnan(f[f.lead == 2].ecmwf).all() or (f.lead == 2).sum() == 0  # run not public yet
    con.close()


def test_t_crps_closed_form_and_heavy_tail_fit():
    for nu, y in ((3.0, 0.4), (5.5, -2.0), (40.0, 1.0)):
        assert float(p5.crps_t(0.0, 1.3, nu, y)) == pytest.approx(
            p5.crps_numeric(0.0, 1.3, y, nu=nu, step=0.005), abs=0.01
        )
    assert float(p5.crps_t(0.0, 1.0, 1e6, 0.3)) == pytest.approx(
        float(p5.crps_normal(0.0, 1.0, 0.3)), abs=1e-3
    )
    rng = np.random.default_rng(5)
    n = 600
    x = 20 + 6 * rng.standard_normal(n)
    y = 1.0 + x + 1.5 * rng.standard_t(4, n)  # heavy tails
    theta = p5.fit_emos(x[:, None], np.full(n, np.nan), y)
    mu, sg, nu = p5.predict_emos(theta, np.array([20.0]), np.nan)
    assert nu < 8 and mu == pytest.approx(21.0, abs=0.4) and sg == pytest.approx(1.5, rel=0.3)
    # the t interval covers, the normal fit of the same data would not
    q = np.array([p5.ppf(0.95, 0, 1, nu)])[0]
    assert 1.9 < q < 2.6
    ps = [
        p5.bucket_prob_floor(72.4, 1.5, -math.inf, lo, hi, 4.0)
        for lo, hi in [(None, 69), (70, 71), (72, 73), (74, 75), (76, None)]
    ]
    assert abs(sum(ps) - 1) < 1e-3 and ps[0] > p5.bucket_prob_floor(72.4, 1.5, -math.inf, None, 69)


def test_out_of_sample_scale_inflation_is_point_in_time():
    days = pd.date_range("2026-01-01", periods=200, freq="D")
    rng = np.random.default_rng(6)
    ec = 15 + 8 * np.sin(np.arange(200) / 12) + rng.normal(0, 1, 200)
    feats = pd.DataFrame(
        {
            "day": days,
            "lead": 2,
            "t": days,
            "ecmwf": ec,
            "gfs": ec + 0.2,
            "gefs_mean": np.nan,
            "gefs_spread": np.nan,
        }
    )
    # errors change regime: the trailing fit is too confident right after the switch
    noise = np.where(np.arange(200) < 120, 0.5, 2.5) * rng.standard_normal(200)
    y = pd.Series(ec + 1.0 + noise, index=days)
    wf = p5.walk_forward(feats, y, 2).set_index("day")
    assert wf.loc[days[100], "emos_scale"] == pytest.approx(1.0, abs=0.3)
    assert wf.loc[days[195], "emos_scale"] > 1.8  # the wider regime is learned from past misses
    # the scale on day 195 uses only days before 194 (lead 2): changing later labels does nothing
    y2 = y.copy()
    y2[days[194:]] += 100
    wf2 = p5.walk_forward(feats, y2, 2).set_index("day")
    assert wf2.loc[days[195], "emos_scale"] == pytest.approx(wf.loc[days[195], "emos_scale"])
    assert wf2.loc[days[195], "emos_mu"] == pytest.approx(wf.loc[days[195], "emos_mu"])


def test_emos_with_two_spread_terms():
    rng = np.random.default_rng(7)
    n = 500
    x = 20 + 6 * rng.standard_normal(n)
    s1 = rng.uniform(0.5, 2.0, n)
    s2 = rng.uniform(0.5, 3.0, n)
    y = x + 0.5 + rng.standard_normal(n) * np.sqrt(0.2 + 0.1 * s1**2 + 1.0 * s2**2)
    theta = p5.fit_emos(x[:, None], np.c_[s1, s2], y)
    assert len(theta) == 1 + 1 + 1 + 2 + 1
    mu, sg, nu = p5.predict_emos(theta, np.array([20.0]), np.array([1.0, 2.0]))
    assert mu == pytest.approx(20.5, abs=0.4) and sg == pytest.approx(
        math.sqrt(0.2 + 0.1 + 4.0), rel=0.2
    )
    assert math.exp(theta[4]) > 3 * math.exp(theta[3])  # the second spread carries the variance
