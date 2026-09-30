"""Phase 0: inventory of Polymarket daily temperature markets.

Fetches every "Highest temperature in <city> on <date>?" event from the Gamma API,
parses station, unit, resolution source and buckets from each bucket market's rules
text, stores rows in DuckDB (tables markets, rules_history) and writes one report with
the per-city, per-month history table grouped by resolution source.

Every fetched event is also dumped as JSONL under --raw so a run can be reprocessed
offline with --from-raw (no network, same result).

Usage:
  python -m weather_edge.markets
  python -m weather_edge.markets --from-raw data/raw/gamma_events_20260929T200000Z.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
import time
from datetime import UTC, date, datetime
from pathlib import Path

import duckdb
import pandas as pd
import requests

GAMMA_URL = "https://gamma-api.polymarket.com"
TITLE_RE = re.compile(r"^\s*highest temperature in (?P<city>.+?) on (?P<when>.+?)\??\s*$", re.I)
MONTHS = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
]
WHEN_RE = re.compile(
    r"(?P<month>" + "|".join(m[:3] + r"[a-z]*" for m in MONTHS) + r")\.?\s+(?P<day>\d{1,2})"
    r"(?:\s*,?\s*(?P<year>\d{4}))?",
    re.I,
)
SLUG_YEAR_RE = re.compile(r"-(\d{4})$")
ICAO_SITE_RE = re.compile(r"site=([A-Za-z]{4})\b")
WU_PATH_RE = re.compile(r"wunderground\.com/history/daily/([^\s\"'<>)]+)")
WU_WEATHER_RE = re.compile(r"wunderground\.com/weather/([A-Za-z]{4})\b")
CWA_ID_RE = re.compile(r"cwa\.gov\.tw/\S*?[?&]ID=(\d+)")
ICAO_OBS_RE = re.compile(r"obhistory/([A-Za-z]{4})\b")
ICAO_PAREN_RE = re.compile(r"\(([A-Z]{4})\)")
STATION_NAME_RE = re.compile(
    r"(?:recorded|measured|observed)(?:\s+by\s+[A-Za-z]+)?\s+at\s+(?:the\s+)?"
    r"(?P<name>[^,(]+?)(?:\s+in\s+degrees|\s*\(|,|\s+on\s+|\s+in\s+)",
    re.I,
)
NUM = r"(-?\d+(?:\.\d+)?)"
DEG = r"\s*(?:°|º|˚)?\s*(?:[FC]|℉|℃)?\s*"
BUCKET_RES = [
    ("below", re.compile(rf"^{NUM}{DEG}or\s+(?:below|lower|less|under)\b", re.I)),
    ("above", re.compile(rf"^{NUM}{DEG}or\s+(?:above|higher|more|over)\b", re.I)),
    ("range", re.compile(rf"^{NUM}{DEG}(?:-|–|—|to)\s*{NUM}{DEG}$", re.I)),
    ("single", re.compile(rf"^{NUM}{DEG}$", re.I)),
]
NOT_ICAO = {"NOAA", "ASOS", "AWOS", "ICAO", "METAR", "SPECI", "UTC", "GMT", "NWS"}
# Resolution sources by cited URL, in text order: the first cited is primary, the next is the
# fallback. National services other than NOAA come from live markets (PolyWeather registry).
SOURCE_URLS = [
    (r"weather\.gov\.hk|hko\.gov\.hk", "hko"),
    (r"(?<![a-z])weather\.gov/wrh/timeseries", "noaa_wrh"),
    (r"(?<![a-z])weather\.gov(?!\.hk|/wrh/timeseries)", "noaa_other"),
    (r"wunderground\.com", "wunderground"),
    (r"meteo\.fr|meteofrance|aeroweb", "meteo_france"),
    (r"ims\.gov\.il", "ims"),
    (r"ncm\.gov\.sa", "ncm"),
    (r"imgw\.pl", "imgw"),
    (r"aviationweather\.gov|ogimet", "metar"),
    (r"cwa\.gov\.tw", "cwa"),
]
SOURCE_WORDS = [
    ("hong kong observatory", "hko"),
    ("central weather administration", "cwa"),
    ("weather underground", "wunderground"),
    ("time series", "noaa_wrh"),
    ("timeseries", "noaa_wrh"),
    ("noaa", "noaa_other"),
]
QUESTION_BUCKET_RE = re.compile(r"\bbe\s+(?:between\s+)?(?P<b>.+?)\s+on\s+", re.I)

log = logging.getLogger("phase0")


# ----------------------------------------------------------------------------- fetching
class Gamma:
    """Thin Gamma API client with retries and fixed-size paging."""

    def __init__(
        self,
        session: requests.Session | None = None,
        page: int = 100,
        pause: float = 0.2,
    ):
        self.s = session or requests.Session()
        self.s.headers.update({"User-Agent": "polymarket-weather-edge/phase0"})
        self.page = page
        self.pause = pause

    def get(self, path: str, params: dict | None = None, retries: int = 5):
        for attempt in range(retries):
            try:
                r = self.s.get(f"{GAMMA_URL}/{path}", params=params, timeout=60)
            except requests.RequestException as e:
                log.warning("request error %s (attempt %d): %s", path, attempt + 1, e)
                time.sleep(2 * (attempt + 1))
                continue
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
            log.warning("HTTP %s on %s (attempt %d)", r.status_code, path, attempt + 1)
            time.sleep(5 * (attempt + 1))
        raise RuntimeError(f"Gamma request failed after {retries} attempts: {path} {params}")

    def iter_events(self, **filters):
        """Page GET /events/keyset with after_cursor (offset paging is capped at 2,500)."""
        cursor = None
        while True:
            params = {"limit": self.page, **filters}
            if cursor:
                params["after_cursor"] = cursor
            page = self.get("events/keyset", params) or {}
            events = page.get("events") or []
            yield from events
            cursor = page.get("next_cursor")
            if not events or not cursor:
                return
            time.sleep(self.pause)


def fetch_temperature_events(gamma: Gamma) -> list[dict]:
    """All events whose title matches the daily highest-temperature pattern.

    Primary route: title_search on the phrase itself. Cross-check: the tag slug weather (seen
    on a real event). Events found by only one route are logged. If both find nothing, every
    event is scanned.
    """
    routes = {"title": {"title_search": "highest temperature in"}, "tag": {"tag_slug": "weather"}}
    found: dict[str, dict[str, dict]] = {k: {} for k in routes}
    for closed in ("true", "false"):
        for name, flt in routes.items():
            for ev in gamma.iter_events(closed=closed, **flt):
                if TITLE_RE.match(ev.get("title") or ""):
                    found[name][str(ev["id"])] = ev
            log.info("closed=%s route=%s: %d temperature events", closed, name, len(found[name]))
    only_title = set(found["title"]) - set(found["tag"])
    only_tag = set(found["tag"]) - set(found["title"])
    if only_title or only_tag:
        log.warning(
            "%d events only via title search, %d only via tag", len(only_title), len(only_tag)
        )
    events = {**found["tag"], **found["title"]}
    if not events:
        log.warning("title and tag routes found nothing; scanning all events")
        for closed in ("true", "false"):
            for ev in gamma.iter_events(closed=closed):
                if TITLE_RE.match(ev.get("title") or ""):
                    events[str(ev["id"])] = ev
    return sorted(events.values(), key=lambda e: int(e["id"]))


def dump_raw(events: list[dict], raw_dir: Path, fetched_at: datetime) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"gamma_events_{fetched_at:%Y%m%dT%H%M%SZ}.jsonl"
    with path.open("w") as f:
        for ev in events:
            f.write(json.dumps(ev, separators=(",", ":")) + "\n")
    return path


def load_raw(path: Path) -> list[dict]:
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]


# ------------------------------------------------------------------------------ parsing
def _json_list(v) -> list:
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            out = json.loads(v)
            return out if isinstance(out, list) else []
        except ValueError:
            return []
    return []


def _ts(v) -> datetime | None:
    if not v:
        return None
    try:
        return (
            datetime.fromisoformat(str(v).replace("Z", "+00:00"))
            .astimezone(UTC)
            .replace(tzinfo=None)
        )
    except ValueError:
        return None


def _date(v) -> date | None:
    try:
        return date.fromisoformat(str(v)[:10]) if v else None
    except ValueError:
        return None


def _num(v) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _to_int(s: str) -> int:
    x = float(s)
    return int(x) if x == int(x) else round(x)


def parse_event_title(title: str, slug: str = "", end_date: datetime | None = None):
    """Return (city, date) from 'Highest temperature in <city> on <Month day[, year]>?'."""
    m = TITLE_RE.match(title or "")
    if not m:
        return None, None
    city = m.group("city").strip()
    w = WHEN_RE.search(m.group("when"))
    if not w:
        return city, None
    month = next(i for i, m in enumerate(MONTHS, 1) if m.startswith(w.group("month").lower()[:3]))
    day = int(w.group("day"))
    year = w.group("year")
    if not year and end_date is not None:  # nearest year to endDate; slugs can carry a wrong year
        ref = end_date.date()
        cands = []
        for y in (ref.year - 1, ref.year, ref.year + 1):
            try:
                cands.append(date(y, month, day))
            except ValueError:
                pass
        return city, min(cands, key=lambda d: abs((d - ref).days)) if cands else None
    if not year:
        sm = SLUG_YEAR_RE.search(slug or "")
        year = sm.group(1) if sm else None
    if not year:
        return city, None
    try:
        return city, date(int(year), month, day)
    except ValueError:
        return city, None


def _station_code(text: str) -> str | None:
    """ICAO from the NOAA site= parameter, the WU history path, or a parenthesised code."""
    m = ICAO_SITE_RE.search(text)
    if m:
        return m.group(1).upper()
    m = WU_PATH_RE.search(text)
    if m:
        segs = m.group(1).rstrip(".,;:").split("/")
        cand = segs[segs.index("date") - 1] if "date" in segs else segs[-1]
        if re.fullmatch(r"[A-Za-z]{4}", cand):
            return cand.upper()
    m = WU_WEATHER_RE.search(text) or ICAO_OBS_RE.search(text)
    if m:
        return m.group(1).upper()
    m = CWA_ID_RE.search(text)
    if m:
        return "CWA" + m.group(1)  # Taiwan Central Weather Administration station id
    codes = [c for c in ICAO_PAREN_RE.findall(text) if c not in NOT_ICAO]
    return codes[0] if codes else None


def parse_rules(text: str, source_url: str | None = None) -> dict:
    """Station, resolution source and fallback from a market's rules text.

    The rules text is authoritative. source_url (Gamma's resolutionSource field) only fills in
    a station or a source the text does not state; it can lag the text.
    """
    text = text or ""
    low = text.lower()
    station = _station_code(text) or _station_code(source_url or "")
    hits = [(m.start(), key) for rx, key in SOURCE_URLS for m in re.finditer(rx, low)]
    hits += [(low.find(w), key) for w, key in SOURCE_WORDS if w in low]
    keys = [k for _, k in sorted(hits)]
    if "noaa_wrh" in keys:  # a plain NOAA mention next to the timeseries URL is one source
        keys = ["noaa_wrh" if k == "noaa_other" else k for k in keys]
    keys = list(dict.fromkeys(keys))  # first mention wins, later distinct ones are fallbacks
    if not keys and source_url:
        url = source_url.lower()
        keys = [key for rx, key in SOURCE_URLS if re.search(rx, url)][:1]
    source = keys[0] if keys else ("unknown" if text.strip() else "missing")
    fallback = keys[1] if len(keys) > 1 else None
    if source == "hko" and station is None:
        station = "HKO"  # no ICAO in HKO rules; pseudo-code for the observatory itself
    nm = STATION_NAME_RE.search(text)
    n_f = len(re.findall(r"°\s*f|ºf|℉|fahrenheit", low))
    n_c = len(re.findall(r"°\s*c|ºc|℃|celsius", low))
    unit = "F" if n_f > n_c else ("C" if n_c > n_f else None)
    return {
        "station": station,
        "station_name": nm.group("name").strip() if nm else None,
        "resolution_source": source,
        "resolution_fallback": fallback,
        "unit_in_rules": unit,
    }


def _unit_of(s: str) -> str | None:
    up = s.upper()
    m = re.search(r"(?:°|º|˚)\s*([FC])\b", up) or re.search(r"\d\s*([FC])\b", up)
    return m.group(1) if m else None


def parse_bucket(label: str, question: str = ""):
    """Return (lo, hi, unit); None bound means open end. Falls back to the question."""
    s = (label or "").strip().replace("º", "°").replace("℉", "°F").replace("℃", "°C")
    unit = _unit_of(s)
    for kind, rx in BUCKET_RES:
        m = rx.match(s)
        if not m:
            continue
        if kind == "below":
            return None, _to_int(m.group(1)), unit
        if kind == "above":
            return _to_int(m.group(1)), None, unit
        if kind == "range":
            return _to_int(m.group(1)), _to_int(m.group(2)), unit
        return _to_int(m.group(1)), _to_int(m.group(1)), unit
    qm = QUESTION_BUCKET_RE.search(question or "")
    if qm:
        return parse_bucket(qm.group("b"))
    return None, None, unit


def rules_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode()).hexdigest()[:16]


def pick_winner(markets: list[dict]) -> str | None:
    """Label of the bucket whose YES resolved to 1, or None if unresolved."""
    winners = []
    for m in markets:
        prices = _json_list(m.get("outcomePrices"))
        outcomes = [str(o).lower() for o in _json_list(m.get("outcomes"))] or ["yes", "no"]
        idx = outcomes.index("yes") if "yes" in outcomes else 0
        p = _num(prices[idx]) if idx < len(prices) else None
        if m.get("closed") is not False and p is not None and p >= 0.99:
            winners.append(m)
    if len(winners) == 1:
        return winners[0].get("groupItemTitle") or winners[0].get("question")
    if len(winners) > 1:
        log.warning("multiple winners in event %s", winners[0].get("events", [{}])[0].get("id"))
    return None


def event_rows(ev: dict, fetched_at: datetime) -> list[dict]:
    """Flatten one event into one row per bucket market."""
    mkts = ev.get("markets") or []
    end = _ts(ev.get("endDate")) or next(
        (_ts(m.get("endDate")) for m in mkts if m.get("endDate")), None
    )
    ref = end or _ts(ev.get("createdAt"))  # year reference when the title carries none
    city, day = parse_event_title(ev.get("title", ""), ev.get("slug", ""), ref)
    day = _date(ev.get("eventDate")) or day or (end.date() if end else None)
    if city:
        city = re.sub(r"\s*\([^)]*\)\s*$", "", city)  # "Seoul (Incheon)" is Seoul
    winner = pick_winner(mkts)
    rows = []
    for m in mkts:
        rules = m.get("description") or ev.get("description") or ""
        r = parse_rules(rules, m.get("resolutionSource") or ev.get("resolutionSource"))
        label = m.get("groupItemTitle") or ""
        lo, hi, unit = parse_bucket(label, m.get("question", ""))
        unit = unit or r["unit_in_rules"]
        outcomes = [str(o).lower() for o in _json_list(m.get("outcomes"))] or ["yes", "no"]
        prices = _json_list(m.get("outcomePrices"))
        tokens = _json_list(m.get("clobTokenIds"))
        yi = outcomes.index("yes") if "yes" in outcomes else 0
        rows.append(
            {
                "market_id": str(m.get("id")),
                "event_id": str(ev.get("id")),
                "condition_id": m.get("conditionId"),
                "event_slug": ev.get("slug"),
                "event_title": ev.get("title"),
                "city": city,
                "station": r["station"],
                "station_name": r["station_name"],
                "date": day,
                "unit": unit,
                "bucket_label": label or None,
                "bucket_lo": lo,
                "bucket_hi": hi,
                "question": m.get("question"),
                "rules_text": rules,
                "rules_hash": rules_hash(rules),
                "resolution_source": r["resolution_source"],
                "resolution_fallback": r["resolution_fallback"],
                "resolved_bucket": winner,
                "is_winner": bool(winner) and (label or m.get("question")) == winner,
                "yes_price_final": _num(prices[yi]) if yi < len(prices) else None,
                "uma_status": m.get("umaResolutionStatus"),
                "disputed": "disputed"
                in [str(x).lower() for x in _json_list(m.get("umaResolutionStatuses"))],
                "volume_usd": _num(m.get("volumeNum"))
                if m.get("volumeNum") is not None
                else _num(m.get("volume")),
                "liquidity_usd": _num(m.get("liquidityNum"))
                if m.get("liquidityNum") is not None
                else _num(m.get("liquidity")),
                "clob_token_yes": str(tokens[yi]) if yi < len(tokens) else None,
                "clob_token_no": str(tokens[1 - yi]) if len(tokens) > 1 - yi >= 0 else None,
                "created_at": _ts(m.get("createdAt")),
                "start_date": _ts(m.get("startDate")),
                "end_date": _ts(m.get("endDate")),
                "closed_at": _ts(m.get("closedTime")),
                "closed": bool(m.get("closed")),
                "fetched_at": fetched_at,
            }
        )
    return rows


# ------------------------------------------------------------------------------ storage
MARKETS_DDL = """
CREATE TABLE IF NOT EXISTS markets (
  market_id VARCHAR PRIMARY KEY, event_id VARCHAR, condition_id VARCHAR, event_slug VARCHAR,
  event_title VARCHAR, city VARCHAR, station VARCHAR, station_name VARCHAR, date DATE, unit VARCHAR,
  bucket_label VARCHAR, bucket_lo INTEGER, bucket_hi INTEGER, question VARCHAR, rules_text VARCHAR,
  rules_hash VARCHAR, resolution_source VARCHAR, resolution_fallback VARCHAR,
  resolved_bucket VARCHAR, is_winner BOOLEAN, yes_price_final DOUBLE, uma_status VARCHAR,
  disputed BOOLEAN,
  volume_usd DOUBLE, liquidity_usd DOUBLE, clob_token_yes VARCHAR, clob_token_no VARCHAR,
  created_at TIMESTAMP, start_date TIMESTAMP, end_date TIMESTAMP, closed_at TIMESTAMP,
  closed BOOLEAN, fetched_at TIMESTAMP
)"""
RULES_DDL = """
CREATE TABLE IF NOT EXISTS rules_history (
  market_id VARCHAR, fetched_at TIMESTAMP, rules_hash VARCHAR, rules_text VARCHAR
)"""
COLS = [
    "market_id",
    "event_id",
    "condition_id",
    "event_slug",
    "event_title",
    "city",
    "station",
    "station_name",
    "date",
    "unit",
    "bucket_label",
    "bucket_lo",
    "bucket_hi",
    "question",
    "rules_text",
    "rules_hash",
    "resolution_source",
    "resolution_fallback",
    "resolved_bucket",
    "is_winner",
    "yes_price_final",
    "uma_status",
    "disputed",
    "volume_usd",
    "liquidity_usd",
    "clob_token_yes",
    "clob_token_no",
    "created_at",
    "start_date",
    "end_date",
    "closed_at",
    "closed",
    "fetched_at",
]


def store(con: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> int:
    """Upsert markets; append to rules_history only when the hash changed. Returns #changes.

    Rows whose fetched_at is older than the stored row are ignored, so reprocessing an old raw
    dump after a newer fetch changes nothing.
    """
    con.execute(MARKETS_DDL)
    con.execute(RULES_DDL)
    con.register("incoming_all", df[COLS])
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE incoming AS
        SELECT i.* FROM incoming_all i LEFT JOIN markets m USING (market_id)
        WHERE m.market_id IS NULL OR m.fetched_at <= i.fetched_at
        """
    )
    stale = len(df) - con.execute("SELECT count(*) FROM incoming").fetchone()[0]
    if stale:
        log.warning("%d rows older than the stored data were ignored", stale)
    changed = con.execute(
        """
        SELECT i.market_id, i.fetched_at, i.rules_hash, i.rules_text,
               h.rules_hash IS NOT NULL AS is_change
        FROM incoming i
        LEFT JOIN (
          SELECT market_id, rules_hash FROM rules_history
          QUALIFY row_number() OVER (PARTITION BY market_id ORDER BY fetched_at DESC) = 1
        ) h USING (market_id)
        WHERE h.rules_hash IS NULL OR h.rules_hash <> i.rules_hash
        """
    ).df()
    n_change = int(changed["is_change"].sum()) if len(changed) else 0
    con.register("changed", changed.drop(columns=["is_change"]))
    con.execute("INSERT INTO rules_history SELECT * FROM changed")
    con.execute("INSERT OR REPLACE INTO markets SELECT * FROM incoming")
    con.unregister("incoming_all")
    con.unregister("changed")
    if n_change:
        log.warning("rules text changed for %d markets", n_change)
    return n_change


