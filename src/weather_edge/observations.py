"""Phase 3: rebuild every resolved market's high from station observations and compare.

Observations come from the Iowa Environmental Mesonet ASOS/METAR archive (routine and SPECI
reports), one CSV per station and year under data/iem, loaded into the DuckDB table observations.
For every resolved event the local clock day (station time zone) is rebuilt under candidate
displayed-value transforms and compared with the bucket Polymarket resolved:
  whole    max over reports of round_half_up(F) from the whole-degree METAR group (C markets: whole C)
  tenths   the same from the T group tenths when present (US ASOS), else the whole group
  routine  as whole, but routine reports only (report minutes with at least a quarter of the station's busiest minute)
  tenths_routine  as tenths, routine reports only (the NOAA hourly table for US stations)
Hong Kong is compared with the Observatory's published daily maximum (one decimal).
Outputs: reports/phase3_ground_truth.md, and the tables observations and truth in the research DB.

Usage: python -m weather_edge.observations [--skip-fetch] [--years 2025 2026]
"""

from __future__ import annotations

import argparse
import io
import logging
import math
import re
import sys
import time
from pathlib import Path

import duckdb
import pandas as pd
import requests

from weather_edge.market_checks import STATION_TZ

IEM_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
HKO_URL = "https://data.weather.gov.hk/weatherAPI/opendata/opendata.php"
TEMP_RE = re.compile(r"(?<![A-Z0-9/])(M?\d{2})/(M?\d{2})?(?=\s|$)")
TGROUP_RE = re.compile(r"\bT([01])(\d{3})([01])(\d{3})\b")
log = logging.getLogger("phase3")


# ------------------------------------------------------------------------------ parsing
def round_half_up(x: float) -> int:
    return int(math.floor(x + 0.5))


def c_to_f(c: float) -> int:
    return round_half_up(c * 9 / 5 + 32)


def parse_metar_temps(raw: str) -> tuple[int | None, float | None]:
    """(whole-degree C from the TT/TD group, tenths C from the T group or None)."""
    whole = None
    for m in TEMP_RE.finditer(raw or ""):
        whole = -int(m.group(1)[1:]) if m.group(1).startswith("M") else int(m.group(1))
        break
    tenths = None
    m = TGROUP_RE.search(raw or "")
    if m:
        tenths = int(m.group(2)) / 10 * (-1 if m.group(1) == "1" else 1)
    return whole, tenths


def iem_station(icao: str) -> str:
    """IEM uses the 3-letter identifier for US ASOS stations and the ICAO elsewhere."""
    return icao[1:] if icao.startswith("K") and len(icao) == 4 else icao


def parse_iem_csv(text: str, icao: str) -> pd.DataFrame:
    if not text.startswith("station"):
        return pd.DataFrame(
            columns=["station", "obs_time_utc", "raw", "temp_c_whole", "temp_c_tenths", "tmpf_iem"]
        )
    df = pd.read_csv(io.StringIO(text), dtype={"metar": str})
    temps = df["metar"].map(parse_metar_temps)
    return pd.DataFrame(
        {
            "station": icao,
            "obs_time_utc": pd.to_datetime(df["valid"]),
            "raw": df["metar"],
            "temp_c_whole": [t[0] for t in temps],
            "temp_c_tenths": [t[1] for t in temps],
            "tmpf_iem": pd.to_numeric(df["tmpf"], errors="coerce"),
        }
    )


