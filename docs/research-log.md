# Research log

My working document for this project: what was decided, what was verified, every hypothesis and test run, in the order it happened. Facts marked "verify" may have changed since; check the live source before relying on them.

## 1. Goal

Find out, with data, whether a statistical edge exists in Polymarket daily temperature markets ("Highest temperature in <city> on <date>?"), and if it does, trade it systematically.

Constraints:
- Starting capital for live trading: 200 USD. The first live phase is validation, not income.
- Infrastructure: local machine (VS Code) for research, backtests and model training. AWS free plan with 100 USD credits for the always-on collector and later the paper/live trader.
- Keep running costs near zero until paper trading shows an edge.

## 2. Working rules

- Decide the success criteria before looking at results, and log every test run against the hypotheses register. No unlogged experiments.
- Point-in-time correctness everywhere: a decision at time t may use only data that was public at t.
- One consolidated report per phase, committed, with the command that produced it.
- Only reputable sources for research: official documentation, well-cited papers, widely used repositories.
- No time estimates for building; the only timelines that mean anything are paper-trading durations.

## 3. Why this strategy (research summary)

Findings that shaped the choice, from 2025-2026 studies of Polymarket and Kalshi trade data:
- Profits are highly concentrated. Akey, Grégoire, Harvie, Martineau (SSRN/CEPR 2026, "Who Wins and Who Loses in Prediction Markets?"): top 1% of profitable users capture 76.5% of profits; winners mostly provide liquidity with limit orders, losers mostly take liquidity.
- Skill exists and persists. Gómez-Cram, Guo, Jensen, Kung (LBS/Yale 2026, "Prediction Market Accuracy: Crowd Wisdom or Informed Minority?"): about 3% of accounts are skilled; skilled traders react fast to public news, trade against behavioral biases and correct pricing violations; skill classification persists out of sample far more than for mutual funds.
- Makers beat takers. Becker (2026, "The Microstructure of Wealth Transfer in Prediction Markets", 72M Kalshi trades) and Bürgi, Deng, Whelan ("Makers and Takers: The Economics of the Kalshi Prediction Market"): systematic transfer from takers to makers; strongest in high-engagement categories.
- Favorite-longshot bias. Cardozo and Rivero-Wildemauwe (arXiv 2609.12878, 588M Polymarket trades): purchases below 10c lose heavily, purchases at or above 90c earn slightly positive returns; the effect depends on category (present in Crypto and Politics, absent in Sports).
- Pure arbitrage is mostly competed away and capacity-limited (IMDEA arXiv 2508.03474; UCLA arXiv 2605.00864). Not a focus here.

Why weather: repetitive daily markets, objective public data, a clear place for a data-science edge (calibrated probabilities for the exact resolution definition), and plenty of quirks most traders ignore. Always trade as a maker where possible.

## 4. Market mechanics (verify all against live docs and each market's Rules text)

### 4.1 Resolution
- Current Polymarket US temperature markets resolve on the highest value in the "Temp" column of NOAA's weather.gov time series for one named station (for example NYC = LaGuardia, KLGA; Houston uses KHOU; Miami uses Miami Intl), in whole degrees F. International markets use the same NOAA page in whole degrees C (for example Tokyo = Haneda, RJTT).
- Fallback: if NOAA data is unavailable by 11:59 PM ET the following day, the Weather Underground Daily Observations table is used.
- Revisions count only until the first datapoint of the following date is published.
- The day is local clock time.
- The resolution source has changed over time. Older markets resolved on Weather Underground station history. Some markets may still use WU; Hong Kong uses the Hong Kong Observatory. Every historical market must be graded with the rule that applied to it, taken from its own rules text.
- Resolution disputes go through the UMA optimistic oracle (proposal, 2-hour challenge window, token-holder vote on dispute). Rare for clean temperature markets but a tail risk.
- Kalshi temperature markets resolve on the official NWS Daily Climate Report (CLI), which can differ from the displayed series by 1F or more because it captures peaks from 6-hour max and DSM data. Kalshi and Polymarket can therefore resolve differently for the same station and day.

### 4.2 The rounding pipeline (critical)
- ASOS stations store whole-degree Fahrenheit internally. METARs report whole-degree Celsius, plus a T-group with tenths of Celsius when present. Websites often convert rounded Celsius back to Fahrenheit and round again, producing values that differ from what the station recorded (sources: NWS Chicago "Weather Observations and NWS Climate Products FAQ"; Iowa Environmental Mesonet METAR dataset notes and "Wagering on ASOS Temperatures").
- Routine METARs are typically recorded near :52 past the hour; SPECI reports fire on significant changes. Only reported observations appear in the resolution series, so a peak between reports does not count.
- Hypothesis to test: if displayed F values derive from whole-degree C, some F integers become rare or impossible (23C = 73.4F -> 73, 24C = 75.2F -> 75, so 74 is skipped). This would make some buckets structurally less likely than any forecast implies.

### 4.3 Fees and incentives (verify in docs.polymarket.com and help.polymarket.com)
- Weather is a fee-enabled category. Taker fee per fill = theta x shares x p x (1 - p), peaking at 50c. theta varies by category.
- Maker (resting limit) orders pay no fee and earn Maker Rebates: a category-specific share of taker fees, paid daily, proportional to your share of filled maker liquidity in each market.
- Taker Rebate Program: tiered rebates on taker fees by 30-day volume.
- Liquidity Rewards: separate program paying for resting orders near the midpoint. Check whether weather markets are included and any minimum size thresholds.
- Check the minimum order size. Quarter-Kelly sizing on 200 USD can produce orders below it.
- Verified 2026-09-30 (docs.polymarket.com/trading/fees, programs/maker-rebates, programs/liquidity-rewards; Gamma dump 2026-09-29): Weather taker fee rate 0.05, maker fee 0, fee = shares x 0.05 x p x (1 - p) charged to the taker at match time (1.25c per share at 50c, 0.45c at 10c or 90c). Maker rebate pool 25% of taker fees per market per day, split by fee-curve-weighted filled maker volume, paid daily in pUSD, 1 USD minimum payout: a maker earns back about 25% of the fee its fills generated. Minimum order size 5 shares (orderMinSize 5 on all 118,990 bucket markets); tick 0.001 on 118,144 markets, 0.01 on 846. Liquidity rewards: weather buckets carry a config (min size 20 to 100 shares, max spread 4.5c from the midpoint) but almost no reward pool (33 of 16,819 markets ending 2026-09 have a daily rate), so they do not pay for weather today.

## 5. Data sources

