"""The target: the highest displayed value per station and local day, market day or not.

The maximum over a day's reports of the T-group tenths when present, else the whole METAR degree, in
Celsius. Models train on this continuous value and convert to the market's unit and rounding only
when scoring, which keeps one label definition for Fahrenheit and Celsius cities.
"""

from __future__ import annotations

import sys

import duckdb
import pandas as pd

from weather_edge import config
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
    con = duckdb.connect(str(config.RESEARCH_DB))
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
