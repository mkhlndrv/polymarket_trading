"""Known-answer checks for the Phase 3 rebuild."""

from datetime import date

import duckdb
import pandas as pd

import weather_edge.observations as p3


def test_metar_temperature_parsing_and_rounding():
    assert p3.parse_metar_temps(
        "KLGA 200051Z 14009KT 10SM SCT045 19/12 A3016 RMK AO2 SLP213 T01940122 $"
    ) == (19, 19.4)
    assert p3.parse_metar_temps("RJTT 200000Z 35019KT 9999 FEW030 09/M01 Q1007") == (9, None)
    assert p3.parse_metar_temps("EGLC 200020Z AUTO 17003KT 110V240 9999 OVC036 M03/M05 Q1019") == (
        -3,
        None,
    )
    assert p3.parse_metar_temps(
        "KORD 010051Z 00000KT 10SM CLR M01/M03 A3030 RMK AO2 T10171028"
    ) == (-1, -1.7)
    assert p3.parse_metar_temps("KXXX 010051Z 23004KT 10SM 22/ A3030") == (
        22,
        None,
    )  # missing dew point
    assert (p3.c_to_f(19), p3.c_to_f(19.4), p3.c_to_f(23), p3.c_to_f(24), p3.c_to_f(22.5)) == (
        66,
        67,
        73,
        75,
        73,
    )
    assert p3.round_half_up(2.5) == 3 and p3.round_half_up(-2.5) == -2
    assert (
        p3.iem_station("KLGA") == "LGA"
        and p3.iem_station("EGLC") == "EGLC"
        and p3.iem_station("KBKF") == "BKF"
    )


def test_fetch_iem_requests_an_exclusive_end_after_dec_31(tmp_path):
    class _S:
        def get(self, url, params=None, timeout=None):
            self.params = params

            class R:
                status_code, text = 200, "station,valid,tmpf,metar\n"

            return R()

    s = _S()
    p3.fetch_iem(s, "KLGA", 2025, tmp_path)
    assert (s.params["year2"], s.params["month2"], s.params["day2"]) == (2026, 1, 1)
    assert s.params["station"] == "LGA" and (tmp_path / "KLGA_2025.csv").exists()


def test_parse_iem_csv():
    text = (
        "station,valid,tmpf,metar\n"
        "LGA,2026-09-20 00:51,67.00,KLGA 200051Z 14009KT 19/12 A3016 RMK AO2 T01940122\n"
        "LGA,2026-09-20 01:51,,KLGA 200151Z 12012KT ///// A3016\n"
    )
    df = p3.parse_iem_csv(text, "KLGA")
    assert len(df) == 2 and df.iloc[0]["temp_c_whole"] == 19 and df.iloc[0]["temp_c_tenths"] == 19.4
    assert pd.isna(df.iloc[1]["temp_c_whole"]) and pd.isna(df.iloc[1]["tmpf_iem"])
    assert p3.parse_iem_csv("Too many requests", "KLGA").empty


def _db(tmp_path):
    con = duckdb.connect(str(tmp_path / "r.duckdb"))
    con.execute(
        "CREATE TABLE markets (event_id VARCHAR, city VARCHAR, station VARCHAR, date DATE, unit VARCHAR, "
        "resolution_source VARCHAR, bucket_lo INTEGER, bucket_hi INTEGER, resolved_bucket VARCHAR, is_winner BOOLEAN, closed BOOLEAN)"
    )
    # NYC 2026-09-20 (EDT = UTC-4): winner 66-67F. London 2026-02-25 (GMT): winner 13C. HK: 33C.
    con.execute(
        """INSERT INTO markets VALUES
        ('e1', 'NYC', 'KLGA', DATE '2026-09-20', 'F', 'noaa_wrh', 66, 67, '66-67°F', true, true),
        ('e2', 'London', 'EGLC', DATE '2026-02-25', 'C', 'wunderground', 13, 13, '13°C', true, true),
        ('e3', 'Hong Kong', 'HKO', DATE '2026-03-16', 'C', 'hko', 33, 33, '33°C', true, true)"""
    )
    return con


def test_rebuild_local_day_and_transforms(tmp_path):
    con = _db(tmp_path)
    obs = [
        # NYC: 2026-09-20 local day = 04:00Z 09-20 to 04:00Z 09-21. A 23C SPECI at 19:30Z (73F whole,
        # 74F from T2350 tenths); routine :51 reports reach 22.8C -> whole 22 -> 72F, tenths 73F.
        (
            "KLGA",
            "2026-09-20 03:51",
            "KLGA 200351Z 25/12 RMK T02500120",
        ),  # 23:51 local on 09-19: excluded
        ("KLGA", "2026-09-20 18:51", "KLGA 201851Z 22/12 RMK T02280120"),
        ("KLGA", "2026-09-20 19:30", "KLGA 201930Z 23/12 RMK T02350120"),  # SPECI
        ("KLGA", "2026-09-20 20:51", "KLGA 202051Z 22/12 RMK T02170120"),
        ("KLGA", "2026-09-21 03:51", "KLGA 210351Z 20/12 RMK T02000120"),  # 23:51 local: included
        (
            "KLGA",
            "2026-09-21 04:51",
            "KLGA 210451Z 30/12 RMK T03000120",
        ),  # 00:51 local 09-21: excluded
        ("EGLC", "2026-02-25 13:20", "EGLC 251320Z 13/05 Q1010"),
        ("EGLC", "2026-02-25 13:50", "EGLC 251350Z 12/05 Q1010"),
    ]
    df = pd.DataFrame(
        [
            {
                "station": s,
                "obs_time_utc": pd.Timestamp(t),
                "raw": r,
                "temp_c_whole": p3.parse_metar_temps(r)[0],
                "temp_c_tenths": p3.parse_metar_temps(r)[1],
                "tmpf_iem": None,
            }
            for s, t, r in obs
        ]
    )
    con.register("obs_in", df)
    con.execute("CREATE TABLE observations AS SELECT * FROM obs_in")
    p3.rebuild(con)
    t = con.execute(
        "SELECT event_id, n_obs, whole, tenths, routine, match_whole, match_tenths, match_routine, "
        "strftime(t_max_local, '%H:%M'), tenths_routine FROM truth ORDER BY event_id"
    ).fetchall()
    # the 15:30 local SPECI (23C) is the day's peak: whole 73F, tenths 74F; routine reports peak at 72F
    assert t[0] == (
        "e1",
        4,
        73,
        74,
        72,
        False,
        False,
        False,
        "15:30",
        73,
    )  # 66-67F resolved: all miss
    assert t[1] == ("e2", 2, 13, 13, 13, True, True, True, "13:20", 13)
    hko = p3.hko_truth(con, pd.DataFrame([{"date": date(2026, 3, 16), "max_c": 33.6}]))
    assert bool(hko.iloc[0]["match_floor"]) and not bool(hko.iloc[0]["match_round"])
    tables = p3.summary_tables(con)
    assert tables["by_era_unit"]["n_events"].sum() == 2 and len(tables["mismatches"]) == 1
    assert tables["peak_time"].set_index("city").loc["NYC", "share_before_06"] == 0
    con.close()