# ------------------------------------------------------------------------------ fetching
def fetch_iem(session, icao: str, year: int, out_dir: Path) -> Path:
    path = out_dir / f"{icao}_{year}.csv"
    if path.exists() and path.stat().st_size > 100:
        return path
    params = {
        "station": iem_station(icao),
        "data": ["tmpf", "metar"],
        "year1": year,
        "month1": 1,
        "day1": 1,
        "year2": year + 1,
        "month2": 1,
        "day2": 1,  # IEM's end date is exclusive: this keeps Dec 31
        "tz": "Etc/UTC",
        "format": "onlycomma",
        "latlon": "no",
        "missing": "empty",
        "trace": "empty",
        "direct": "no",
        "report_type": [3, 4],
    }
    for attempt in range(6):
        r = session.get(IEM_URL, params=params, timeout=300)
        if r.status_code == 200 and r.text.startswith("station"):
            out_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(r.text)
            return path
        log.warning(
            "IEM %s %s: HTTP %s (%s), waiting", icao, year, r.status_code, r.text[:60].strip()
        )
        time.sleep(15 * (attempt + 1))
    raise RuntimeError(f"IEM download failed for {icao} {year}")


def fetch_hko(session, year: int) -> pd.DataFrame:
    r = session.get(
        HKO_URL,
        params={"dataType": "CLMMAXT", "year": year, "rformat": "csv", "station": "HKO"},
        timeout=120,
    )
    r.raise_for_status()
    rows = []
    for line in r.text.splitlines():
        parts = line.split(",")
        if len(parts) >= 4 and parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit():
            try:
                rows.append(
                    {
                        "date": pd.Timestamp(int(parts[0]), int(parts[1]), int(parts[2])).date(),
                        "max_c": float(parts[3]),
                    }
                )
            except ValueError:
                continue
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------ rebuild
def load_observations(con, files: list[tuple[Path, str]]) -> int:
    frames = [parse_iem_csv(p.read_text(), icao) for p, icao in files]
    df = pd.concat(frames, ignore_index=True) if frames else parse_iem_csv("", "")
    con.register("obs_in", df)
    con.execute(
        "CREATE OR REPLACE TABLE observations AS SELECT DISTINCT * FROM obs_in ORDER BY station, obs_time_utc"
    )
    con.unregister("obs_in")
    return con.execute("SELECT count(*) FROM observations").fetchone()[0]


