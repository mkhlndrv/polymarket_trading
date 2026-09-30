"""Known-answer checks for phase0_inventory.

tests/fixtures/gamma_events_sample.jsonl holds three real Gamma events (from public dumps):
Seoul 2025-12-31 (Weather Underground era, partial fields, no groupItemTitle, slug without
year), London 2026-02-25 (Weather Underground era, one resolved NO bucket) and NYC 2026-09-02
(NOAA weather.gov era, 11 open buckets).
"""

import json
from datetime import date, datetime
from pathlib import Path

import duckdb
import pandas as pd
import pytest
import requests

import weather_edge.markets as p

FIXTURE = Path(__file__).parent / "fixtures" / "gamma_events_sample.jsonl"


@pytest.fixture(scope="module")
def events():
    return p.load_raw(FIXTURE)


@pytest.fixture(scope="module")
def by_city(events):
    return {p.parse_event_title(e["title"])[0]: e for e in events}


def test_parse_rules_real_noaa_text(by_city):
    m = by_city["NYC"]["markets"][0]
    r = p.parse_rules(m["description"], m["resolutionSource"])
    assert r["station"] == "KLGA"
    assert r["resolution_source"] == "noaa_wrh"
    assert r["resolution_fallback"] == "wunderground"
    assert r["station_name"] == "LaGuardia Airport Station"
    assert r["unit_in_rules"] == "F"
    # the lowercase site code in the description alone is enough
    assert p.parse_rules(m["description"])["station"] == "KLGA"


def test_parse_rules_real_wu_text(by_city):
    m = by_city["London"]["markets"][0]
    r = p.parse_rules(m["description"], m["resolutionSource"])
    assert (r["station"], r["resolution_source"], r["resolution_fallback"]) == (
        "EGLC",
        "wunderground",
        None,
    )
    assert r["station_name"] == "London City Airport Station"
    assert r["unit_in_rules"] == "C"
    seoul = by_city["Seoul"]
    assert p.parse_rules(seoul["description"], seoul["resolutionSource"])["station"] == "RKSI"


@pytest.mark.parametrize(
    "text,station,source,fallback",
    [
        # Hong Kong data lives under weather.gov.hk, which must not read as NOAA weather.gov
        ("https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather", "HKO", "hko", None),
        # a WU URL with a date segment, and a 4-letter city segment that is not the station
        (
            "https://www.wunderground.com/history/daily/it/rome/LIRF/date/2024-8-15",
            "LIRF",
            "wunderground",
            None,
        ),
        ("https://www.wunderground.com/history/daily/pe/lima/SPJC.", "SPJC", "wunderground", None),
        # (NOAA) is not a station code; aviationweather.gov is METAR, not the weather.gov series
        (
            "recorded by NOAA (NOAA) at Haneda Airport (RJTT); the NOAA time series",
            "RJTT",
            "noaa_wrh",
            None,
        ),
        (
            "METAR for Vnukovo (UUWW) at https://aviationweather.gov/data/metar/?id=UUWW",
            "UUWW",
            "metar",
            None,
        ),
        (
            "https://www.weather.gov/wrh/timeseries?site=klga; else https://aviationweather.gov",
            "KLGA",
            "noaa_wrh",
            "metar",
        ),
        (
            "per NOAA at https://forecast.weather.gov/data/obhistory/KLGA.html",
            "KLGA",
            "noaa_other",
            None,
        ),
        (
            "Israel Meteorological Service at https://ims.gov.il/en/data_gov (station 225)",
            None,
            "ims",
            None,
        ),
        # earliest WU-era US markets (Dec 2025) cite the current-weather page, not the history path
        (
            "recorded at the Dallas Love Field Station in degrees Fahrenheit on 4 Dec '25. ... "
            "information from Wunderground ... available here: https://www.wunderground.com/weather/KDAL.",
            "KDAL",
            "wunderground",
            None,
        ),
        # Taipei resolves on Taiwan's Central Weather Administration station 46692
        (
            "recorded by Taipei's Central Weather Administration in degrees Celsius on 16 Mar '26. "
            "available here: https://www.cwa.gov.tw/V8/C/W/OBS_Station.html?ID=46692",
            "CWA46692",
            "cwa",
            None,
        ),
        (
            "Meteo-France AEROWEB at https://aviation.meteo.fr for Le Bourget (LFPB)",
            "LFPB",
            "meteo_france",
            None,
        ),
    ],
)
def test_parse_rules_sources_and_station_traps(text, station, source, fallback):
    r = p.parse_rules(text)
    assert (r["station"], r["resolution_source"], r["resolution_fallback"]) == (
        station,
        source,
        fallback,
    )


