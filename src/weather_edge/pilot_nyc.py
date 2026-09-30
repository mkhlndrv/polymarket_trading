"""Phase 4: the full chain for one city (NYC, KLGA): forecasts, labels, baseline models, market
comparison and a maker-only backtest skeleton. Built to flush out pipeline bugs before generalizing.

Forecasts: Open-Meteo Previous Runs API, hourly 2 m temperature at fixed lead offsets. Per its
documentation, temperature_2m_previous_dayK is the value predicted K x 24 hours before the valid
time. Decision time for lead K is 12:00 local on day D - (K - 1); every hour of day D used at that
decision was predicted at least 11 hours earlier (plus at most 8 hours of publication delay, which is
asserted). Fresher runs exist by then, so the model is understated, never leaked.

Labels: the rebuilt displayed high (T-group tenths transform, table truth) and the resolved bucket.
Models (walk-forward, trailing windows only): climatology (last 30 days of labels), raw multi-model
(mean and spread of the models' daily maxima), EMOS-lite (linear fit of the label on the model mean
over the last 60 days, residual spread). Bucket probabilities integrate a normal over half-integers.
Holdout: days from 2026-08-01 are excluded from everything here (PLAN.md section 8).
Backtest: maker-only, 5 shares (minimum order), bid 1c under the market price when the model's
probability exceeds the market's by the edge, fill only if the later price touched the bid, and a
50% fill haircut when the bucket won (fills are likelier when the model is wrong). No fees for makers,
rebates ignored.

Usage: python -m weather_edge.pilot_nyc [--skip-fetch]
"""

from __future__ import annotations

import argparse
import logging
import math
import sys
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb
import numpy as np
import pandas as pd
import requests

from weather_edge.market_checks import STATION_TZ
from weather_edge.observations import c_to_f

PREV_URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
STATION, LAT, LON = "KLGA", 40.77945, -73.88027
MODELS = ["gfs_seamless", "ecmwf_ifs025", "icon_seamless", "gem_seamless"]
LEADS = [1, 2, 3]
PUBLICATION_DELAY_H = 8  # upper bound for a global run to appear on Open-Meteo
HOLDOUT_START = date(2026, 8, 1)
EDGE, TICK, SHARES = 0.10, 0.01, 5
log = logging.getLogger("phase4")


# ------------------------------------------------------------------------------ forecasts
def fetch_chunk(session, start: date, end: date, models=MODELS, leads=LEADS) -> pd.DataFrame:
    hourly = ",".join(f"temperature_2m_previous_day{k}" for k in leads)
    params = {
        "latitude": LAT,
        "longitude": LON,
        "hourly": hourly,
        "models": ",".join(models),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "timezone": "UTC",
    }
    for attempt in range(5):
        r = session.get(PREV_URL, params=params, timeout=180)
        if r.status_code == 200:
            return parse_previous_runs(r.json(), fetched_at=datetime.now(UTC).replace(tzinfo=None))
        log.warning("previous-runs HTTP %s: %s", r.status_code, r.text[:120])
        if r.status_code == 429 and "Daily" in r.text:
            raise RuntimeError("Open-Meteo daily quota exhausted; rerun after 00:00 UTC")
        time.sleep(10 * (attempt + 1))
    raise RuntimeError("previous-runs fetch failed")


def parse_previous_runs(payload: dict, fetched_at: datetime) -> pd.DataFrame:
    h = payload["hourly"]
    times = pd.to_datetime(h["time"])
    rows = []
    for key, vals in h.items():
        if not key.startswith("temperature_2m_previous_day"):
            continue
        rest = key[len("temperature_2m_previous_day") :]
        lead, model = (
            (int(rest.split("_")[0]), rest.split("_", 1)[1])
            if "_" in rest
            else (int(rest), "default")
        )
        for t, v in zip(times, vals, strict=True):
            if v is not None:
                rows.append(
                    {
                        "station": STATION,
                        "model": model,
                        "lead_days": lead,
                        "valid_time_utc": t,
                        "temp_c": float(v),
                        "fetched_at": fetched_at,
                    }
                )
    return pd.DataFrame(rows)