# ------------------------------------------------------------------------------- report
def build_tables(df: pd.DataFrame, min_days: int) -> dict[str, pd.DataFrame]:
    df = df.assign(date=pd.to_datetime(df["date"]))  # NaT for missing dates
    ev = (
        df.groupby("event_id")
        .agg(
            city=("city", "first"),
            station=("station", "first"),
            unit=("unit", "first"),
            date=("date", "first"),
            resolution_source=("resolution_source", "first"),
            resolution_fallback=("resolution_fallback", "first"),
            n_buckets=("market_id", "count"),
            volume_usd=("volume_usd", "sum"),
            resolved=("resolved_bucket", lambda s: s.notna().any()),
            disputed=("disputed", "any"),
            closed=("closed", "all"),
            n_stations=("station", "nunique"),
            n_sources=("resolution_source", "nunique"),
        )
        .reset_index()
    )
    ev["month"] = pd.to_datetime(ev["date"]).dt.to_period("M").astype(str)
    dup = ev.groupby(["city", "date"], dropna=False)["event_id"].transform("count") > 1
    monthly = (
        ev.groupby(["city", "station", "unit", "month", "resolution_source"], dropna=False)
        .agg(
            n_days=("date", "nunique"),
            n_resolved=("resolved", "sum"),
            volume_usd=("volume_usd", "sum"),
        )
        .reset_index()
        .sort_values(["city", "month", "resolution_source"])
    )
    eras = (
        ev.groupby(
            ["city", "station", "unit", "resolution_source", "resolution_fallback"],
            dropna=False,
        )
        .agg(first=("date", "min"), last=("date", "max"), n_days=("date", "nunique"))
        .reset_index()
        .sort_values(["city", "first"])
    )
    cities = (
        ev.groupby("city")
        .agg(
            stations=("station", lambda s: ",".join(sorted(set(x for x in s if x)))),
            unit=("unit", lambda s: ",".join(sorted(set(x for x in s if x)))),
            first=("date", "min"),
            last=("date", "max"),
            n_days=("date", "nunique"),
            n_resolved=("resolved", "sum"),
            n_disputed=("disputed", "sum"),
            volume_usd=("volume_usd", "sum"),
            sources=("resolution_source", lambda s: ",".join(sorted(set(s)))),
        )
        .reset_index()
        .sort_values(["n_days", "volume_usd", "city"], ascending=[False, False, True])
    )
    cities["enough_history"] = cities["n_days"] >= min_days
    issues = ev[
        ev["station"].isna()
        | ev["unit"].isna()
        | ev["date"].isna()
        | (ev["n_stations"] > 1)
        | (ev["n_sources"] > 1)
        | (ev["closed"] & ~ev["resolved"])
        | (ev["resolution_source"].isin(["unknown", "missing"]))
        | dup
    ]
    bad_buckets = df[df["bucket_lo"].isna() & df["bucket_hi"].isna()][
        ["market_id", "event_id", "city", "date", "bucket_label", "question"]
    ]
    ev["date"] = ev["date"].dt.date
    for frame in (eras, cities):
        frame["first"], frame["last"] = frame["first"].dt.date, frame["last"].dt.date
    return {
        "events": ev,
        "monthly": monthly,
        "eras": eras,
        "cities": cities,
        "issues": issues,
        "bad_buckets": bad_buckets,
    }


