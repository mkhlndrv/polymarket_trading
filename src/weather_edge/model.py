"""The model: EMOS fit by CRPS per station and lead, scored against the market point in time.

Features at a decision time are the latest run of each source whose steps inside the local day were
all public by then; the feature is the run's maximum over those steps. The predictive distribution
is a Student t whose scale is a linear function of the ensemble spreads, fit by minimising the CRPS
over a trailing window, then rescaled by the root mean square of the last out-of-sample errors.
Without that last step the nominal 90% interval covered 82% of days.

The same-day variant conditions on the running maximum and the last METAR: the final high is
max(running max, Z) with Z from a censored regression, which is what a resting observation does to
the distribution.

Scores: CRPS and PIT on every day; Brier and log loss against the as-of market price on resolved
buckets, and the market-minus-model Brier on the buckets where the two disagree by 10c or more,
with a day bootstrap. --holdout scores the untouched period once.
"""

from __future__ import annotations

import argparse
import logging
import math
import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import beta as beta_fn
from scipy.stats import norm
from scipy.stats import t as t_dist

from weather_edge import config
from weather_edge.config import HOLDOUT_START
from weather_edge.market_checks import STATION_TZ
from weather_edge.pilot_nyc import bootstrap_ci

SOURCES = ["ecmwf", "gfs", "gefs_mean", "gefs_spread", "nbm_tmax", "nbm_tmax_spread"]
DET = ["ecmwf", "gfs", "gefs_mean", "nbm_tmax"]  # deterministic inputs (maxima)
SPREADS = {"gefs_mean": "gefs_spread", "nbm_tmax": "nbm_tmax_spread"}  # mean -> its spread
REST = [f"{c}_rest" for c in DET]
LEADS = [1, 2, 3]
MODELS = ("clim", "raw", "emos", "obs")
OBS_DELAY_MIN = 5  # a METAR counts as reported this many minutes after its observation time
log = logging.getLogger("phase5")


# ------------------------------------------------------------------------------ features
def features(
    con, station: str, tz: str, decision_hour: int = 12, extra_days: list[date] | None = None
) -> pd.DataFrame:
    """Wide frame: day, lead, one column per source (C), spread at the mean's max, decision time t.
    Days come from daily_truth; extra_days adds days without a label yet (live decisions)."""
    extra = ", ".join(f"DATE '{d.isoformat()}'" for d in extra_days or [])
    union = f" UNION SELECT unnest([{extra}])" if extra else ""
    df = con.execute(
        f"""
        WITH days AS (SELECT day FROM daily_truth WHERE station = ?{union}),
        dec AS (
          SELECT day, k AS lead,
                 ((day - (k - 1) * INTERVAL 1 DAY + INTERVAL {int(decision_hour)} HOUR)::TIMESTAMP AT TIME ZONE ?) AT TIME ZONE 'UTC' AS t
          FROM days CROSS JOIN (SELECT unnest([1, 2, 3]) AS k)),
        steps AS (
          SELECT d.day, d.lead, d.t, f.model, f.init_time, f.available_time, f.valid_time, f.temp_c
          FROM dec d JOIN fc.forecasts f
            ON f.station = ?
           AND ((f.valid_time AT TIME ZONE 'UTC') AT TIME ZONE ?) >= d.day::TIMESTAMP
           AND ((f.valid_time AT TIME ZONE 'UTC') AT TIME ZONE ?) < (d.day + INTERVAL 1 DAY)::TIMESTAMP),
        runs AS (
          SELECT day, lead, t, model, init_time, max(available_time) AS available_time,
                 max(temp_c) AS max_c, arg_max(valid_time, temp_c) AS t_of_max, count(*) AS n,
                 max(temp_c) FILTER (WHERE valid_time > t) AS rest_c
          FROM steps GROUP BY 1, 2, 3, 4, 5
          HAVING max(available_time) <= t AND count(*) >= CASE WHEN model LIKE 'nbm%' THEN 1 ELSE 7 END),
        latest AS (
          SELECT * FROM runs QUALIFY row_number() OVER (PARTITION BY day, lead, model ORDER BY init_time DESC) = 1)
        SELECT l.day, l.lead, l.t, l.model, l.init_time, l.available_time, l.max_c, l.rest_c,
               CASE WHEN l.model IN ('gefs_mean', 'nbm_tmax') THEN (
                 SELECT s.temp_c FROM steps s WHERE s.day = l.day AND s.lead = l.lead
                    AND s.model = CASE l.model WHEN 'gefs_mean' THEN 'gefs_spread' ELSE 'nbm_tmax_spread' END
                    AND s.init_time = l.init_time AND s.valid_time = l.t_of_max) END AS spread_at_max
        FROM latest l
        """,
        [station, tz, station, tz, tz],
    ).df()
    assert (df.available_time <= df.t).all(), "a run was used before it was public"
    if df.empty:
        return pd.DataFrame(columns=["day", "lead", "t"] + SOURCES + REST)
    det = df[~df.model.isin(SPREADS.values())]  # a spread's own maximum is meaningless
    wide = det.pivot_table(
        index=["day", "lead", "t"], columns="model", values="max_c"
    ).reset_index()
    rest = det.pivot_table(index=["day", "lead"], columns="model", values="rest_c").reset_index()
    rest.columns = [c if c in ("day", "lead") else f"{c}_rest" for c in rest.columns]
    wide = wide.merge(rest, on=["day", "lead"], how="left")
    for mean, spread in SPREADS.items():
        sp = df[df.model == mean][["day", "lead", "spread_at_max"]].rename(
            columns={"spread_at_max": spread}
        )
        wide = wide.merge(sp, on=["day", "lead"], how="left")
    for c in SOURCES + REST:
        if c not in wide.columns:
            wide[c] = np.nan
    wide["day"] = pd.to_datetime(wide["day"])
    return wide


