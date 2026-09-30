"""Paper trading of the two-days-out strategy against live books. No real orders.

At noon local, two days before each market day, the model is fitted on the trailing window and
post-only paper orders are placed where it disagrees with the book by 10c or more. Fills are inferred
from taker prints and from the book crossing the price, and PnL is computed per fill rule after
resolution. The point of running it is the one thing the backtest cannot measure: adverse selection
against a live book.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb
import numpy as np
import pandas as pd
import requests

import weather_edge.forecasts as fo
import weather_edge.markets as p0
import weather_edge.model as p5
from weather_edge import config
from weather_edge.collector import (
    CLOB_BOOKS,
    FIXED_COORDS,
    METAR_URL,
    Store,
    alert,
    market_rows,
    now_utc,
    station_coords,
)
from weather_edge.labels import build_daily_truth
from weather_edge.market_checks import STATION_TZ
from weather_edge.observations import parse_metar_temps

EDGE, TICK, SHARES, LIFE_H = 0.10, 0.01, 5, 24
LEAD, DECISION_HOUR = 3, 12
MODELS = ["ecmwf", "gfs", "gefs_mean", "gefs_spread"]
TRADES_URL = "https://data-api.polymarket.com/trades"
PUBLISH_H = {"ecmwf": 9, "gfs": 5, "gefs_mean": 5, "gefs_spread": 5}  # wait this long after init
INTERVALS = {
    "markets": 600,
    "labels": 3600,
    "forecasts": 1800,
    "decide": 60,
    "fills": 120,
    "resolve": 3600,
    "report": 3600,
    "flush": 900,
}
ORDER_COLS = [
    "order_id",
    "placed_at",
    "station",
    "day",
    "market_id",
    "condition_id",
    "token_yes",
    "token_no",
    "unit",
    "lo",
    "hi",
    "side",  # 'sell_yes' (buy NO) or 'buy_yes'
    "price",  # in YES terms
    "size",
    "p_model",
    "mu_c",
    "sigma_c",
    "nu",
    "scale",
    "mid",
    "best_bid",
    "best_ask",
    "expires_at",
    "status",  # open, expired, resolved
    "touch_volume",
    "through_volume",
    "book_filled",
    "first_touch",
    "first_through",
    "outcome",
]
log = logging.getLogger("paper")


# ------------------------------------------------------------------------------ pure logic
def bucket_probs(row: pd.Series, buckets: pd.DataFrame) -> np.ndarray:
    """Model probability per bucket row (lo, hi, unit) from a walk_forward row."""
    out = []
    for _, b in buckets.iterrows():
        mu, sg = p5.to_unit(row.emos_mu, row.emos_sigma, b.unit)
        out.append(p5.bucket_prob_floor(mu, sg, -np.inf, b.lo, b.hi, row.emos_nu))
    return np.array(out)


def make_orders(
    buckets: pd.DataFrame, probs: np.ndarray, books: dict[str, dict], row: pd.Series, t: datetime
) -> list[dict]:
    """Paper orders for one event. buckets: market rows; books: token_yes -> {bid, ask}."""
    orders = []
    for (_, b), p in zip(buckets.iterrows(), probs, strict=True):
        bk = books.get(b.token_yes)
        if not bk or bk.get("bid") is None or bk.get("ask") is None:
            continue
        bid, ask = float(bk["bid"]), float(bk["ask"])
        mid = (bid + ask) / 2
        side = price = None
        if mid - p >= EDGE:  # market too high: sell YES
            price = max(mid + TICK, p + EDGE)
            if price <= bid:  # would cross: stay one tick above the best bid, if still an edge
                price = bid + TICK
            if price >= p + EDGE:
                side = "sell_yes"
        elif p - mid >= EDGE:  # market too low: buy YES
            price = min(mid - TICK, p - EDGE)
            if price >= ask:
                price = ask - TICK
            if price <= p - EDGE:
                side = "buy_yes"
        if side is None:
            continue
        price = round(price, 3)
        if not 0.01 <= price <= 0.99:
            continue
        orders.append(
            {
                "order_id": f"{b.market_id}-{t:%Y%m%d%H%M}-{side}",
                "placed_at": t,
                "station": b.station,
                "day": pd.Timestamp(b.date),
                "market_id": b.market_id,
                "condition_id": b.condition_id,
                "token_yes": b.token_yes,
                "token_no": b.token_no,
                "unit": b.unit,
                "lo": b.lo,
                "hi": b.hi,
                "side": side,
                "price": price,
                "size": SHARES,
                "p_model": float(p),
                "mu_c": float(row.emos_mu),
                "sigma_c": float(row.emos_sigma),
                "nu": float(row.emos_nu),
                "scale": float(row.get("emos_scale", 1.0)),
                "mid": mid,
                "best_bid": bid,
                "best_ask": ask,
                "expires_at": t + timedelta(hours=LIFE_H),
                "status": "open",
                "touch_volume": 0.0,
                "through_volume": 0.0,
                "book_filled": 0.0,
                "first_touch": pd.NaT,
                "first_through": pd.NaT,
                "outcome": np.nan,
            }
        )
    return orders


def apply_prints(order: dict, trades: list[dict]) -> dict:
    """Update touch and through volumes from taker prints (data-api rows) since placement."""
    o = dict(order)
    placed = pd.Timestamp(o["placed_at"])
    expires = pd.Timestamp(o["expires_at"])
    for tr in trades:
        ts = pd.Timestamp(datetime.fromtimestamp(int(tr["timestamp"]), UTC).replace(tzinfo=None))
        if ts <= placed or ts > expires:
            continue
        price, size, side, asset = (
            float(tr["price"]),
            float(tr["size"]),
            tr["side"],
            str(tr["asset"]),
        )
        if asset == str(o["token_yes"]):
            yes_price, taker_long_yes = price, side == "BUY"
        elif asset == str(o["token_no"]):
            yes_price, taker_long_yes = 1 - price, side == "SELL"
        else:
            continue
        if o["side"] == "sell_yes":  # our ask lifts when a taker buys YES at or above it
            touch = taker_long_yes and yes_price >= o["price"] - 1e-9
            through = taker_long_yes and yes_price > o["price"] + 1e-9
        else:
            touch = (not taker_long_yes) and yes_price <= o["price"] + 1e-9
            through = (not taker_long_yes) and yes_price < o["price"] - 1e-9
        if touch:
            o["touch_volume"] = float(o["touch_volume"]) + size
            if pd.isna(o["first_touch"]) or ts < o["first_touch"]:
                o["first_touch"] = ts
        if through:
            o["through_volume"] = float(o["through_volume"]) + size
            if pd.isna(o["first_through"]) or ts < o["first_through"]:
                o["first_through"] = ts
    return o


def apply_book(order: dict, bid: float | None, ask: float | None) -> dict:
    """Book rule: a resting ask is lifted when the best bid reaches it, a bid hit when the ask falls to it."""
    o = dict(order)
    if o["side"] == "sell_yes" and bid is not None and bid >= o["price"] - 1e-9:
        o["book_filled"] = float(o["size"])
    if o["side"] == "buy_yes" and ask is not None and ask <= o["price"] + 1e-9:
        o["book_filled"] = float(o["size"])
    return o


def pnl_per_share(side: str, price: float, outcome: float) -> float:
    return outcome - price if side == "buy_yes" else price - outcome


def summarize(orders: pd.DataFrame) -> pd.DataFrame:
    rows = []
    done = orders[orders.status == "resolved"]
    for station, g in [("all", orders)] + list(orders.groupby("station")):
        d = done if station == "all" else done[done.station == station]
        for rule in ("touch", "through", "book"):
            filled = (
                np.minimum(d["size"], d[f"{rule}_volume"]) if rule != "book" else d["book_filled"]
            )
            pps = np.array(
                [pnl_per_share(s, p, o) for s, p, o in zip(d.side, d.price, d.outcome, strict=True)]
            )
            pnl = filled * pps if len(d) else pd.Series(dtype=float)
            exp = np.where(d.side == "buy_yes", d.p_model - d.price, d.price - d.p_model)
            has = filled > 0
            rows.append(
                {
                    "station": station,
                    "rule": rule,
                    "orders": len(g),
                    "open": int((g.status == "open").sum()),
                    "resolved": len(d),
                    "orders_filled": int(has.sum()),
                    "filled_shares": float(filled.sum()),
                    "pnl_usd": float(pnl.sum()),
                    "pnl_c_per_share": 100 * pnl.sum() / filled.sum() if filled.sum() else np.nan,
                    "expected_c_per_share_filled": 100 * float(exp[has].mean())
                    if has.any()
                    else np.nan,
                    "win_rate_filled": float((pps[has] > 0).mean()) if has.any() else np.nan,
                }
            )
    return pd.DataFrame(rows)


def local_now(tz: str, t: datetime | None = None) -> datetime:
    return (t or now_utc()).replace(tzinfo=UTC).astimezone(ZoneInfo(tz)).replace(tzinfo=None)


def due_decisions(
    stations: list[str], decided: list, t: datetime | None = None
) -> list[tuple[str, date]]:
    """(station, day) pairs whose decision window (DECISION_HOUR local, first 30 min) is open now
    and not yet taken; day = local today + LEAD - 1."""
    t = t or now_utc()
    out = []
    for st in stations:
        now_l = local_now(STATION_TZ[st], t)
        if now_l.hour == DECISION_HOUR and now_l.minute < 30:
            day = now_l.date() + timedelta(days=LEAD - 1)
            if [st, day.isoformat()] not in decided:
                out.append((st, day))
    return out


# ------------------------------------------------------------------------------ trader
class PaperTrader:
    def __init__(
        self, out: Path, forecasts_db: str, stations: list[str], session=None, bucket=None
    ):
        self.out, self.stations = out, stations
        out.mkdir(parents=True, exist_ok=True)
        self.s = session or requests.Session()
        self.s.headers.update({"User-Agent": "polymarket-weather-edge/paper"})
        self.gamma = p0.Gamma(session=self.s)
        self.store = Store(out, bucket, os.environ.get("PAPER_S3_PREFIX", "paper"))
        self.con = duckdb.connect(str(out / "paper.duckdb"))
        self.con.execute("SET enable_progress_bar=false")
        self.con.execute(f"ATTACH '{forecasts_db}' AS fc")
        self.fcur = (
            self.con.cursor()
        )  # same file lock, default catalog fc: the extractor writes there
        self.fcur.execute("USE fc")
        self.con.execute(
            "CREATE TABLE IF NOT EXISTS observations (station VARCHAR, obs_time_utc TIMESTAMP, raw VARCHAR, "
            "temp_c_whole DOUBLE, temp_c_tenths DOUBLE, tmpf_iem DOUBLE)"
        )
        self.orders_path = out / "orders.parquet"
        self.orders = (
            pd.read_parquet(self.orders_path)
            if self.orders_path.exists()
            else pd.DataFrame(columns=ORDER_COLS)
        )
        self.markets = pd.DataFrame()
        self.coords = {s: FIXED_COORDS[s] for s in stations if s in FIXED_COORDS}
        self.coords.update(station_coords(self.s, {s for s in stations if s not in self.coords}))
        self.failures: dict[str, int] = {}

    def save_orders(self) -> None:
        self.orders.to_parquet(self.orders_path, index=False)

    # --- data
    def task_markets(self) -> None:
        t = now_utc()
        rows = []
        for ev in self.gamma.iter_events(closed="false", title_search="highest temperature in"):
            if not p0.TITLE_RE.match(ev.get("title") or ""):
                continue
            rows += [r for r in market_rows(ev, t) if r["station"] in self.stations]
        self.markets = pd.DataFrame(rows)
        log.info("%d live bucket markets for %s", len(rows), self.stations)

    def task_labels(self) -> None:
        """New METARs for the traded stations into observations, then daily_truth rebuilt."""
        r = self.s.get(
            METAR_URL,
            params={"ids": ",".join(self.stations), "format": "json", "hours": 72},
            timeout=60,
        )
        r.raise_for_status()
        rows = []
        for m in r.json():
            raw, st = m.get("rawOb"), m.get("icaoId")
            if not raw or st not in self.stations:
                continue
            whole, tenths = parse_metar_temps(raw)
            if whole is None:
                continue
            obs = datetime.fromtimestamp(int(m["obsTime"]), UTC).replace(tzinfo=None)
            rows.append((st, obs, raw, float(whole), tenths, None))
        if rows:
            self.con.register(
                "new_obs",
                pd.DataFrame(
                    rows,
                    columns=[
                        "station",
                        "obs_time_utc",
                        "raw",
                        "temp_c_whole",
                        "temp_c_tenths",
                        "tmpf_iem",
                    ],
                ),
            )
            self.con.execute(
                "INSERT INTO observations SELECT n.* FROM new_obs n WHERE NOT EXISTS (SELECT 1 FROM observations o "
                "WHERE o.station = n.station AND o.obs_time_utc = n.obs_time_utc AND o.raw = n.raw)"
            )
            self.con.unregister("new_obs")
        n = build_daily_truth(self.con)
        log.info("%d METARs seen, daily_truth has %d rows", len(rows), n)

    def task_forecasts(self) -> None:
        today = now_utc().date()
        tasks = fo.plan(
            self.fcur, MODELS, [0, 6, 12, 18], today - timedelta(days=2), today, 72, 3, True
        )
        # only runs past their usual publication time (research log section 12: ECMWF 6.5 to 7.6 h after
        # init, GFS and GEFS about 4 h); earlier requests would be logged as missing. Missing steps
        # of the last days are retried every cycle (retry_missing).
        tasks = [x for x in tasks if x[1] + timedelta(hours=PUBLISH_H[x[0]]) <= now_utc()]
        if tasks:
            ok, missing = fo.run(self.fcur, self.s, tasks, self.coords, workers=4)
            log.info("forecast steps: %d ok, %d missing", ok, missing)

    # --- decisions
    def due_decisions(self, t: datetime | None = None) -> list[tuple[str, date]]:
        return due_decisions(self.stations, self.store.state.setdefault("decided", []), t)

    def fetch_books(self, tokens: list[str]) -> dict[str, dict]:
        books = {}
        for i in range(0, len(tokens), 100):
            r = self.s.post(
                CLOB_BOOKS, json=[{"token_id": x} for x in tokens[i : i + 100]], timeout=60
            )
            r.raise_for_status()
            for b in r.json():
                bids = [float(x["price"]) for x in b.get("bids") or []]
                asks = [float(x["price"]) for x in b.get("asks") or []]
                books[str(b.get("asset_id"))] = {
                    "bid": max(bids) if bids else None,
                    "ask": min(asks) if asks else None,
                    "hash": b.get("hash"),
                }
        return books

    def task_decide(self) -> None:
        for st, day in self.due_decisions():
            t = now_utc()
            tz = STATION_TZ[st]
            mk = (
                self.markets[(self.markets.station == st) & (self.markets.date == day)]
                if len(self.markets)
                else self.markets
            )
            if mk.empty:
                log.info("%s %s: no live markets yet", st, day)
                continue
            feats = p5.features(self.con, st, tz, DECISION_HOUR, extra_days=[day])
            feats = feats[feats.day >= pd.Timestamp(day) - pd.Timedelta(days=200)]
            labels = self.con.execute(
                "SELECT day, max_c FROM daily_truth WHERE station = ?", [st]
            ).df()
            labels = labels.assign(day=pd.to_datetime(labels.day)).set_index("day")["max_c"]
            wf = p5.walk_forward(feats, labels, LEAD).set_index("day")
            self.store.state["decided"].append([st, day.isoformat()])
            if pd.Timestamp(day) not in wf.index or pd.isna(wf.loc[pd.Timestamp(day), "emos_mu"]):
                log.warning("%s %s: no model (runs not public or too little history)", st, day)
                continue
            row = wf.loc[pd.Timestamp(day)]
            buckets = mk.rename(columns={"bucket_lo": "lo", "bucket_hi": "hi"})
            probs = bucket_probs(row, buckets)
            books = self.fetch_books(list(buckets.token_yes))
            self.store.add(
                "books_at_decision",
                [
                    {"fetched_at": t, "station": st, "day": day, "token_id": k, **v}
                    for k, v in books.items()
                ],
            )
            new = make_orders(buckets, probs, books, row, t)
            if new:
                self.orders = pd.concat([self.orders, pd.DataFrame(new)], ignore_index=True)
                self.save_orders()
            log.info(
                "%s %s: mu %.1f C sigma %.2f, %d buckets, %d orders (%d sell YES)",
                st,
                day,
                row.emos_mu,
                row.emos_sigma,
                len(buckets),
                len(new),
                sum(o["side"] == "sell_yes" for o in new),
            )

    # --- fills and outcomes
    def task_fills(self) -> None:
        t = now_utc()
        open_idx = self.orders.index[self.orders.status == "open"]
        if len(open_idx) == 0:
            return
        conds = sorted(set(self.orders.loc[open_idx, "condition_id"]))
        prints: dict[str, list[dict]] = {}
        for c in conds:
            r = self.s.get(
                TRADES_URL, params={"market": c, "limit": 1000, "takerOnly": "true"}, timeout=60
            )
            r.raise_for_status()
            prints[c] = r.json()
            time.sleep(0.5)
        toks = sorted(set(self.orders.loc[open_idx, "token_yes"]))
        books = self.fetch_books(toks)
        for i in open_idx:
            o = self.orders.loc[i].to_dict()
            o = apply_prints(o, prints.get(o["condition_id"], []))
            bk = books.get(str(o["token_yes"]), {})
            o = apply_book(o, bk.get("bid"), bk.get("ask"))
            if t >= pd.Timestamp(o["expires_at"]):
                o["status"] = "expired"
            for k, v in o.items():
                self.orders.at[i, k] = v
        self.save_orders()
        log.info("%d open orders checked against %d markets", len(open_idx), len(conds))

    def task_resolve(self) -> None:
        pending = self.orders[(self.orders.status == "expired") & self.orders.outcome.isna()]
        for mid in sorted(set(pending.market_id)):
            r = self.s.get(f"{p0.GAMMA_URL}/markets/{mid}", timeout=60)
            if r.status_code != 200:
                continue
            m = r.json()
            if not m.get("closed"):
                continue
            prices = p0._json_list(m.get("outcomePrices"))
            outcomes = p0._json_list(m.get("outcomes"))
            if not prices or not outcomes:
                continue
            won = {o: float(p) for o, p in zip(outcomes, prices, strict=True)}
            if max(won.values()) < 0.99:
                continue  # not resolved yet
            outcome = 1.0 if won.get("Yes", 0) >= 0.99 else 0.0
            sel = self.orders.market_id == mid
            self.orders.loc[sel, "outcome"] = outcome
            self.orders.loc[sel, "status"] = "resolved"
        self.save_orders()

    def task_report(self) -> None:
        s = summarize(self.orders) if len(self.orders) else pd.DataFrame()
        lines = [
            "# Phase 9 paper trading",
            "",
            f"Updated {now_utc():%Y-%m-%d %H:%M} UTC. Stations {', '.join(self.stations)}. "
            f"Orders {len(self.orders)}, open {(self.orders.status == 'open').sum()}, resolved {(self.orders.status == 'resolved').sum()}.",
            "",
            p5.md(s),
        ]
        (self.out / "report.md").write_text("\n".join(lines))
        self.store.add("paper_orders", self.orders.to_dict("records"))

    def task_flush(self) -> None:
        self.store.flush()

    def run(self, once: bool = False) -> None:
        tasks = {
            "markets": self.task_markets,
            "labels": self.task_labels,
            "forecasts": self.task_forecasts,
            "decide": self.task_decide,
            "fills": self.task_fills,
            "resolve": self.task_resolve,
            "report": self.task_report,
            "flush": self.task_flush,
        }
        due = dict.fromkeys(tasks, 0.0)
        heartbeat = self.out / "heartbeat"
        while True:
            now = time.time()
            for name, fn in tasks.items():
                if now < due[name]:
                    continue
                try:
                    fn()
                    self.failures[name] = 0
                    due[name] = now + INTERVALS[name]
                except Exception as e:  # noqa: BLE001 - one failing task must not stop the others
                    self.failures[name] = self.failures.get(name, 0) + 1
                    log.error("task %s failed (%d in a row): %s", name, self.failures[name], e)
                    if self.failures[name] == 3:
                        alert(f"paper trader task {name} failed 3 times: {e}")
                    due[name] = now + min(INTERVALS[name], 300)
            heartbeat.write_text(now_utc().isoformat())
            if once:
                self.store.flush()
                return
            time.sleep(max(1.0, min(due.values()) - time.time()))


def init_from(out: Path, research_db: str, stations: list[str]) -> None:
    """Seed the paper DB with the historical observations and labels of the traded stations."""
    out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(out / "paper.duckdb"))
    con.execute(f"ATTACH '{research_db}' AS r (READ_ONLY)")
    con.execute(
        "CREATE OR REPLACE TABLE observations AS SELECT * FROM r.observations WHERE station IN (SELECT unnest(?::VARCHAR[]))",
        [stations],
    )
    n = build_daily_truth(con)
    print(
        f"seeded {con.execute('SELECT count(*) FROM observations').fetchone()[0]} observations, {n} daily_truth rows"
    )
    con.close()


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--out", default=str(config.PAPER))
    ap.add_argument("--forecasts", default=str(config.FORECASTS_DB))
    ap.add_argument("--stations", nargs="+", default=["EGLC", "KLGA"])
    ap.add_argument("--init-from", help="research DuckDB to seed observations and labels from")
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    out = Path(a.out)
    if a.init_from:
        init_from(out, a.init_from, a.stations)
        return 0
    PaperTrader(out, a.forecasts, a.stations, bucket=os.environ.get("PAPER_S3_BUCKET") or None).run(
        a.once
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