def test_parse_rules_empty_and_unknown():
    assert p.parse_rules("")["resolution_source"] == "missing"
    assert p.parse_rules("Resolves per the city website.")["resolution_source"] == "unknown"


@pytest.mark.parametrize(
    "label,expected",
    [
        ("69°F or below", (None, 69, "F")),
        ("74-75°F", (74, 75, "F")),
        ("74–75°F", (74, 75, "F")),
        ("88°F or higher", (88, None, "F")),
        ("15°C or below", (None, 15, "C")),
        ("18°C", (18, 18, "C")),
        ("-3°C", (-3, -3, "C")),
        ("-1°C or higher", (-1, None, "C")),
        ("-3°C to -2°C", (-3, -2, "C")),
        ("70ºF or lower", (None, 70, "F")),
        ("70F or below", (None, 70, "F")),
    ],
)
def test_parse_bucket(label, expected):
    assert p.parse_bucket(label) == expected


@pytest.mark.parametrize(
    "question,expected",
    [
        (
            "Will the highest temperature in New York City be between 74-75°F on September 2?",
            (74, 75, "F"),
        ),
        (
            "Will the highest temperature in New York City be 88°F or higher on September 2?",
            (88, None, "F"),
        ),
        (
            "Will the highest temperature in New York City be 69°F or below on September 2?",
            (None, 69, "F"),
        ),
        ("Will the highest temperature in London be 18°C on February 25?", (18, 18, "C")),
        ("Will the highest temperature in Seoul be -3°C on December 31?", (-3, -3, "C")),
        ("no numbers here", (None, None, None)),
    ],
)
def test_parse_bucket_question_fallback(question, expected):
    assert p.parse_bucket("", question) == expected
    assert p.parse_bucket(None, question) == expected


def test_parse_event_title_year_sources():
    assert p.parse_event_title(
        "Highest temperature in NYC on September 2?",
        "highest-temperature-in-nyc-on-september-2-2026",
    ) == ("NYC", date(2026, 9, 2))
    assert p.parse_event_title("Highest temperature in NYC on September 2, 2026?", "") == (
        "NYC",
        date(2026, 9, 2),
    )
    # no year anywhere: pick the year closest to endDate, across the new-year boundary
    assert p.parse_event_title(
        "Highest temperature in Seoul on December 31?", "", datetime(2026, 1, 2)
    ) == ("Seoul", date(2025, 12, 31))
    assert p.parse_event_title("Highest temperature in Seoul on December 31?", "") == (
        "Seoul",
        None,
    )
    assert p.parse_event_title("Lowest temperature in NYC on May 1?", "") == (None, None)


def test_parse_event_title_month_abbreviations_and_bad_slug_year():
    # abbreviated month (Jan 2025 London markets), and a slug with a wrong year loses to endDate
    assert p.parse_event_title(
        "Highest temperature in London on Jan 22?",
        "highest-temperature-in-london-on-jan-22",
        datetime(2025, 1, 22, 12),
    ) == ("London", date(2025, 1, 22))
    assert p.parse_event_title(
        "Highest temperature in London on Jan 26?",
        "highest-temperature-in-london-on-jan-26-2024",
        datetime(2025, 1, 26, 12),
    ) == ("London", date(2025, 1, 26))
    assert p.parse_event_title("Highest temperature in NYC on Sept 2?", "x-2026") == (
        "NYC",
        date(2026, 9, 2),
    )