def obs_features(con, station: str, tz: str, decision_hour: int) -> pd.DataFrame:
    """Per day (index): running displayed max and last observation (C) from METARs reported by the decision."""
    df = con.execute(
        f"""
        WITH dec AS (
          SELECT day, ((day::TIMESTAMP + INTERVAL {int(decision_hour)} HOUR) AT TIME ZONE ?) AT TIME ZONE 'UTC' AS t,
                 (day::TIMESTAMP AT TIME ZONE ?) AT TIME ZONE 'UTC' AS day_start
          FROM daily_truth WHERE station = ?)
        SELECT d.day, d.t, max(coalesce(o.temp_c_tenths, o.temp_c_whole)) AS run_max,
               arg_max(coalesce(o.temp_c_tenths, o.temp_c_whole), o.obs_time_utc) AS last_obs,
               max(o.obs_time_utc) AS last_obs_time, count(*) AS n_obs
        FROM dec d JOIN observations o
          ON o.station = ? AND o.obs_time_utc >= d.day_start
         AND o.obs_time_utc + INTERVAL {int(OBS_DELAY_MIN)} MINUTE <= d.t
         AND coalesce(o.temp_c_tenths, o.temp_c_whole) IS NOT NULL
        GROUP BY 1, 2
        """,
        [tz, tz, station, station],
    ).df()
    assert (df.last_obs_time + pd.Timedelta(minutes=OBS_DELAY_MIN) <= df.t).all()
    df["day"] = pd.to_datetime(df["day"])
    return df.set_index("day").sort_index()