Market data:
- Polymarket historical dataset: github.com/SII-WANGZJ/Polymarket_data (about 107 GB, 1B+ trades, tools for fetching fresh data via API). Contains trades, not full order book snapshots.
- Jon Becker's public prediction market dataset and analysis (jbecker.dev; about 36 GB, 72M Kalshi trades). Use Kalshi temperature markets as a second, independent test bed.
- Polymarket APIs for live data: gamma-api.polymarket.com (market metadata), clob.polymarket.com (order books, orders), data-api.polymarket.com (trades, positions). Confirm endpoints in docs.polymarket.com.

Observations:
- Iowa Environmental Mesonet (mesonet.agron.iastate.edu) ASOS/METAR archive for historical observations; also has DSM daily summaries and 1-minute ASOS data (delayed). Note IEM's notes on precision and local standard time.
- weather.gov time series (weather.gov/wrh/timeseries?site=<ICAO>) is the live resolution source. aviationweather.gov for live METARs.

Forecasts:
- Open-Meteo (open-meteo.com):
  - Previous Runs API: variables at fixed lead-time offsets of 1 to 7 days; most models archived from January 2024, GFS 2m temperature from March 2021. Use this for training.
  - Historical Forecast API: stitches the first hours of each run into one series. Do NOT use it for training; it creates look-ahead bias.
  - Single Runs API: full individual runs by init time (ECMWF IFS HRES from March 2024).
  - Ensemble API for ensemble members.
  - Free tier is for non-commercial use up to 10,000 calls/day. Trading likely counts as commercial; check terms before live trading. Self-hosting is an option.
- ECMWF open data (data.ecmwf.int; Python package ecmwf-opendata): IFS ENS and AIFS ENS v2 (51 members, 4 runs/day since May 2026). Free.
- NOAA National Blend of Models (NBM, v5.0 since May 2026): calibrated probabilistic daily max temperature as percentiles (NBP text bulletin elements TXNP1, TXNP2, TXNP5, TXNP7, TXNP9 = 10th/25th/50th/75th/90th, plus mean TXNMN and std TXNSD) for about 9,000 stations including most US airports. Note NBM targets the official max, not the displayed series. Historical NBM text archives must be located (verify availability).
- HRRR (US, hourly updates) via Open-Meteo for same-day updating.

## 6. Repos (vetted status)

Use or study:
- evan-kolberg/prediction-market-backtesting (about 1.2k stars, active): backtesting on historical markets.
- SII-WANGZJ/Polymarket_data (about 850 stars): main historical dataset.
- ent0n29/polybot (about 1k stars): analyzing trading behavior of specific wallets. Use for competitor analysis of top weather wallets.
- lihanyu81/polymarket_lp_tool (about 550 stars): reference for liquidity-reward quoting logic.
- yangyuan-zhen/PolyWeather (about 320 stars, very active): reference for weather data sources (METAR, forecasts). Data tool, not proof of profit.
- aarora4/Awesome-Prediction-Market-Tools: link list for discovery.
- pydantic/pydantic-ai: optional, only if an agent component is ever needed.

Do not use:
- recogardtech/AutoPilotPM. Low stars, rebranded copy of another project, recommends installing a prebuilt release package that touches wallets. Treat as unsafe.

Security rules for any third-party code: build from source, never install prebuilt release binaries or packages; read how private keys are handled before entering one; use a dedicated wallet holding only the trading funds.

## 7. Architecture

- One Python project in one repo. Local DuckDB database for research. Parquet for bulk and time-series data.
- Core tables:
  - markets: market_id, event_id, city, station (ICAO), date, unit (F/C), bucket definitions, rules_text, resolution_source (as parsed from rules), resolved_bucket, created_at, closed_at.
  - rules_history: market_id, fetched_at, rules_text hash, rules_text. Flag any change.
  - observations: station, obs_time_utc, raw METAR, temp_c, t_group_c, displayed value as the resolution source would show it, report type (routine/SPECI).
  - forecasts: station, model, init_time, available_time (when it was actually published), valid_date, lead, variable, value or member values/percentiles.
  - prices: market_id, bucket, timestamp, trade price, side, size (from dataset); later order book snapshots from the collector.
  - orders_log: every paper or live order with model version, inputs snapshot id, probability, price, size, fill, outcome.
- Point-in-time rule: every backtest decision at time t may only use forecasts with available_time <= t, observations reported <= t, and prices <= t. Model init times are not availability times.
- Reproducibility: version data snapshots and model artifacts; every order references the model version and input snapshot that produced it.
- AWS: one small instance runs only the collector (and later the paper/live trader). Store order book snapshots as compressed Parquet in S3, only for screened cities. Heavy compute stays local. Set a billing alert and check when credits and the free plan expire.

## 8. Phases

Each phase has a gate. Do not proceed past a failed gate without an explicit decision.

### Phase 0: Inventory
- Extract all temperature markets from the dataset: city, date, station, buckets, rules text, resolution, full trade history.
- Count markets per city per month. Group by resolution source era.
- Deliverable: table of cities with history length, volume, and rule eras.
- Gate: identify cities with enough history to evaluate. Park the rest.

### Phase 1: Market-side quick checks (uses dataset resolutions, no ground-truth rebuild needed)
- Calibration of market prices vs outcomes, per city and by hours-before-close.
- Extreme buckets: are low-priced buckets overpriced, high-priced underpriced (favorite-longshot), per city.
- Sum of YES prices across buckets over time.
- Maker vs taker returns in weather markets.
- Traded volume at mispriced levels (capacity estimate).
- Deliverable: short report. Kill ideas that show nothing.

### Phase 2: Live collector (start early; it accumulates data only with calendar time)
- On AWS: poll order books for active temperature markets in candidate cities, fresh forecasts with their publish times, and new observations every few minutes. Save rules text and flag changes.
- Must be robust: restarts, logging, failure alerts.

### Phase 3: Ground truth
- For each candidate city, rebuild each market's resolved high from IEM observations using the rule of its era (station, local day, displayed-value transform, WU where applicable).
- Compare with actual Polymarket resolutions. Investigate every mismatch; each is a resolution quirk to encode.
- Test the rounding hypothesis: histogram of resolved highs per station; look for impossible or rare values.
- Also measure how often the daily high occurs before sunrise or around midnight (frontal days).
- Gate: near-perfect match rate. Nothing downstream is valid otherwise.

### Phase 4: Build end to end for ONE city first
- Run the full chain (markets, ground truth, forecasts, baseline model, backtest) for one city to flush out pipeline bugs. Then generalize.

