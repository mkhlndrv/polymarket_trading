"""Market-side checks before any modelling: calibration by horizon, taker losses, price sums.

The price at horizon h is the last CLOB point at or before local midnight of the event day minus
h hours, because local midnight is when the observation window closes. Profit is gross of fees; the
dataset carries no fee column.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import duckdb
import pandas as pd

from weather_edge import config

HORIZONS = [30, 24, 18, 12, 6, 3, 1]  # hours before local midnight that ends the event day
BANDS = [0, 0.02, 0.05, 0.10, 0.20, 0.35, 0.50, 0.65, 0.80, 0.90, 0.95, 0.98, 1.0001]
STATION_TZ = {
    "EHAM": "Europe/Amsterdam",
    "LTAC": "Europe/Istanbul",
    "KATL": "America/New_York",
    "KAUS": "America/Chicago",
    "ZBAA": "Asia/Shanghai",
    "SAEZ": "America/Argentina/Buenos_Aires",
    "RKPK": "Asia/Seoul",
    "FACT": "Africa/Johannesburg",
    "ZUUU": "Asia/Shanghai",
    "KORD": "America/Chicago",
    "ZUCK": "Asia/Shanghai",
    "KDCA": "America/New_York",
    "KDAL": "America/Chicago",
    "KBKF": "America/Denver",
    "KDEN": "America/Denver",
    "OMDB": "Asia/Dubai",
    "ZGGG": "Asia/Shanghai",
    "EFHK": "Europe/Helsinki",
    "HKO": "Asia/Hong_Kong",
    "VHHH": "Asia/Hong_Kong",
    "KHOU": "America/Chicago",
    "LTFM": "Europe/Istanbul",
    "WIHH": "Asia/Jakarta",
    "OEJN": "Asia/Riyadh",
    "ZSJN": "Asia/Shanghai",
    "OPKC": "Asia/Karachi",
    "WMKK": "Asia/Kuala_Lumpur",
    "DNMM": "Africa/Lagos",
    "EGLC": "Europe/London",
    "KLAX": "America/Los_Angeles",
    "VILK": "Asia/Kolkata",
    "LEMD": "Europe/Madrid",
    "RPLL": "Asia/Manila",
    "MMMX": "America/Mexico_City",
    "KMIA": "America/New_York",
    "LIMC": "Europe/Rome",
    "UUWW": "Europe/Moscow",
    "EDDM": "Europe/Berlin",
    "KLGA": "America/New_York",
    "MPMG": "America/Panama",
    "LFPB": "Europe/Paris",
    "LFPG": "Europe/Paris",
    "KPHX": "America/Phoenix",
    "ZSQD": "Asia/Shanghai",
    "KSFO": "America/Los_Angeles",
    "SBGR": "America/Sao_Paulo",
    "KSEA": "America/Los_Angeles",
    "RKSI": "Asia/Seoul",
    "ZSPD": "Asia/Shanghai",
    "ZGSZ": "Asia/Shanghai",
    "WSSS": "Asia/Singapore",
    "RCSS": "Asia/Taipei",
    "RCTP": "Asia/Taipei",
    "CWA46692": "Asia/Taipei",
    "LLBG": "Asia/Jerusalem",
    "RJTT": "Asia/Tokyo",
    "CYYZ": "America/Toronto",
    "EPWA": "Europe/Warsaw",
    "NZWN": "Pacific/Auckland",
    "ZHHH": "Asia/Shanghai",
    "ZHCC": "Asia/Shanghai",
}
log = logging.getLogger("phase1")


def connect(research: str, prices: str) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(research, read_only=True)
    con.execute(f"ATTACH '{prices}' AS px (READ_ONLY)")
    return con


def build_views(con: duckdb.DuckDBPyConnection) -> None:
    """Resolved bucket markets with timezone, era and bucket position; prices at each horizon."""
    con.register("tz_map", pd.DataFrame(list(STATION_TZ.items()), columns=["station", "tz"]))
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE res AS
        SELECT m.market_id, m.event_id, m.city, m.station, m.date, m.unit, m.resolution_source AS era,
               m.is_winner::int AS outcome, m.volume_usd AS shares,
               CASE WHEN m.bucket_lo IS NULL THEN 'low_edge' WHEN m.bucket_hi IS NULL THEN 'high_edge'
                    ELSE 'middle' END AS bucket_pos,
               ((m.date + INTERVAL 1 DAY)::TIMESTAMP AT TIME ZONE t.tz) AT TIME ZONE 'UTC' AS day_end_utc
        FROM markets m JOIN tz_map t USING (station)
        WHERE m.closed AND m.resolved_bucket IS NOT NULL AND m.date IS NOT NULL
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE horizon_px AS
        WITH h AS (SELECT r.*, hz.h, r.day_end_utc - INTERVAL (hz.h) HOUR AS t
                   FROM res r CROSS JOIN (SELECT unnest({HORIZONS}) AS h) hz)
        SELECT h.*, p.price, p.ts AS price_ts
        FROM h ASOF JOIN px.prices_history p ON p.market_id = h.market_id AND p.ts <= h.t
        WHERE p.price IS NOT NULL AND p.ts >= h.t - INTERVAL 6 HOUR
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE binned AS
        SELECT *, list_position({BANDS[:-1]}, (SELECT max(b) FROM unnest({BANDS[:-1]}) AS u(b) WHERE b <= price)) AS band
        FROM horizon_px
        """
    )


