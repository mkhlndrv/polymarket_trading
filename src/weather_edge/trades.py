"""On-chain fills for the inventory markets, from the SII-WANGZJ/Polymarket_data dataset.

The dataset is 36 GB, so it is streamed one row group at a time and only rows whose market is in the
inventory are kept. The check at the end is what makes the fills usable as a fill model later: per
closed market, the sum of fill sizes has to match Gamma's volume, which is a share count and not a
dollar amount.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from weather_edge import config

HF_PATH = "datasets/SII-WANGZJ/Polymarket_data/trades.parquet"
COLS = [
    "timestamp",
    "block_number",
    "transaction_hash",
    "log_index",
    "market_id",
    "condition_id",
    "maker",
    "taker",
    "price",
    "usd_amount",
    "token_amount",
    "maker_direction",
    "taker_direction",
    "nonusdc_side",
    "asset_id",
]
log = logging.getLogger("phase1_trades")


def filter_group(tbl: pa.Table, ids: set[str]) -> pa.Table:
    """Rows of one row group whose market_id is in ids."""
    mask = pc.is_in(tbl["market_id"], value_set=pa.array(sorted(ids), pa.string()))
    return tbl.filter(mask)


def stream(pf: pq.ParquetFile, ids: set[str], out: Path, since_ts: int) -> tuple[int, int]:
    """Write matching rows of every row group ending after since_ts. Returns (groups read, rows)."""
    md = pf.metadata
    ti = [md.schema.column(i).name for i in range(md.num_columns)].index("timestamp")
    groups = []
    for g in range(md.num_row_groups):
        st = md.row_group(g).column(ti).statistics
        if st is None or not st.has_min_max or st.max >= since_ts:
            groups.append(g)
    log.info("%d of %d row groups end after the cutoff", len(groups), md.num_row_groups)
    out.parent.mkdir(parents=True, exist_ok=True)
    writer, rows = None, 0
    for n, g in enumerate(groups, 1):
        part = filter_group(pf.read_row_group(g, columns=COLS), ids)
        if writer is None:
            writer = pq.ParquetWriter(out, part.schema, compression="zstd")
        if part.num_rows:
            writer.write_table(part)
            rows += part.num_rows
        if n % 50 == 0 or n == len(groups):
            log.info("%d/%d groups, %d rows kept", n, len(groups), rows)
    if writer is not None:
        writer.close()
    return len(groups), rows


def load(con: duckdb.DuckDBPyConnection, path: Path) -> int:
    con.execute(
        f"""
        CREATE OR REPLACE TABLE trades AS
        SELECT to_timestamp(timestamp)::TIMESTAMP AS ts, block_number, transaction_hash, log_index,
               market_id, condition_id, maker, taker, price, usd_amount, token_amount,
               maker_direction, taker_direction, nonusdc_side, asset_id
        FROM read_parquet('{path}') ORDER BY ts, log_index
        """
    )
    return con.execute("SELECT count(*) FROM trades").fetchone()[0]


def check(con: duckdb.DuckDBPyConnection, until: str) -> dict:
    """Share volume per market vs Gamma volume, for closed markets whose day ends before `until`."""
    r = (
        con.execute(
            f"""
        WITH v AS (SELECT market_id, sum(token_amount) shares FROM trades GROUP BY 1)
        SELECT count(*) AS markets, count(v.market_id) AS with_trades,
               quantile_cont(v.shares / m.volume_usd, 0.5) AS median_ratio,
               avg((abs(v.shares - m.volume_usd) <= 0.01 * m.volume_usd)::int) AS share_within_1pct
        FROM markets m LEFT JOIN v USING (market_id)
        WHERE m.closed AND m.date < DATE '{until}' AND m.volume_usd > 0
        """
        )
        .df()
        .iloc[0]
    )
    return {k: (float(x) if x == x else None) for k, x in r.items()}


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--db", default=str(config.RESEARCH_DB))
    ap.add_argument("--out", default=str(config.TRADES))
    ap.add_argument(
        "--since", default="2025-01-20", help="skip row groups that end before this UTC date"
    )
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from huggingface_hub import HfFileSystem

    con = duckdb.connect(a.db, read_only=True)
    ids = {r[0] for r in con.execute("SELECT market_id FROM markets").fetchall()}
    con.close()  # the DB stays free while the stream runs
    since_ts = int(datetime.fromisoformat(a.since).replace(tzinfo=UTC).timestamp())
    with HfFileSystem().open(HF_PATH, "rb") as f:
        groups, rows = stream(pq.ParquetFile(f), ids, Path(a.out), since_ts)
    con = duckdb.connect(a.db)
    n = load(con, Path(a.out))
    result = check(con, "2026-07-20")
    con.close()
    log.info("%d groups read, %d rows written, %d rows loaded; check: %s", groups, rows, n, result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
