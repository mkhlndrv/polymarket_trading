"""Does the market lag the model runs? An event study around each run's publication time.

For every run covering a market day, the run's change in its daily maximum against the previous run
is paired with the change of the market-implied expected high from an hour before publication to
minutes after. The slope of one on the other, by minutes after publication, is the pass-through; a
window before publication is the control.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from weather_edge import config
from weather_edge.market_checks import STATION_TZ
from weather_edge.model import HOLDOUT_START, md

MODELS = ["ecmwf", "gfs"]
DELTAS = [-30, 0, 5, 15, 30, 60, 120, 240]
BASELINE = -60


def run_moves(con, station: str, tz: str) -> pd.DataFrame:
    return con.execute(
        """
        WITH ev AS (
          SELECT event_id, date AS day, any_value(unit) AS unit,
                 ((date::TIMESTAMP AT TIME ZONE ?) AT TIME ZONE 'UTC') AS day_start
          FROM markets WHERE station = ? AND closed AND resolved_bucket IS NOT NULL AND date < ?
          GROUP BY 1, 2),
        steps AS (
          SELECT e.event_id, e.day, e.unit, e.day_start, f.model, f.init_time, f.available_time, f.temp_c
          FROM ev e JOIN fc.forecasts f
            ON f.station = ? AND f.model IN ('ecmwf', 'gfs')
           AND f.valid_time >= e.day_start AND f.valid_time < e.day_start + INTERVAL 1 DAY),
        runs AS (
          SELECT event_id, day, unit, day_start, model, init_time,
                 max(available_time) AS pub, max(temp_c) AS max_c
          FROM steps GROUP BY 1, 2, 3, 4, 5, 6 HAVING count(*) >= 7),
        seq AS (
          SELECT *, lag(max_c) OVER (PARTITION BY event_id, model ORDER BY pub) AS prev_c,
                 lag(pub) OVER (PARTITION BY event_id, model ORDER BY pub) AS prev_pub
          FROM runs)
        SELECT event_id, day, unit, model, init_time, pub, max_c, prev_c, prev_pub,
               epoch(day_start - pub) / 3600.0 AS hours_before_day
        FROM seq
        WHERE prev_c IS NOT NULL AND pub >= day_start - INTERVAL 48 HOUR
          AND pub <= day_start + INTERVAL 20 HOUR AND pub - prev_pub >= INTERVAL 3 HOUR
        """,
        [tz, station, HOLDOUT_START, station],
    ).df()


def implied_highs(con, moves: pd.DataFrame) -> pd.DataFrame:
    """Market-implied expected high per (event, run, delta) from as-of prices of all buckets."""
    probes = moves[["event_id", "model", "init_time", "pub"]].merge(
        pd.DataFrame({"delta": DELTAS + [BASELINE]}), how="cross"
    )
    probes["t"] = probes.pub + pd.to_timedelta(probes.delta, unit="m")
    con.register("probes", probes)
    df = con.execute(
        """
        WITH b AS (
          SELECT p.event_id, p.model, p.init_time, p.delta, p.t, m.market_id,
                 coalesce((m.bucket_lo + m.bucket_hi) / 2.0, m.bucket_hi - 1, m.bucket_lo + 1) AS centre
          FROM probes p JOIN markets m ON m.event_id = p.event_id),
        q AS (
          SELECT b.*, h.price
          FROM b ASOF JOIN px.prices_history h ON h.market_id = b.market_id AND h.ts <= b.t
          WHERE h.ts >= b.t - INTERVAL 6 HOUR)
        SELECT event_id, model, init_time, delta, count(*) AS n_buckets, sum(price) AS sum_p,
               sum(price * centre) / sum(price) AS implied
        FROM q GROUP BY 1, 2, 3, 4 HAVING count(*) >= 5 AND sum(price) BETWEEN 0.5 AND 2.0
        """
    ).df()
    con.unregister("probes")
    return df


def horizon(h: float) -> str:
    return "two days before" if h >= 24 else ("day before" if h >= 0 else "same day")


def analyse(moves: pd.DataFrame, implied: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    wide = implied.pivot_table(
        index=["event_id", "model", "init_time"], columns="delta", values="implied"
    )
    m = moves.set_index(["event_id", "model", "init_time"]).join(wide, how="inner")
    m = m[m[BASELINE].notna()]
    m["model_move"] = (m.max_c - m.prev_c) * np.where(m.unit == "F", 1.8, 1.0)
    m["horizon"] = m.hours_before_day.map(horizon)
    rows = []
    for (model, hz), g in m.groupby(["model", "horizon"]):
        for d in DELTAS:
            ok = g[d].notna()
            x, y = g.model_move[ok].to_numpy(), (g[d] - g[BASELINE])[ok].to_numpy()
            if len(x) < 30:
                continue
            beta = np.polyfit(x, y, 1)[0] if x.std() > 0 else np.nan
            big = np.abs(x) >= 1
            rows.append(
                {
                    "model": model,
                    "horizon": hz,
                    "minutes_after": d,
                    "runs": len(x),
                    "slope": beta,
                    "corr": np.corrcoef(x, y)[0, 1] if x.std() > 0 and y.std() > 0 else np.nan,
                    "mean_abs_market_move_big": float(np.abs(y[big]).mean())
                    if big.any()
                    else np.nan,
                    "mean_abs_market_move_small": float(np.abs(y[~big]).mean())
                    if (~big).any()
                    else np.nan,
                    "share_same_sign_big": float((np.sign(y[big]) == np.sign(x[big])).mean())
                    if big.any()
                    else np.nan,
                }
            )
    return m.reset_index(), pd.DataFrame(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--db", default=str(config.RESEARCH_DB))
    ap.add_argument("--prices", default=str(config.PRICES_DB))
    ap.add_argument("--forecasts", default=str(config.FORECASTS_DB))
    ap.add_argument("--stations", nargs="+", default=["EGLC", "KLGA"])
    ap.add_argument("--report", default=str(config.REPORTS / "phase8_timing.md"))
    a = ap.parse_args(argv)
    con = duckdb.connect(a.db, read_only=True)
    con.execute("SET enable_progress_bar=false")
    con.execute(f"ATTACH '{a.prices}' AS px (READ_ONLY)")
    con.execute(f"ATTACH '{a.forecasts}' AS fc (READ_ONLY)")
    parts = [
        "# Phase 8: price reaction to model releases",
        "",
        __doc__.split("Usage:")[0].strip(),
        "",
    ]
    for st in a.stations:
        moves = run_moves(con, st, STATION_TZ[st])
        implied = implied_highs(con, moves)
        m, stats = analyse(moves, implied)
        big = m[np.abs(m.model_move) >= 1]
        head = pd.DataFrame(
            [
                {
                    "station": st,
                    "runs_with_prices": len(m),
                    "days": m.day.nunique(),
                    "runs_model_moved_1_unit_or_more": len(big),
                    "median_abs_model_move": float(np.abs(m.model_move).median()),
                    "unit": m.unit.mode().iloc[0] if len(m) else "",
                }
            ]
        )
        parts += [f"## {st}", "", md(head), "", md(stats), ""]
        print(st)
        print(head.to_string(index=False))
        print(stats.to_string(index=False))
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    Path(a.report).write_text("\n".join(parts))
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