def t1_calibration(con) -> dict[str, pd.DataFrame]:
    labels = {i + 1: f"{BANDS[i]:.2f}-{min(BANDS[i + 1], 1):.2f}" for i in range(len(BANDS) - 1)}
    rel = con.execute(
        """
        SELECT h, band, count(*) AS n, avg(price) AS mean_price, avg(outcome) AS hit_rate,
               avg(outcome) - avg(price) AS bias,
               1.96 * sqrt(avg(outcome) * (1 - avg(outcome)) / count(*)) AS ci95
        FROM binned GROUP BY 1, 2 ORDER BY 1 DESC, 2
        """
    ).df()
    rel["band"] = rel["band"].map(labels)
    brier = con.execute(
        """
        WITH base AS (SELECT h, avg(outcome) AS rate FROM binned GROUP BY 1)
        SELECT b.h, count(*) AS n, avg((price - outcome) ** 2) AS brier_market,
               avg((outcome - rate) ** 2) AS brier_base_rate
        FROM binned b JOIN base USING (h) GROUP BY 1 ORDER BY 1 DESC
        """
    ).df()
    by_city = con.execute(
        """
        SELECT city, h, count(*) AS n, avg((price - outcome) ** 2) AS brier,
               avg(outcome) - avg(price) AS bias
        FROM binned WHERE h IN (24, 12, 3) GROUP BY 1, 2 ORDER BY 1, 2 DESC
        """
    ).df()
    by_era = con.execute(
        """
        SELECT era, h, count(*) AS n, avg((price - outcome) ** 2) AS brier, avg(outcome) - avg(price) AS bias
        FROM binned WHERE h IN (24, 12, 3) GROUP BY 1, 2 ORDER BY 1, 2 DESC
        """
    ).df()
    return {"reliability": rel, "brier": brier, "by_city": by_city, "by_era": by_era}


def t2_extremes(con) -> pd.DataFrame:
    labels = {i + 1: f"{BANDS[i]:.2f}-{min(BANDS[i + 1], 1):.2f}" for i in range(len(BANDS) - 1)}
    df = con.execute(
        """
        SELECT h, bucket_pos, band, count(*) AS n, avg(price) AS mean_price, avg(outcome) AS hit_rate,
               avg(outcome - price) AS return_per_share,
               1.96 * sqrt(avg(outcome) * (1 - avg(outcome)) / count(*)) AS ci95
        FROM binned WHERE h IN (12, 3) GROUP BY 1, 2, 3 ORDER BY 1 DESC, 2, 3
        """
    ).df()
    df["band"] = df["band"].map(labels)
    return df


