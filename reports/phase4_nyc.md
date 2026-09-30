# Phase 4: NYC end to end

Forecast source: open

Phase 4: the full chain for one city (NYC, KLGA): forecasts, labels, baseline models, market
comparison and a maker-only backtest skeleton. Built to flush out pipeline bugs before generalizing.

Forecasts: Open-Meteo Previous Runs API, hourly 2 m temperature at fixed lead offsets. Per its
documentation, temperature_2m_previous_dayK is the value predicted K x 24 hours before the valid
time. Decision time for lead K is 12:00 local on day D - (K - 1); every hour of day D used at that
decision was predicted at least 11 hours earlier (plus at most 8 hours of publication delay, which is
asserted). Fresher runs exist by then, so the model is understated, never leaked.

Labels: the rebuilt displayed high (T-group tenths transform, table truth) and the resolved bucket.
Models (walk-forward, trailing windows only): climatology (last 30 days of labels), raw multi-model
(mean and spread of the models' daily maxima), EMOS-lite (linear fit of the label on the model mean
over the last 60 days, residual spread). Bucket probabilities integrate a normal over half-integers.
Holdout: days from 2026-08-01 are excluded from everything here (docs/research-log.md section 8).
Backtest: maker-only, 5 shares (minimum order), bid 1c under the market price when the model's
probability exceeds the market's by the edge, fill only if the later price touched the bid, and a
50% fill haircut when the bucket won (fills are likelier when the model is wrong). No fees for makers,
rebates ignored.

## Coverage

|   forecast_days |   label_days |   market_buckets | first_day           | last_day            | holdout_start   |
|----------------:|-------------:|-----------------:|:--------------------|:--------------------|:----------------|
|             610 |          552 |            11493 | 2025-01-22 00:00:00 | 2026-09-28 00:00:00 | 2026-08-01      |

## Model vs market: Brier on all buckets and on disagreement buckets (|p_model - p_market| >= 0.10)

market_minus_model_brier_on_disagree > 0 means the model beats the market where they disagree; ci is a 95% bootstrap over event days.

|   lead | model   |   n_buckets |   days |   brier_market |   brier_model |   n_disagree |   market_minus_model_brier_on_disagree |   ci_low |   ci_high |
|-------:|:--------|------------:|-------:|---------------:|--------------:|-------------:|---------------------------------------:|---------:|----------:|
|      1 | clim    |        3893 |    528 |         0.0739 |        0.1577 |         1821 |                                -0.1762 |  -0.1912 |   -0.1617 |
|      1 | raw     |        3953 |    537 |         0.0746 |        0.1146 |         1608 |                                -0.0964 |  -0.1086 |   -0.0832 |
|      1 | emos    |        3834 |    518 |         0.0736 |        0.1007 |         1511 |                                -0.0656 |  -0.0783 |   -0.0528 |
|      2 | clim    |        4276 |    527 |         0.0871 |        0.1458 |         2173 |                                -0.1137 |  -0.1227 |   -0.1036 |
|      2 | raw     |        4325 |    534 |         0.0882 |        0.1031 |         1475 |                                -0.0416 |  -0.0510 |   -0.0330 |
|      2 | emos    |        4239 |    521 |         0.0869 |        0.0929 |         1183 |                                -0.0168 |  -0.0266 |   -0.0071 |
|      3 | clim    |        3215 |    408 |         0.1079 |        0.1508 |         1989 |                                -0.0682 |  -0.0780 |   -0.0587 |
|      3 | raw     |        3215 |    408 |         0.1079 |        0.1090 |         1492 |                                -0.0003 |  -0.0109 |    0.0098 |
|      3 | emos    |        3201 |    406 |         0.1080 |        0.1009 |         1214 |                                 0.0217 |   0.0109 |    0.0330 |

## Maker-only backtest skeleton (5-share bids, 1c under market, touch fills, 50% haircut on wins, no fees)

|   lead | model   |   orders |   touched |   filled_shares |   pnl_usd |   pnl_per_filled_share |   days |   win_rate_of_fills |
|-------:|:--------|---------:|----------:|----------------:|----------:|-----------------------:|-------:|--------------------:|
|      1 | raw     |      392 |       382 |       1830.0000 | -106.2250 |                -0.0580 |    334 |              0.0838 |
|      1 | emos    |      367 |       359 |       1722.5000 |  -62.3750 |                -0.0362 |    321 |              0.0808 |
|      2 | raw     |      408 |       401 |       1942.5000 | -108.4000 |                -0.0558 |    319 |              0.0623 |
|      2 | emos    |      330 |       324 |       1537.5000 |  -51.9750 |                -0.0338 |    253 |              0.1019 |
|      3 | raw     |      302 |       295 |       1410.0000 |  -71.9500 |                -0.0510 |    219 |              0.0881 |
|      3 | emos    |      181 |       172 |        810.0000 |  -47.4500 |                -0.0586 |    148 |              0.1163 |