def rebuild(con) -> None:
    """Table truth: one row per resolved event with the candidate highs and match flags."""
    con.register("tz_map", pd.DataFrame(list(STATION_TZ.items()), columns=["station", "tz"]))
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE ev AS
        SELECT m.event_id, m.city, m.station, m.date, m.unit, m.resolution_source AS era, t.tz,
               m.bucket_lo AS lo, m.bucket_hi AS hi, m.resolved_bucket
        FROM markets m JOIN tz_map t USING (station)
        WHERE m.is_winner AND m.closed AND m.date IS NOT NULL
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE routine_min AS
        SELECT station, minute FROM (
          SELECT station, minute(obs_time_utc) AS minute, count(*) AS n,
                 max(count(*)) OVER (PARTITION BY station) AS mx
          FROM observations GROUP BY 1, 2) WHERE n >= 0.25 * mx  -- routine slots report every hour
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE obs_local AS
        SELECT o.station, o.obs_time_utc, o.raw, o.temp_c_whole, o.temp_c_tenths,
               ((o.obs_time_utc AT TIME ZONE 'UTC') AT TIME ZONE t.tz) AS local_time,
               minute(o.obs_time_utc) IN (SELECT minute FROM routine_min r WHERE r.station = o.station) AS routine
        FROM observations o JOIN tz_map t USING (station)
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE cand AS
        SELECT e.event_id,
               count(o.raw) AS n_obs,
               max(CASE WHEN e.unit = 'F' THEN floor(o.temp_c_whole * 9 / 5 + 32 + 0.5) ELSE o.temp_c_whole END) AS whole,
               max(CASE WHEN e.unit = 'F' THEN floor(coalesce(o.temp_c_tenths, o.temp_c_whole) * 9 / 5 + 32 + 0.5)
                        ELSE floor(coalesce(o.temp_c_tenths, o.temp_c_whole) + 0.5) END) AS tenths,
               max(CASE WHEN o.routine THEN CASE WHEN e.unit = 'F' THEN floor(o.temp_c_whole * 9 / 5 + 32 + 0.5)
                        ELSE o.temp_c_whole END END) AS routine,
               max(CASE WHEN o.routine THEN CASE WHEN e.unit = 'F' THEN floor(coalesce(o.temp_c_tenths, o.temp_c_whole) * 9 / 5 + 32 + 0.5)
                        ELSE floor(coalesce(o.temp_c_tenths, o.temp_c_whole) + 0.5) END END) AS tenths_routine,
               arg_max(o.local_time, o.temp_c_whole) AS t_max_local,
               arg_max(o.raw, o.temp_c_whole) AS raw_max
        FROM ev e LEFT JOIN obs_local o
          ON o.station = e.station AND o.local_time >= e.date::TIMESTAMP
         AND o.local_time < (e.date + INTERVAL 1 DAY)::TIMESTAMP AND o.temp_c_whole IS NOT NULL
        GROUP BY 1
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE truth AS
        SELECT e.*, c.n_obs, c.whole, c.tenths, c.routine, c.tenths_routine, c.t_max_local, c.raw_max,
               (c.whole IS NOT NULL AND coalesce(e.lo, -999) <= c.whole AND c.whole <= coalesce(e.hi, 999)) AS match_whole,
               (c.tenths IS NOT NULL AND coalesce(e.lo, -999) <= c.tenths AND c.tenths <= coalesce(e.hi, 999)) AS match_tenths,
               (c.routine IS NOT NULL AND coalesce(e.lo, -999) <= c.routine AND c.routine <= coalesce(e.hi, 999)) AS match_routine,
               (c.tenths_routine IS NOT NULL AND coalesce(e.lo, -999) <= c.tenths_routine AND c.tenths_routine <= coalesce(e.hi, 999)) AS match_tenths_routine
        FROM ev e JOIN cand c USING (event_id)
        """
    )


def hko_truth(con, daily: pd.DataFrame) -> pd.DataFrame:
    con.register("hko_daily", daily)
    return con.execute(
        """
        SELECT e.event_id, e.date, e.resolved_bucket, e.bucket_lo AS lo, e.bucket_hi AS hi, d.max_c,
               (coalesce(e.bucket_lo, -999) <= floor(d.max_c) AND floor(d.max_c) <= coalesce(e.bucket_hi, 999)) AS match_floor,
               (coalesce(e.bucket_lo, -999) <= floor(d.max_c + 0.5) AND floor(d.max_c + 0.5) <= coalesce(e.bucket_hi, 999)) AS match_round
        FROM (SELECT * FROM markets WHERE is_winner AND closed AND station = 'HKO') e
        LEFT JOIN hko_daily d USING (date) ORDER BY e.date
        """
    ).df()


# ------------------------------------------------------------------------------- report
def summary_tables(con) -> dict[str, pd.DataFrame]:
    q = lambda s: con.execute(s).df()  # noqa: E731
    return {
        "by_era_unit": q("""SELECT era, unit, count(*) AS n_events, sum((n_obs = 0)::int) AS no_obs,
                               avg(match_whole::int) AS whole, avg(match_tenths::int) AS tenths, avg(match_routine::int) AS routine, avg(match_tenths_routine::int) AS tenths_routine
                            FROM truth WHERE station <> 'HKO' GROUP BY 1, 2 ORDER BY 3 DESC"""),
        "by_city": q("""SELECT city, station, unit, count(*) AS n_events, sum((n_obs = 0)::int) AS no_obs,
                           avg(match_whole::int) AS whole, avg(match_tenths::int) AS tenths, avg(match_routine::int) AS routine, avg(match_tenths_routine::int) AS tenths_routine
                        FROM truth WHERE station <> 'HKO' GROUP BY 1, 2, 3 ORDER BY 4 DESC"""),
        "mismatches": q("""SELECT city, date, era, unit, resolved_bucket, whole, tenths, routine, n_obs,
                              strftime(t_max_local, '%H:%M') AS t_max, raw_max
                           FROM truth WHERE station <> 'HKO' AND n_obs > 0 AND NOT match_whole AND NOT match_tenths
                           ORDER BY city, date"""),
        "f_histogram": q("""SELECT station, coalesce(lo, hi) AS resolved_edge_or_lo, count(*) AS n
                            FROM truth WHERE unit = 'F' AND lo = hi GROUP BY 1, 2 ORDER BY 1, 2"""),
        "peak_time": q("""SELECT city, count(*) AS n_events,
                             avg((hour(t_max_local) < 6)::int) AS share_before_06,
                             avg((hour(t_max_local) >= 22)::int) AS share_after_22
                          FROM truth WHERE n_obs > 0 GROUP BY 1 ORDER BY 3 DESC"""),
    }


def md(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False, floatfmt=".4f") if len(df) else "No data."


def write_report(path: Path, t: dict, hko: pd.DataFrame, n_obs: int) -> None:
    hk = pd.DataFrame(
        [
            {
                "n_events": len(hko),
                "with_daily_max": int(hko.max_c.notna().sum()),
                "match_floor": hko.match_floor.mean() if len(hko) else None,
                "match_round": hko.match_round.mean() if len(hko) else None,
            }
        ]
    )
    parts = [
        "# Phase 3: ground truth rebuilt from station observations",
        "",
        f"IEM ASOS/METAR archive, {n_obs:,} reports loaded. Candidate transforms: whole (whole-degree METAR group), "
        "tenths (T group when present), routine (whole, routine reports only). A match means the rebuilt high falls "
        "in the bucket Polymarket resolved. Local day = station time zone.",
        "",
        "## Match rate by era and unit",
        "",
        md(t["by_era_unit"]),
        "",
        "## Match rate by city",
        "",
        md(t["by_city"]),
        "",
        "## Hong Kong: Observatory daily maximum vs resolved bucket",
        "",
        md(hk),
        "",
        md(hko[~hko.match_floor.fillna(False)].head(40)) if len(hko) else "",
        "",
        f"## Mismatches under both whole and tenths ({len(t['mismatches'])} events)",
        "",
        md(t["mismatches"].head(300)),
        "",
        "## H3: resolved single-degree F buckets per station (frequency of each value)",
        "",
        md(t["f_histogram"]),
        "",
        "## Time of the daily maximum: share before 06:00 and at or after 22:00 local",
        "",
        md(t["peak_time"]),
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts))


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--db", default="data/research.duckdb")
    ap.add_argument("--iem-dir", default="data/iem")
    ap.add_argument("--years", type=int, nargs="+", default=[2025, 2026])
    ap.add_argument("--skip-fetch", action="store_true", help="use the CSVs already in --iem-dir")
    ap.add_argument("--report", default="reports/phase3_ground_truth.md")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    con = duckdb.connect(a.db)
    stations = [
        r[0]
        for r in con.execute(
            "SELECT DISTINCT station FROM markets WHERE closed AND is_winner AND station IS NOT NULL AND station <> 'HKO' "
            "AND station NOT LIKE 'CWA%' ORDER BY 1"
        ).fetchall()
    ]
    session = requests.Session()
    session.headers.update({"User-Agent": "polymarket-weather-edge/phase3"})
    files = []
    for icao in stations:
        for year in a.years:
            path = Path(a.iem_dir) / f"{icao}_{year}.csv"
            if not a.skip_fetch and not path.exists():
                fetch_iem(session, icao, year, Path(a.iem_dir))
                time.sleep(3)
            if path.exists():
                files.append((path, icao))
    n = load_observations(con, files)
    log.info("%d observations for %d stations", n, len(stations))
    rebuild(con)
    hko = hko_truth(con, pd.concat([fetch_hko(session, y) for y in a.years], ignore_index=True))
    t = summary_tables(con)
    write_report(Path(a.report), t, hko, n)
    con.close()
    print(t["by_era_unit"].to_string(index=False))
    print(
        f"HKO: {len(hko)} events, match_floor {hko.match_floor.mean():.3f}, match_round {hko.match_round.mean():.3f}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
