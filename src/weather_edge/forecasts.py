"""Phase 5 data: point forecasts of 2 m temperature from open GRIB archives, with real availability times.

Sources (licence-clean, no quota):
  ecmwf  IFS 0.25 deg HRES open data (CC-BY 4.0), Google Cloud mirror of ECMWF's bucket, since 2023-07;
         00/12Z runs are stream oper, 06/18Z runs stream scda until 2026-05-11 and oper from 2026-05-12
  gfs    NOAA GFS 0.25 deg on AWS Open Data, since 2021
  gefs_mean, gefs_spread  NOAA GEFS 0.25 deg ensemble mean and standard deviation (31 members), since 2025-01
  nbm_tmax, nbm_tmax_spread  NOAA NBM core CONUS 2.5 km: 12-hour maximum of 2 m temperature for the
         12Z to 00Z window (valid at the window end) and its ensemble standard deviation; runs 00, 06, 12
         and 18Z, steps chosen per cycle (STEPS_BY_CYCLE); nearest grid point; US stations only
  (ECMWF ENS comes only as 51 member messages, about 525 GB for the period, and is deferred)
Each run step is one GRIB2 file with an index; only the 2 m temperature message is fetched by byte
range, decoded with ecCodes and interpolated bilinearly to every station at once. available_time is
the object's Last-Modified header (when the file appeared on the mirror), never the run's init time.

Tables in data/forecasts.duckdb:
  forecasts     station, model, init_time, available_time, valid_time, lead_h, temp_c
  forecast_runs model, init_time, lead_h, status (ok, missing), fetched_at   (resume log)

Usage: python -m weather_edge.forecasts --start 2025-01-01 --end 2026-09-29 [--models ecmwf gfs] [--cycles 0 12] [--retry-missing]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from email.utils import parsedate_to_datetime

import duckdb
import numpy as np
import pandas as pd
import requests

from weather_edge.collector import FIXED_COORDS, station_coords

SOURCES = {
    "ecmwf": {
        "url": "https://storage.googleapis.com/ecmwf-open-data/{d:%Y%m%d}/{c:02d}z/ifs/0p25/{stream}/{d:%Y%m%d}{c:02d}0000-{s}h-{stream}-fc",
        "index_ext": ".index",
        "data_ext": ".grib2",
    },
    "gfs": {
        "url": "https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.{d:%Y%m%d}/{c:02d}/atmos/gfs.t{c:02d}z.pgrb2.0p25.f{s:03d}",
        "index_ext": ".idx",
        "data_ext": "",
    },
    # GEFS 0.25 deg ensemble mean and spread (31 members), one field each per step
    "gefs_mean": {
        "url": "https://noaa-gefs-pds.s3.amazonaws.com/gefs.{d:%Y%m%d}/{c:02d}/atmos/pgrb2sp25/geavg.t{c:02d}z.pgrb2s.0p25.f{s:03d}",
        "index_ext": ".idx",
        "data_ext": "",
    },
    "gefs_spread": {
        "url": "https://noaa-gefs-pds.s3.amazonaws.com/gefs.{d:%Y%m%d}/{c:02d}/atmos/pgrb2sp25/gespr.t{c:02d}z.pgrb2s.0p25.f{s:03d}",
        "index_ext": ".idx",
        "data_ext": "",
    },
    # NBM core CONUS (2.5 km Lambert grid): 12-hour maximum of 2 m temperature for the 12Z to 00Z
    # window and its ensemble standard deviation, one message each per run
    "nbm_tmax": {
        "url": "https://noaa-nbm-grib2-pds.s3.amazonaws.com/blend.{d:%Y%m%d}/{c:02d}/core/blend.t{c:02d}z.core.f{s:03d}.co.grib2",
        "index_ext": ".idx",
        "data_ext": "",
    },
    "nbm_tmax_spread": {
        "url": "https://noaa-nbm-grib2-pds.s3.amazonaws.com/blend.{d:%Y%m%d}/{c:02d}/core/blend.t{c:02d}z.core.f{s:03d}.co.grib2",
        "index_ext": ".idx",
        "data_ext": "",
    },
}
# wgrib-style index line per model: (field text, whether the line must carry 'ens std dev'; None: any)
IDX_FIELD = {
    "gfs": (":TMP:2 m above ground:", None),
    "gefs_mean": (":TMP:2 m above ground:", None),
    "gefs_spread": (":TMP:2 m above ground:", None),
    "nbm_tmax": (":TMAX:2 m above ground:", False),
    "nbm_tmax_spread": (":TMAX:2 m above ground:", True),
}
# steps whose 12-hour window is 12Z to 00Z of the run day, the next day and the day after
STEPS_BY_CYCLE = {
    "nbm_tmax": {0: [24, 48, 72], 6: [18, 42, 66], 12: [12, 36, 60], 18: [30, 54]},
}
STEPS_BY_CYCLE["nbm_tmax_spread"] = STEPS_BY_CYCLE["nbm_tmax"]
log = logging.getLogger("forecasts")
ECMWF_SCDA_END = date(2026, 5, 12)  # 06/18Z runs were stream scda before this date, oper from it on


def ecmwf_stream(init: datetime) -> str:
    return "scda" if init.hour in (6, 18) and init.date() < ECMWF_SCDA_END else "oper"


def step_url(model: str, init: datetime, step: int) -> str:
    return SOURCES[model]["url"].format(
        d=init.date(), c=init.hour, s=step, stream=ecmwf_stream(init)
    )


# ------------------------------------------------------------------------------ parsing
def byte_range(model: str, index_text: str) -> tuple[int, int] | None:
    """(offset, length) of the 2 m temperature message, from an ECMWF JSON index or a GFS .idx."""
    if model == "ecmwf":
        for line in index_text.splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            if e.get("param") == "2t":
                return int(e["_offset"]), int(e["_length"])
        return None
    field, want_spread = IDX_FIELD[model]
    lines = index_text.splitlines()
    for i, line in enumerate(lines):
        if field in line and (want_spread is None or ("ens std dev" in line) == want_spread):
            off = int(line.split(":")[1])
            end = int(lines[i + 1].split(":")[1]) if i + 1 < len(lines) else None
            return off, (end - off) if end else -1
    return None


_NEAREST: dict[tuple, dict[tuple[float, float], int]] = {}  # grid signature -> (lat, lon) -> index


def decode(blob: bytes) -> tuple[dict, np.ndarray]:
    import eccodes

    gid = eccodes.codes_new_from_message(blob)
    if eccodes.codes_get(gid, "gridType") != "regular_ll":
        k = {
            x: eccodes.codes_get(gid, x)
            for x in ("gridType", "Nx", "Ny", "dataDate", "dataTime", "step")
        }
        k["lat1"] = eccodes.codes_get(gid, "latitudeOfFirstGridPointInDegrees")
        k["lon1"] = eccodes.codes_get(gid, "longitudeOfFirstGridPointInDegrees")
        k["sig"] = (k["gridType"], k["Nx"], k["Ny"], round(k["lat1"], 3), round(k["lon1"], 3))
        if k["sig"] not in _NEAREST:  # first message on this grid: keep the coordinates
            k["lats"] = eccodes.codes_get_double_array(gid, "latitudes")
            k["lons"] = eccodes.codes_get_double_array(gid, "longitudes")
        vals = eccodes.codes_get_values(gid)
        eccodes.codes_release(gid)
        return k, vals
    keys = (
        "Ni",
        "Nj",
        "latitudeOfFirstGridPointInDegrees",
        "longitudeOfFirstGridPointInDegrees",
        "iDirectionIncrementInDegrees",
        "jDirectionIncrementInDegrees",
        "jScansPositively",
        "dataDate",
        "dataTime",
        "step",
    )
    k = {x: eccodes.codes_get(gid, x) for x in keys}
    vals = eccodes.codes_get_values(gid).reshape(k["Nj"], k["Ni"])
    eccodes.codes_release(gid)
    return k, vals


def nearest(k: dict, lat: float, lon: float) -> int:
    """Flat index of the closest grid point on a projected grid, cached per grid and station."""
    cache = _NEAREST.setdefault(k["sig"], {})
    key = (round(lat, 4), round(lon, 4))
    if key not in cache:
        lons = (np.asarray(k["lons"]) + 180) % 360 - 180
        d2 = (np.asarray(k["lats"]) - lat) ** 2 + (
            ((lons - ((lon + 180) % 360 - 180)) * np.cos(np.radians(lat))) ** 2
        )
        cache[key] = int(np.argmin(d2))
    return cache[key]


def interpolate(k: dict, vals: np.ndarray, lat: float, lon: float) -> float:
    """Bilinear interpolation on a regular lat/lon grid, wrapping in longitude; nearest point on a
    projected grid (a station off the grid, e.g. outside CONUS, gets NaN). Kelvin in, Celsius out."""
    if k.get("gridType", "regular_ll") != "regular_ll":
        i = nearest(k, lat, lon)
        if "lats" in k:
            far = (
                abs(k["lats"][i] - lat) > 0.1 or abs(((k["lons"][i] - lon + 180) % 360) - 180) > 0.1
            )
            _NEAREST[k["sig"]][(round(lat, 4), round(lon, 4))] = -1 if far else i
            i = _NEAREST[k["sig"]][(round(lat, 4), round(lon, 4))]
        return float(vals[i]) - 273.15 if i >= 0 else float("nan")
    lat0, lon0 = k["latitudeOfFirstGridPointInDegrees"], k["longitudeOfFirstGridPointInDegrees"]
    dlat, dlon = k["jDirectionIncrementInDegrees"], k["iDirectionIncrementInDegrees"]
    fi = (lat - lat0) / dlat if k["jScansPositively"] else (lat0 - lat) / dlat
    fj = ((lon - lon0) % 360) / dlon
    i0, j0 = int(np.floor(fi)), int(np.floor(fj))
    wi, wj = fi - i0, fj - j0
    nj, ni = vals.shape

    def g(i, j):
        return vals[min(max(i, 0), nj - 1), j % ni]

    v = (
        (1 - wi) * (1 - wj) * g(i0, j0)
        + wi * (1 - wj) * g(i0 + 1, j0)
        + (1 - wi) * wj * g(i0, j0 + 1)
        + wi * wj * g(i0 + 1, j0 + 1)
    )
    return float(v) - 273.15


# ------------------------------------------------------------------------------ fetching
def fetch_step(
    session, model: str, init: datetime, step: int, coords: dict[str, tuple[float, float]]
) -> tuple[str, list[dict], datetime | None]:
    """Returns (status, rows, available_time). status: ok, missing."""
    src = SOURCES[model]
    base = step_url(model, init, step)
    for attempt in range(6):
        try:
            r = session.get(base + src["index_ext"], timeout=60)
            if r.status_code == 404:
                return "missing", [], None
            if r.status_code != 200:
                raise OSError(f"index HTTP {r.status_code}")
            rng = byte_range(model, r.text)
            if rng is None:
                return "missing", [], None
            off, length = rng
            end = "" if length < 0 else str(off + length - 1)
            r = session.get(
                base + src["data_ext"], headers={"Range": f"bytes={off}-{end}"}, timeout=120
            )
            if r.status_code not in (200, 206):
                raise OSError(f"data HTTP {r.status_code}")
            available = (
                parsedate_to_datetime(r.headers["Last-Modified"])
                .astimezone(UTC)
                .replace(tzinfo=None)
            )
            k, vals = decode(r.content)
            valid = init + timedelta(hours=step)
            offset = (
                273.15 if model.endswith("_spread") else 0.0
            )  # a spread is a difference, not a temperature
            rows = [
                {
                    "station": st,
                    "model": model,
                    "init_time": init,
                    "available_time": available,
                    "valid_time": valid,
                    "lead_h": step,
                    "temp_c": interpolate(k, vals, lat, lon) + offset,
                }
                for st, (lat, lon) in coords.items()
            ]
            rows = [r_ for r_ in rows if not np.isnan(r_["temp_c"])]  # stations off a regional grid
            return "ok", rows, available
        except (OSError, requests.RequestException, KeyError) as e:
            log.warning("%s %s +%dh attempt %d: %s", model, init, step, attempt + 1, e)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"gave up on {model} {init} +{step}h")


def plan(
    con,
    models,
    cycles,
    start: date,
    end: date,
    max_step: int,
    step_h: int,
    retry_missing: bool = False,
) -> list[tuple[str, datetime, int]]:
    con.execute(
        "CREATE TABLE IF NOT EXISTS forecasts (station VARCHAR, model VARCHAR, init_time TIMESTAMP, "
        "available_time TIMESTAMP, valid_time TIMESTAMP, lead_h INTEGER, temp_c DOUBLE)"
    )
    con.execute(
        "CREATE TABLE IF NOT EXISTS forecast_runs (model VARCHAR, init_time TIMESTAMP, lead_h INTEGER, "
        "status VARCHAR, fetched_at TIMESTAMP)"
    )
    done = {
        (m, i, s)
        for m, i, s in con.execute(
            "SELECT model, init_time, lead_h FROM forecast_runs"
            + (" WHERE status = 'ok'" if retry_missing else "")
        ).fetchall()
    }
    tasks = []
    d = start
    while d <= end:
        for c in cycles:
            init = datetime(d.year, d.month, d.day, c)
            for m in models:
                steps = STEPS_BY_CYCLE.get(m, {}).get(c, range(0, max_step + 1, step_h))
                for s in steps:
                    if (m, init, s) not in done:
                        tasks.append((m, init, s))
        d += timedelta(days=1)
    return tasks


def run(con, session, tasks, coords, workers: int = 8, batch: int = 200) -> tuple[int, int]:
    rows_buf, runs_buf, n_ok, n_missing = [], [], 0, 0

    def one(t):
        m, init, s = t
        status, rows, _ = fetch_step(session, m, init, s, coords)
        return t, status, rows

    def flush():
        nonlocal rows_buf, runs_buf
        if rows_buf:
            con.register("fc", pd.DataFrame(rows_buf))
            con.execute("INSERT INTO forecasts SELECT * FROM fc")
            con.unregister("fc")
        if runs_buf:
            con.register(
                "fr",
                pd.DataFrame(
                    runs_buf, columns=["model", "init_time", "lead_h", "status", "fetched_at"]
                ),
            )
            con.execute("INSERT INTO forecast_runs SELECT * FROM fr")
            con.unregister("fr")
        rows_buf, runs_buf = [], []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, (t, status, rows) in enumerate(pool.map(one, tasks), 1):
            rows_buf += rows
            runs_buf.append((*t, status, datetime.now(UTC).replace(tzinfo=None)))
            n_ok += status == "ok"
            n_missing += status == "missing"
            if i % batch == 0 or i == len(tasks):
                flush()
                log.info("%d/%d steps, %d ok, %d missing", i, len(tasks), n_ok, n_missing)
    return n_ok, n_missing


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--db", default="data/forecasts.duckdb")
    ap.add_argument("--markets-db", default="data/research.duckdb")
    ap.add_argument("--start", default="2025-01-01")
    ap.add_argument("--end", default=(date.today() - timedelta(days=1)).isoformat())
    ap.add_argument("--models", nargs="+", default=["ecmwf", "gfs"], choices=list(SOURCES))
    ap.add_argument("--cycles", nargs="+", type=int, default=[0, 12])
    ap.add_argument("--max-step", type=int, default=72)
    ap.add_argument("--step", type=int, default=3)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument(
        "--retry-missing", action="store_true", help="fetch steps logged as missing again"
    )
    ap.add_argument(
        "--stations", nargs="*", help="ICAO codes; default: every station with resolved markets"
    )
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    src = duckdb.connect(a.markets_db, read_only=True)
    stations = a.stations or [
        r[0]
        for r in src.execute(
            "SELECT DISTINCT station FROM markets WHERE closed AND is_winner AND station IS NOT NULL AND station NOT LIKE 'CWA%' ORDER BY 1"
        ).fetchall()
    ]
    src.close()
    session = requests.Session()
    session.headers.update({"User-Agent": "polymarket-weather-edge/forecasts"})
    coords = {s: FIXED_COORDS[s] for s in stations if s in FIXED_COORDS}
    coords.update(station_coords(session, {s for s in stations if s not in FIXED_COORDS}))
    con = duckdb.connect(a.db)
    tasks = plan(
        con,
        a.models,
        a.cycles,
        date.fromisoformat(a.start),
        date.fromisoformat(a.end),
        a.max_step,
        a.step,
        a.retry_missing,
    )
    log.info("%d stations with coordinates, %d steps to fetch", len(coords), len(tasks))
    ok, missing = run(con, session, tasks, coords, a.workers)
    con.close()
    log.info("done: %d ok, %d missing", ok, missing)
    return 0


if __name__ == "__main__":
    sys.exit(main())