def t3_sum_of_yes(con) -> pd.DataFrame:
    return con.execute(
        """
        WITH s AS (
          SELECT event_id, h, sum(price) AS total, count(*) AS n_priced,
                 (SELECT count(*) FROM res r WHERE r.event_id = hp.event_id) AS n_buckets
          FROM horizon_px hp GROUP BY 1, 2
        )
        SELECT h, count(*) AS n_events, avg(total) AS mean_sum, quantile_cont(total, 0.05) AS p05,
               quantile_cont(total, 0.5) AS median_sum, quantile_cont(total, 0.95) AS p95,
               avg((total < 0.95)::int) AS share_below_095, avg((total > 1.05)::int) AS share_above_105
        FROM s WHERE n_priced = n_buckets GROUP BY 1 ORDER BY 1 DESC
        """
    ).df()


def t4_maker_taker(con) -> dict[str, pd.DataFrame]:
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE fills AS
        SELECT t.ts, t.market_id, r.city, r.era, r.date, t.maker, t.taker, t.token_amount AS shares,
               r.date < DATE '2026-05-01' AS complete_month,
               CASE WHEN t.nonusdc_side = 'token1' THEN t.price ELSE 1 - t.price END AS yes_price,
               CASE WHEN (t.taker_direction = 'BUY') = (t.nonusdc_side = 'token1') THEN 1 ELSE -1 END
                 AS taker_sign,
               r.outcome
        FROM trades t JOIN res r USING (market_id)
        """
    )
    con.execute(
        "CREATE OR REPLACE TEMP TABLE fpnl AS SELECT *, taker_sign * (outcome - yes_price) * shares "
        "AS taker_pnl FROM fills"
    )
    overall = con.execute(
        """
        SELECT era, complete_month, count(*) AS n_fills, sum(shares) AS shares,
               sum(taker_pnl) AS taker_pnl_usd, sum(taker_pnl) / sum(shares) AS taker_pnl_per_share,
               avg((taker_sign = 1)::int) AS share_taker_buys_yes
        FROM fpnl GROUP BY 1, 2 ORDER BY 1, 2 DESC
        """
    ).df()
    by_city = con.execute(
        """
        SELECT city, count(*) AS n_fills, sum(shares) AS shares, sum(taker_pnl) AS taker_pnl_usd,
               sum(taker_pnl) / sum(shares) AS taker_pnl_per_share
        FROM fpnl GROUP BY 1 ORDER BY 3 DESC
        """
    ).df()
    by_band = con.execute(
        f"""
        SELECT CASE WHEN taker_sign = 1 THEN 'taker buys YES' ELSE 'taker sells YES' END AS side,
               list_position({BANDS[:-1]}, (SELECT max(b) FROM unnest({BANDS[:-1]}) AS u(b) WHERE b <= yes_price)) AS band,
               count(*) AS n_fills, sum(shares) AS shares, sum(taker_pnl) / sum(shares) AS taker_pnl_per_share
        FROM fpnl GROUP BY 1, 2 ORDER BY 1, 2
        """
    ).df()
    labels = {i + 1: f"{BANDS[i]:.2f}-{min(BANDS[i + 1], 1):.2f}" for i in range(len(BANDS) - 1)}
    by_band["band"] = by_band["band"].map(labels)
    makers = con.execute(
        """
        SELECT maker, count(*) AS n_fills, sum(shares) AS shares, count(DISTINCT market_id) AS n_markets,
               -sum(taker_pnl) AS maker_pnl_usd, -sum(taker_pnl) / sum(shares) AS maker_pnl_per_share
        FROM fpnl GROUP BY 1 ORDER BY shares DESC LIMIT 15
        """
    ).df()
    return {
        "overall": overall,
        "by_city": by_city,
        "by_band": by_band,
        "makers": makers,
        "fill_coverage": fill_coverage(con),
    }


def t5_capacity(con) -> pd.DataFrame:
    return con.execute(
        """
        WITH d AS (
          SELECT city, date,
                 coalesce(sum(shares) FILTER (WHERE yes_price < 0.10 OR yes_price > 0.90), 0) AS extreme_shares,
                 sum(shares) AS all_shares, count(*) AS n_fills
          FROM fills GROUP BY 1, 2
        )
        SELECT city, count(*) AS n_days, avg(all_shares) AS mean_shares_per_day,
               quantile_cont(all_shares, 0.5) AS median_shares_per_day,
               avg(extreme_shares) AS mean_extreme_shares_per_day, avg(n_fills) AS mean_fills_per_day
        FROM d GROUP BY 1 ORDER BY 3 DESC
        """
    ).df()


def fill_coverage(con) -> pd.DataFrame:
    """Dataset fill shares vs Gamma volume per month: complete means the two agree within 1%."""
    return con.execute(
        """
        WITH v AS (SELECT market_id, sum(shares) AS shares FROM fills GROUP BY 1)
        SELECT strftime(r.date, '%Y-%m') AS month, count(*) AS n_markets,
               avg((abs(v.shares / r.shares - 1) < 0.01)::int) AS share_exact,
               quantile_cont(v.shares / r.shares, 0.5) AS median_ratio
        FROM res r JOIN v USING (market_id) WHERE r.shares > 0 GROUP BY 1 ORDER BY 1
        """
    ).df()


def coverage(con) -> pd.DataFrame:
    return con.execute(
        """
        SELECT (SELECT count(*) FROM res) AS resolved_markets,
               (SELECT count(DISTINCT market_id) FROM horizon_px) AS markets_with_prices,
               (SELECT count(DISTINCT market_id) FROM fills) AS markets_with_fills,
               (SELECT min(date) FROM res) AS first_day, (SELECT max(date) FROM res) AS last_day,
               (SELECT max(ts) FROM fills) AS last_fill
        """
    ).df()


def md(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False, floatfmt=".4f") if len(df) else "No data."


def write_report(path: Path, cov, t1, t2, t3, t4, t5) -> None:
    parts = [
        "# Phase 1: market-side checks",
        "",
        "Tests T1 to T5 of the research log. Prices are CLOB history sampled at h hours before the "
        "local midnight that ends the event day (as-of, never after). Outcome is the resolved bucket. "
        "Profit figures are gross of fees.",
        "",
        "## Coverage",
        "",
        md(cov),
        "",
        "## T1 (H1) Calibration: Brier score by horizon (base rate = predicting the mean outcome)",
        "",
        md(t1["brier"]),
        "",
        "### Reliability by price band and horizon (bias = hit rate minus mean price; ci95 on hit rate)",
        "",
        md(t1["reliability"]),
        "",
        "### Brier and bias by city (h = 24, 12, 3)",
        "",
        md(t1["by_city"]),
        "",
        "### Brier and bias by rule era",
        "",
        md(t1["by_era"]),
        "",
        "## T2 (H2) Return of buying YES by bucket position and price band (h = 12 and 3)",
        "",
        md(t2),
        "",
        "## T3 Sum of YES prices across an event's buckets",
        "",
        md(t3),
        "",
        "## Dataset fill coverage by month (fill shares vs Gamma volume)",
        "",
        md(t4["fill_coverage"]),
        "",
        "## T4 (H9) Taker profit per fill (maker profit is the negative, gross of fees)",
        "",
        "complete_month = event day before 2026-05-01, where the dataset holds every fill.",
        "",
        md(t4["overall"]),
        "",
        "### By city",
        "",
        md(t4["by_city"]),
        "",
        "### By taker side and YES-equivalent price band",
        "",
        md(t4["by_band"]),
        "",
        "### Largest makers by shares",
        "",
        md(t4["makers"]),
        "",
        "## T5 Capacity: shares per city-day (extreme = YES price under 0.10 or over 0.90)",
        "",
        md(t5),
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts))


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--research", default=str(config.RESEARCH_DB))
    ap.add_argument("--prices", default=str(config.PRICES_DB))
    ap.add_argument("--report", default=str(config.REPORTS / "phase1_market_checks.md"))
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    con = connect(a.research, a.prices)
    build_views(con)
    t1, t2, t3 = t1_calibration(con), t2_extremes(con), t3_sum_of_yes(con)
    t4 = t4_maker_taker(con)
    t5, cov = t5_capacity(con), coverage(con)
    write_report(Path(a.report), cov, t1, t2, t3, t4, t5)
    log.info("report written to %s", a.report)
    print(cov.to_string(index=False))
    print(t1["brier"].to_string(index=False))
    print(t4["overall"].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