def fetch_all(con, session, start: date, end: date, chunk_days: int = 92) -> int:
    con.execute(
        "CREATE TABLE IF NOT EXISTS forecasts_prev (station VARCHAR, model VARCHAR, lead_days INTEGER, "
        "valid_time_utc TIMESTAMP, temp_c DOUBLE, fetched_at TIMESTAMP)"
    )
    have = con.execute(
        "SELECT count(*), max(valid_time_utc) FROM forecasts_prev WHERE station = ?", [STATION]
    ).fetchone()
    cur = start if have[0] == 0 else (have[1].date() + timedelta(days=1))
    n = 0
    while cur <= end:
        stop = min(cur + timedelta(days=chunk_days - 1), end)
        df = fetch_chunk(session, cur, stop)
        con.register("fc_in", df)
        con.execute("INSERT INTO forecasts_prev SELECT * FROM fc_in")
        con.unregister("fc_in")
        n += len(df)
        log.info("forecasts %s..%s: %d rows", cur, stop, len(df))
        cur = stop + timedelta(days=1)
        time.sleep(2)
    return n


# ------------------------------------------------------------------------------ features
def decision_time_utc(day: date, lead: int, tz: str) -> datetime:
    """12:00 local on day - (lead - 1), as naive UTC."""
    local = datetime.combine(day - timedelta(days=lead - 1), datetime.min.time()).replace(
        hour=12, tzinfo=ZoneInfo(tz)
    )
    return local.astimezone(UTC).replace(tzinfo=None)


def assert_point_in_time(valid_time_utc: datetime, lead: int, decision_utc: datetime) -> None:
    """A previous_dayK value was predicted K x 24h before valid time; it must be public by decision."""
    latest_public = (
        valid_time_utc - timedelta(hours=24 * lead) + timedelta(hours=PUBLICATION_DELAY_H)
    )
    if latest_public > decision_utc:
        raise AssertionError(
            f"forecast for {valid_time_utc} lead {lead} not public at {decision_utc}"
        )


def daily_model_max(con, tz: str) -> pd.DataFrame:
    """Per day, lead and model: the max over the local day's hours of the forecast, in display units (F)."""
    df = con.execute(
        """
        SELECT model, lead_days, ((valid_time_utc AT TIME ZONE 'UTC') AT TIME ZONE ?)::DATE AS day,
               max(temp_c) AS max_c, min(valid_time_utc) AS first_valid, max(valid_time_utc) AS last_valid, count(*) AS n
        FROM forecasts_prev WHERE station = ? GROUP BY 1, 2, 3 HAVING count(*) >= 20
        """,
        [tz, STATION],
    ).df()
    df["max_f"] = df["max_c"].map(c_to_f)
    for r in df.itertuples():
        assert_point_in_time(
            r.last_valid.to_pydatetime(),
            int(r.lead_days),
            decision_time_utc(r.day, int(r.lead_days), tz),
        )
    wide = df.pivot_table(index=["day", "lead_days"], columns="model", values="max_f").reset_index()
    models = [m for m in MODELS if m in wide.columns]
    wide["model_mean"] = wide[models].mean(axis=1)
    wide["model_spread"] = wide[models].std(axis=1).fillna(0.0)
    wide["n_models"] = wide[models].notna().sum(axis=1)
    return wide