def test_timestamps():
    assert p._ts("2026-02-25 17:08:38+00") == datetime(2026, 2, 25, 17, 8, 38)
    assert p._ts("2026-08-31T07:55:58.773165Z") == datetime(2026, 8, 31, 7, 55, 58, 773165)
    assert p._ts(None) is None and p._ts("garbage") is None
    assert p._date("2026-09-02") == date(2026, 9, 2) and p._date(None) is None


def test_pick_winner(by_city):
    assert p.pick_winner(by_city["NYC"]["markets"]) is None  # open event
    assert p.pick_winner(by_city["London"]["markets"]) is None  # only a NO bucket in the dump
    win = p.pick_winner(by_city["Seoul"]["markets"])
    assert win == "Will the highest temperature in Seoul be -1°C or higher on December 31?"


def test_event_rows_known_answers(by_city):
    rows = {r["bucket_label"]: r for r in p.event_rows(by_city["NYC"], datetime(2026, 9, 29))}
    assert len(rows) == 11
    r = rows["74-75°F"]
    assert (r["city"], r["station"], r["unit"], r["date"]) == ("NYC", "KLGA", "F", date(2026, 9, 2))
    assert (r["bucket_lo"], r["bucket_hi"]) == (74, 75)
    assert (r["resolution_source"], r["resolution_fallback"]) == ("noaa_wrh", "wunderground")
    assert r["market_id"] == "4021608" and r["event_id"] == "940515"
    assert r["clob_token_yes"].startswith("4334963252") and r["yes_price_final"] == 0.28
    assert r["volume_usd"] == pytest.approx(821.78655) and r["closed"] is False
    assert r["created_at"] == datetime(2026, 8, 31, 7, 55, 58, 773165)
    assert (
        rows["69°F or below"]["bucket_lo"] is None and rows["88°F or higher"]["bucket_hi"] is None
    )
    seoul = p.event_rows(by_city["Seoul"], datetime(2026, 9, 29))
    assert [(x["bucket_lo"], x["bucket_hi"], x["is_winner"]) for x in seoul] == [
        (-3, -3, False),
        (-2, -2, False),
        (-1, None, True),
    ]
    assert seoul[0]["date"] == date(2025, 12, 31) and seoul[0]["unit"] == "C"
    london = p.event_rows(by_city["London"], datetime(2026, 9, 29))[0]
    assert (
        london["closed_at"] == datetime(2026, 2, 25, 17, 8, 38)
        and london["uma_status"] == "resolved"
    )
    assert london["date"] == date(2026, 2, 25) and london["is_winner"] is False


def test_run_end_to_end(tmp_path, events):
    db, report = tmp_path / "r.duckdb", tmp_path / "report.md"
    t = p.run(events, datetime(2026, 9, 29, 20), db, report, "test", min_days=1)
    con = duckdb.connect(str(db))
    assert con.execute("SELECT count(*) FROM markets").fetchone()[0] == 15
    assert con.execute("SELECT count(*) FROM rules_history").fetchone()[0] == 15
    assert con.execute("SELECT count(*) FROM markets WHERE is_winner").fetchone()[0] == 1
    assert con.execute("SELECT count(*) FROM markets WHERE station IS NULL").fetchone()[0] == 0
    con.close()
    cities = t["cities"].set_index("city")
    assert list(cities.index) == ["London", "NYC", "Seoul"]  # ties on n_days sort by volume
    assert cities["n_days"].tolist() == [1, 1, 1]
    assert cities.loc["London", "volume_usd"] == pytest.approx(99995.334101)
    assert cities.loc["NYC", "volume_usd"] == pytest.approx(6545.176017, rel=1e-3)
    assert cities.loc["NYC", "sources"] == "noaa_wrh" and cities.loc["Seoul", "stations"] == "RKSI"
    assert cities["enough_history"].all()
    monthly = t["monthly"].set_index(["city", "month", "resolution_source"])
    assert monthly.loc[("NYC", "2026-09", "noaa_wrh"), "n_days"] == 1
    assert monthly.loc[("London", "2026-02", "wunderground"), "n_resolved"] == 0
    assert monthly.loc[("Seoul", "2025-12", "wunderground"), "n_resolved"] == 1
    assert len(t["eras"]) == 3 and len(t["bad_buckets"]) == 0
    # the London dump holds one NO bucket of a closed event: flagged as closed but unresolved
    assert t["issues"]["event_id"].tolist() == ["227949"]
    text = report.read_text()
    assert "## Per city per month" in text and "KLGA" in text and "EGLC" in text


