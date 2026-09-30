"""Known-answer checks for the open GRIB extractor."""

from datetime import date, datetime

import duckdb
import numpy as np
import pytest

import weather_edge.forecasts as fo


def test_byte_range_from_both_index_formats():
    ecmwf = '{"param": "msl", "_offset": 0, "_length": 10}\n{"param": "2t", "levtype": "sfc", "_offset": 1000, "_length": 650000}\n'
    assert fo.byte_range("ecmwf", ecmwf) == (1000, 650000)
    gfs = "1:0:d=2025011500:PRMSL:mean sea level:12 hour fcst:\n2:995180:d=2025011500:TMP:2 m above ground:12 hour fcst:\n3:1878000:d=2025011500:RH:2 m above ground:12 hour fcst:\n"
    assert fo.byte_range("gfs", gfs) == (995180, 1878000 - 995180)
    assert fo.byte_range("gfs", "1:0:d=2025011500:TMP:2 m above ground:12 hour fcst:\n") == (
        0,
        -1,
    )  # last message: open range
    assert fo.byte_range("ecmwf", '{"param": "msl", "_offset": 0, "_length": 10}\n') is None
    gefs = (
        "9:3000000:d=2025011500:RH:2 m above ground:12 hour fcst:ens mean\n"
        "10:4006880:d=2025011500:TMP:2 m above ground:12 hour fcst:ens mean\n"
        "11:4900000:d=2025011500:DPT:2 m above ground:12 hour fcst:ens mean\n"
    )
    assert fo.byte_range("gefs_mean", gefs) == (4006880, 4900000 - 4006880)
    from datetime import date

    assert (
        fo.SOURCES["gefs_spread"]["url"]
        .format(d=date(2025, 1, 15), c=6, s=12)
        .endswith("gefs.20250115/06/atmos/pgrb2sp25/gespr.t06z.pgrb2s.0p25.f012")
    )


def _synthetic_field():
    """A 0.25 deg global GRIB2 field whose value is 250 + lat + lon/10 K, built with ecCodes samples."""
    import eccodes

    gid = eccodes.codes_grib_new_from_samples("regular_ll_sfc_grib2")
    ni, nj = 1440, 721
    for k, v in (
        ("Ni", ni),
        ("Nj", nj),
        ("latitudeOfFirstGridPointInDegrees", 90),
        ("longitudeOfFirstGridPointInDegrees", 0),
        ("latitudeOfLastGridPointInDegrees", -90),
        ("longitudeOfLastGridPointInDegrees", 359.75),
        ("iDirectionIncrementInDegrees", 0.25),
        ("jDirectionIncrementInDegrees", 0.25),
        ("jScansPositively", 0),
    ):
        eccodes.codes_set(gid, k, v)
    lats = 90 - 0.25 * np.arange(nj)
    lons = 0.25 * np.arange(ni)
    field = 250 + lats[:, None] + lons[None, :] / 10
    eccodes.codes_set_values(gid, field.ravel())
    blob = eccodes.codes_get_message(gid)
    eccodes.codes_release(gid)
    return blob


def test_decode_and_bilinear_interpolation():
    k, vals = fo.decode(_synthetic_field())
    assert (k["Ni"], k["Nj"], k["jScansPositively"]) == (1440, 721, 0)
    # the field is linear, so bilinear interpolation is exact: 250 + lat + lon/10 - 273.15
    assert fo.interpolate(k, vals, 40.77945, -73.88027) == pytest.approx(
        250 + 40.77945 + (360 - 73.88027) / 10 - 273.15, abs=0.01
    )
    assert fo.interpolate(k, vals, 51.505, 0.055) == pytest.approx(
        250 + 51.505 + 0.0055 - 273.15, abs=0.01
    )
    assert fo.interpolate(k, vals, -33.965, 18.602) == pytest.approx(
        250 - 33.965 + 1.8602 - 273.15, abs=0.01
    )