def daily_model_max_open(con, tz: str, station: str = STATION) -> pd.DataFrame:
    """Same features from the open-archive table (data/forecasts.duckdb attached as fc).

    For day D and lead K the decision time is 12:00 local on D - (K - 1). Per model, the run used is
    the latest one whose available_time (object publication time) is at or before the decision and
    whose steps cover the local day; availability is asserted, not assumed.
    """
    df = con.execute(
        """
        WITH days AS (
          SELECT DISTINCT date AS day FROM markets WHERE station = ? AND closed AND resolved_bucket IS NOT NULL),
        dec AS (
          SELECT day, k AS lead_days,
                 ((day - (k - 1) * INTERVAL 1 DAY + INTERVAL 12 HOUR)::TIMESTAMP AT TIME ZONE ?) AT TIME ZONE 'UTC' AS t
          FROM days CROSS JOIN (SELECT unnest([1, 2, 3]) AS k)),
        runs AS (
          SELECT d.day, d.lead_days, d.t, f.model, f.init_time, max(f.available_time) AS available_time,
                 max(f.temp_c) AS max_c, count(*) AS n
          FROM dec d JOIN fc.forecasts f
            ON f.station = ?
           AND ((f.valid_time AT TIME ZONE 'UTC') AT TIME ZONE ?) >= d.day::TIMESTAMP
           AND ((f.valid_time AT TIME ZONE 'UTC') AT TIME ZONE ?) < (d.day + INTERVAL 1 DAY)::TIMESTAMP
          GROUP BY 1, 2, 3, 4, 5
          HAVING max(f.available_time) <= d.t)  -- every step of the local day must be public by then
        SELECT day, lead_days, t, model, init_time, available_time, max_c, n
        FROM runs QUALIFY row_number() OVER (PARTITION BY day, lead_days, model ORDER BY init_time DESC) = 1
        """,
        [station, tz, station, tz, tz],
    ).df()
    df = df[df.n >= 7]  # at least seven 3-hourly steps inside the local day
    assert (df.available_time <= df.t).all(), "a forecast run was used before it was public"
    df["max_f"] = df["max_c"].map(c_to_f)
    wide = df.pivot_table(index=["day", "lead_days"], columns="model", values="max_f").reset_index()
    models = [m for m in ("ecmwf", "gfs") if m in wide.columns]
    wide["model_mean"] = wide[models].mean(axis=1)
    wide["model_spread"] = wide[models].std(axis=1).fillna(0.0)
    wide["n_models"] = wide[models].notna().sum(axis=1)
    wide["day"] = pd.to_datetime(wide["day"])  # Timestamps, like the labels and market frames
    return wide


# ------------------------------------------------------------------------------ models
def normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def bucket_prob(mu: float, sigma: float, lo, hi) -> float:
    """P(lo <= displayed integer <= hi) under N(mu, sigma) with half-integer edges."""
    sigma = max(sigma, 0.3)
    a = -math.inf if lo is None or pd.isna(lo) else (lo - 0.5 - mu) / sigma
    b = math.inf if hi is None or pd.isna(hi) else (hi + 0.5 - mu) / sigma
    return max(1e-4, min(1 - 1e-4, normal_cdf(b) - normal_cdf(a)))


def walk_forward(feats: pd.DataFrame, labels: pd.Series, lead: int) -> pd.DataFrame:
    """Per day: mu and sigma for climatology, raw multi-model and EMOS-lite, trailing windows only."""
    f = feats[feats.lead_days == lead].set_index("day").sort_index()
    y = labels.sort_index()
    out = []
    for day in f.index:
        past = y[(y.index < day - timedelta(days=lead - 1))]  # labels known at the decision time
        clim = past.tail(30)
        row = {"day": day, "lead": lead, "y": y.get(day)}
        if len(clim) >= 10:
            row.update(clim_mu=clim.mean(), clim_sigma=clim.std(ddof=1))
        mm = f.loc[day, "model_mean"]
        if pd.notna(mm):
            row.update(raw_mu=mm, raw_sigma=math.sqrt(f.loc[day, "model_spread"] ** 2 + 2.0**2))
            train = f[(f.index < day - timedelta(days=lead - 1))].tail(60)
            train = train.join(y.rename("y"), how="inner").dropna(subset=["model_mean", "y"])
            if len(train) >= 20:
                b, a = np.polyfit(train["model_mean"], train["y"], 1)
                resid = train["y"] - (a + b * train["model_mean"])
                row.update(emos_mu=a + b * mm, emos_sigma=max(resid.std(ddof=2), 0.5))
        out.append(row)
    return pd.DataFrame(out)