def test_main_from_raw(tmp_path):
    raw = tmp_path / "gamma_events_20260929T200000Z.jsonl"
    raw.write_text(FIXTURE.read_text())
    db, report = tmp_path / "r.duckdb", tmp_path / "rep.md"
    rc = p.main(
        ["--from-raw", str(raw), "--db", str(db), "--report", str(report), "--min-days", "5"]
    )
    assert rc == 0 and report.exists()
    con = duckdb.connect(str(db))
    assert con.execute("SELECT max(fetched_at) FROM markets").fetchone()[0] == datetime(
        2026, 9, 29, 20
    )
    con.close()


def test_dump_raw_round_trip(tmp_path, events):
    path = p.dump_raw(events, tmp_path / "raw", datetime(2026, 9, 29, 20, 0, 0))
    assert path.name == "gamma_events_20260929T200000Z.jsonl"
    assert p.load_raw(path) == events


def test_store_detects_rules_change(tmp_path, by_city):
    con = duckdb.connect(str(tmp_path / "x.duckdb"))
    ev = json.loads(json.dumps(by_city["NYC"]))
    df = pd.DataFrame(p.event_rows(ev, datetime(2026, 9, 1)))
    assert p.store(con, df) == 0
    ev["markets"][0]["description"] += " Amended."
    df2 = pd.DataFrame(p.event_rows(ev, datetime(2026, 9, 2)))
    assert p.store(con, df2) == 1
    assert con.execute("SELECT count(*) FROM rules_history").fetchone()[0] == 12
    assert con.execute("SELECT count(*) FROM markets").fetchone()[0] == 11
    assert p.store(con, df2) == 0
    con.close()


class _Resp:
    def __init__(self, data, status=200):
        self._d, self.status_code = data, status

    def json(self):
        return self._d


class _Session:
    """Stub of requests.Session for GET /events/keyset with pages of 2.

    title_search serves every event whose title holds the phrase. tag weather serves Seoul,
    NYC and a rain event (London carries no tag, so it is found only via the title).
    London is closed, the others are open.
    """

    headers = {}

    def __init__(self, evs):
        self.ev = {e["id"]: e for e in evs}
        self.rain = {
            "id": "5",
            "title": "Will it rain in NYC on May 1?",
            "slug": "rain",
            "markets": [],
        }
        self.calls = []

    def listing(self, params):
        if params.get("title_search"):
            return [e for e in self.ev.values() if params["title_search"] in e["title"].lower()]
        if params.get("tag_slug") == "weather":
            return [self.ev["130716"], self.ev["940515"], self.rain]
        return []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, dict(params or {})))
        assert url.endswith("/events/keyset")
        closed = params["closed"] == "true"
        src = [e for e in self.listing(params) if (e["id"] == "227949") == closed]
        off = int(params.get("after_cursor", "c0")[1:])
        page = src[off : off + params["limit"]]
        nxt = f"c{off + len(page)}" if off + len(page) < len(src) else None
        return _Resp({"events": page, "next_cursor": nxt})