### Phase 5: Baselines and baseline model
- Training data: all days since forecasts exist (January 2024 for most Open-Meteo models), not only market days. Market days are only needed for edge evaluation.
- Baselines: climatology, raw ensemble counting, NBM percentiles used directly (US).
- Model: Gaussian EMOS (Gneiting et al. 2005): mean = regression on ensemble/model forecasts, variance linear in ensemble spread, fit by minimizing CRPS, per station and lead time, rolling seasonal training window. Try pooled-across-stations with station features vs per-station.
- Convert continuous distribution to bucket probabilities by simulating the displayed-value transform. Alternative to test: model the resolved integer directly.
- Evaluation: CRPS, Brier score per bucket, log loss, reliability diagrams, PIT histograms.

### Phase 6: City ranking
- Compare model probabilities to market prices at the same timestamps (point-in-time).
- Score specifically on cases where the model disagrees with the market; that is where trades happen.
- Rank cities by hypothetical edge per trade, weighted by liquidity and competition (number of active maker wallets, spread).
- Include Kalshi temperature markets as an independent check.
- Gate: pre-defined success criteria (section 10). If no city passes, stop.

### Phase 7: Backtest survivors
- Only top cities and ideas that survived Phases 1 and 3.
- Walk-forward: train on past, test on next month, roll. Plus a final holdout of the most recent months, used once at the end.
- Maker-only orders, conservative fill model (assume fills are more likely when you are wrong), fees and rebates, minimum order size.
- Sizing: fractional Kelly (quarter or less), treating all buckets of one event as one position; cap exposure per event, per city, per day; account for correlation across nearby days and cities.
- Quote management: cancel or widen quotes before known information events (the :52 METAR, model releases, fast afternoon warming).

### Phase 8: Upgrades (each kept only if it improves calibration on disagreement cases)
- Intraday model: condition on running max so far, current reading, time relative to typical peak, latest HRRR, upwind neighboring stations.
- Gradient-boosted distributional model (for example gradient-boosted EMOS or quantile regression forests), features: several models' forecasts, ensemble spread, cloud cover, precipitation timing, wind direction, dew point, recent errors.
- Stacking with market price as an input (model alone vs market alone vs blend).
- Regime features: post-rain days, frontal passages, snow cover.
- Model release timing: measure whether prices lag new ECMWF/GFS runs.

### Phase 9: Paper trading, 2 to 4 weeks
- Full live pipeline on AWS logging hypothetical orders against the real order book.
- Tests the speed-based ideas history cannot measure.
- Compare paper results with backtest expectations.

### Phase 10: Live, small
- 200 USD, one or two cities, dedicated wallet, hard caps, kill switch.
- Weekly comparison of live vs paper results. Scale only if they match.
- Pre-set rules to pause a city when live calibration or PnL degrades (edge decay; weather markets attract more bots over time).

## 9. Hypotheses register (write down before testing; log every test run)

H1 Market prices in some cities are poorly calibrated at specific hours before close.
H2 Extreme (low-priced) buckets are overpriced in weather markets.
H3 Some displayed F values are rare or impossible per station due to the C/F rounding pipeline, and markets misprice those buckets.
H4 Markets underreact to highs locked in before sunrise on frontal days.
H5 Post-processed forecasts beat market prices in cities with local effects (sea breeze, marine layer, downslope winds, lake effects).
H6 Prices lag new model runs.
H7 Prices lag observations (the :52 METAR, SPECI, neighboring stations).
H8 International cities (fewer US-built bots, trading in US night hours) are less efficient.
H9 Maker quoting in weather markets earns positive returns after adverse selection, including rebates.
H10 Blending model with market price beats either alone.
H11 Late favorites are overpriced: YES bought by takers at 65c to 95c loses 2 to 5c per share (T4). Test whether a maker should quote only the sell side there, and whether it persists after fees.
H14 Forecast edge lives at long horizons: two days out (lead 3) a plain EMOS on two global models beats the market on disagreement buckets (T9), one day out it does not. Test whether that edge survives realistic fills at the thin early books, and whether ensembles (IFS ENS, GEFS) and fresher cycles (06Z, 18Z) extend it to lead 2.
H15 Same-day edge needs observations, not forecasts: at noon local the market beats every forecast-only model by a wide margin (T9). Test models that condition on the running maximum, the latest METAR and the forecast residual so far (Phase 8 intraday), evaluated at fixed local times from 06:00.
H13 Lowest-bracket resolution risk: when the NOAA page has no data for the day, the market resolves to the lowest bucket (Panama City three times in Aug and Sep 2026). Test whether stations with flaky NOAA coverage make the lowest bucket systematically underpriced, and whether the missing-data cases are predictable (MPMG had 5 to 25 reports on those days).
H12 Adverse selection concentrates in taker sells of 35c to 90c buckets (T4): those sellers know the running max. Test quote withdrawal rules around observation times against this flow.
H16 Same-day and one-day edge needs hourly high-resolution guidance: the market at 06:00 local already beats global forecasts plus the running maximum (T11), and 3-hourly global steps miss the afternoon peak. Test hourly GFS steps (f000 to f120), HRRR (3 km, hourly runs, AWS noaa-hrrr-bdp-pds) and the NBM daily maximum product (AWS noaa-nbm-grib2-pds) as EMOS inputs under the same point-in-time rules, NYC first.
H17 The market lags model releases: when a new ECMWF or GFS run becomes public and moves the forecast high, the market's implied high takes minutes to hours to follow, leaving a window for a fast quoter. The daily-decision model of Phases 5 to 7 never measured timing. Test with the 1-minute price history and the runs' real publication times (Last-Modified), London and NYC, before the holdout.

Add new hypotheses to this list before testing them, not after.