# ------------------------------------------------------------------------------ evaluation
def market_at_decision(con, tz: str) -> pd.DataFrame:
    """Market price of every KLGA bucket at each lead's decision time, as-of, never after."""
    rows = []
    for lead in LEADS:
        h = 12 + 24 * (lead - 1)
        rows.append(
            con.execute(
                f"""
            WITH ev AS (
              SELECT m.market_id, m.event_id, m.date AS day, m.bucket_lo AS lo, m.bucket_hi AS hi, m.is_winner::int AS outcome,
                     ((m.date + INTERVAL 1 DAY)::TIMESTAMP AT TIME ZONE ?) AT TIME ZONE 'UTC' - INTERVAL {h} HOUR AS t
              FROM markets m WHERE m.station = ? AND m.closed AND m.resolved_bucket IS NOT NULL AND m.date < ?)
            SELECT ev.*, {lead} AS lead, p.price AS market_p
            FROM ev ASOF JOIN px.prices_history p ON p.market_id = ev.market_id AND p.ts <= ev.t
            WHERE p.ts >= ev.t - INTERVAL 6 HOUR
            """,
                [tz, STATION, HOLDOUT_START],
            ).df()
        )
    return pd.concat(rows, ignore_index=True)


def score(mkt: pd.DataFrame, wf: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = mkt.merge(wf, on=["day", "lead"], how="inner")
    for name in ("clim", "raw", "emos"):
        df[f"p_{name}"] = [
            bucket_prob(mu, sg, lo, hi) if pd.notna(mu) else np.nan
            for mu, sg, lo, hi in zip(
                df[f"{name}_mu"], df[f"{name}_sigma"], df.lo, df.hi, strict=True
            )
        ]
    rows = []
    for lead, g in df.groupby("lead"):
        for name in ("clim", "raw", "emos"):
            p = g[f"p_{name}"]
            ok = p.notna()
            if ok.sum() == 0:
                continue
            bm = ((g.market_p - g.outcome) ** 2)[ok]
            bmod = ((p - g.outcome) ** 2)[ok]
            d = g[ok & ((p - g.market_p).abs() >= 0.10)]
            diff = (d.market_p - d.outcome) ** 2 - (d[f"p_{name}"] - d.outcome) ** 2
            ci = bootstrap_ci(diff, d.day) if len(d) else (np.nan, np.nan)
            rows.append(
                {
                    "lead": lead,
                    "model": name,
                    "n_buckets": int(ok.sum()),
                    "days": g[ok].day.nunique(),
                    "brier_market": bm.mean(),
                    "brier_model": bmod.mean(),
                    "n_disagree": len(d),
                    "market_minus_model_brier_on_disagree": diff.mean() if len(d) else np.nan,
                    "ci_low": ci[0],
                    "ci_high": ci[1],
                }
            )
    return df, pd.DataFrame(rows)


def bootstrap_ci(
    diff: pd.Series, days: pd.Series, n: int = 1000, seed: int = 0
) -> tuple[float, float]:
    """95% interval of the mean, resampling event days (buckets of one day are dependent)."""
    by_day = (
        pd.DataFrame({"d": diff.values, "day": days.values})
        .groupby("day")["d"]
        .agg(["sum", "count"])
    )
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(by_day), size=(n, len(by_day)))
    sums = by_day["sum"].values[idx].sum(axis=1)
    counts = by_day["count"].values[idx].sum(axis=1)
    means = sums / counts
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


# ------------------------------------------------------------------------------- backtest
def backtest(con, df: pd.DataFrame, model: str, tz: str) -> pd.DataFrame:
    """Maker-only bids on buckets the model likes; conservative touch fills; PnL per order."""
    p = df[f"p_{model}"]
    cand = df[(p - df.market_p >= EDGE) & df.market_p.between(0.02, 0.95)].copy()
    if cand.empty:
        return pd.DataFrame(columns=["day", "lead", "market_id", "bid", "outcome", "filled", "pnl"])
    cand["bid"] = (cand.market_p - TICK).round(2)
    con.register("orders", cand[["market_id", "t", "bid"]])
    touched = con.execute(
        """
        SELECT o.market_id, o.bid, bool_or(p.price <= o.bid) AS touched
        FROM orders o JOIN px.prices_history p ON p.market_id = o.market_id AND p.ts > o.t
        GROUP BY 1, 2
        """
    ).df()
    con.unregister("orders")
    cand = cand.merge(touched, on=["market_id", "bid"], how="left")
    cand["touched"] = cand.touched.fillna(False)
    cand["filled"] = cand.touched * np.where(
        cand.outcome == 1, 0.5, 1.0
    )  # haircut when the model was right
    cand["pnl"] = cand.filled * (cand.outcome - cand.bid) * SHARES
    return cand[
        [
            "day",
            "lead",
            "market_id",
            "market_p",
            f"p_{model}",
            "bid",
            "outcome",
            "touched",
            "filled",
            "pnl",
        ]
    ]