def test_fetch_pages_filters_and_dedupes(monkeypatch, events, caplog):
    monkeypatch.setattr(p.time, "sleep", lambda _s: None)
    s = _Session(events)
    got = p.fetch_temperature_events(p.Gamma(session=s, page=2))
    assert [e["id"] for e in got] == ["130716", "227949", "940515"]
    tag_open = [
        c[1].get("after_cursor")
        for c in s.calls
        if c[1].get("tag_slug") and c[1]["closed"] == "false"
    ]
    assert tag_open == [None, "c2"]  # three open events: a full page, then the cursor page
    assert "1 events only via title search" in caplog.text


# ----------------------------------------------------------------- review follow-ups
def _second_nyc_day(nyc):
    ev = json.loads(json.dumps(nyc))
    ev["id"], ev["eventDate"], ev["endDate"] = "940516", "2026-09-03", "2026-09-03T12:00:00Z"
    ev["title"], ev["slug"] = (
        "Highest temperature in NYC on September 3?",
        "highest-temperature-in-nyc-on-september-3-2026",
    )
    for m in ev["markets"]:
        m["id"] = str(int(m["id"]) + 1000)
        m["endDate"] = "2026-09-03T12:00:00Z"
    return ev


def test_tables_count_days_within_a_city_month(by_city):
    nyc, nyc2 = by_city["NYC"], _second_nyc_day(by_city["NYC"])
    rows = p.event_rows(nyc, datetime(2026, 9, 29)) + p.event_rows(nyc2, datetime(2026, 9, 29))
    t = p.build_tables(pd.DataFrame(rows), 2)
    monthly = t["monthly"].set_index(["city", "month", "resolution_source"])
    assert len(monthly) == 1 and monthly.loc[("NYC", "2026-09", "noaa_wrh"), "n_days"] == 2
    assert monthly.loc[("NYC", "2026-09", "noaa_wrh"), "volume_usd"] == pytest.approx(
        2 * 6545.176017, rel=1e-3
    )
    era = t["eras"].iloc[0]
    assert (era["first"], era["last"], era["n_days"]) == (date(2026, 9, 2), date(2026, 9, 3), 2)
    city = t["cities"].iloc[0]
    assert city["n_days"] == 2 and bool(city["enough_history"])
    assert not p.build_tables(pd.DataFrame(rows), 3)["cities"]["enough_history"].any()


def test_gate_flag_false_below_min_days(tmp_path, events):
    t = p.run(events, datetime(2026, 9, 29, 20), tmp_path / "r.duckdb", tmp_path / "r.md", "t", 2)
    assert t["cities"]["n_days"].tolist() == [1, 1, 1] and not t["cities"]["enough_history"].any()
    cities_section = (tmp_path / "r.md").read_text().split("## Rule eras")[0]
    assert "True" not in cities_section and cities_section.count("False") == 3


def test_pick_winner_ignores_open_market_near_one(by_city):
    ev = json.loads(json.dumps(by_city["NYC"]))
    ev["markets"][0]["outcomePrices"] = '["0.995", "0.005"]'
    assert ev["markets"][0]["closed"] is False
    assert p.pick_winner(ev["markets"]) is None
    rows = p.event_rows(ev, datetime(2026, 9, 29))
    assert not any(r["is_winner"] for r in rows) and rows[0]["resolved_bucket"] is None


def test_event_without_date_is_flagged_not_fatal(tmp_path, by_city):
    ev = json.loads(json.dumps(by_city["Seoul"]))
    del ev["eventDate"]
    for m in ev["markets"]:
        del m["endDate"]
    rows = p.event_rows(ev, datetime(2026, 9, 29)) + p.event_rows(
        by_city["NYC"], datetime(2026, 9, 29)
    )
    assert rows[0]["date"] is None
    t = p.build_tables(pd.DataFrame(rows), 1)
    assert t["issues"]["event_id"].tolist() == ["130716"]
    assert t["cities"].set_index("city").loc["NYC", "first"] == date(2026, 9, 2)
    p.write_report(t, tmp_path / "r.md", "t", 1)
    assert "130716" in (tmp_path / "r.md").read_text()