Test log (every run gets a line: id, hypothesis, data, result):
- T1 (H1) Calibration by hours before local midnight, per city and era. Data: CLOB price history, 5-minute fidelity, 117,514 resolved bucket markets, 2025-01-20 to 2026-09-29 (weather_edge/prices.py, weather_edge/market_checks.py). Result 2026-09-30: the market is well calibrated. Brier 0.061 at 24h and 0.055 at 12h against a base rate of 0.087 to 0.091, then 0.003 at 6h and 0.0009 at 3h, so the day is decided by 18:00 local. Reliability bias at 24h: bands 2c to 35c overpriced by 0.7 to 1.3c, bands 50c to 80c underpriced by about 3c (ci95 2 to 4c); at 12h all bands within 1.3c. No city has a bias beyond its ci95 at 12h; only NYC at 24h (minus 1.1c, ci95 0.8c). Brier by city ranges 0.047 (Tel Aviv, Austin) to 0.077 (NYC, London) at 24h. Verdict: H1 killed as a stand-alone idea; any edge must come from forecast skill before noon local or from microstructure.
- T2 (H2) Return of buying YES by bucket position and price band at 12h and 3h. Result 2026-09-30: middle buckets flat. "X or higher" edge buckets priced 5c to 35c lose 3 to 4.5c per share (n 220 to 310 per band, ci95 2 to 5c); the "X or below" edge is too thin to say (n under 130 per band). Verdict: weak, borderline significant overpricing of the warm edge; re-test as a model feature, not a stand-alone trade.
- T3 (check) Sum of YES mid prices per event. Result 2026-09-30: mean 1.045 at 30h, 1.043 at 24h, 1.027 at 12h, 1.007 from 6h; 33% of events above 1.05 at 24h, 7% below 0.95 at 12h. Reads as spread width of about 4% of the book early in the day; not a tradable arbitrage at mid.
- T4 (H9) Taker profit per fill, gross of fees. Data: 27.9M dataset fills (complete through 2026-04, about 80% coverage after). Result 2026-09-30: in complete months takers lose 0.29c per share in the WU era (1.33M USD on 454M shares), 0.40c in the HKO era; makers as a group earn that. London minus 0.68c, NYC minus 0.45c, Seoul minus 0.33c per share for takers; Atlanta, Wellington, Chicago about flat. By band: takers who buy YES at 65c to 95c lose 2 to 5c per share; takers who sell YES at 35c to 90c earn 1 to 4c per share (informed selling, the adverse-selection zone for a maker); takers selling YES under 35c lose 0.6 to 0.8c. Largest maker earned 87K USD on 12.8M shares (0.68c per share); most large makers are between 0 and 0.3c per share, some negative. Verdict: H9 supported gross of fees at the aggregate level; the margin is thin and depends on avoiding mid-priced sells.
- T6 (gate, Phase 3) Rebuilt highs vs Polymarket resolutions. Data: IEM ASOS/METAR 2025 to 2026, 1,345,000 reports, 58 stations, 11,037 resolved events (weather_edge/observations.py, reports/phase3_ground_truth.md). Result 2026-09-30, after excluding the 2026-05-17 to 05-19 duplicate events, Shenzhen, Jinan (not in IEM) and two VHHH days: Weather Underground era F markets 100.0% (2,820 events) with the T-group tenths transform (whole-degree conversion only 82.6%); NOAA era F 99.75% (407) with tenths; Weather Underground era C 99.4% (5,601) with whole degrees, 99.89% without Seoul; NOAA era C 98.9% (1,772) with routine reports only; Hong Kong 100% of the 166 days with a published Observatory maximum using floor(max), i.e. a bucket "33°C" covers 33.0 to 33.9. Gate passed for every city except the parked ones below. Remaining misses: Panama City resolved to the lowest bracket three times when NOAA data was missing (2026-08-30 to 09-01); five Asian cities resolved one degree low on 2026-09-20; Taipei's RCTP fortnight (6 of 13); single days in Sao Paulo, Lagos, Jakarta, London, Madrid, Miami. SPECI reports count in the NOAA table for Mexico City, Toronto, Cape Town and Panama City, but Moscow's off-minute reports (:24, :50) do not (11 of 11 fixed by routine-only), so the transform is per station.
- T7 (H3) Result 2026-09-30: killed. US F values come from the T-group tenths (100% match), so no F integer is structurally impossible; C markets show whole METAR degrees directly. The rounding pipeline is not a source of mispriced buckets.
- T8 (check, feeds H4) Result 2026-09-30: 5.0% of event days have their maximum before 06:00 local and 0.3% at or after 22:00. Toronto 14.5%, Wellington 14.3%, Chongqing 12.9%, NYC 11.0%, most tropical cities near 0.
- T9 (H5, Phase 4) NYC end to end on ECMWF IFS 0.25 and GFS 0.25 open archives (00Z and 12Z runs, 3-hourly steps, real publication times; weather_edge/forecasts.py, weather_edge/pilot_nyc.py --source open). 610 forecast days, 552 labels, 11,493 market buckets, 2025-01-22 to 2026-07-31; holdout from 2026-08-01 untouched. Result 2026-09-30: at the same-day noon decision (lead 1) the market is far sharper than any forecast-only model: Brier 0.074 (market) vs 0.101 (EMOS-lite) vs 0.115 (raw two-model) vs 0.158 (30-day climatology); on disagreement buckets the market wins by 0.066 Brier (ci 0.053 to 0.078). Lead 2 (noon the day before): market 0.087 vs EMOS 0.093, market wins by 0.017 (ci 0.007 to 0.027). Lead 3 (noon two days before): EMOS 0.101 vs market 0.108, and on disagreement buckets EMOS beats the market by 0.022 (ci 0.011 to 0.033, 1,214 buckets on 406 days). The maker-only skeleton loses money at every lead (0.03 to 0.06 USD per filled share) because fills concentrate on losing buckets under touch fills and the 50% haircut. Verdict: a forecast-only model does not beat the market once the day has started; the market at noon already holds the morning's observations. The only signal is two days out, where books are thin. Pipeline bugs flushed: per-step publication times split runs (fixed: a run counts when all in-day steps are public), Timestamp vs date keys.
- T5 (check) Shares per city-day. Result 2026-09-30: Seoul 240K, Shanghai 210K, Hong Kong 200K, London 170K (median 120K), NYC 140K shares per day; 80% or more of shares trade at YES prices under 10c or over 90c; 3,500 to 8,000 fills per day in the big cities. Capacity is not the constraint for 200 USD.
- T10 (H5, H14, Phase 5) EMOS fitted by Gaussian CRPS instead of least squares (weather_edge/model.py): rolling 90-day fit per station and lead, mean = a0 + sum a_i model_i over ECMWF, GFS and GEFS mean, variance = exp(b0) + exp(b1) GEFS spread^2, bucket probabilities from the normal CDF at half-integer edges; all four daily cycles with real publication times, decision noon local, labels from daily_truth (every station-day, not only market days). Scores: CRPS, MAE, PIT histogram and 90% coverage against raw multi-model and 30-day climatology; Brier against the market on disagreement buckets with day-bootstrap CI (section 10). Holdout from 2026-08-01 untouched. Result 2026-09-30 (NYC, 577 days, 2025-01-22 to 2026-07-31, reports/phase5_emos.md): lead 3 EMOS beats the market on disagreement buckets at every decision hour and more the earlier the decision: +0.048 Brier at 06:00 (ci 0.034 to 0.060, 709 buckets, 213 days), +0.037 at 08:00, +0.023 at 10:00, +0.023 at noon (ci 0.012 to 0.034, 1,260 buckets, 408 days). Lead 2: market minus EMOS -0.007 at 06:00 (ci -0.016 to +0.002), -0.011 at 08:00, -0.014 at 10:00, -0.015 at noon (Phase 4 two models: -0.017). Lead 1: market wins by 0.053 to 0.063. CRPS (C) lead 1/2/3 at noon: EMOS 0.79/0.92/1.03, raw 0.95/1.07/1.17, climatology 3.1/3.2/3.3. EMOS is underdispersed (90% interval covers 81 to 83%, U-shaped PIT); CRPS fitting and the GEFS spread changed little versus least squares. Verdict: H14 holds (edge two days out, larger when books are thinner); take lead 3 to the fill-calibrated backtest. Fix dispersion (heavier tails or inflation) before that.
- T11 (H15, Phase 5) Same-day model conditioned on observations (weather_edge/model.py, model obs): final displayed max y = max(R, Z), R = running max from METARs observed at least 5 minutes before the decision, Z ~ N(a0 + a.rest + c last_obs, sigma^2) with rest = each source's forecast maximum over the steps after the decision, fit by left-censored Gaussian likelihood over the trailing 90 days (days whose maximum was already in are censored at R). Decision hours 06, 08, 10 and 12 local at NYC, scored as T10 against the market at the same times. Result 2026-09-30: the observations help the model (lead 1 CRPS 0.80 C to 0.73 C at 06:00 and to 0.61 C at noon; 90% coverage 86 to 89%) but the market still wins on disagreement buckets at every hour: 0.043 at 06:00 (ci 0.032 to 0.055), 0.044 at 08:00, 0.045 at 10:00, 0.042 at noon (ci 0.028 to 0.055). Market Brier 0.071 to 0.075 at every hour. Verdict: H15 as stated is rejected for NYC with global-model inputs; the market at 06:00 already beats forecasts plus the running maximum. The 3-hourly global steps miss the afternoon peak; see H16.
- T12 (H14, Phase 5 fix) EMOS with a Student t predictive instead of a normal: nu fitted by CRPS (closed form for the t, checked against numeric integration) together with the other parameters, bucket probabilities from the t CDF. Purpose: the normal EMOS in T10 covers 81 to 83% with a nominal 90% interval. Same data and scoring as T10. Result 2026-09-30 (reports/phase5_emos.md): the t alone changes nothing, nu runs to its upper bound (the in-sample fit is overconfident, not thin-tailed). Added an out-of-sample scale calibration: the predictive scale is multiplied by the root mean square of the last 90 standardized errors known at the decision. Coverage 88 to 92%, flat PIT, CRPS about 0.01 C worse. Market minus model on disagreement buckets, NYC: lead 3 +0.037 at 06:00 (ci 0.024 to 0.050), +0.032 at 08:00, +0.017 at 10:00, +0.021 at noon (ci 0.011 to 0.031); lead 2 -0.011 to -0.018; lead 1 -0.050 to -0.062, with observations -0.041 to -0.045. Verdict: calibration fixed, conclusions of T10 and T11 unchanged; this is the model used from here on.
- T13 (H14, Phase 7) Backtest of the lead-3 EMOS signal on NYC with fills from the trade tape (dataset fills through 2026-07-20): at the decision (06:00 and 12:00 local two days before the day) bid on buckets where the model is at least 10c above the last price at min(last price - 1c, model - 10c), and the mirror on the NO side; 5 shares per order, resting 24 h. Fill models: touch (any taker print at or through the price), through (a print strictly beyond the price, which proves the level was cleared), each also with a 50% haircut on winning fills. Maker fee zero, rebates ignored. Reports PnL per filled share, per day with a day bootstrap, by month and side, and the taker volume that traded through the level as capacity. Holdout excluded. Result 2026-09-30 (reports/phase7_backtest.md, t EMOS): 06:00 decision 701 orders, 233 through fills, 1,119 shares, +93 USD, +8.3c per share (PnL per order 90% day bootstrap +0.17 to +0.64 USD); noon decision 1,246 orders, 505 fills, 2,403 shares, +60 USD, +2.5c per share (ci -0.06 to +0.30). With the 50% haircut on winning fills: -3.1c and -8.7c per share. Model expects about 20c per share on filled orders and realizes 8c or less: 60% adverse selection. NO side carries it (79% of fills win, +9.4c at 06:00); YES side wins 16 to 24% of fills. 2025-02 to 04 contribute 56 of the 93 USD at 06:00; from 2025-05 about +4c per share. Capacity 139k to 227k shares printed beyond the levels. Rerun with the calibrated spread (T12): 06:00 748 orders, 272 through fills, +56 USD, +4.3c per share (ci -0.00 to +0.44 USD per order); noon 1,279 orders, 564 fills, +25 USD, +0.9c per share; with the haircut -8.6c and -11.6c. Verdict: Brier criterion passed, PnL criterion not passed at conservative fills; the two-days-out edge is real in probability terms but not tradeable on its own with maker orders at 10c of edge.
- T14 (Phase 6 gate) City ranking: the Phase 5 chain (t EMOS, all sources and cycles, decision noon local, leads 1 to 3, same-day observation model) on every station with at least 200 resolved market days before the holdout: London EGLC, NYC KLGA, Dallas KDAL, Seoul RKSI, Toronto CYYZ, Atlanta KATL, Seattle KSEA, Buenos Aires SAEZ. Ranked by market-minus-model Brier on disagreement buckets per lead with the day-bootstrap CI (section 10). Report reports/phase6_cities.md. Result 2026-09-30: same shape in every city: two days out the model is at least level with the market, one day out the market is level or slightly ahead, same day the market wins by 0.03 to 0.07 Brier and the observation model closes about a third of the gap. Lead 3, market minus model on disagreement buckets: London +0.042 (ci 0.031 to 0.053, 364 days), NYC +0.021 (0.011 to 0.031, 408 days), Atlanta +0.016 (-0.003 to 0.036), Buenos Aires +0.015, Seattle +0.009, Toronto +0.007, Seoul +0.044 on 39 buckets, Dallas -0.014; the six cities listed since 2025-12 have about 165 lead-3 days and intervals including zero. Lead 2 negative or zero everywhere (-0.006 to -0.023). Newer cities have a sharper market (lead 1 Brier 0.057 to 0.065 vs 0.073 in London and NYC). Verdict: London and NYC pass the Brier criterion at lead 3, none passes on PnL yet; London goes to the tape backtest (T16).
- T16 (H14, Phase 7) London EGLC lead-3 backtest with tape fills, same logic and fill models as T13, decision hours 06 and 12 local two days before. Result 2026-09-30 (reports/phase7_backtest.md): noon 1,041 orders, 412 through fills, 1,993 shares, +110 USD, +5.5c per share, PnL per order 90% day bootstrap +0.08 to +0.45 USD, 15 of 18 months positive, not front-loaded; 06:00 383 orders, 164 fills, +3.2c per share (ci -0.14 to +0.44). Model expects 18.6c per filled share (70% adverse selection). NO side +6.7c (71% of fills win), YES side +2.1c (ci around zero). With the 50% haircut on winning fills -7.1c and -7.9c. Capacity about 470 shares printed beyond the level per filled order. Verdict: marginal pass; PnL positive with an interval excluding zero on through fills, negative under the haircut. London noon, NO side, is the paper-trading candidate.
- T15 (H16, Phase 5) NBM as an EMOS input: NBM core 12-hour daytime maximum (12Z to 00Z window) and its ensemble standard deviation at 00, 06, 12 and 18Z with real publication times (weather_edge/forecasts.py --models nbm_tmax nbm_tmax_spread), added to ECMWF, GFS and GEFS in the Phase 5 chain for NYC at decision hours 06, 08, 10 and 12 local; same scoring as T10 and T11, and the lead-3 backtest of T13 rerun if lead 1 or 2 changes. Result 2026-09-30: no gain at any hour or lead. Lead 1 EMOS CRPS 0.80 to 0.81 C with NBM against 0.79 to 0.81 without, observation model 0.60 to 0.74 C either way; market minus model on disagreement buckets within 0.002 of the run without NBM at every hour (lead 1 -0.051 to -0.062, observation model -0.042 to -0.045, lead 2 -0.014 to -0.019, lead 3 +0.019 to +0.038). The EMOS slopes put no weight on the NBM daytime maximum once ECMWF, GFS and GEFS are in. Verdict: H16 in its NBM form is rejected for NYC; NBM already blends HRRR and the NWS guidance, so the hourly HRRR variant is parked. The same-day gap to the market is not a forecast-quality problem that public guidance closes.
- T17 (holdout, one shot) Final choice before paper trading: calibrated t EMOS on ECMWF, GFS and GEFS, lead 3, decision noon local, London and NYC. Scored once on the untouched holdout 2026-08-01 to 2026-09-28 (59 resolved days per city; the trade tape ends 2026-07-20, so only the Brier comparison against the market runs there). Training stays walk-forward on data before each day. Pass: market minus model Brier on disagreement buckets above zero. Report reports/phase5_holdout.md. Result 2026-09-30, run once: London 57 days, 627 buckets, 69 disagreement buckets, market minus model -0.007 (ci -0.036 to +0.021), market Brier 0.0670 vs model 0.0666; NYC 29 days (markets listed only 27 h ahead in August), 319 buckets, -0.038 (ci -0.078 to +0.005). The market two days out is far sharper than in-sample (Brier 0.067 and 0.062 vs 0.102 and 0.108) while the model's CRPS is as good or better; the edge vanished because the market caught up. KLGA's run included the NBM inputs (T15: immaterial). Verdict: FAIL on the holdout criterion. No tradeable edge demonstrated; paper trading would be a zero-stakes check only.
- T18 (Phase 9) Paper trader (weather_edge/paper_trader.py): London and NYC, noon local two days before, calibrated t EMOS at lead 3, post-only paper orders at 10c of edge against the live CLOB book, fills inferred from data-api prints (touch, through) and from the book, PnL per rule after resolution. Built and unit-tested 2026-09-30. Status: not started. After T17 failed the holdout it is a zero-stakes check only, not a path to live capital; run it only if a live confirmation of the negative result is wanted.
- T19 (H17, Phase 8) Event study of price reaction to run publication (weather_edge/timing.py): for every London and NYC market day before the holdout and every ECMWF and GFS run covering it, the change of the run's daily maximum against the previous run of the same model (in the market's unit) and the change of the market-implied expected high (probability-weighted bucket centres from as-of prices) from one hour before publication to 0, 5, 15, 30, 60, 120 and 240 minutes after, plus 30 minutes before as a control. Regression slope and correlation of market move on model move per window, by model and by how far ahead of the day the run was published. Pass for H17: the slope keeps rising for more than 30 minutes after publication with a move worth more than the spread. Report reports/phase8_timing.md. Result 2026-09-30: London 8,025 and NYC 8,331 run publications; slope of the market's implied-high move on the model's move is 0.00 at 15 minutes and 0.03 to 0.05 at four hours for the day-before and two-days-before horizons (0.10 same day), correlation at most 0.15; the market moves 0.25 to 0.5 F over four hours whether or not the run changed; sign agreement 44 to 60%; nothing before publication either. Verdict: H17 rejected. The market does not lag ECMWF and GFS releases, it does not respond to them; its price moves come from other information. No timing edge.

