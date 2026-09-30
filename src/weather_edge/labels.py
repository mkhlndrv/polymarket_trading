"""Phase 5 labels: the daily displayed high for every station and local day, market day or not.

From the IEM observations table (Phase 3): per station and local clock day, the maximum over reports
of the T-group tenths when present, else the whole-degree METAR value, in degrees C. Models train on
this continuous target in C and are converted to each market's display unit at scoring time.
Writes the table daily_truth (station, day, max_c, n_obs, t_max_local) in the research DB.

Usage: python -m weather_edge.labels
"""

from __future__ import annotations

import sys

import duckdb
import pandas as pd

from weather_edge.market_checks import STATION_TZ


def build_daily_truth(con: duckdb.DuckDBPyConnection) -> int:
    con.register("tz_map", pd.DataFrame(list(STATION_TZ.items()), columns=["station", "tz"]))
    con.execute(
        """
        CREATE OR REPLACE TABLE daily_truth AS
        WITH o AS (
          SELECT o.station, coalesce(o.temp_c_tenths, o.temp_c_whole) AS c,
                 ((o.obs_time_utc AT TIME ZONE 'UTC') AT TIME ZONE t.tz) AS local_time
          FROM observations o JOIN tz_map t USING (station) WHERE o.temp_c_whole IS NOT NULL)
        SELECT station, local_time::DATE AS day, max(c) AS max_c, count(*) AS n_obs,
               arg_max(local_time, c) AS t_max_local
        FROM o GROUP BY 1, 2 HAVING count(*) >= 12
        ORDER BY 1, 2
        """
    )
    con.unregister("tz_map")
    return con.execute("SELECT count(*) FROM daily_truth").fetchone()[0]


def main(argv=None):
    con = duckdb.connect("data/research.duckdb")
    n = build_daily_truth(con)
    chk = (
        con.execute(
            """
        SELECT count(*) AS market_days, avg((abs(d.max_c * 9 / 5 + 32 - t.tenths) < 1)::int) AS within_1F
        FROM truth t JOIN daily_truth d ON d.station = t.station AND d.day = t.date
        WHERE t.unit = 'F' AND t.n_obs > 0
        """
        )
        .df()
        .iloc[0]
    )
    con.close()
    print(
        f"daily_truth rows: {n}; F market days matched within 1F of the Phase 3 label: {chk.within_1F:.4f} of {int(chk.market_days)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