# ------------------------------------------------------------------------------ models
def fit_censored(
    x: np.ndarray, y: np.ndarray, floor: np.ndarray, start: np.ndarray | None = None
) -> np.ndarray | None:
    """[a0, a_1..a_p, b0] of y = max(floor, Z), Z ~ N(a0 + a.x, exp(b0)^2), by censored likelihood."""
    n, p = x.shape
    if n < 20:
        return None
    cens = y <= floor + 1e-9
    lam = 1e-3

    def nll(theta):
        mu = theta[0] + x @ theta[1 : 1 + p]
        s = math.exp(theta[1 + p])
        z = (y - mu) / s
        ll = np.where(cens, norm.logcdf((floor - mu) / s), -0.5 * z**2 - math.log(s))
        return -ll.mean() + lam * float(theta[1 : 1 + p] @ theta[1 : 1 + p])

    if start is None or len(start) != 2 + p:
        start = np.r_[0.0, np.full(p, 1.0 / p), np.log(2.0)]
    bounds = [(None, None)] * (1 + p) + [(-8, 8)]
    res = minimize(nll, start, method="L-BFGS-B", bounds=bounds, options={"maxiter": 300})
    return res.x if np.isfinite(res.fun) else None


def cdf(x, mu: float, sigma: float, nu: float = np.nan, floor: float = -np.inf):
    """P(max(floor, Z) <= x), Z normal (nu NaN) or Student t with nu degrees of freedom."""
    x = np.asarray(x, float)
    z = (x - mu) / sigma
    c = norm.cdf(z) if np.isnan(nu) else t_dist.cdf(z, nu)
    return np.where(x < floor, 0.0, c)


def ppf(q: float, mu: float, sigma: float, nu: float = np.nan) -> float:
    return mu + sigma * (norm.ppf(q) if np.isnan(nu) else t_dist.ppf(q, nu))


def bucket_prob_floor(mu: float, sigma: float, floor: float, lo, hi, nu: float = np.nan) -> float:
    sigma = max(sigma, 0.3)
    a = -math.inf if lo is None or pd.isna(lo) else lo - 0.5
    b = math.inf if hi is None or pd.isna(hi) else hi + 0.5
    p = float(cdf(b, mu, sigma, nu, floor) - cdf(a, mu, sigma, nu, floor))
    return max(1e-4, min(1 - 1e-4, p))


def crps_numeric(
    mu: float,
    sigma: float,
    y: float,
    nu: float = np.nan,
    floor: float = -np.inf,
    step: float = 0.01,
) -> float:
    """CRPS by integrating the squared CDF difference on a grid (reference and floored case)."""
    lo = max(floor, min(y, mu - 8 * sigma) - 1)  # below the floor both CDFs are zero
    x = np.arange(lo, max(y, floor, mu + 8 * sigma) + 1, step)
    return float(np.sum((cdf(x, mu, sigma, nu, floor) - (x >= y)) ** 2) * step)


def crps_normal(mu, sigma, y) -> np.ndarray:
    z = (y - mu) / sigma
    return sigma * (z * (2 * norm.cdf(z) - 1) + 2 * norm.pdf(z) - 1 / math.sqrt(math.pi))


def crps_t(mu, sigma, nu, y) -> np.ndarray:
    """Closed-form CRPS of the location-scale Student t (Jordan, Krueger and Lerch 2019), nu > 1."""
    z = (y - mu) / sigma
    return sigma * (
        z * (2 * t_dist.cdf(z, nu) - 1)
        + 2 * t_dist.pdf(z, nu) * (nu + z**2) / (nu - 1)
        - 2 * np.sqrt(nu) / (nu - 1) * beta_fn(0.5, nu - 0.5) / beta_fn(0.5, nu / 2) ** 2
    )


def crps_one(mu: float, sigma: float, nu: float, floor: float, y: float) -> float:
    if np.isfinite(floor):
        return crps_numeric(mu, sigma, y, nu, floor)
    if np.isnan(nu):
        return float(crps_normal(mu, sigma, y))
    return float(crps_t(mu, sigma, nu, y))


