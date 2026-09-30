"""Live snapshots of the order books, rules, observations and forecasts, for later analysis.

Runs forever. Every row carries the time it was fetched, nothing is backfilled, and each table is
flushed to Parquet files (and to S3 when a bucket is configured). A heartbeat file is touched every
loop and three consecutive failures of one task post to a webhook, which is what an unattended
process on a small instance needs.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import os
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

import weather_edge.markets as p0
from weather_edge import config

CLOB_BOOKS = "https://clob.polymarket.com/books"
METAR_URL = "https://aviationweather.gov/api/data/metar"
STATION_URL = "https://aviationweather.gov/api/data/stationinfo"
HKO_URL = (
    "https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_1min_temperature.csv"
)
OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
MODELS = "gfs_seamless,ecmwf_ifs025,icon_seamless,gem_seamless"
FIXED_COORDS = {"HKO": (22.302, 114.174)}  # Hong Kong Observatory headquarters, no ICAO
INTERVALS = {"markets": 600, "books": 120, "observations": 120, "forecasts": 10800, "flush": 900}
log = logging.getLogger("collector")


def now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)


# ------------------------------------------------------------------------------ parsing
def market_rows(ev: dict, fetched_at: datetime) -> list[dict]:
    """Active bucket markets of one live event, using the Phase 0 parsers."""
    rows = []
    for r in p0.event_rows(ev, fetched_at):
        rows.append(
            {
                "fetched_at": fetched_at,
                "market_id": r["market_id"],
                "event_id": r["event_id"],
                "city": r["city"],
                "station": r["station"],
                "date": r["date"],
                "unit": r["unit"],
                "bucket_label": r["bucket_label"],
                "bucket_lo": r["bucket_lo"],
                "bucket_hi": r["bucket_hi"],
                "token_yes": r["clob_token_yes"],
                "token_no": r["clob_token_no"],
                "condition_id": r["condition_id"],
                "resolution_source": r["resolution_source"],
                "rules_hash": r["rules_hash"],
                "rules_text": r["rules_text"],
                "closed": r["closed"],
                "end_date": r["end_date"],
            }
        )
    return rows


def book_rows(
    books: list[dict], token_market: dict[str, str], fetched_at: datetime, state: dict
) -> list[dict]:
    """One row per book whose hash changed since the last stored snapshot."""
    seen = state.setdefault("book_hash", {})
    rows = []
    for b in books:
        tok = str(b.get("asset_id"))
        if seen.get(tok) == b.get("hash"):
            continue
        seen[tok] = b.get("hash")
        bids = sorted((float(x["price"]), float(x["size"])) for x in b.get("bids") or [])
        asks = sorted((float(x["price"]), float(x["size"])) for x in b.get("asks") or [])
        rows.append(
            {
                "fetched_at": fetched_at,
                "market_id": token_market.get(tok),
                "token_id": tok,
                "book_ts": datetime.fromtimestamp(int(b["timestamp"]) / 1000, UTC).replace(
                    tzinfo=None
                )
                if b.get("timestamp")
                else None,
                "hash": b.get("hash"),
                "best_bid": bids[-1][0] if bids else None,
                "best_ask": asks[0][0] if asks else None,
                "bids": json.dumps(bids),
                "asks": json.dumps(asks),
                "last_trade_price": p0._num(b.get("last_trade_price")),
                "min_order_size": p0._num(b.get("min_order_size")),
                "tick_size": p0._num(b.get("tick_size")),
            }
        )
    return rows


def metar_rows(reports: list[dict], fetched_at: datetime, state: dict) -> list[dict]:
    """New METAR or SPECI reports (deduplicated on station, observation time and raw text)."""
    seen = state.setdefault("obs_seen", [])
    keys = set(map(tuple, seen))
    rows = []
    for m in reports:
        key = (m.get("icaoId"), int(m.get("obsTime") or 0), m.get("rawOb"))
        if key in keys or not key[0]:
            continue
        keys.add(key)
        rows.append(
            {
                "fetched_at": fetched_at,
                "station": m["icaoId"],
                "source": "metar",
                "obs_time": datetime.fromtimestamp(key[1], UTC).replace(tzinfo=None),
                "report_time": p0._ts(m.get("reportTime")),
                "receipt_time": p0._ts(m.get("receiptTime")),
                "temp_c": p0._num(m.get("temp")),
                "dewp_c": p0._num(m.get("dewp")),
                "raw": m.get("rawOb"),
                "report_type": m.get("metarType"),
            }
        )
    state["obs_seen"] = [list(k) for k in keys][-20000:]
    return rows


def hko_rows(csv_text: str, fetched_at: datetime, state: dict) -> list[dict]:
    """The Hong Kong Observatory station line of the 1-minute temperature CSV (HKT to UTC)."""
    seen = state.setdefault("obs_seen", [])
    keys = set(map(tuple, seen))
    rows = []
    for rec in csv.DictReader(io.StringIO(csv_text)):
        station = next((v for k, v in rec.items() if "station" in k.lower()), "")
        if station.strip().lower() not in ("hk observatory", "hong kong observatory", "hko"):
            continue
        stamp = next((v for k, v in rec.items() if "date" in k.lower()), "")
        temp = next((v for k, v in rec.items() if "temperature" in k.lower()), None)
        try:
            obs = datetime.strptime(stamp.strip(), "%Y%m%d%H%M") - timedelta(hours=8)
        except ValueError:
            continue
        key = ("HKO", int(obs.replace(tzinfo=UTC).timestamp()), None)
        if key in keys:
            continue
        keys.add(key)
        rows.append(
            {
                "fetched_at": fetched_at,
                "station": "HKO",
                "source": "hko_1min",
                "obs_time": obs,
                "report_time": None,
                "receipt_time": None,
                "temp_c": p0._num(temp),
                "dewp_c": None,
                "raw": ",".join(str(v) for v in rec.values()),
                "report_type": "1min",
            }
        )
    state["obs_seen"] = [list(k) for k in keys][-20000:]
    return rows


def forecast_rows(payload: dict, station: str, fetched_at: datetime) -> list[dict]:
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    rows = []
    for key, values in hourly.items():
        if not key.startswith("temperature_2m"):
            continue
        model = key.replace("temperature_2m_", "") if key != "temperature_2m" else "default"
        for t, v in zip(times, values, strict=True):
            if v is not None:
                rows.append(
                    {
                        "available_time": fetched_at,
                        "station": station,
                        "model": model,
                        "valid_time": datetime.fromisoformat(t),
                        "temp_c": float(v),
                    }
                )
    return rows


def rules_rows(markets: list[dict], state: dict) -> list[dict]:
    seen = state.setdefault("rules_hash", {})
    rows = []
    for m in markets:
        if seen.get(m["market_id"]) != m["rules_hash"]:
            if m["market_id"] in seen:
                log.warning("rules changed for market %s", m["market_id"])
            seen[m["market_id"]] = m["rules_hash"]
            rows.append(
                {
                    "fetched_at": m["fetched_at"],
                    "market_id": m["market_id"],
                    "rules_hash": m["rules_hash"],
                    "rules_text": m["rules_text"],
                }
            )
    return rows


# ------------------------------------------------------------------------------ storage
class Store:
    """Buffers rows per table, flushes hourly Parquet files, uploads them to S3 when configured."""

    def __init__(self, out: Path, bucket: str | None = None, prefix: str = "collector"):
        self.out, self.bucket, self.prefix = out, bucket, prefix
        self.buffers: dict[str, list[dict]] = {}
        self.state_path = out / "state.json"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {}
        self.s3 = None
        if bucket:
            import boto3

            self.s3 = boto3.client("s3")

    def add(self, table: str, rows: list[dict]) -> None:
        if rows:
            self.buffers.setdefault(table, []).extend(rows)

    def flush(self, when: datetime | None = None) -> list[Path]:
        when = when or now_utc()
        written = []
        for table, rows in list(self.buffers.items()):
            if not rows:
                continue
            path = self.out / table / when.strftime("%Y-%m-%d") / f"{when:%H%M%S}.parquet"
            path.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(rows).to_parquet(path, compression="zstd", index=False)
            self.buffers[table] = []
            written.append(path)
            log.info("wrote %d rows to %s", len(rows), path)
        pending = self.state.setdefault("pending_uploads", [])
        pending.extend(str(p) for p in written)
        if self.s3 is not None:
            still = []
            for f in pending:
                key = f"{self.prefix}/{Path(f).relative_to(self.out)}"
                try:
                    self.s3.upload_file(f, self.bucket, key)
                except Exception as e:  # noqa: BLE001 - any upload failure is retried next flush
                    log.warning("upload of %s failed: %s", f, e)
                    still.append(f)
            self.state["pending_uploads"] = still
        else:
            self.state["pending_uploads"] = []
        self.out.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self.state))
        return written


# ------------------------------------------------------------------------------ collector
class Collector:
    def __init__(
        self, store: Store, session: requests.Session | None = None, cities: set[str] | None = None
    ):
        self.store, self.cities = store, cities
        self.s = session or requests.Session()
        self.s.headers.update({"User-Agent": "polymarket-weather-edge/collector"})
        self.gamma = p0.Gamma(session=self.s)
        self.markets: list[dict] = []
        self.coords: dict[str, tuple[float, float]] = dict(FIXED_COORDS)
        self.failures: dict[str, int] = {}

    # --- tasks
    def task_markets(self) -> None:
        t = now_utc()
        since = (t - timedelta(days=2)).date()
        rows = []
        for ev in self.gamma.iter_events(closed="false", title_search="highest temperature in"):
            if not p0.TITLE_RE.match(ev.get("title") or ""):
                continue
            for r in market_rows(ev, t):
                if (r["date"] or since) >= since and (not self.cities or r["city"] in self.cities):
                    rows.append(r)
        self.markets = rows
        self.store.add(
            "markets_live", [{k: v for k, v in r.items() if k != "rules_text"} for r in rows]
        )
        self.store.add("rules_history", rules_rows(rows, self.store.state))
        missing = {r["station"] for r in rows if r["station"] and r["station"] not in self.coords}
        if missing:
            self.coords.update(station_coords(self.s, missing))
        log.info("%d active bucket markets in %d cities", len(rows), len({r["city"] for r in rows}))

    def task_books(self) -> None:
        t = now_utc()
        token_market = {r["token_yes"]: r["market_id"] for r in self.markets if r["token_yes"]}
        toks = list(token_market)
        books = []
        for i in range(0, len(toks), 100):
            r = self.s.post(
                CLOB_BOOKS, json=[{"token_id": x} for x in toks[i : i + 100]], timeout=60
            )
            r.raise_for_status()
            books.extend(r.json())
        rows = book_rows(books, token_market, t, self.store.state)
        self.store.add("books", rows)
        log.info("%d books fetched, %d changed", len(books), len(rows))

    def task_observations(self) -> None:
        t = now_utc()
        stations = sorted(
            {
                r["station"]
                for r in self.markets
                if r["station"] and r["station"] not in FIXED_COORDS and len(r["station"]) == 4
            }
        )
        rows = []
        for i in range(0, len(stations), 50):
            r = self.s.get(
                METAR_URL,
                params={"ids": ",".join(stations[i : i + 50]), "format": "json", "hours": 3},
                timeout=60,
            )
            r.raise_for_status()
            rows += metar_rows(r.json(), t, self.store.state)
        if any(r["station"] == "HKO" for r in self.markets):
            r = self.s.get(HKO_URL, timeout=60)
            if r.status_code == 200:
                rows += hko_rows(r.text, t, self.store.state)
        self.store.add("observations", rows)
        log.info("%d new observations for %d stations", len(rows), len(stations))

    def task_forecasts(self) -> None:
        t = now_utc()
        rows = []
        for station, (lat, lon) in sorted(self.coords.items()):
            if not any(r["station"] == station for r in self.markets):
                continue
            r = self.s.get(
                OPEN_METEO,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": "temperature_2m",
                    "models": MODELS,
                    "forecast_days": 3,
                    "timezone": "UTC",
                },
                timeout=60,
            )
            if r.status_code != 200:
                log.warning("open-meteo %s for %s: %s", r.status_code, station, r.text[:100])
                continue
            rows += forecast_rows(r.json(), station, t)
            time.sleep(0.2)
        self.store.add("forecasts", rows)
        log.info("%d forecast rows", len(rows))

    def task_flush(self) -> None:
        self.store.flush()

    # --- loop
    def run(self, once: bool = False, intervals: dict | None = None) -> None:
        intervals = intervals or INTERVALS
        tasks = {
            "markets": self.task_markets,
            "books": self.task_books,
            "observations": self.task_observations,
            "forecasts": self.task_forecasts,
            "flush": self.task_flush,
        }
        due = dict.fromkeys(tasks, 0.0)
        heartbeat = self.store.out / "heartbeat"
        self.store.out.mkdir(parents=True, exist_ok=True)
        while True:
            now = time.time()
            for name, fn in tasks.items():
                if now < due[name]:
                    continue
                try:
                    fn()
                    self.failures[name] = 0
                    due[name] = now + intervals[name]
                except Exception as e:  # noqa: BLE001 - one failing task must not stop the others
                    self.failures[name] = self.failures.get(name, 0) + 1
                    log.error("task %s failed (%d in a row): %s", name, self.failures[name], e)
                    if self.failures[name] == 3:
                        alert(f"collector task {name} failed 3 times: {e}")
                    due[name] = now + min(
                        intervals[name], 300
                    )  # retry a failed task within 5 minutes
            heartbeat.write_text(now_utc().isoformat())
            if once:
                self.store.flush()
                return
            time.sleep(max(1.0, min(due.values()) - time.time()))


def station_coords(session, stations: set[str]) -> dict[str, tuple[float, float]]:
    ids = sorted(s for s in stations if len(s) == 4)
    if not ids:
        return {}
    r = session.get(STATION_URL, params={"ids": ",".join(ids), "format": "json"}, timeout=60)
    r.raise_for_status()
    found = {
        x["icaoId"]: (float(x["lat"]), float(x["lon"]))
        for x in r.json()
        if x.get("lat") is not None
    }
    for s in ids:
        if s not in found:
            log.warning("no coordinates for station %s; no forecasts for it", s)
    return found


def alert(message: str) -> None:
    url = os.environ.get("COLLECTOR_ALERT_WEBHOOK")
    if url:
        try:
            requests.post(url, json={"text": message}, timeout=30)
        except requests.RequestException as e:
            log.error("alert failed: %s", e)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--out", default=os.environ.get("COLLECTOR_DIR", str(config.COLLECTOR)))
    ap.add_argument("--once", action="store_true", help="run every task once, flush and exit")
    ap.add_argument(
        "--cities",
        default=os.environ.get("COLLECTOR_CITIES", ""),
        help="comma-separated, empty = all",
    )
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    store = Store(
        Path(a.out),
        os.environ.get("COLLECTOR_S3_BUCKET") or None,
        os.environ.get("COLLECTOR_S3_PREFIX", "collector"),
    )
    cities = {c.strip() for c in a.cities.split(",") if c.strip()} or None
    Collector(store, cities=cities).run(once=a.once)
    return 0


if __name__ == "__main__":
    sys.exit(main())
