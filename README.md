# Is there a tradeable edge in Polymarket's daily temperature markets?

[![CI](https://github.com/mkhlndrv/polymarket_trading/actions/workflows/ci.yml/badge.svg)](https://github.com/mkhlndrv/polymarket_trading/actions/workflows/ci.yml)

Every day Polymarket lists a market for 56 cities: *Highest temperature in New York on 3 October?*
There is one YES/NO contract per 2 °F or 1 °C bucket, and the market resolves on a weather station
page the next morning. Weather forecasts are public and good. I wanted to know if the prices lag
them.

**They do not, at least not in a way you can trade.** A calibrated model built from ECMWF, GFS and
GEFS beats the prices two days before the day, by 0.021 to 0.042 Brier on the buckets where the
two disagree. That is the only place it wins. One day before, the market is level with it. On the
day itself the market is far ahead, even when the model also sees the morning's observations. As
maker orders with fills taken from the real trade tape, the two-days-out edge is worth about 5c a
share in London and nothing in New York. On the two months I held out until the end, it is gone.
The market got sharper during 2026 and the model did not.

I set aside 200 USD for live trading and did not spend it. That is the right outcome when the edge
is not there. What the repository holds is the measurement: data pipelines that know when each
forecast became public, a ground-truth rebuild that matches Polymarket's own resolutions, a model
scored against prices point in time, a backtest that never assumes a fill, and a holdout used once.

## Contents

- [The result](#the-result): where the model beats the market and where it does not
- [What the market already knows](#what-the-market-already-knows): calibration, who loses money,
  when a market gets listed
- [What a market resolves on](#what-a-market-resolves-on): the displayed value, and how I checked it
- [Point in time](#point-in-time): publication times, and two bugs the rule caught
- [The model](#the-model): EMOS by CRPS, the calibration fix, the same-day variant
- [What it is worth in money](#what-it-is-worth-in-money): fills from the tape, adverse selection,
  fees
- [The holdout](#the-holdout): scored once, and what changed
- [Two things that did not help](#two-things-that-did-not-help): NBM, and trading around model
  releases
- [What this does not show](#what-this-does-not-show)
- [Reproducing it](#reproducing-it)
- [Layout](#layout)
- [Licence and attribution](#licence-and-attribution)

---

## The result

![Model against market by city and lead](reports/figures/model_vs_market.png)

Each point is the market's Brier score minus the model's, on the buckets where the two disagree by
10c or more. Right of zero means the model priced those buckets better. Decisions are at noon local.
The 90% intervals come from a bootstrap over days, because the buckets of one day share one
weather outcome.

| city | days | two days before | the day before | same day, with observations |
|---|---|---|---|---|
| London | 548 | **+0.042** [0.031, 0.053] | −0.009 [−0.020, +0.001] | −0.054 [−0.069, −0.039] |
| New York | 537 | **+0.021** [0.011, 0.031] | −0.018 [−0.027, −0.009] | −0.041 [−0.055, −0.027] |
| Atlanta | 230 | +0.016 [−0.003, +0.036] | −0.006 [−0.022, +0.009] | −0.032 [−0.053, −0.008] |
| Buenos Aires | 232 | +0.015 [−0.006, +0.036] | −0.023 [−0.037, −0.008] | −0.032 [−0.051, −0.013] |
| Seattle | 233 | +0.009 [−0.015, +0.032] | −0.014 [−0.031, +0.004] | −0.033 [−0.057, −0.009] |
| Toronto | 227 | +0.007 [−0.009, +0.025] | −0.013 [−0.028, +0.003] | −0.041 [−0.061, −0.020] |
| Dallas | 232 | −0.014 [−0.031, +0.001] | −0.023 [−0.038, −0.009] | −0.037 [−0.056, −0.017] |

**Two cities pass, six are inconclusive, and the shape is the same everywhere.** Two days out the
model is at least level with the market. In the two cities with a year and a half of history it is
clearly ahead. The day before, the ensemble spread and the extra forecast cycles bring it to a
draw. On the day, the market wins by 0.03 to 0.07 Brier in every city. A version of the model that
reads the running maximum and the latest METAR before deciding closes about a third of that gap.
Seoul is not in the table because almost nobody quotes Seoul two days ahead: 39 buckets in seven
months.

The market's own numbers explain the same-day column. At noon its Brier is 0.071 to 0.075 in London
and New York and 0.057 to 0.065 in the newer cities, on buckets whose base rate is about 0.09.
Whoever moves these prices in the morning knows something a forecast model does not, and the
[timing study below](#two-things-that-did-not-help) shows it is not the model runs.

## What the market already knows

![Brier score of YES prices by hours before the day ends](reports/figures/market_calibration.png)

**The prices are honest probabilities, and they sharpen when you would expect.** Over 117,514
resolved bucket markets, the Brier score of the YES price is 0.061 a day ahead, against 0.087 for
predicting the base rate. Six hours before local midnight it is 0.003. The day's maximum is usually
in by 18:00 and the market knows it. Reliability by price band shows no bias worth trading at any
horizon.

**Takers lose, a little.** Across 27.9 million on-chain fills the taker side loses 0.29c a share
before fees, in the months where the dataset is complete. Most of it is takers buying YES at 65c to
95c, paying up for the favourite once the day's high is nearly in. The one thing takers do well is
sell buckets priced 35c to 90c, where they make 1 to 4c a share. That is someone selling a bucket
they can already see will not happen, and it is exactly the fill a resting maker order gets.

**A market exists for about two days before its day, and that changed during the project.** New
York markets were listed a median 42 to 48 hours before the local day through May 2026, 27 hours in
June, July and August, and 44 hours again from September. A two-days-out decision needs a market
to exist, which is true on 436 of 552 New York days at noon and 236 at 06:00. The backtest counts an
order only when there was a market to place it in.

## What a market resolves on

A market does not resolve on the day's official maximum. It resolves on the highest value
**displayed** on a web page for a named station over the local clock day. The page was Weather
Underground for most of the history and weather.gov's hourly table since August 2026. The page
converts units and rounds before it displays. For a Fahrenheit market at LaGuardia that means:
take each METAR's tenth-of-a-degree temperature from the T group, convert to Fahrenheit, round half
up, keep the largest. For a Celsius market it is the whole-degree METAR value, no tenths. Hong Kong
uses the Observatory's own daily maximum, floored.

I checked this by rebuilding every resolved event from the raw METAR archive under several rules and
comparing each rule with the bucket Polymarket paid out:

| resolution source | unit | events | whole-degree rule | tenths rule |
|---|---|---|---|---|
| Weather Underground | °F | 2,863 | 82.2% | **99.7%** |
| Weather Underground | °C | 5,945 | **96.3%** | 96.3% |
| weather.gov | °F | 407 | 77.2% | **99.8%** |
| weather.gov | °C | 1,822 | **98.6%** | 98.6% |
| Hong Kong Observatory | °C | 2,090 | | **100%** |

The tenths matter. A station reporting 82.9 °F displays 83, and a rule that rounds the whole-degree
Celsius group gets a fifth of Fahrenheit days wrong. The 205 events that no rule matches are listed
in the report. 119 of them are Shenzhen, where the page's value is a degree or two away from the
airport's METAR on most days and I never found the rule, so Shenzhen is not modelled. 30 are Seoul
in the Weather Underground era, one degree off. 21 are from 19 May 2026, when Polymarket listed
every city's market twice under two slugs and 40 of the 46 pairs resolved to different buckets. The
rest are single days, most of them a missing NOAA page.

Everything downstream is scored against this rebuilt value, for every station-day and not only the
days with a market. That gives the model 577 training days per city instead of the 230 to 550 that
have prices.

## Point in time

**A forecast can be used from the moment its file appeared, not from the run's nominal time.**
ECMWF's 00Z run shows up on the open-data mirror a median 7.6 hours after 00Z. GFS takes 4.0 hours,
GEFS 4.1. The extractor fetches the 2 m temperature message of each GRIB file by byte range and
stores the file's Last-Modified header as its availability time. A run is used at a decision only
if every step inside the local day was public before it. A test fails if any input to a decision is
stamped after it.

The rule caught two bugs. In the first version of the feature code, per-step publication times split
runs in two, which quietly emptied the feature table until I grouped by run. Then on 12 May 2026
ECMWF moved its 06Z and 18Z runs to another directory of the mirror, and every step after that date
came back as missing. I only noticed because the backfill log showed a 25% miss rate. Both would
have looked like modelling results if nobody had checked.

Prices get the same treatment. The market price at a decision is the last CLOB point at or before
it, and the on-chain fills in the backtest carry their block time.

## The model

**EMOS, fit by CRPS, one fit per station and lead every day on the trailing 90 days.** The mean is a
regression on the daily maxima of ECMWF, GFS and the GEFS ensemble mean from the latest public
runs. The scale grows with the GEFS spread. The distribution is a Student t. Bucket probabilities
integrate it between half-integer edges in the market's unit, which is where the rounding of the
displayed value lives.

**The first version was too sure of itself.** Its nominal 90% interval covered 82% of days and the
PIT histogram was U-shaped. A Student t did not fix it: the degrees of freedom went to the upper
bound. The errors are not heavy-tailed, the in-sample fit is simply overconfident about a window
that keeps moving. What fixed it was scaling the spread by the root mean square of the last 90
out-of-sample errors known at the decision. Coverage is now 88 to 92% and the PIT is flat. It cost
0.01 °C of CRPS and moved the market comparison by less than 0.002.

**On the day, the model can also read the thermometer.** By 06:00 local some of the day's reports
are in. The same-day variant treats the final maximum as the larger of the running maximum and a
value drawn from a censored regression on the remaining forecast hours and the last METAR. That
lowers CRPS from 0.81 °C to 0.73 °C at 06:00 in New York and to 0.61 °C at noon. The market still
wins by 0.04 Brier at every hour from 06:00. Reading the observations is not what it does better.

## What it is worth in money

![Cumulative paper PnL by decision](reports/figures/backtest_cumulative_pnl.png)

The backtest places a maker order wherever the model is at least 10c from the last price, on either
side, five shares (the exchange minimum), resting 24 hours. **It never assumes a fill.** Fills are
read off the on-chain trade tape. A taker print at or through the price is a touch fill. A print
strictly beyond the price is a through fill: the level was cleared, so a resting order there would
have gone with it whatever its queue position. A third variant halves every winning fill, because
fills are more likely when the model is wrong.

| decision, two days before | orders | through fills | PnL | c per share | 90% interval on PnL per order |
|---|---|---|---|---|---|
| London, noon | 1,041 | 412 | +110 USD | +5.5 | [+0.08, +0.45] USD |
| London, 06:00 | 383 | 164 | +25 USD | +3.2 | [−0.14, +0.44] |
| New York, 06:00 | 748 | 272 | +56 USD | +4.3 | [−0.00, +0.44] |
| New York, noon | 1,279 | 564 | +25 USD | +0.9 | [−0.11, +0.20] |

**London at noon is the one case with an interval above zero, and it is thin.** Fifteen of eighteen
months are positive. It adds up to 110 USD in a year and a half at five shares an order. The model
expected 18.6c a share on the orders that filled and got 5.5c, so about 70% of the paper edge is
adverse selection. The tape captures that on its own. With the winning fills halved, every row is
negative. The NO side carries what there is: bids on NO when the market prices a bucket 10c above
the model win 71% of the time, bids on YES on the underpriced side win 15%.

Fees do not change this. Weather is a fee-enabled category. The taker pays 0.05 × p × (1 − p) a
share, about a cent at typical prices; makers pay nothing and get a quarter of the taker's fee
back. Capacity is not the constraint either: 195,000 shares printed beyond the London levels over
the period, against 2,000 filled at five an order.

## The holdout

![Two days out, before and on the holdout](reports/figures/holdout.png)

August and September 2026 stayed untouched until every choice above was fixed. Then I scored them
once, for the configuration that had passed: two days out, noon, London and New York.

| city | holdout days | disagreement buckets | market minus model |
|---|---|---|---|
| London | 57 | 69 | −0.007 [−0.036, +0.021] |
| New York | 29 | 52 | −0.038 [−0.078, +0.005] |

**The edge is not there.** The model is fine: its CRPS on the holdout months is better than
in-sample, because August and September are easy months. What moved is the market. Two days before
the day its Brier is 0.067 in London and 0.062 in New York, against 0.102 and 0.108 over the year
and a half before. It disagrees with the model on 1.2 buckets a day where it used to be three. New
York has only 29 holdout days with a quote at noon two days before, because of the 27-hour listing
window that summer, so its interval is wide. London's is not wide, and it contains zero.

A model built from public data in the autumn of 2026 arrives after the market has already improved.
Better to learn that from sixty held-out days than from a live account.

## Two things that did not help

**Higher-resolution guidance.** The obvious explanation for the same-day gap was resolution.
Three-hourly steps of a 25 km global model miss the afternoon peak, and the market has hourly
products. So I pulled the National Blend of Models' 12-hour daytime maximum and its ensemble spread
for the fourteen stations on its grid, all four cycles, with publication times. NBM is what the NWS
forecast is built on and it already blends HRRR. Added as inputs, it moves every score at every hour
by less than 0.002 Brier, and the fitted slopes give it no weight once ECMWF, GFS and GEFS are in.

**Trading around model releases.** If the market followed the runs with a lag, the moment a file
appeared would be a window. Across 16,000 ECMWF and GFS publications the market's implied high
moves by 0.00 of the run's change in the first 15 minutes and by 0.03 to 0.05 of it after four
hours. The sign agrees 44 to 60% of the time. The market moves by the same amount whether or not
the newest run changed anything. Whatever the prices respond to, it is not the global model runs.

![Market move per unit of forecast change](reports/figures/timing.png)

## What this does not show

**What information the market trades on.** The results say it is not the public global runs and
not the raw observations. They do not say what it is. Blended products, the NWS forecast, private
models, or people who watch the METAR and quote faster than a daily model all fit the data. The
live collector in this repository stores full order books every two minutes and was built to
answer that. The question is still open.

**The six newer cities.** Atlanta, Buenos Aires, Seattle, Toronto and Dallas have markets since
December 2025 and about 165 days with a two-days-out quote each. Five of six point estimates are
positive and every interval contains zero. They are evidence neither against the London and New
York result nor for it.

**Fills in the last three months.** The trade dataset is complete through April 2026 and covers
about 80% of fills after that, so May to July understate what would have filled. That is why the
backtest reports by month.

**A stale reference price.** The backtest bids one cent under the last traded price, which can be
hours old two days before a day. A live order would be placed against the live book. So some of the
adverse selection measured here comes from the stale reference and not from the strategy. That
overstates the cost, which is the safe direction, but it is a limit of a backtest on prices without
depth.

**Kalshi.** The plan called for the same test on Kalshi's temperature markets as an independent
check. I did not do it.

## Reproducing it

```bash
uv sync                  # environment from uv.lock
make test                # 100 known-answer tests
make report              # the figures and models/metrics.json, from the committed reports
make data                # rebuild data/ from the sources: hours, 36 GB of fills streamed
make train               # model, ranking, backtest and timing study, writes reports/
make notebooks           # execute the notebooks in place
```

`make report` is the only stage that runs without data. Every number on this page is read off a
table in `reports/`, so the figures cannot drift from the reports, and CI and the Docker image run it
with nothing mounted. `make data` and `make train` need the datasets described in `data/README.md`;
every load stage is resumable. The holdout was run once with
`python -m weather_edge model --stations EGLC --decision-hours 12 --leads 3 --holdout` and its
output is committed. Running it again would not make it a holdout.

```bash
docker build -t weather-edge . && docker run --rm -v "$(pwd)/reports:/app/reports" weather-edge
```

`docs/research-log.md` is the working document. Every hypothesis was written down before it was
tested, and every test run is logged with its data and its result, T1 to T19, including the ones
that failed.

## Layout

```
notebooks/          01 the market, 02 the target, 03 the model, 04 the money (kept with outputs)
src/weather_edge/
  config.py         paths and the holdout date
  markets.py        Gamma inventory, rules parsing, resolutions
  prices.py         CLOB price history per bucket
  trades.py         on-chain fills from the Hugging Face dataset
  observations.py   METAR archive, the displayed-value rule, the resolution match
  labels.py         the target per station-day
  forecasts.py      GRIB byte-range extraction with publication times
  market_checks.py  calibration, taker losses, price sums
  pilot_nyc.py      the first one-city chain, kept for its bucket and bootstrap helpers
  model.py          features, EMOS by CRPS, calibration, market scoring, the holdout switch
  backtest.py       maker orders with fills from the tape
  timing.py         price reaction to run publication
  plots.py          figures and metrics from the reports
  collector.py      live books, observations and forecasts (systemd unit in deploy/)
  paper_trader.py   paper orders against live books (systemd unit in deploy/)
  __main__.py       python -m weather_edge <stage>
tests/weather_edge/ one test module per package module
reports/            markdown output of every stage; figures/ the plots on this page
models/             metrics.json and the last fitted EMOS parameters
docs/               the research log
deploy/             systemd units
```

The notebooks are where the analysis was done. The package is the tested code that produced the
reports, and the notebooks import it rather than repeating it.

## Licence and attribution

MIT. Market data from Polymarket's public APIs and the
[SII-WANGZJ/Polymarket_data](https://huggingface.co/datasets/SII-WANGZJ/Polymarket_data) fills
dataset. Observations from the Iowa Environmental Mesonet ASOS archive. Forecasts from ECMWF open
data (CC-BY 4.0, via its Google Cloud mirror) and NOAA GFS, GEFS and NBM on AWS Open Data. Not
associated with Polymarket or any weather service.