def write_report(t: dict[str, pd.DataFrame], path: Path, source: str, min_days: int) -> None:
    ev, df_c = t["events"], t["cities"]
    md = ["# Phase 0 inventory: Polymarket daily temperature markets", ""]
    md += [f"Source: {source}", ""]
    md += ["Trade history is not part of this inventory; it comes from the dataset in Phase 1.", ""]
    dates = ev["date"].dropna()
    md += [
        f"Events (city-days): {len(ev)}  |  Bucket markets: {int(ev['n_buckets'].sum())}  |  "
        f"Cities: {ev['city'].nunique()}  |  "
        f"Date range: {dates.min()} to {dates.max()}  |  "
        f"Total volume USD: {ev['volume_usd'].sum():,.0f}",
        "",
        f"## Cities (gate: enough_history = at least {min_days} event-days)",
        "",
        df_c.to_markdown(index=False, floatfmt=",.0f"),
        "",
        "## Rule eras per city (station, unit, resolution source, fallback)",
        "",
        t["eras"].to_markdown(index=False),
        "",
        "## Per city per month, grouped by resolution source",
        "",
        t["monthly"].to_markdown(index=False, floatfmt=",.0f"),
        "",
        f"## Parsing issues ({len(t['issues'])} events)",
        "",
        "Missing station/unit/date, mixed stations or sources within one event, "
        "closed but unresolved, unknown resolution source, or several events for one city-day.",
        "",
        t["issues"].drop(columns=["n_stations", "n_sources"]).to_markdown(index=False)
        if len(t["issues"])
        else "None.",
        "",
        f"## Unparsed bucket labels ({len(t['bad_buckets'])} markets)",
        "",
        t["bad_buckets"].to_markdown(index=False) if len(t["bad_buckets"]) else "None.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(md))


# --------------------------------------------------------------------------------- main
def run(
    events: list[dict],
    fetched_at: datetime,
    db: Path,
    report: Path,
    source: str,
    min_days: int,
):
    rows = [r for ev in events for r in event_rows(ev, fetched_at)]
    if not rows:
        log.error("no temperature markets found")
        return None
    df = pd.DataFrame(rows)
    db.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db))
    changed = store(con, df)
    con.close()
    tables = build_tables(df, min_days)
    write_report(tables, report, source, min_days)
    log.info(
        "%d events, %d markets, %d rules changes -> %s, %s",
        len(events),
        len(df),
        changed,
        db,
        report,
    )
    return tables


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--db", default="data/research.duckdb")
    ap.add_argument("--raw", default="data/raw", help="directory for raw Gamma event dumps")
    ap.add_argument("--report", default="reports/phase0_inventory.md")
    ap.add_argument("--from-raw", help="reprocess a raw JSONL dump instead of fetching")
    ap.add_argument("--min-days", type=int, default=90, help="event-days needed to pass the gate")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if a.from_raw:
        path = Path(a.from_raw)
        events = load_raw(path)
        try:
            fetched_at = datetime.strptime(path.stem.split("_")[-1], "%Y%m%dT%H%M%SZ")
        except ValueError:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, UTC)
            fetched_at = mtime.replace(tzinfo=None, microsecond=0)
            log.warning("no timestamp in %s; using file mtime %s", path.name, fetched_at)
        source = str(path)
    else:
        fetched_at = datetime.now(UTC).replace(tzinfo=None, microsecond=0)
        events = fetch_temperature_events(Gamma())
        path = dump_raw(events, Path(a.raw), fetched_at)
        source = f"Gamma API fetched {fetched_at:%Y-%m-%d %H:%M}Z, raw dump {path}"
    tables = run(events, fetched_at, Path(a.db), Path(a.report), source, a.min_days)
    if tables is None:
        return 1
    print(tables["cities"].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