def fit_emos(
    x: np.ndarray, spread: np.ndarray, y: np.ndarray, start: np.ndarray | None = None
) -> np.ndarray | None:
    """[a0, a_1..a_p, b0, b_1..b_q, c] minimizing the mean t CRPS:
    y ~ t_nu(a0 + a.x, exp(b0) + sum_j exp(b_j) spread_j^2), nu = 2 + exp(c).
    x: (n, p) maxima, spread: (n, q) or (n,) ensemble spreads (NaN counts as zero)."""
    n, p = x.shape
    if n < 20:
        return None
    sp2 = np.nan_to_num(np.asarray(spread, float).reshape(n, -1), nan=0.0) ** 2
    q = sp2.shape[1]
    lam = 1e-3  # small ridge on the slopes keeps collinear sources stable

    def loss(theta):
        a0, a = theta[0], theta[1 : 1 + p]
        b0, b, c = theta[1 + p], theta[2 + p : 2 + p + q], theta[2 + p + q]
        mu = a0 + x @ a
        sigma = np.sqrt(np.exp(b0) + sp2 @ np.exp(b))
        return crps_t(mu, sigma, 2 + math.exp(c), y).mean() + lam * float(a @ a)

    if start is None or len(start) != 3 + p + q:
        start = np.r_[0.0, np.full(p, 1.0 / p), np.log(2.0), np.full(q, np.log(0.5)), np.log(6.0)]
    bounds = [(None, None)] * (1 + p) + [(-8, 8)] * (1 + q) + [(-3, 6)]  # no overflow in exp
    res = minimize(loss, start, method="L-BFGS-B", bounds=bounds, options={"maxiter": 300})
    return res.x if np.isfinite(res.fun) else None


def predict_emos(theta: np.ndarray, x: np.ndarray, spread) -> tuple[float, float, float]:
    p = len(x)
    sp2 = np.nan_to_num(np.atleast_1d(np.asarray(spread, float)), nan=0.0) ** 2
    q = len(sp2)
    mu = theta[0] + float(theta[1 : 1 + p] @ x)
    sigma = math.sqrt(math.exp(theta[1 + p]) + float(sp2 @ np.exp(theta[2 + p : 2 + p + q])))
    return mu, sigma, 2 + math.exp(theta[2 + p + q])


