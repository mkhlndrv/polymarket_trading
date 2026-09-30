"""Figures and models/metrics.json, built from the committed reports rather than the data.

Every number in the README is read off a report table here, so the figures cannot drift from what
the reports say, and the stage runs in CI and in Docker without the datasets. With the research data
present it also snapshots the last fitted EMOS parameters.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import timedelta
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

from weather_edge import config
from weather_edge.config import FIGURES, MODELS, REPORTS

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
VERDICT = (
    "No tradeable edge demonstrated: the model beats the market on probability only two days out "
    "(2025-01 to 2026-07), that edge is not positive at conservative fills and does not hold on the "
    "2026-08 to 09 holdout."
)


# ------------------------------------------------------------------------------ markdown tables
def parse_table(lines: list[str]) -> pd.DataFrame:
    """A markdown pipe table as a frame; columns that are all numbers become numeric."""
    cells = [[c.strip() for c in line.strip().strip("|").split("|")] for line in lines]
    frame = pd.DataFrame(cells[2:], columns=cells[0])  # row 1 is the |---| separator
    for column in frame.columns:
        converted = pd.to_numeric(frame[column], errors="coerce")
        if converted.notna().all():
            frame[column] = converted
    return frame


def read_tables(path: Path | str) -> list[tuple[str, pd.DataFrame]]:
    """Every pipe table in a report, keyed by the nearest "h2 | h3" headings above it."""
    h2, h3 = "", ""
    table_lines: list[str] = []
    tables = []

    def flush():
        if len(table_lines) >= 2:
            tables.append((f"{h2} | {h3}", parse_table(table_lines)))
        table_lines.clear()

    for line in Path(path).read_text().splitlines():
        if line.startswith("|"):
            table_lines.append(line)
            continue
        flush()
        if line.startswith("### "):
            h3 = line[4:].strip()
        elif line.startswith("#"):
            h2, h3 = line.strip("# ").strip(), ""
    flush()
    return tables


def table_after(tables, heading_part: str, column: str, offset: int = 0) -> pd.DataFrame:
    """The offset-th table under a heading containing heading_part that has the column."""
    hits = [table for heading, table in tables if heading_part in heading and column in table]
    return hits[offset]


def market_tables(path: Path, station: str, hour: int = 12) -> pd.DataFrame:
    """The market comparison table of one station and decision hour in a model report."""
    key = f"{station}, decision {hour:02d}:00"
    for heading, table in read_tables(path):
        if key in heading and "market_minus_model_on_disagree" in table.columns:
            return table
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


def line(ax, x, y, color, label):
    ax.plot(x, y, color=color, linewidth=2, marker="o", markersize=5, label=label)


def fig_market_calibration(brier: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7, 3.8))
    by_horizon = brier.sort_values("h", ascending=False)
    line(ax, by_horizon.h, by_horizon.brier_base_rate, SERIES[1], "predicting the base rate")
    line(ax, by_horizon.h, by_horizon.brier_market, SERIES[0], "market price")
    ax.invert_xaxis()
    ax.set_ylim(0, 0.11)
    for hours, score in zip(by_horizon.h, by_horizon.brier_market, strict=True):
        if hours in (30, 12, 6):
            ax.annotate(
                f"{score:.3f}",
                (hours, score),
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
    # cities in the order of their two-days-out result, so the first panel reads top to bottom
    two_days_out = rows[(rows.lead == 3) & (rows.model == "emos")]
    order = two_days_out.sort_values("diff").station.tolist()
    positions = range(len(order))
    axes[0].set_xlim(-0.09, 0.11)
    for ax, (title, lead, model) in zip(axes, panels, strict=True):
        points = rows[(rows.lead == lead) & (rows.model == model)]
        points = points.set_index("station").reindex(order)
        ax.axvline(0, color=INK_2, linewidth=1)
        ax.hlines(positions, points.ci_low, points.ci_high, color=SERIES[0], linewidth=2)
        ax.plot(points["diff"], positions, "o", color=SERIES[0], markersize=7)
        ax.set_yticks(list(positions), [STATION_NAMES.get(s, s) for s in order])
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
    for color, (label, by_month) in zip(SERIES, monthly.items(), strict=False):
        by_month = by_month.sort_values("month")
        months = pd.to_datetime(by_month.month)
        ax.plot(months, by_month.pnl_usd.cumsum(), color=color, linewidth=2, label=label)
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
    periods = (("before 2026-08", SERIES[0], -0.15), ("holdout 2026-08 to 09", SERIES[1], 0.15))
    for period, color, shift in periods:
        rows = points[points.period == period].set_index("station").reindex(stations)
        positions = [i + shift for i in range(len(stations))]
        ax.hlines(positions, rows.ci_low, rows.ci_high, color=color, linewidth=2)
        ax.plot(rows["diff"], positions, "o", color=color, markersize=7, label=period)
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
    horizons = ("two days before", "day before", "same day")
    for ax, (station, slopes) in zip(axes, per_station.items(), strict=True):
        ecmwf = slopes[slopes.model == "ecmwf"]
        for color, horizon in zip(SERIES, horizons, strict=False):
            curve = ecmwf[ecmwf.horizon == horizon].sort_values("minutes_after")
            line(ax, curve.minutes_after, curve.slope, color, horizon)
        ax.axhline(0, color=INK_2, linewidth=1)
        ax.axvline(0, color=GRID, linewidth=1)
        ax.set_ylim(-0.05, 1.0)
        ax.set_xlim(-40, 320)
        style(
            ax,
            f"{STATION_NAMES[station]}: market move per unit of ECMWF forecast change",
            "minutes after the run became public",
            "slope (1 = full pass-through)",
        )
    axes[0].legend(frameon=False, fontsize=9, labelcolor=INK, loc="upper left")
    save(fig, "timing.png")


# ------------------------------------------------------------------------------ metrics
def interval(row) -> dict:
    """One market comparison row of a model report as a small dict."""
    return {
        "diff": row.market_minus_model_on_disagree,
        "ci_low": row.ci_low,
        "ci_high": row.ci_high,
    }


def market_comparison(path: Path, station: str, hour: int, with_counts: bool) -> dict:
    """{"lead3_emos": {diff, ci_low, ci_high[, buckets, days]}, ...} for one station and hour."""
    out = {}
    for row in market_tables(path, station, hour).itertuples():
        entry = interval(row)
        if with_counts:
            entry.update(buckets=int(row.buckets), days=int(row.days))
        out[f"lead{int(row.lead)}_{row.model}"] = entry
    return out


def collect() -> dict:
    """Every number the README and the figures use, read from the reports.

    Keys starting with an underscore are frames for the figures; main() pops them before writing
    the JSON."""
    metrics: dict = {"built_from": "reports/*.md", "verdict": VERDICT}

    brier = table_after(read_tables(REPORTS / "phase1_market_checks.md"), "T1", "brier_market")
    metrics["market_brier_by_hours_before_midnight"] = brier.set_index("h")[
        ["brier_market", "brier_base_rate"]
    ].to_dict("index")

    match = table_after(
        read_tables(REPORTS / "phase3_ground_truth.md"), "Match rate by era and unit", "tenths"
    )
    metrics["ground_truth_match_rate"] = match.set_index(match.era + "_" + match.unit)[
        ["n_events", "whole", "tenths"]
    ].to_dict("index")

    cities = {}
    rows = []
    for station in STATION_NAMES:
        cities[station] = market_comparison(
            REPORTS / "phase6_cities.md", station, 12, with_counts=True
        )
        for row in market_tables(REPORTS / "phase6_cities.md", station).itertuples():
            rows.append(
                {"station": station, "lead": int(row.lead), "model": row.model, **interval(row)}
            )
    metrics["model_vs_market_noon"] = cities
    metrics["_rows"] = pd.DataFrame(rows)

    metrics["nyc_by_decision_hour"] = {
        f"{hour:02d}:00": market_comparison(
            REPORTS / "phase5_emos.md", "KLGA", hour, with_counts=False
        )
        for hour in (6, 8, 10, 12)
    }

    backtest, monthly = {}, {}
    tables = read_tables(REPORTS / "phase7_backtest.md")
    columns = [
        "orders",
        "orders_filled",
        "filled_shares",
        "pnl_usd",
        "pnl_c_per_share",
        "pnl_usd_per_order_ci_low",
        "pnl_usd_per_order_ci_high",
    ]
    for station in ("KLGA", "EGLC"):
        for hour in (6, 12):
            key = f"{station}, decision {hour:02d}:00"
            all_orders = next(t for h, t in tables if key in h and "All orders" in h)
            by_month = next(t for h, t in tables if key in h and "By month" in h)
            backtest[f"{station}_{hour:02d}"] = all_orders.set_index("fill_model")[columns].to_dict(
                "index"
            )
            monthly[f"{STATION_NAMES[station]} {hour:02d}:00"] = by_month
    metrics["backtest_lead3"] = backtest
    metrics["_monthly"] = monthly

    holdout = []
    for station in ("EGLC", "KLGA"):
        table = market_tables(REPORTS / "phase5_holdout.md", station)
        row = table[(table.lead == 3) & (table.model == "emos")].iloc[0]
        holdout.append(
            {
                "station": station,
                "period": "holdout 2026-08 to 09",
                **interval(row),
                "days": int(row.days),
                "buckets": int(row.buckets),
            }
        )
        before = cities[station]["lead3_emos"]
        holdout.append(
            {
                "station": station,
                "period": "before 2026-08",
                "diff": before["diff"],
                "ci_low": before["ci_low"],
                "ci_high": before["ci_high"],
                "days": before["days"],
                "buckets": before["buckets"],
            }
        )
    metrics["holdout_lead3"] = holdout
    metrics["_holdout"] = pd.DataFrame(holdout)

    timing_tables = read_tables(REPORTS / "phase8_timing.md")
    timing = {
        station: next(
            t for h, t in timing_tables if h.startswith(f"{station} |") and "slope" in t.columns
        )
        for station in ("EGLC", "KLGA")
    }
    metrics["timing_ecmwf_slope"] = {
        station: {
            f"{row.horizon}_{int(row.minutes_after)}min": row.slope
            for row in slopes[slopes.model == "ecmwf"].itertuples()
        }
        for station, slopes in timing.items()
    }
    metrics["_timing"] = timing
    return metrics


def emos_snapshot(stations=("EGLC", "KLGA")) -> dict:
    """The EMOS parameters fitted on the last 90 days before the holdout, per station, lead 3."""
    import duckdb

    from weather_edge import model as mdl
    from weather_edge.market_checks import STATION_TZ

    con = duckdb.connect(str(config.RESEARCH_DB), read_only=True)
    con.execute("SET enable_progress_bar=false")
    con.execute(f"ATTACH '{config.PRICES_DB}' AS px (READ_ONLY)")
    con.execute(f"ATTACH '{config.FORECASTS_DB}' AS fc (READ_ONLY)")
    holdout = pd.Timestamp(mdl.HOLDOUT_START)
    out = {
        "fitted_on": "last 90 labelled days before 2026-08-01",
        "lead": 3,
        "decision_hour_local": 12,
    }
    for station in stations:
        feats = mdl.features(con, station, STATION_TZ[station], 12)
        feats = feats[
            (feats.lead == 3) & (feats.day < holdout) & (feats.day >= holdout - timedelta(days=200))
        ]
        labels = con.execute(
            "SELECT day, max_c FROM daily_truth WHERE station = ? AND day < ?",
            [station, mdl.HOLDOUT_START],
        ).df()
        labels = labels.assign(day=pd.to_datetime(labels.day)).set_index("day")["max_c"]
        walk = mdl.walk_forward(feats, labels, 3).dropna(subset=["emos_mu"])
        inputs = [c for c in mdl.DET if c in feats.columns and feats[c].notna().mean() > 0.5]
        spreads = [mdl.SPREADS[c] for c in inputs if c in mdl.SPREADS]
        train = (
            feats.set_index("day")
            .join(labels.rename("yy"), how="inner")
            .dropna(subset=inputs + ["yy"])
            .tail(90)
        )
        theta = mdl.fit_emos(
            train[inputs].to_numpy(float),
            train[spreads].to_numpy(float),
            train["yy"].to_numpy(float),
        )
        out[station] = {
            "inputs": inputs,
            "spreads": spreads,
            "theta": [float(x) for x in theta],
            "nu": 2 + math.exp(float(theta[-1])),
            "calibration_scale": float(walk.iloc[-1].emos_scale),
            "training_days": int(len(train)),
        }
    con.close()
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--no-params", action="store_true", help="skip the EMOS parameter snapshot (needs data/)"
    )
    args = ap.parse_args(argv)
    matplotlib.use("Agg")  # headless in CI and Docker; notebooks importing this module keep inline
    metrics = collect()
    brier = pd.DataFrame.from_dict(metrics["market_brier_by_hours_before_midnight"], orient="index")
    fig_market_calibration(brier.rename_axis("h").reset_index())
    fig_model_vs_market(metrics.pop("_rows"))
    fig_backtest(metrics.pop("_monthly"))
    fig_holdout(metrics.pop("_holdout"))
    fig_timing(metrics.pop("_timing"))
    MODELS.mkdir(exist_ok=True)
    (MODELS / "metrics.json").write_text(json.dumps(metrics, indent=1, default=float))
    print("wrote", sorted(p.name for p in FIGURES.glob("*.png")), "and models/metrics.json")
    if not args.no_params and config.RESEARCH_DB.exists():
        (MODELS / "emos_params.json").write_text(json.dumps(emos_snapshot(), indent=1))
        print("wrote models/emos_params.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
