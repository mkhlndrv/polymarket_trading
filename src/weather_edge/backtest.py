"""Phase 7: backtest of the two-days-out EMOS signal with fills taken from the trade tape.

Signal: phase5_model EMOS at lead 3 (decision at --decision-hours local, two days before the day).
Orders (maker only, 5 shares, resting LIFE_H hours), only on buckets with a market price at the decision:
  buy YES at min(last price - 1c, p_model - EDGE) when p_model - last price >= EDGE
  buy NO  at min(1 - last price - 1c, 1 - p_model - EDGE) when last price - p_model >= EDGE
Fills from the dataset fills (table trades, complete through 2026-04, about 80% coverage after):
  touch    a taker print at or through the order price in the window fills min(size, printed volume)
  through  only prints strictly beyond the price count (the whole level was cleared, so a resting
           order there was filled whatever its queue position)
  *_haircut  the same with winning fills halved (fills are more likely when the model is wrong)
Maker fee zero, rebates ignored. PnL per share = outcome - price for YES, (1 - outcome) - price for NO.
Holdout from 2026-08-01 excluded (the tape ends 2026-07-20 anyway).

Usage: python -m weather_edge.backtest --stations KLGA --decision-hours 6 12
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from weather_edge.model import md, run_station
from weather_edge.pilot_nyc import bootstrap_ci

EDGE, TICK, SHARES, LIFE_H = 0.10, 0.01, 5, 24
LEAD = 3
FILL_MODELS = ["touch", "through", "touch_haircut", "through_haircut"]
log = logging.getLogger("phase7")


def orders_from_signal(scored: pd.DataFrame) -> pd.DataFrame:
    """One order per bucket and side where the model disagrees with the last price by EDGE or more."""
    s = scored.dropna(subset=["p_emos", "market_p"])
    yes = s[s.p_emos - s.market_p >= EDGE].assign(
        side="yes", price=lambda d: np.minimum(d.market_p - TICK, d.p_emos - EDGE)
    )
    no = s[s.market_p - s.p_emos >= EDGE].assign(
        side="no", price=lambda d: np.minimum(1 - d.market_p - TICK, 1 - d.p_emos - EDGE)
    )
    o = pd.concat([yes, no], ignore_index=True)
    o = o[(o.price >= 0.02) & (o.price <= 0.98)].copy()
    o["price"] = (o.price * 100).round() / 100  # whole cents
    o["t_start"] = pd.to_datetime(o.t)
    o["t_end"] = o.t_start + pd.Timedelta(hours=LIFE_H)
    o["expected_pnl_share"] = np.where(o.side == "yes", o.p_emos - o.price, 1 - o.p_emos - o.price)
    o = o.sort_values(["day", "market_id", "side"]).reset_index(drop=True)
    o["order_id"] = np.arange(len(o))
    cols = [
        "order_id",
        "market_id",
        "day",
        "lead",
        "t_start",
        "t_end",
        "side",
        "price",
        "market_p",
        "p_emos",
        "outcome",
        "expected_pnl_share",
    ]
    return o[cols]


def fills_from_tape(con, orders: pd.DataFrame) -> pd.DataFrame:
    """Per order: printed taker volume at or through the price (touch) and strictly beyond it (through)."""
    if orders.empty:
        return orders.assign(
            touch_volume=0.0, through_volume=0.0, touch_ts=pd.NaT, through_ts=pd.NaT
        )
    con.register(
        "orders_tmp", orders[["order_id", "market_id", "t_start", "t_end", "side", "price"]]
    )
    f = con.execute(
        """
        WITH tr AS (
          SELECT t.market_id, t.ts, t.token_amount AS shares,
                 CASE WHEN t.nonusdc_side = 'token1' THEN t.price ELSE 1 - t.price END AS yes_price,
                 (t.taker_direction = 'BUY') = (t.nonusdc_side = 'token1') AS taker_long_yes
          FROM trades t WHERE t.market_id IN (SELECT DISTINCT market_id FROM orders_tmp)),
        j AS (
          SELECT o.order_id, tr.ts, tr.shares,
                 CASE WHEN o.side = 'yes' THEN NOT tr.taker_long_yes AND tr.yes_price <= o.price + 1e-9
                      ELSE tr.taker_long_yes AND tr.yes_price >= 1 - o.price - 1e-9 END AS touch,
                 CASE WHEN o.side = 'yes' THEN NOT tr.taker_long_yes AND tr.yes_price < o.price - 1e-9
                      ELSE tr.taker_long_yes AND tr.yes_price > 1 - o.price + 1e-9 END AS through
          FROM orders_tmp o JOIN tr ON tr.market_id = o.market_id AND tr.ts > o.t_start AND tr.ts <= o.t_end)
        SELECT order_id,
               coalesce(sum(shares) FILTER (WHERE touch), 0) AS touch_volume,
               coalesce(sum(shares) FILTER (WHERE through), 0) AS through_volume,
               min(ts) FILTER (WHERE touch) AS touch_ts, min(ts) FILTER (WHERE through) AS through_ts
        FROM j GROUP BY 1
        """
    ).df()
    con.unregister("orders_tmp")
    out = orders.merge(f, on="order_id", how="left")
    out[["touch_volume", "through_volume"]] = out[["touch_volume", "through_volume"]].fillna(0.0)
    return out


def score_fills(o: pd.DataFrame) -> pd.DataFrame:
    """Filled shares and PnL per order under each fill model."""
    o = o.copy()
    won = np.where(o.side == "yes", o.outcome == 1, o.outcome == 0)
    pnl_share = np.where(o.side == "yes", o.outcome - o.price, (1 - o.outcome) - o.price)
    for m in FILL_MODELS:
        vol = o.through_volume if m.startswith("through") else o.touch_volume
        filled = np.minimum(SHARES, vol)
        if m.endswith("haircut"):
            filled = np.where(won, filled * 0.5, filled)
        o[f"filled_{m}"] = filled
        o[f"pnl_{m}"] = filled * pnl_share
    o["won"] = won
    o["pnl_share"] = pnl_share
    return o


def summarize(o: pd.DataFrame, by: str | None = None) -> pd.DataFrame:
    rows = []
    groups = [(None, o)] if by is None else list(o.groupby(by))
    for key, g in groups:
        for m in FILL_MODELS:
            filled = g[f"filled_{m}"]
            pnl = g[f"pnl_{m}"]
            has = filled > 0
            per_share = pnl.sum() / filled.sum() if filled.sum() > 0 else np.nan
            ci = bootstrap_ci(pnl[has], g.day[has]) if has.sum() >= 5 else (np.nan, np.nan)
            rows.append(
                {
                    **({} if by is None else {by: key}),
                    "fill_model": m,
                    "orders": len(g),
                    "orders_filled": int(has.sum()),
                    "filled_shares": float(filled.sum()),
                    "pnl_usd": float(pnl.sum()),
                    "pnl_c_per_share": 100 * per_share,
                    "pnl_usd_per_order_ci_low": ci[0],
                    "pnl_usd_per_order_ci_high": ci[1],
                    "win_rate_filled": float(g.won[has].mean()) if has.any() else np.nan,
                    "expected_c_per_share_filled": 100 * float(g.expected_pnl_share[has].mean())
                    if has.any()
                    else np.nan,
                    "capacity_shares": float(
                        (g.through_volume if m.startswith("through") else g.touch_volume).sum()
                    ),
                }
            )
    return pd.DataFrame(rows)


def run(con, station: str, hour: int) -> dict:
    r = run_station(con, station, hour, leads=[LEAD])
    scored = r["scored"]
    scored = scored[scored.lead == LEAD]
    orders = orders_from_signal(scored)
    o = score_fills(fills_from_tape(con, orders))
    o["month"] = pd.to_datetime(o.day).dt.strftime("%Y-%m")
    return {
        "orders": o,
        "signal_buckets": len(scored),
        "total": summarize(o),
        "by_side": summarize(o, "side"),
        "by_month": summarize(o[o.side.notna()], "month").query("fill_model == 'through'"),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--db", default="data/research.duckdb")
    ap.add_argument("--prices", default="data/prices.duckdb")
    ap.add_argument("--forecasts", default="data/forecasts.duckdb")
    ap.add_argument("--stations", nargs="+", default=["KLGA"])
    ap.add_argument("--decision-hours", type=int, nargs="+", default=[6, 12])
    ap.add_argument("--report", default="reports/phase7_backtest.md")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    con = duckdb.connect(a.db, read_only=True)
    con.execute("SET enable_progress_bar=false")
    con.execute(f"ATTACH '{a.prices}' AS px (READ_ONLY)")
    con.execute(f"ATTACH '{a.forecasts}' AS fc (READ_ONLY)")
    parts = [
        "# Phase 7: lead-3 EMOS backtest with tape fills",
        "",
        __doc__.split("Usage:")[0].strip(),
        "",
    ]
    for st, hour in ((st, h) for st in a.stations for h in a.decision_hours):
        r = run(con, st, hour)
        parts += [
            f"## {st}, decision {hour:02d}:00 local two days before",
            "",
            f"Scored buckets with a market price at the decision: {r['signal_buckets']}; orders: {len(r['orders'])}.",
            "",
            "### All orders",
            "",
            md(r["total"]),
            "",
            "### By side",
            "",
            md(r["by_side"]),
            "",
            "### By month, through fills (the tape is complete through 2026-04, about 80% after)",
            "",
            md(r["by_month"]),
            "",
        ]
        print(st, hour, "orders", len(r["orders"]))
        print(r["total"].to_string(index=False))
        print(r["by_side"].to_string(index=False))
        print(r["by_month"].to_string(index=False))
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    Path(a.report).write_text("\n".join(parts))
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