def walk_forward(
    feats: pd.DataFrame,
    labels: pd.Series,
    lead: int,
    window: int = 90,
    obs: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Per day: mu and sigma (C) per model, using only labels and observations known at the decision."""
    f = feats[feats.lead == lead].set_index("day").sort_index()
    y = labels.sort_index()
    det = [c for c in DET if c in f.columns and f[c].notna().mean() > 0.5]  # sources with coverage
    spreads = [SPREADS[c] for c in det if c in SPREADS and SPREADS[c] in f.columns]
    out = []
    warm_emos = warm_obs = None  # yesterday's fit starts today's (its window is one day older)
    oos = {}  # day -> out-of-sample standardized EMOS error, for the scale calibration
    for day in f.index:
        cutoff = day - timedelta(days=lead - 1)
        known = y[y.index < cutoff]
        row = {"day": day, "lead": lead, "y": y.get(day, np.nan), "t": f.loc[day, "t"]}
        clim = known.tail(30)
        if len(clim) >= 10:
            row.update(clim_mu=clim.mean(), clim_sigma=max(clim.std(ddof=1), 0.5))
        xs = f.loc[day, det].astype(float)
        if xs.notna().all():
            row.update(
                raw_mu=xs.mean(),
                raw_sigma=math.sqrt(
                    max(xs.std(ddof=1) if len(det) > 1 else 0.0, 0.0) ** 2 + 2.0**2
                ),
            )
            train = (
                f[(f.index < day - timedelta(days=lead - 1))]
                .tail(window)
                .join(y.rename("yy"), how="inner")
            )
            train = train.dropna(subset=det + ["yy"])
            theta = (
                fit_emos(
                    train[det].to_numpy(float),
                    train[spreads].to_numpy(float),
                    train["yy"].to_numpy(float),
                    warm_emos,
                )
                if len(train) >= 20
                else None
            )
            if theta is not None:
                warm_emos = theta
                mu, sg, nu = predict_emos(
                    theta, xs.to_numpy(float), f.loc[day, spreads].to_numpy(float)
                )
                sg = max(sg, 0.4)
                past = [z for d, z in oos.items() if d < cutoff][-window:]
                scale = float(np.sqrt(np.mean(np.square(past)))) if len(past) >= 20 else 1.0
                if not np.isnan(row["y"]):
                    oos[day] = (
                        row["y"] - mu
                    ) / sg  # raw scale: the calibration stays out of sample
                row.update(emos_mu=mu, emos_sigma=sg * scale, emos_nu=nu, emos_scale=scale)
        if lead == 1 and obs is not None and day in obs.index:
            rest = [f"{c}_rest" for c in det]
            xo = np.r_[f.loc[day, rest].astype(float).to_numpy(), obs.loc[day, "last_obs"]]
            if np.isfinite(xo).all():
                train = (
                    f[f.index < day]
                    .tail(window)
                    .join(y.rename("yy"), how="inner")
                    .join(obs[["run_max", "last_obs"]], how="inner")
                    .dropna(subset=rest + ["yy", "run_max", "last_obs"])
                )
                theta = fit_censored(
                    train[rest + ["last_obs"]].to_numpy(float),
                    train["yy"].to_numpy(float),
                    train["run_max"].to_numpy(float),
                    warm_obs,
                )
                if theta is not None:
                    warm_obs = theta
                    row.update(
                        obs_mu=theta[0] + float(theta[1:-1] @ xo),
                        obs_sigma=max(math.exp(theta[-1]), 0.4),
                        obs_floor=float(obs.loc[day, "run_max"]),
                    )
        out.append(row)
    return pd.DataFrame(out)


# ------------------------------------------------------------------------------ scoring
def continuous_scores(wf: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for lead, g in wf.groupby("lead"):
        for m in MODELS:
            if f"{m}_mu" not in g.columns:
                continue
            ok = g[f"{m}_mu"].notna() & g.y.notna()
            if ok.sum() == 0:
                continue
            mu, sg, y = (
                g.loc[ok, f"{m}_mu"].to_numpy(),
                g.loc[ok, f"{m}_sigma"].to_numpy(),
                g.loc[ok, "y"].to_numpy(),
            )
            nu = (
                g.loc[ok, f"{m}_nu"].to_numpy()
                if f"{m}_nu" in g.columns
                else np.full(len(y), np.nan)
            )
            fl = g.loc[ok, "obs_floor"].to_numpy() if m == "obs" else np.full(len(y), -np.inf)
            med = np.maximum(fl, mu)  # median of max(floor, Z)
            lo_q = np.maximum(fl, [ppf(0.05, a, b, c) for a, b, c in zip(mu, sg, nu, strict=True)])
            hi_q = np.maximum(fl, [ppf(0.95, a, b, c) for a, b, c in zip(mu, sg, nu, strict=True)])
            crps = np.mean([crps_one(*a) for a in zip(mu, sg, nu, fl, y, strict=True)])
            if m == "obs":
                hist = None  # PIT is not defined with a point mass at the floor
            else:
                pit = np.array(
                    [cdf(yy, a, b, c) for a, b, c, yy in zip(mu, sg, nu, y, strict=True)]
                )
                hist = np.round(np.histogram(pit, bins=5, range=(0, 1))[0] / len(pit), 2).tolist()
            rows.append(
                {
                    "lead": lead,
                    "model": m,
                    "days": int(ok.sum()),
                    "crps": crps,
                    "mae": np.abs(y - med).mean(),
                    "mean_sigma": sg.mean(),
                    "median_nu": float(np.nanmedian(nu)) if np.isfinite(nu).any() else np.nan,
                    "pit_bins": hist,
                    "coverage_90": float(np.mean((y >= lo_q - 1e-9) & (y <= hi_q))),
                }
            )
    return pd.DataFrame(rows)


def market_buckets(
    con,
    station: str,
    tz: str,
    decision_hour: int,
    leads: list[int] = LEADS,
    end: date = HOLDOUT_START,
) -> pd.DataFrame:
    """Resolved buckets with an as-of price at the decision, for days before end."""
    rows = []
    for lead in leads:
        h = (24 - decision_hour) + 24 * (lead - 1)
        rows.append(
            con.execute(
                f"""
            WITH ev AS (
              SELECT m.market_id, m.date AS day, m.unit, m.bucket_lo AS lo, m.bucket_hi AS hi, m.is_winner::int AS outcome,
                     ((m.date + INTERVAL 1 DAY)::TIMESTAMP AT TIME ZONE ?) AT TIME ZONE 'UTC' - INTERVAL {h} HOUR AS t
              FROM markets m WHERE m.station = ? AND m.closed AND m.resolved_bucket IS NOT NULL AND m.date < ?)
            SELECT ev.*, {lead} AS lead, p.price AS market_p
            FROM ev ASOF JOIN px.prices_history p ON p.market_id = ev.market_id AND p.ts <= ev.t
            WHERE p.ts >= ev.t - INTERVAL 6 HOUR
            """,
                [tz, station, end],
            ).df()
        )
    df = pd.concat(rows, ignore_index=True)
    df["day"] = pd.to_datetime(df["day"])
    return df


def to_unit(mu_c: float, sigma_c: float, unit: str) -> tuple[float, float]:
    return (mu_c * 9 / 5 + 32, sigma_c * 9 / 5) if unit == "F" else (mu_c, sigma_c)


def market_scores(mkt: pd.DataFrame, wf: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = mkt.merge(wf.drop(columns=["t"]), on=["day", "lead"], how="inner")
    models = [m for m in MODELS if f"{m}_mu" in df.columns]
    for m in models:
        ps = []
        fl = df["obs_floor"] if m == "obs" else pd.Series(-np.inf, index=df.index)
        nus = df[f"{m}_nu"] if f"{m}_nu" in df.columns else pd.Series(np.nan, index=df.index)
        for mu, sg, floor, nu, unit, lo, hi in zip(
            df[f"{m}_mu"], df[f"{m}_sigma"], fl, nus, df.unit, df.lo, df.hi, strict=True
        ):
            if pd.isna(mu) or pd.isna(floor):
                ps.append(np.nan)
            else:
                mu_u, sg_u = to_unit(mu, sg, unit)
                fl_u = to_unit(floor, 0.0, unit)[0] if np.isfinite(floor) else -math.inf
                ps.append(bucket_prob_floor(mu_u, sg_u, fl_u, lo, hi, nu))
        df[f"p_{m}"] = ps
    rows = []
    for lead, g in df.groupby("lead"):
        for m in models:
            p = g[f"p_{m}"]
            ok = p.notna()
            if ok.sum() == 0:
                continue
            o = g.outcome[ok]
            pm = g.market_p[ok].clip(1e-4, 1 - 1e-4)
            pp = p[ok]
            d = g[ok & ((p - g.market_p).abs() >= 0.10)]
            diff = (d.market_p - d.outcome) ** 2 - (d[f"p_{m}"] - d.outcome) ** 2
            ci = bootstrap_ci(diff, d.day) if len(d) else (np.nan, np.nan)
            rows.append(
                {
                    "lead": lead,
                    "model": m,
                    "buckets": int(ok.sum()),
                    "days": g[ok].day.nunique(),
                    "brier_market": ((pm - o) ** 2).mean(),
                    "brier_model": ((pp - o) ** 2).mean(),
                    "logloss_market": -(o * np.log(pm) + (1 - o) * np.log(1 - pm)).mean(),
                    "logloss_model": -(o * np.log(pp) + (1 - o) * np.log(1 - pp)).mean(),
                    "n_disagree": len(d),
                    "market_minus_model_on_disagree": diff.mean() if len(d) else np.nan,
                    "ci_low": ci[0],
                    "ci_high": ci[1],
                }
            )
    return df, pd.DataFrame(rows)


def md(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False, floatfmt=".4f") if len(df) else "No data."


def run_station(
    con, station: str, decision_hour: int, leads: list[int] = LEADS, holdout: bool = False
) -> dict:
    """holdout=False: everything before HOLDOUT_START. holdout=True: the one-shot test, scoring only
    days from HOLDOUT_START on; the walk-forward still trains on the days before each decision."""
    tz = STATION_TZ[station]
    end = date(2100, 1, 1) if holdout else HOLDOUT_START
    feats = features(con, station, tz, decision_hour)
    labels = con.execute(
        "SELECT day, max_c FROM daily_truth WHERE station = ? AND day < ?", [station, end]
    ).df()
    labels = labels.assign(day=pd.to_datetime(labels.day)).set_index("day")["max_c"]
    feats = feats[feats.day < pd.Timestamp(end)]
    obs = obs_features(con, station, tz, decision_hour)
    obs = obs[obs.index < pd.Timestamp(end)]
    wf = pd.concat([walk_forward(feats, labels, k, obs=obs) for k in leads], ignore_index=True)
    mkt = market_buckets(con, station, tz, decision_hour, leads, end)
    if holdout:
        wf = wf[wf.day >= pd.Timestamp(HOLDOUT_START)]
        mkt = mkt[mkt.day >= pd.Timestamp(HOLDOUT_START)]
    cont = continuous_scores(wf)
    scored, ms = market_scores(mkt, wf)
    cov = pd.DataFrame(
        [
            {
                "station": station,
                "decision_hour_local": decision_hour,
                "period": "holdout from 2026-08-01" if holdout else "before 2026-08-01",
                "feature_days": feats.day.nunique(),
                "label_days": len(labels),
                "sources_with_coverage": [c for c in SOURCES if feats[c].notna().mean() > 0.5],
                "obs_days": len(obs),
                "share_max_before_decision": float((wf.obs_floor >= wf.y - 1e-9).mean())
                if "obs_floor" in wf
                else np.nan,
                "market_buckets": len(mkt),
            }
        ]
    )
    return {"coverage": cov, "continuous": cont, "market": ms, "wf": wf, "scored": scored}


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--db", default=str(config.RESEARCH_DB))
    ap.add_argument("--prices", default=str(config.PRICES_DB))
    ap.add_argument("--forecasts", default=str(config.FORECASTS_DB))
    ap.add_argument("--stations", nargs="+", default=["KLGA"])
    ap.add_argument("--decision-hours", type=int, nargs="+", default=[12])
    ap.add_argument("--leads", type=int, nargs="+", default=LEADS)
    ap.add_argument("--holdout", action="store_true", help="one-shot scoring on the holdout")
    ap.add_argument("--report", default=str(config.REPORTS / "phase5_emos.md"))
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    con = duckdb.connect(a.db, read_only=True)
    con.execute(f"ATTACH '{a.prices}' AS px (READ_ONLY)")
    con.execute(f"ATTACH '{a.forecasts}' AS fc (READ_ONLY)")
    parts = ["# Phase 5: EMOS by CRPS vs the market", "", __doc__.split("Usage:")[0].strip(), ""]
    for st, hour in ((st, h) for st in a.stations for h in a.decision_hours):
        r = run_station(con, st, hour, a.leads, a.holdout)
        parts += [
            f"## {st}, decision {hour:02d}:00 local",
            "",
            md(r["coverage"]),
            "",
            "### Continuous scores (C), all days",
            "",
            md(r["continuous"]),
            "",
            "### Market comparison at the decision time (disagreement = |p_model - p_market| >= 0.10)",
            "",
            md(r["market"]),
            "",
        ]
        print(st, hour)
        print(r["coverage"].to_string(index=False))
        print(r["continuous"].to_string(index=False))
        print(r["market"].to_string(index=False))
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    Path(a.report).write_text("\n".join(parts))
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