def summarize_backtest(bt: pd.DataFrame) -> dict:
    if bt.empty:
        return {"orders": 0}
    return {
        "orders": len(bt),
        "touched": int(bt.touched.sum()),
        "filled_shares": float(bt.filled.sum() * SHARES),
        "pnl_usd": float(bt.pnl.sum()),
        "pnl_per_filled_share": float(bt.pnl.sum() / max(bt.filled.sum() * SHARES, 1e-9)),
        "days": int(bt.day.nunique()),
        "win_rate_of_fills": float((bt[bt.filled > 0].outcome == 1).mean())
        if (bt.filled > 0).any()
        else np.nan,
    }


# ----------------------------------------------------------------------------------- main
def md(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False, floatfmt=".4f") if len(df) else "No data."


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--db", default="data/research.duckdb")
    ap.add_argument("--prices", default="data/prices.duckdb")
    ap.add_argument("--start", default="2025-01-01")
    ap.add_argument("--skip-fetch", action="store_true")
    ap.add_argument(
        "--source",
        choices=["open", "prev"],
        default="open",
        help="open: ECMWF and GFS archives in --forecasts-db; prev: Open-Meteo previous runs",
    )
    ap.add_argument("--forecasts-db", default="data/forecasts.duckdb")
    ap.add_argument("--report", default="reports/phase4_nyc.md")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    tz = STATION_TZ[STATION]
    con = duckdb.connect(a.db)
    con.execute(f"ATTACH '{a.prices}' AS px (READ_ONLY)")
    if a.source == "open":
        con.execute(f"ATTACH '{a.forecasts_db}' AS fc (READ_ONLY)")
        feats = daily_model_max_open(con, tz)
    else:
        if not a.skip_fetch:
            session = requests.Session()
            n = fetch_all(
                con, session, date.fromisoformat(a.start), HOLDOUT_START - timedelta(days=1)
            )
            log.info("%d forecast rows added", n)
        feats = daily_model_max(con, tz)
    labels = (
        con.execute(
            "SELECT date AS day, tenths AS y FROM truth WHERE station = ? AND n_obs > 0 AND date < ?",
            [STATION, HOLDOUT_START],
        )
        .df()
        .set_index("day")["y"]
    )
    wf = pd.concat([walk_forward(feats, labels, k) for k in LEADS], ignore_index=True)
    mkt = market_at_decision(con, tz)
    scored, table = score(mkt, wf)
    bt_rows = []
    for lead in LEADS:
        for model in ("raw", "emos"):
            bt = backtest(
                con, scored[(scored.lead == lead) & scored[f"p_{model}"].notna()], model, tz
            )
            bt_rows.append({"lead": lead, "model": model, **summarize_backtest(bt)})
    bt_table = pd.DataFrame(bt_rows)
    cov = pd.DataFrame(
        [
            {
                "forecast_days": feats.day.nunique(),
                "label_days": len(labels),
                "market_buckets": len(mkt),
                "first_day": feats.day.min(),
                "last_day": feats.day.max(),
                "holdout_start": HOLDOUT_START,
            }
        ]
    )
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    Path(a.report).write_text(
        "\n".join(
            [
                "# Phase 4: NYC end to end",
                "",
                f"Forecast source: {a.source}",
                "",
                __doc__.split("Usage:")[0].strip(),
                "",
                "## Coverage",
                "",
                md(cov),
                "",
                "## Model vs market: Brier on all buckets and on disagreement buckets (|p_model - p_market| >= 0.10)",
                "",
                "market_minus_model_brier_on_disagree > 0 means the model beats the market where they disagree; "
                "ci is a 95% bootstrap over event days.",
                "",
                md(table),
                "",
                "## Maker-only backtest skeleton (5-share bids, 1c under market, touch fills, 50% haircut on wins, no fees)",
                "",
                md(bt_table),
                "",
            ]
        )
    )
    con.close()
    print(cov.to_string(index=False))
    print(table.to_string(index=False))
    print(bt_table.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