def test_disputed_flag_from_uma_trail(by_city):
    ev = json.loads(json.dumps(by_city["London"]))
    row = p.event_rows(ev, datetime(2026, 9, 29))[0]
    assert row["uma_status"] == "resolved" and row["disputed"] is False
    ev["markets"][0]["umaResolutionStatuses"] = '["proposed", "disputed", "resolved"]'
    rows = p.event_rows(ev, datetime(2026, 9, 29)) + p.event_rows(
        by_city["NYC"], datetime(2026, 9, 29)
    )
    assert rows[0]["disputed"] is True
    cities = p.build_tables(pd.DataFrame(rows), 1)["cities"].set_index("city")
    assert cities.loc["London", "n_disputed"] == 1 and cities.loc["NYC", "n_disputed"] == 0


def test_store_ignores_older_dump(tmp_path, by_city):
    con = duckdb.connect(str(tmp_path / "x.duckdb"))
    ev = json.loads(json.dumps(by_city["NYC"]))
    newer = pd.DataFrame(p.event_rows(ev, datetime(2026, 9, 2)))
    assert p.store(con, newer) == 0
    ev["markets"][0]["description"] += " Older wording."
    older = pd.DataFrame(p.event_rows(ev, datetime(2026, 9, 1)))
    assert p.store(con, older) == 0
    assert con.execute("SELECT count(*) FROM rules_history").fetchone()[0] == 11
    assert con.execute("SELECT min(fetched_at) FROM markets").fetchone()[0] == datetime(2026, 9, 2)
    con.close()


def test_main_fetch_path_dumps_raw_and_reprocesses(tmp_path, monkeypatch, events):
    monkeypatch.setattr(p, "fetch_temperature_events", lambda gamma: events)
    args = [
        "--db",
        str(tmp_path / "a.duckdb"),
        "--raw",
        str(tmp_path / "raw"),
        "--report",
        str(tmp_path / "a.md"),
    ]
    assert p.main(args + ["--min-days", "1"]) == 0
    dumps = list((tmp_path / "raw").glob("gamma_events_*Z.jsonl"))
    assert len(dumps) == 1 and p.load_raw(dumps[0]) == events
    assert f"raw dump {dumps[0]}" in (tmp_path / "a.md").read_text()
    assert (
        p.main(
            [
                "--from-raw",
                str(dumps[0]),
                "--db",
                str(tmp_path / "b.duckdb"),
                "--report",
                str(tmp_path / "b.md"),
            ]
        )
        == 0
    )


def test_main_exit_codes_and_untimestamped_dump(tmp_path):
    raw = tmp_path / "gamma_events_20260101T000000Z.jsonl"
    raw.write_text(json.dumps({"id": "1", "title": "Will it rain?", "markets": []}) + "\n")
    assert (
        p.main(
            [
                "--from-raw",
                str(raw),
                "--db",
                str(tmp_path / "d.duckdb"),
                "--report",
                str(tmp_path / "r.md"),
            ]
        )
        == 1
    )
    assert not (tmp_path / "r.md").exists()
    renamed = tmp_path / "dump.jsonl"
    renamed.write_text(FIXTURE.read_text())
    assert (
        p.main(
            [
                "--from-raw",
                str(renamed),
                "--db",
                str(tmp_path / "e.duckdb"),
                "--report",
                str(tmp_path / "e.md"),
            ]
        )
        == 0
    )


class _FlakySession(_Session):
    """Raises once per distinct request, then behaves normally."""

    def __init__(self, evs):
        super().__init__(evs)
        self.failed = set()

    def get(self, url, params=None, timeout=None):
        key = (url, json.dumps(params, sort_keys=True))
        if key not in self.failed:
            self.failed.add(key)
            raise requests.ConnectionError("boom")
        return super().get(url, params, timeout)


