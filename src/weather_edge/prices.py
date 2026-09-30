"""Phase 1 data: CLOB price history for every bucket market of the Phase 0 inventory.

GET clob.polymarket.com/prices-history for each YES token at --fidelity minutes between the
market's creation and its close (or now for open markets). Old markets return nothing without an
explicit window (checked 2026-09-29). Rows go to the table prices_history in its own DuckDB file (a
snapshot of the markets table is copied in on first run); markets already stored are skipped,
so the script can be rerun after an interruption.

Usage: python -m weather_edge.prices [--fidelity 5] [--limit N]
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import duckdb
import pandas as pd
import requests

CLOB_URL = "https://clob.polymarket.com/prices-history"
DDL = "CREATE TABLE IF NOT EXISTS prices_history (market_id VARCHAR, ts TIMESTAMP, price DOUBLE)"
log = logging.getLogger("phase1_prices")


def fetch_history(
    session, token: str, start: datetime, end: datetime, fidelity: int, retries=6
) -> list[dict]:
    params = {
        "market": token,
        "startTs": int(start.timestamp()),
        "endTs": int(end.timestamp()),
        "fidelity": fidelity,
    }
    for attempt in range(retries):
        try:
            r = session.get(CLOB_URL, params=params, timeout=60)
        except requests.RequestException as e:
            log.warning("request error (attempt %d): %s", attempt + 1, e)
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 200:
            return r.json().get("history") or []
        wait = 5 * (attempt + 1) if r.status_code == 429 else 2 * (attempt + 1)
        log.warning("HTTP %s for token %s... (attempt %d)", r.status_code, token[:12], attempt + 1)
        time.sleep(wait)
    log.error("giving up on token %s after %d attempts", token[:12], retries)
    return []


def pending(con) -> pd.DataFrame:
    con.execute(DDL)
    return con.execute(
        """
        SELECT market_id, clob_token_yes AS token, created_at, closed_at, end_date FROM markets
        WHERE clob_token_yes IS NOT NULL
          AND market_id NOT IN (SELECT DISTINCT market_id FROM prices_history)
        ORDER BY date DESC, market_id
        """
    ).df()


def window(row, now: datetime) -> tuple[datetime, datetime]:
    """Creation minus 1h to close plus 1h. Without a close time: 36h after the market's end date,
    else 4 days after creation. The endpoint rejects windows of several months."""
    start = row.created_at.to_pydatetime().replace(tzinfo=UTC) - timedelta(hours=1)
    if pd.notna(row.closed_at):
        end = row.closed_at.to_pydatetime().replace(tzinfo=UTC) + timedelta(hours=1)
    elif pd.notna(row.end_date):
        end = row.end_date.to_pydatetime().replace(tzinfo=UTC) + timedelta(hours=36)
    else:
        end = start + timedelta(days=4)
    return start, min(end, now)


def run(con, session, fidelity, pause, limit, now=None, workers=8) -> int:
    """Fetch pending markets with a thread pool; insert in the caller's thread every 200 markets."""
    now = now or datetime.now(UTC)
    todo = pending(con)
    if limit:
        todo = todo.head(limit)
    log.info("%d markets to fetch with %d workers", len(todo), workers)

    def one(row):
        start, end = window(row, now)
        hist = fetch_history(session, row.token, start, end, fidelity)
        time.sleep(pause)
        rows = [
            (row.market_id, datetime.fromtimestamp(h["t"], UTC).replace(tzinfo=None), float(h["p"]))
            for h in hist
        ]
        return rows or [(row.market_id, None, None)]  # remember empty markets: no endless retries

    buf, total = [], 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, rows in enumerate(pool.map(one, todo.itertuples(), chunksize=4), 1):
            buf += rows
            if i % 200 == 0 or i == len(todo):
                frame = pd.DataFrame(buf, columns=["market_id", "ts", "price"])
                con.register("buf", frame)  # bulk insert; executemany was the bottleneck
                con.execute("INSERT INTO prices_history SELECT * FROM buf")
                con.unregister("buf")
                total += len(buf)
                buf = []
                log.info("%d/%d markets, %d rows stored", i, len(todo), total)
    return total


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--db", default="data/prices.duckdb", help="own file: the research DB stays free"
    )
    ap.add_argument("--markets-db", default="data/research.duckdb")
    ap.add_argument("--fidelity", type=int, default=5, help="minutes between points")
    ap.add_argument("--pause", type=float, default=0.1, help="seconds between requests")
    ap.add_argument("--limit", type=int, help="fetch at most this many markets (for a trial run)")
    ap.add_argument("--workers", type=int, default=8, help="concurrent requests")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    con = duckdb.connect(a.db)
    if not con.execute(
        "SELECT count(*) FROM duckdb_tables() WHERE table_name = 'markets'"
    ).fetchone()[0]:
        con.execute(f"ATTACH '{a.markets_db}' AS src (READ_ONLY)")
        con.execute(
            "CREATE TABLE markets AS SELECT market_id, clob_token_yes, created_at, closed_at, "
            "end_date, date FROM src.markets"
        )
        con.execute("DETACH src")
    session = requests.Session()
    session.headers.update({"User-Agent": "polymarket-weather-edge/phase1"})
    n = run(con, session, a.fidelity, a.pause, a.limit, workers=a.workers)
    con.close()
    log.info("done, %d rows stored", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