## 10. Success criteria (fix before looking at results)

A city/idea counts as an edge only if:
- Its Brier score beats the market's on cases where the model disagrees with the price, with a confidence interval excluding zero.
- Walk-forward PnL is positive after fees at conservative fills.
- It holds on the final holdout.
- Ideally it also appears on Kalshi data or in more than one city, unless there is a clear physical reason it is city-specific.

## 11. Risks and operations

- Resolution risk: rules changes (watch rules_history), WU fallback differences, UMA disputes.
- Adverse selection when quoting.
- Thin books: capacity may be small; measured in Phase 1.
- Security: dedicated trading wallet with limited funds; keys never in code or repo; build third-party code from source only.
- Ops: collector and trader on a server, restart on failure, alerts, kill switch.
- Costs: AWS billing alert; check credit/free plan expiry; Open-Meteo terms before live use.
- Record every paper and live trade from day one for accounting and taxes.

## 12. Open questions to verify first

- Answered 2026-09-29 by the live Phase 0 run (reports/phase0_inventory.md; 11,375 events, 118,990 bucket markets, 56 cities, 2025-01-22 to 2026-10-01, 916M USD volume): London and NYC since 2025-01-22 (615 and 613 days, 97M and 79M USD); Dallas, Seoul, Toronto, Atlanta, Seattle, Buenos Aires, Miami, Chicago, Los Angeles, Denver since early Dec 2025 (about 190 to 300 days); most other cities since Mar or Apr 2026 (about 170 to 210 days). 49 cities have at least 90 event-days. Hong Kong (46M USD) and Seoul (57M USD) are the biggest non-US books. Phoenix, DC, Dubai, Lagos, Jakarta were short-lived.
- Resolution eras (verified from rules text): almost every city switched from Weather Underground to the NOAA weather.gov hourly table on 2026-08-23 (US cohort) or 2026-08-24 (rest); Tel Aviv and Taipei on 2026-03-23, Shenzhen 2026-03-29, Moscow and Istanbul 2026-03-30. So the NOAA era is only weeks old and almost all backtest history is WU-era; the WU displayed-value transform matters most for Phase 3, the NOAA one for live trading. Hong Kong resolves on the Hong Kong Observatory since 2026-03-16. Station changes: Paris LFPG to LFPB 2026-04-19, Taipei CWA 46692 to RCTP (2026-03-23) to RCSS (2026-04-05), Denver KBKF with five KDEN days in Mar 2026. Seoul events are titled "Seoul (Incheon)" since 2026-07-29.
- Data quirks to encode in Phase 3: 149 events on 2026-05-17 to 05-19 carry an "arch-" slug; on 05-19 they were re-created, and the two events for one city-day resolved to different buckets (Atlanta 96-97F vs 89F or below). The tables count distinct city-days and list these in the issues section. One event (DC, Inauguration Day 2025-01-20) has no date in its title.
- Verified 2026-09-29 from real Gamma dumps found in public repos (NYC 2026-09-02 event 940515, London 2026-02-25 market 1427388, Seoul 2025-12-31 event 130716), stored in tests/fixtures/gamma_events_sample.jsonl:
  - Rules wording, NOAA era: "highest temperature recorded by NOAA at the LaGuardia Airport Station in degrees Fahrenheit on 2 Sep '26", source "the highest reading under the Temp column for all times on this day" at weather.gov/wrh/timeseries?site=klga (lowercase code), "resolve off of the Hourly Data provided using the Show Hourly Data button", WU Daily Observations table as fallback if NOAA data is unavailable by 11:59 PM ET next day, and "resolve to the lowest bracket" if no data at all by then. Whole degrees F. Revisions count until the first datapoint of the following date.
  - Rules wording, WU era: "recorded at the London City Airport Station in degrees Celsius", source wunderground.com/history/daily/gb/london/EGLC (URL ends at the station code). The WU era was still in use for international cities in 2026 (London Feb, Amsterdam Apr, Jinan May 2026); the era is per city, not global.
  - Gamma fields: each market and event carries resolutionSource (the URL), groupItemTitle (bucket label like "74-75°F", "69°F or below", "88°F or higher"; single degrees for C cities), outcomes/outcomePrices/clobTokenIds as JSON strings, volumeNum, closedTime like "2026-02-25 17:08:38+00", umaResolutionStatus, eventDate (the target local date), tags weather (id 84), daily-temperature, highest-temperature and a city tag, series like nyc-daily-weather. Questions read "Will the highest temperature in New York City be between 74-75°F on September 2?". "Lowest temperature" markets also exist (not in scope).
  - Parser validated on a 2,602-event, 22,894-bucket historical snapshot (31 cities, Dec 2025 to Apr 2026, from the public polymarket-tmax-lab repo): every bucket label parsed, unit found for all, exactly one winning bucket per closed event, station found for all. The earliest US markets (Dec 2025) cite wunderground.com/weather/<ICAO>; Paris changed station from LFPG to LFPB on 2026-04-19; London switched from whole degrees F to whole degrees C on 2025-12-11 (same station EGLC); NYC and London history goes back to at least 2025-01-22; Taipei resolves on Taiwan's Central Weather Administration station 46692 to one decimal place, so its buckets differ from the whole-degree cities.
  - UMA disputes are not rare: 74 of the 2,602 snapshot events carry "disputed" in umaResolutionStatuses (London 34 of 421, NYC 17 of 392). The markets table keeps a disputed flag and the report counts them per city; Phase 3 must separate oracle outcomes from data quirks.
  - Verified 2026-09-30 (Phase 3 gate): displayed-value transforms per era. Weather Underground and NOAA F markets: round_half_up of the T-group tenths converted to F, SPECI included (WU) or per station (NOAA). C markets: the whole-degree METAR group. NOAA hourly table: SPECI reports count for most stations but not Moscow's :24/:50 reports. Hong Kong: Observatory daily maximum, bucket = floor. Parked cities: Shenzhen (Weather Underground era 76% mismatch, source unknown; NOAA era 100% on 38 days), Jinan (no IEM data), Taipei (three station changes), Seoul's Weather Underground era (88.5% on 261 days, one-degree misses in both directions, NOAA era 37 of 37; use Polymarket resolutions as labels there), Panama City (missing-data resolutions). IEM's asos.py end date is exclusive and its rate limit is about one request per 3 seconds; routine report minutes per station are those with at least a quarter of the busiest minute's count.