class _Resp:
    def __init__(self, status, text="", content=b"", headers=None):
        self.status_code, self.text, self.content, self.headers = (
            status,
            text,
            content,
            headers or {},
        )


class _Session:
    def __init__(self, blob):
        self.blob, self.calls = blob, []

    def get(self, url, headers=None, timeout=None):
        self.calls.append((url, headers or {}))
        if "20250116" in url:
            return _Resp(404)
        if url.endswith(".index"):
            return _Resp(
                200, text=f'{{"param": "2t", "_offset": 7, "_length": {len(self.blob)}}}\n'
            )
        rng = headers["Range"]
        assert rng == f"bytes=7-{7 + len(self.blob) - 1}"
        return _Resp(
            206, content=self.blob, headers={"Last-Modified": "Wed, 15 Jan 2025 08:37:17 GMT"}
        )


def test_fetch_step_rows_and_availability_and_missing():
    s = _Session(_synthetic_field())
    coords = {"KLGA": (40.77945, -73.88027), "EGLC": (51.505, 0.055)}
    status, rows, avail = fo.fetch_step(s, "ecmwf", datetime(2025, 1, 15, 0), 12, coords)
    assert status == "ok" and avail == datetime(2025, 1, 15, 8, 37, 17) and len(rows) == 2
    r = {x["station"]: x for x in rows}["KLGA"]
    assert (r["init_time"], r["valid_time"], r["lead_h"], r["available_time"]) == (
        datetime(2025, 1, 15),
        datetime(2025, 1, 15, 12),
        12,
        avail,
    )
    assert r["temp_c"] == pytest.approx(250 + 40.77945 + (360 - 73.88027) / 10 - 273.15, abs=0.01)
    assert fo.fetch_step(s, "ecmwf", datetime(2025, 1, 16, 0), 12, coords)[0] == "missing"


def test_plan_and_run_are_resumable(tmp_path, monkeypatch):
    monkeypatch.setattr(fo.time, "sleep", lambda _s: None)
    con = duckdb.connect(str(tmp_path / "f.duckdb"))
    from datetime import date

    tasks = fo.plan(con, ["ecmwf"], [0], date(2025, 1, 15), date(2025, 1, 16), max_step=6, step_h=3)
    assert len(tasks) == 2 * 3  # two days, steps 0, 3, 6
    s = _Session(_synthetic_field())
    ok, missing = fo.run(con, s, tasks, {"KLGA": (40.78, -73.88)}, workers=2, batch=2)
    assert (ok, missing) == (3, 3)  # the 16th is missing
    assert con.execute("SELECT count(*) FROM forecasts").fetchone()[0] == 3
    assert con.execute("SELECT count(*) FROM forecast_runs").fetchone()[0] == 6
    assert (
        fo.plan(con, ["ecmwf"], [0], date(2025, 1, 15), date(2025, 1, 16), 6, 3) == []
    )  # nothing left
    con.close()


def test_spread_fields_keep_kelvin_differences():
    """A spread field is a difference: the Kelvin offset must not be subtracted."""
    blob = _synthetic_field()

    class _S:
        def get(self, url, headers=None, timeout=None):
            if url.endswith(".idx"):
                return _Resp(
                    200, text="1:7:d=2025011500:TMP:2 m above ground:12 hour fcst:ens std dev\n"
                )
            return _Resp(
                206, content=blob, headers={"Last-Modified": "Wed, 15 Jan 2025 03:40:10 GMT"}
            )

    coords = {"KLGA": (40.77945, -73.88027)}
    _, rows_t, _ = fo.fetch_step(_S(), "gefs_mean", datetime(2025, 1, 15), 12, coords)
    _, rows_s, _ = fo.fetch_step(_S(), "gefs_spread", datetime(2025, 1, 15), 12, coords)
    assert rows_s[0]["temp_c"] - rows_t[0]["temp_c"] == pytest.approx(273.15, abs=1e-6)


