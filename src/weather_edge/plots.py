"""Report stage: figures and models/metrics.json from the committed reports, plus a snapshot of the
last fitted EMOS parameters when the research data is present.

python -m weather_edge report [--no-params]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

REPORTS = Path("reports")
FIGURES = REPORTS / "figures"
MODELS = Path("models")
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e0"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]  # fixed order
STATION_NAMES = {
    "EGLC": "London",
    "KLGA": "NYC",
    "KDAL": "Dallas",
    "RKSI": "Seoul",
    "CYYZ": "Toronto",
    "KATL": "Atlanta",
    "KSEA": "Seattle",
    "SAEZ": "Buenos Aires",
}


# ------------------------------------------------------------------------------ markdown tables
def read_tables(path: Path | str) -> list[tuple[str, pd.DataFrame]]:
    """Every pipe table in a report with the nearest heading above it."""
    h2, h3, rows, out = "", "", [], []

    def flush():
        if len(rows) >= 2:
            cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
            frame = pd.DataFrame(cells[2:], columns=cells[0])
            for c in frame.columns:
                converted = pd.to_numeric(frame[c], errors="coerce")
                if converted.notna().all():
                    frame[c] = converted
            out.append((f"{h2} | {h3}", frame))
        rows.clear()

    for line in Path(path).read_text().splitlines():
        if line.startswith("|"):
            rows.append(line)
            continue
        flush()
        if line.startswith("### "):
            h3 = line[4:].strip()
        elif line.startswith("#"):
            h2, h3 = line.strip("# ").strip(), ""
    flush()
    return out


def table_after(tables, heading_part: str, column: str, offset: int = 0) -> pd.DataFrame:
    """The offset-th table under a heading containing heading_part that has the column."""
    hits = [t for h, t in tables if heading_part in h and column in t.columns]
    return hits[offset]


def market_tables(path: Path, station: str, hour: int = 12) -> pd.DataFrame:
    key = f"{station}, decision {hour:02d}:00"
    for h, t in read_tables(path):
        if key in h and "market_minus_model_on_disagree" in t.columns:
            return t
    raise KeyError(f"{station} {hour} not in {path}")


# ------------------------------------------------------------------------------ figures
def style(ax, title: str, xlabel: str = "", ylabel: str = ""):
    ax.set_facecolor(SURFACE)
    ax.figure.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", color=INK, fontsize=11, pad=10)
    ax.set_xlabel(xlabel, color=INK_2, fontsize=9)
    ax.set_ylabel(ylabel, color=INK_2, fontsize=9)
    ax.tick_params(colors=INK_2, labelsize=9, length=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def save(fig, name: str):
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIGURES / name, dpi=160)
    plt.close(fig)


def fig_market_calibration(t1: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7, 3.8))
    d = t1.sort_values("h", ascending=False)
    ax.plot(
        d.h,
        d.brier_base_rate,
        color=SERIES[1],
        linewidth=2,
        marker="o",
        markersize=5,
        label="predicting the base rate",
    )
    ax.plot(
        d.h,
        d.brier_market,
        color=SERIES[0],
        linewidth=2,
        marker="o",
        markersize=5,
        label="market price",
    )
    ax.invert_xaxis()
    ax.set_ylim(0, 0.11)
    for x, y in zip(d.h, d.brier_market, strict=True):
        if x in (30, 12, 6):
            ax.annotate(
                f"{y:.3f}",
                (x, y),
                textcoords="offset points",
                xytext=(0, 7),
                ha="center",
                fontsize=8,
                color=INK_2,
            )
    style(
        ax,
        "The market is sharp: Brier score of YES prices, 117,514 bucket markets",
        "hours before local midnight",
        "Brier score",
    )
    ax.legend(frameon=False, fontsize=9, labelcolor=INK)
    save(fig, "market_calibration.png")


def fig_model_vs_market(rows: pd.DataFrame):
    panels = [
        ("lead 3: noon two days before", 3, "emos"),
        ("lead 2: noon the day before", 2, "emos"),
        ("lead 1: noon same day, with observations", 1, "obs"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(11, 4), sharey=True, sharex=True)
    order = rows[(rows.lead == 3) & (rows.model == "emos")].sort_values("diff").station.tolist()
    axes[0].set_xlim(-0.09, 0.11)
    for ax, (title, lead, model) in zip(axes, panels, strict=True):
        d = rows[(rows.lead == lead) & (rows.model == model)].set_index("station").reindex(order)
        y = range(len(order))
        ax.axvline(0, color=INK_2, linewidth=1)
        ax.hlines(y, d.ci_low, d.ci_high, color=SERIES[0], linewidth=2)
        ax.plot(d["diff"], y, "o", color=SERIES[0], markersize=7)
        ax.set_yticks(list(y), [STATION_NAMES.get(s, s) for s in order])
        style(ax, title, "market minus model Brier on disagreement buckets")
        ax.grid(axis="x", color=GRID, linewidth=0.8)
        ax.grid(axis="y", visible=False)
    fig.suptitle(
        "Where the model beats the market (right of zero) at noon, 90% day-bootstrap intervals",
        x=0.01,
        ha="left",
        color=INK,
        fontsize=11,
    )
    save(fig, "model_vs_market.png")


def fig_backtest(monthly: dict[str, pd.DataFrame]):
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.axhline(0, color=INK_2, linewidth=1)
    for i, (label, d) in enumerate(monthly.items()):
        d = d.sort_values("month")
        ax.plot(
            pd.to_datetime(d.month), d.pnl_usd.cumsum(), color=SERIES[i], linewidth=2, label=label
        )
    style(
        ax,
        "Cumulative paper PnL of the two-days-out signal, 5 shares per order, through fills, no fees (USD)",
        "",
        "USD",
    )
    ax.legend(frameon=False, fontsize=9, labelcolor=INK, loc="upper left")
    save(fig, "backtest_cumulative_pnl.png")


def fig_holdout(points: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.axvline(0, color=INK_2, linewidth=1)
    stations = ["EGLC", "KLGA"]
    periods = (("before 2026-08", SERIES[0]), ("holdout 2026-08 to 09", SERIES[1]))
    for j, (period, color) in enumerate(periods):
        d = points[points.period == period].set_index("station").reindex(stations)
        y = [i + (0.15 if j else -0.15) for i in range(len(stations))]
        ax.hlines(y, d.ci_low, d.ci_high, color=color, linewidth=2)
        ax.plot(d["diff"], y, "o", color=color, markersize=7, label=period)
    ax.set_yticks(range(len(stations)), [STATION_NAMES[s] for s in stations])
    ax.set_ylim(-0.7, 1.7)
    style(
        ax,
        "Two days out, before and on the holdout (market minus model Brier, 90% intervals)",
        "market minus model Brier on disagreement buckets",
    )
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.grid(axis="y", visible=False)
    ax.legend(frameon=False, fontsize=9, labelcolor=INK, loc="upper left")
    save(fig, "holdout.png")


def fig_timing(per_station: dict[str, pd.DataFrame]):
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
    for ax, (st, d) in zip(axes, per_station.items(), strict=True):
        d = d[d.model == "ecmwf"]
        for i, hz in enumerate(("two days before", "day before", "same day")):
            g = d[d.horizon == hz].sort_values("minutes_after")
            ax.plot(
                g.minutes_after,
                g.slope,
                color=SERIES[i],
                linewidth=2,
                marker="o",
                markersize=5,
                label=hz,
            )
        ax.axhline(0, color=INK_2, linewidth=1)
        ax.axvline(0, color=GRID, linewidth=1)
        ax.set_ylim(-0.05, 1.0)
        ax.set_xlim(-40, 320)
        style(
            ax,
            f"{STATION_NAMES[st]}: market move per unit of ECMWF forecast change",
            "minutes after the run became public",
            "slope (1 = full pass-through)",
        )
    axes[0].legend(frameon=False, fontsize=9, labelcolor=INK, loc="upper left")
    save(fig, "timing.png")


# ------------------------------------------------------------------------------ metrics
def collect() -> dict:
    m: dict = {
        "built_from": "reports/*.md",
        "verdict": "No tradeable edge demonstrated: the model beats the market on probability only two days out (2025-01 to 2026-07), that edge is not positive at conservative fills and does not hold on the 2026-08 to 09 holdout.",
    }
    t1 = table_after(read_tables(REPORTS / "phase1_market_checks.md"), "T1", "brier_market")
    m["market_brier_by_hours_before_midnight"] = t1.set_index("h")[
        ["brier_market", "brier_base_rate"]
    ].to_dict("index")
    gt = table_after(
        read_tables(REPORTS / "phase3_ground_truth.md"), "Match rate by era and unit", "tenths"
    )
    m["ground_truth_match_rate"] = gt.set_index(gt.era + "_" + gt.unit)[
        ["n_events", "whole", "tenths"]
    ].to_dict("index")
    cities = {}
    rows = []
    for st in STATION_NAMES:
        t = market_tables(REPORTS / "phase6_cities.md", st)
        cities[st] = {
            f"lead{int(r.lead)}_{r.model}": {
                "diff": r.market_minus_model_on_disagree,
                "ci_low": r.ci_low,
                "ci_high": r.ci_high,
                "buckets": int(r.buckets),
                "days": int(r.days),
            }
            for r in t.itertuples()
        }
        for r in t.itertuples():
            rows.append(
                {
                    "station": st,
                    "lead": int(r.lead),
                    "model": r.model,
                    "diff": r.market_minus_model_on_disagree,
                    "ci_low": r.ci_low,
                    "ci_high": r.ci_high,
                }
            )
    m["model_vs_market_noon"] = cities
    m["_rows"] = pd.DataFrame(rows)
    nyc = {}
    for hour in (6, 8, 10, 12):
        t = market_tables(REPORTS / "phase5_emos.md", "KLGA", hour)
        nyc[f"{hour:02d}:00"] = {
            f"lead{int(r.lead)}_{r.model}": {
                "diff": r.market_minus_model_on_disagree,
                "ci_low": r.ci_low,
                "ci_high": r.ci_high,
            }
            for r in t.itertuples()
        }
    m["nyc_by_decision_hour"] = nyc
    bt, monthly = {}, {}
    tables = read_tables(REPORTS / "phase7_backtest.md")
    for st in ("KLGA", "EGLC"):
        for hour in (6, 12):
            key = f"{st}, decision {hour:02d}:00"
            all_orders = next(t for h, t in tables if key in h and "All orders" in h)
            by_month = next(t for h, t in tables if key in h and "By month" in h)
            bt[f"{st}_{hour:02d}"] = all_orders.set_index("fill_model")[
                [
                    "orders",
                    "orders_filled",
                    "filled_shares",
                    "pnl_usd",
                    "pnl_c_per_share",
                    "pnl_usd_per_order_ci_low",
                    "pnl_usd_per_order_ci_high",
                ]
            ].to_dict("index")
            monthly[f"{STATION_NAMES[st]} {hour:02d}:00"] = by_month
    m["backtest_lead3"] = bt
    m["_monthly"] = monthly
    hold = []
    for st in ("EGLC", "KLGA"):
        r = market_tables(REPORTS / "phase5_holdout.md", st)
        r = r[(r.lead == 3) & (r.model == "emos")].iloc[0]
        hold.append(
            {
                "station": st,
                "period": "holdout 2026-08 to 09",
                "diff": r.market_minus_model_on_disagree,
                "ci_low": r.ci_low,
                "ci_high": r.ci_high,
                "days": int(r.days),
                "buckets": int(r.buckets),
            }
        )
        c = cities[st]["lead3_emos"]
        hold.append(
            {
                "station": st,
                "period": "before 2026-08",
                "diff": c["diff"],
                "ci_low": c["ci_low"],
                "ci_high": c["ci_high"],
                "days": c["days"],
                "buckets": c["buckets"],
            }
        )
    m["holdout_lead3"] = hold
    m["_holdout"] = pd.DataFrame(hold)
    timing = {}
    ttables = read_tables(REPORTS / "phase8_timing.md")
    for st in ("EGLC", "KLGA"):
        t = next(t for h, t in ttables if h.startswith(f"{st} |") and "slope" in t.columns)
        timing[st] = t
    m["timing_ecmwf_slope"] = {
        st: {
            f"{r.horizon}_{int(r.minutes_after)}min": r.slope
            for r in t[t.model == "ecmwf"].itertuples()
        }
        for st, t in timing.items()
    }
    m["_timing"] = timing
    return m


def emos_snapshot(stations=("EGLC", "KLGA")) -> dict:
    """The EMOS parameters fitted on the last 90 days before the holdout, per station, lead 3."""
    import duckdb

    from weather_edge import model as mdl
    from weather_edge.market_checks import STATION_TZ

    con = duckdb.connect("data/research.duckdb", read_only=True)
    con.execute("SET enable_progress_bar=false")
    con.execute("ATTACH 'data/prices.duckdb' AS px (READ_ONLY)")
    con.execute("ATTACH 'data/forecasts.duckdb' AS fc (READ_ONLY)")
    out = {
        "fitted_on": "last 90 labelled days before 2026-08-01",
        "lead": 3,
        "decision_hour_local": 12,
    }
    for st in stations:
        feats = mdl.features(con, st, STATION_TZ[st], 12)
        feats = feats[
            (feats.lead == 3)
            & (feats.day < pd.Timestamp(mdl.HOLDOUT_START))
            & (feats.day >= pd.Timestamp(mdl.HOLDOUT_START - timedelta(days=200)))
        ]
        labels = con.execute(
            "SELECT day, max_c FROM daily_truth WHERE station = ? AND day < ?",
            [st, mdl.HOLDOUT_START],
        ).df()
        labels = labels.assign(day=pd.to_datetime(labels.day)).set_index("day")["max_c"]
        wf = mdl.walk_forward(feats, labels, 3).dropna(subset=["emos_mu"])
        det = [c for c in mdl.DET if c in feats.columns and feats[c].notna().mean() > 0.5]
        spreads = [mdl.SPREADS[c] for c in det if c in mdl.SPREADS]
        train = (
            feats.set_index("day")
            .join(labels.rename("yy"), how="inner")
            .dropna(subset=det + ["yy"])
            .tail(90)
        )
        theta = mdl.fit_emos(
            train[det].to_numpy(float), train[spreads].to_numpy(float), train["yy"].to_numpy(float)
        )
        out[st] = {
            "inputs": det,
            "spreads": spreads,
            "theta": [float(x) for x in theta],
            "nu": 2 + math.exp(float(theta[-1])),
            "calibration_scale": float(wf.iloc[-1].emos_scale),
            "training_days": int(len(train)),
        }
    con.close()
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--no-params", action="store_true", help="skip the EMOS parameter snapshot (needs data/)"
    )
    a = ap.parse_args(argv)
    m = collect()
    fig_market_calibration(
        pd.DataFrame.from_dict(m["market_brier_by_hours_before_midnight"], orient="index")
        .rename_axis("h")
        .reset_index()
    )
    fig_model_vs_market(m.pop("_rows"))
    fig_backtest(m.pop("_monthly"))
    fig_holdout(m.pop("_holdout"))
    fig_timing(m.pop("_timing"))
    MODELS.mkdir(exist_ok=True)
    (MODELS / "metrics.json").write_text(json.dumps(m, indent=1, default=float))
    print("wrote", sorted(p.name for p in FIGURES.glob("*.png")), "and models/metrics.json")
    if not a.no_params and Path("data/research.duckdb").exists():
        (MODELS / "emos_params.json").write_text(json.dumps(emos_snapshot(), indent=1))
        print("wrote models/emos_params.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