- Verified 2026-09-30 (weather_edge/collector.py smoke run): one cycle covers 1,496 active bucket markets in 50 cities in 27 seconds. CLOB POST /books returns 100 books per call with a hash per book (stored only on change); aviationweather.gov METAR JSON keeps tenths of a degree when the T group exists and gives receiptTime (the true availability time); Hong Kong's 1-minute temperature CSV at data.weather.gov.hk is public and its resolution source is the Daily Extract "Absolute Daily Max" to one decimal, i.e. the official daily max, not a displayed hourly series; Open-Meteo forecast returns 4 models for 3 days in one call per station. Books are stored for YES tokens only (the NO book mirrors it in negRisk markets). Deployment still needs: an AWS instance, an S3 bucket and /etc/collector.env with credentials (deploy/collector.service). Until then the collector runs in the research container and writes to data/collector.
- Verified 2026-09-30 (T1): prices are near-certain by 18:00 local (Brier 0.003 at 6h before midnight) and still open at noon (mean sum of YES 1.03, buckets spread 10c to 50c). A forecast edge has to be used before noon local; afternoon edge is a nowcasting problem (H4, H7).
- Open question narrowed: the NOAA rules point at the hourly table, so the displayed-value transform must reproduce that table, not the 5-minute data.
- Verified 2026-09-29 (weather_edge/trades.py, 27.9M fills for 79,249 inventory markets, 2025-01-18 to 2026-07-20): the dataset's fill shares equal Gamma volume within 1% for essentially every closed market through April 2026, but only for about 5% of markets from May 2026 (median 0.83 in May, 0.78 in June, 0.79 in July), so about 20% of fills are missing from May 2026 on, worst in Hong Kong and the Chinese cities. Fill-based results (T4, T5) are therefore split into complete months (before 2026-05-01) and the rest. Direction semantics reconciled against data-api trades by transaction hash for market 1427385 (502 transactions, all matched, shares equal to 0.1): a taker "buy NO" appears as taker_direction SELL of token1 (YES) at the YES price, so YES price = price for token1 and 1 minus price for token2, and the taker is long YES when (direction = BUY) equals (side = token1).
- Verified 2026-09-29: Gamma volume for these markets equals the number of shares filled (data-api fills for market 1427385 sum to 24,919.5 shares = volumeNum), not USD notional. The dataset's trades.parquet covers 2022-11-21 to 2026-07-20 (1.03 billion fills, 1,027 row groups of 128 MB, roughly time-ordered) with maker, taker, both directions, price and size; fills after 2026-07-20 must come from the data-api (about 2 requests per second before HTTP 429). The CLOB prices-history endpoint returns 1-minute points from market creation to close when startTs and endTs are given (interval=max returns nothing for old markets) and tolerated 16 requests per second.
- Verified 2026-09-29: markets.parquet in SII-WANGZJ/Polymarket_data holds no rules text (its Gamma fetcher keeps only question, outcomes, tokens, volume, dates). Rules text and resolutions come from the Gamma API; the dataset is for trades only.
- Exact resolution rule per era and which markets used WU vs NOAA vs other sources.
- Does the weather.gov time series show only routine and SPECI METARs, or also 5-minute data, for each station? This decides the displayed-value transform.
- Answered 2026-09-30, see section 4.3: weather taker rate 0.05, maker fee 0, maker rebate pool 25%, minimum order 5 shares, liquidity rewards configured but unfunded for weather.
- Availability of historical NBM text bulletins.
- Verified 2026-09-30 (weather_edge/forecasts.py): ECMWF IFS 0.25 HRES open data is served by Google's mirror (storage.googleapis.com/ecmwf-open-data, history from 2023-07-12) with a JSON index per step; the AWS bucket (ecmwf-forecasts) answers SlowDown 503 to this IP. NOAA GFS 0.25 on AWS (noaa-gfs-bdp-pds) serves .idx files and byte ranges. One 2 m temperature field is 0.65 MB (ECMWF) or 0.88 MB (GFS) and decodes with the eccodes wheel; bilinear interpolation lands within 1 C of the METAR (KLGA 2025-01-15 12Z: ECMWF -5.0, GFS -4.2, METAR -4.4). The object's Last-Modified is the availability time: ECMWF 00Z run appeared 08:37 UTC, GFS 00Z at 03:40 UTC. These replace Open-Meteo for Phase 5 training and for live use (CC-BY 4.0 and public domain).
- Open-Meteo commercial terms. Verified 2026-09-30: the free tier is non-commercial only, 10,000 calls per day per IP (600 per minute), and this container's egress IP exhausted it after the collector's hourly 50-station pulls; the customer tier (customer-api.open-meteo.com) carries a commercial licence and no daily limit. ECMWF open data (CC-BY 4.0) and NOAA GFS on AWS Open Data are the licence-clean alternatives for Phase 5.
- ECMWF open data on the Google mirror: 00/12Z runs are stream oper; 06/18Z runs were stream scda (steps to 90 h) until 2026-05-11 and are stream oper (steps beyond 100 h) from 2026-05-12. Verified 2026-09-30 by probing the index files; weather_edge/forecasts.py picks the stream by init time.
- Market creation lead (NYC, from Gamma createdAt): events appear a median 42 to 48 h before the local day (about 06:00 local two days before) from 2025-02 to 2026-05, only 27 h before (21:00 local two days before) from 2026-06 to 2026-08, and 44 h before again since 2026-09. Of 552 resolved NYC days before the holdout, 236 had a market at 06:00 two days before, 436 at noon two days before, 543 at noon the day before. Other cities in 2026-09: 19 h (Zhengzhou, Jinan) to 40 h (Atlanta, Chicago) before UTC midnight of the day. A lead-3 quote is possible on most days now.
- H16 inputs verified 2026-09-30 on AWS Open Data: HRRR (noaa-hrrr-bdp-pds, hrrr.<date>/conus/hrrr.t<HH>z.wrfsfcf<FF>.grib2 with .idx, field 'TMP:2 m above ground', 3 km Lambert grid, hourly runs, 06Z f01 public 52 min after init) and NBM core (noaa-nbm-grib2-pds, blend.<date>/<HH>/core/blend.t<HH>z.core.f<FFF>.co.grib2 with .idx, 'TMP:2 m above ground' plus its 'ens std dev', 2.5 km grid, 06Z f012 public 43 min after init). Both present for 2025-01 and 2026-09. Needs nearest-grid-point lookup instead of the lat-lon bilinear used for the 0.25 degree models.
- NBM archive pulled 2026-09-30 (weather_edge/forecasts.py --models nbm_tmax nbm_tmax_spread, data/forecasts_nbm.duckdb): 637 runs per cycle at 00, 06, 12 and 18Z, 2025-01-01 to 2026-09-29, 14,014 steps, none missing; 14 stations fall on the CONUS grid (the 12 US stations plus Toronto and Denver's KBKF); the rest get no value. Publication median 1.0 h after init (p90 1.2 h). Mean ensemble standard deviation of the daytime maximum 1.1 C.
- Holdout 2026-08 to 09 (T17): the market two days out has become much sharper than in 2025 to mid-2026 (lead-3 Brier 0.067 in London and 0.062 in NYC against 0.102 and 0.108 before; 1.2 disagreement buckets per day against 3). The in-sample two-days-out edge does not hold on unseen data.
- Publication delay on the mirrors (steps to 48 h, from Last-Modified, 2025-01 to 2026-09): ECMWF 00/12Z median 7.6 h after init (p90 8.6 h), ECMWF 06/18Z 6.5 h (p90 7.5 h), GFS 4.0 h, GEFS mean and spread 4.1 h. A few runs appeared days late; the point-in-time rule drops them automatically. The mirror lacks ECMWF 06/18Z runs from 2025-01-07 to 2025-02-12 (61 runs); everything else is complete (637 runs per model and cycle, one ECMWF step missing).

## 13. Status

Phases 0 to 8 are done and Phase 9 (paper trading) is built but not started. The two-days-out signal that passed the probability criterion in-sample (T10, T12, T14) did not pass the fill criterion (T13, T16) and did not hold on the one-shot holdout (T17); the market does not react to model releases (T19). The project stops here with no live capital deployed. What remains open is a market-microstructure question, not a forecasting one: who moves these prices, and on what information.
