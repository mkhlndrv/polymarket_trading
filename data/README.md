# data/

**Nothing in here is committed except this file.** The datasets are large and every one of them is
rebuilt by code, so the loaders ship and the data does not.

## What lives here

```
data/
  raw/               Gamma event dumps, one JSONL per inventory run
  iem/               METAR archives, one CSV per station and year
  research.duckdb    markets, rules_history, trades, observations, truth, daily_truth
  prices.duckdb      prices_history: 1-minute CLOB points for 118,924 bucket markets
  forecasts.duckdb   forecasts, forecast_runs: 2 m temperature per station, model, run and step
  trades.parquet     27.9M on-chain fills for the inventory markets
  collector/         live snapshots written by the collector
  paper/             paper-trading state
```

About 4 GB in total for the 2026-09-30 build; the prices file is 775 MB and the fills 1.1 GB.

## Where it comes from

**Polymarket's Gamma API** for the markets themselves: title, rules text, outcomes, token ids,
resolution. The rules text is what gets parsed, because the structured fields that claim to hold the
resolution source and the station lag behind it.

**The CLOB `prices-history` endpoint** for prices. Old markets return nothing without an explicit
window, and windows longer than a few days are refused, so each market is fetched in bounded pieces.

**[SII-WANGZJ/Polymarket_data](https://huggingface.co/datasets/SII-WANGZJ/Polymarket_data)** for
fills, streamed one row group at a time. The dataset is complete through April 2026 and covers about
80% of fills after that, which the backtest reports by month for that reason.

**The Iowa Environmental Mesonet ASOS archive** for observations: every routine and special METAR of
every station, with the T-group tenths that decide Fahrenheit resolutions.

**The open GRIB archives**: ECMWF IFS 0.25 through its Google Cloud mirror (CC-BY 4.0), NOAA GFS,
GEFS and NBM on AWS Open Data. Only the 2 m temperature message of each file is fetched, by byte
range, and its Last-Modified header is stored as the time the run became public.

## Regenerating

`make data` rebuilds everything in order: inventory, prices, fills, observations, forecasts, labels.
It takes hours, most of them streaming the fills and fetching about 400,000 GRIB byte ranges. Every
stage is resumable, so an interrupted run continues where it stopped.
