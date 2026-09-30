"""Paths and the few constants every stage shares.

Absolute paths from the package location, so the stages and the notebooks agree on where the data
is whatever the working directory.
"""

from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
IEM = DATA / "iem"
RESEARCH_DB = DATA / "research.duckdb"
PRICES_DB = DATA / "prices.duckdb"
FORECASTS_DB = DATA / "forecasts.duckdb"
TRADES = DATA / "trades.parquet"
COLLECTOR = DATA / "collector"
PAPER = DATA / "paper"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
MODELS = ROOT / "models"

# The period scored exactly once, after every modelling choice was fixed. Nothing trains on it.
HOLDOUT_START = date(2026, 8, 1)