def test_ecmwf_stream_switch_and_retry_missing(tmp_path):
    assert "/scda/20250105180000-3h-scda-fc" in fo.step_url("ecmwf", datetime(2025, 1, 5, 18), 3)
    assert "/oper/20260512060000-3h-oper-fc" in fo.step_url("ecmwf", datetime(2026, 5, 12, 6), 3)
    assert "/oper/20250105000000-72h-oper-fc" in fo.step_url("ecmwf", datetime(2025, 1, 5, 0), 72)
    assert fo.step_url("gfs", datetime(2025, 1, 5, 6), 3).endswith("gfs.t06z.pgrb2.0p25.f003")
    con = duckdb.connect(str(tmp_path / "f.duckdb"))
    fo.plan(con, ["ecmwf"], [6], date(2025, 1, 1), date(2025, 1, 1), 3, 3)
    con.execute(
        "INSERT INTO forecast_runs VALUES ('ecmwf', TIMESTAMP '2025-01-01 06:00', 0, 'ok', now()), "
        "('ecmwf', TIMESTAMP '2025-01-01 06:00', 3, 'missing', now())"
    )
    assert fo.plan(con, ["ecmwf"], [6], date(2025, 1, 1), date(2025, 1, 1), 3, 3) == []
    assert fo.plan(con, ["ecmwf"], [6], date(2025, 1, 1), date(2025, 1, 1), 3, 3, True) == [
        ("ecmwf", datetime(2025, 1, 1, 6), 3)
    ]
    con.close()


def test_nbm_index_fields_steps_and_nearest_point():
    idx = (
        "69:60000000:d=2026060106:TMP:2 m above ground:18 hour fcst:\n"
        "70:63894715:d=2026060106:TMAX:2 m above ground:6-18 hour max fcst:\n"
        "71:66171512:d=2026060106:TMAX:2 m above ground:6-18 hour max fcst:ens std dev\n"
        "72:68000000:d=2026060106:TMIN:2 m above ground:6-18 hour min fcst:\n"
    )
    assert fo.byte_range("nbm_tmax", idx) == (63894715, 66171512 - 63894715)
    assert fo.byte_range("nbm_tmax_spread", idx) == (66171512, 68000000 - 66171512)
    assert fo.byte_range("gfs", idx) == (60000000, 63894715 - 60000000)
    con = duckdb.connect()
    tasks = fo.plan(con, ["nbm_tmax", "gfs"], [6], date(2025, 1, 1), date(2025, 1, 1), 6, 3)
    assert [s for m, i, s in tasks if m == "nbm_tmax"] == [18, 42, 66]
    assert [s for m, i, s in tasks if m == "gfs"] == [0, 3, 6]
    assert fo.step_url("nbm_tmax", datetime(2026, 6, 1, 6), 18).endswith(
        "blend.t06z.core.f018.co.grib2"
    )
    # a tiny projected grid: 2 x 3 points, station between two of them, one station far away
    k = {
        "gridType": "lambert",
        "sig": ("lambert", 3, 2, 40.0, -75.0),
        "lats": np.array([40.0, 40.0, 40.0, 40.02, 40.02, 40.02]),
        "lons": np.array([285.0, 285.02, 285.04, 285.0, 285.02, 285.04]),  # 0-360 convention
    }
    vals = np.array([280.0, 281.0, 282.0, 283.0, 284.0, 285.0])
    fo._NEAREST.clear()
    assert fo.interpolate(k, vals, 40.019, -74.979) == pytest.approx(284.0 - 273.15)
    assert np.isnan(fo.interpolate(k, vals, 51.5, -0.1))  # London is off the CONUS grid
    k2 = {"gridType": "lambert", "sig": k["sig"]}  # later messages carry no coordinates: cache hit
    assert fo.interpolate(k2, vals + 1, 40.019, -74.979) == pytest.approx(285.0 - 273.15)
    assert np.isnan(fo.interpolate(k2, vals, 51.5, -0.1))