class _NoTagSession(_Session):
    """Title and tag routes return nothing; a plain listing serves everything."""

    def listing(self, params):
        if params.get("title_search") or params.get("tag_slug"):
            return []
        return [*self.ev.values(), self.rain]


def test_fetch_retries_transient_errors_and_raises_on_persistent_ones(monkeypatch, events):
    monkeypatch.setattr(p.time, "sleep", lambda _s: None)
    got = p.fetch_temperature_events(p.Gamma(session=_FlakySession(events), page=2))
    assert [e["id"] for e in got] == ["130716", "227949", "940515"]

    class _Down:
        headers = {}

        def get(self, url, params=None, timeout=None):
            return _Resp(None, status=500)

    with pytest.raises(RuntimeError):
        p.fetch_temperature_events(p.Gamma(session=_Down(), page=2))


def test_fetch_falls_back_to_full_scan(monkeypatch, events, caplog):
    monkeypatch.setattr(p.time, "sleep", lambda _s: None)
    got = p.fetch_temperature_events(p.Gamma(session=_NoTagSession(events), page=2))
    assert [e["id"] for e in got] == ["130716", "227949", "940515"]
    assert "scanning all events" in caplog.text


def test_rules_text_outranks_resolution_source_field(by_city):
    noaa_text = by_city["NYC"]["markets"][0]["description"]
    r = p.parse_rules(noaa_text, "https://www.wunderground.com/history/daily/cn/shenzhen/zgsz")
    assert (r["resolution_source"], r["resolution_fallback"], r["station"]) == (
        "noaa_wrh",
        "wunderground",
        "KLGA",
    )
    # a field URL still supplies station and source when the text states neither
    r = p.parse_rules(
        "Resolves on the highest temperature of the day.",
        "https://www.wunderground.com/history/daily/kr/incheon/RKSI",
    )
    assert (r["resolution_source"], r["station"]) == ("wunderground", "RKSI")


def test_event_date_fallbacks_and_city_suffix(by_city):
    ev = json.loads(json.dumps(by_city["London"]))
    ev["title"] = "Highest temperature in DC on Inauguration Day?"
    ev["slug"], ev["eventDate"], ev["endDate"] = (
        "highest-temperature-in-dc",
        None,
        "2025-01-20T12:00:00Z",
    )
    row = p.event_rows(ev, datetime(2026, 9, 29))[0]
    assert (row["city"], row["date"]) == ("DC", date(2025, 1, 20))
    ev["title"], ev["slug"] = (
        "Highest temperature in NYC on May 9?",
        "highest-temperature-in-nyc-on-may-8-625",
    )
    ev["endDate"], ev["createdAt"] = None, "2025-05-07T07:52:33Z"
    for m in ev["markets"]:
        m["endDate"] = None
    assert p.event_rows(ev, datetime(2026, 9, 29))[0]["date"] == date(2025, 5, 9)
    ev["title"] = "Highest temperature in Seoul (Incheon) on May 9?"
    assert p.event_rows(ev, datetime(2026, 9, 29))[0]["city"] == "Seoul"


def test_duplicate_city_day_counts_once_and_is_flagged(by_city):
    nyc, dup = by_city["NYC"], json.loads(json.dumps(by_city["NYC"]))
    dup["id"], dup["slug"] = "999", "arch-" + dup["slug"]
    for m in dup["markets"]:
        m["id"] = "9" + m["id"]
    rows = p.event_rows(nyc, datetime(2026, 9, 29)) + p.event_rows(dup, datetime(2026, 9, 29))
    t = p.build_tables(pd.DataFrame(rows), 1)
    assert t["cities"].iloc[0]["n_days"] == 1 and t["monthly"].iloc[0]["n_days"] == 1
    assert sorted(t["issues"]["event_id"]) == ["940515", "999"]
