# Phase 5: EMOS by CRPS vs the market

Phase 5: EMOS per station and lead, fit by CRPS, scored against the market.

Features per station, day and lead K at the decision time (default 12:00 local on day D - (K - 1)):
for each source in ecmwf, gfs, gefs_mean, gefs_spread the latest run all of whose steps inside the
local day were public by the decision; the feature is the maximum over those steps (for the spread,
its value at the step of the ensemble-mean maximum). Everything is in degrees C.
Label: daily_truth.max_c, every station-day, market or not (weather_edge/labels.py).
Models, walk-forward with trailing windows only:
  clim  N(mean, sd) of the last 30 labels
  raw   N(mean of the deterministic maxima, sd across sources with a 2 C floor)
  emos  y ~ t_nu(a0 + a.x, scale^2 = exp(b0) + exp(b1) * spread^2), nu = 2 + exp(c), all fit by minimizing
        the mean CRPS (closed form for the t) over the last 90 days; x = available maxima (ecmwf, gfs,
        gefs_mean). The scale is then multiplied by the root mean square of the last 90 out-of-sample
        standardized errors known at the decision (the in-sample fit is overconfident: 82% coverage
        of the nominal 90% interval without this step; the t alone does not fix it, nu runs to its bound).
  obs   same-day only (lead 1): y = max(R, Z). R is the running displayed maximum from METARs observed
        at least OBS_DELAY_MIN minutes before the decision, Z ~ N(a0 + a.rest + c * last_obs, exp(b0)^2)
        where rest is each source's forecast maximum over the steps after the decision; fit by the
        left-censored Gaussian likelihood over the last 90 days (days whose maximum was already in by
        the decision are censored at R).
Scores: CRPS and MAE on all days; PIT histogram; on market days, Brier and log loss vs the market at
the decision time, and the market-minus-model Brier on disagreement buckets with a day bootstrap.
Bucket probabilities integrate the predictive distribution over half-integer edges in the market's unit.
Holdout from 2026-08-01 excluded.

## Findings (NYC KLGA, 2025-01-22 to 2026-07-31; holdout from 2026-08-01 untouched)

Command: `python -m weather_edge.model --stations KLGA --decision-hours 6 8 10 12` (calibrated t EMOS). Inputs: ECMWF IFS, GFS, GEFS mean and spread at 00/06/12/18Z, 3-hourly steps, publication times from the mirrors; 577 feature days; 10,515 to 11,493 market buckets per decision hour. The first run with a plain normal EMOS is recorded in PLAN.md T10; this one adds a Student t fit and an out-of-sample scale calibration (T12).

| decision | lead 3 (two days before) | lead 2 (day before) | lead 1 EMOS | lead 1 with observations |
|---|---|---|---|---|
| 06:00 | **+0.037 (0.024 to 0.050)**, 779 buckets on 213 days | -0.011 (-0.019 to -0.003) | -0.050 | -0.043 |
| 08:00 | **+0.032 (0.020 to 0.044)** | -0.016 | -0.054 | -0.044 |
| 10:00 | **+0.017 (0.006 to 0.028)** | -0.018 | -0.054 | -0.045 |
| 12:00 | **+0.021 (0.011 to 0.031)**, 1,332 buckets on 408 days | -0.018 (-0.027 to -0.009) | -0.062 | -0.041 |

Market minus model Brier on disagreement buckets (|p_model - p_market| >= 0.10), positive means the model wins, 90% day bootstrap in brackets.

- Two days ahead the model beats the market at every decision hour, and more the earlier the decision, where fewer markets carry quotes (markets appear about 42 h before the day, see PLAN.md section 12). One day ahead the market is slightly ahead. On the day the market wins by 0.05 to 0.06 against forecasts alone and by 0.04 against the model that also knows the running maximum and the last METAR.
- Observations help the same-day model (lead 1 CRPS 0.81 C to 0.73 C at 06:00 and to 0.61 C at noon) but not enough: the market's Brier is 0.071 to 0.075 at every hour from 06:00, so the market at 06:00 already knows more than global-model forecasts plus the morning observations.
- Calibration: the plain normal EMOS covered 81 to 83% with its nominal 90% interval (U-shaped PIT). Fitting a Student t by CRPS did not fix it (nu runs to its upper bound, the in-sample fit is simply overconfident). Scaling the spread by the root mean square of the last 90 out-of-sample standardized errors gives 88 to 92% coverage and a flat PIT at a cost of about 0.01 C in CRPS; the disagreement scores moved by less than 0.01.
- CRPS (C) at noon, lead 1/2/3: EMOS 0.79/0.93/1.05, raw multi-model 0.95/1.07/1.17, 30-day climatology 3.1/3.2/3.3. GEFS spread and the 06/18Z cycles add little over ECMWF and GFS at 00/12Z (T10 vs Phase 4).
- Reading: for the same day the forecast inputs are the bottleneck, not the conditioning. The lead-3 signal is the one worth trading if fills allow (T13, T16). Higher-resolution guidance does not change it: with the NBM 12-hour daytime maximum and its spread as extra inputs (T15, 14 CONUS stations, four cycles) every score at every hour is within 0.002 Brier and 0.01 C CRPS of the run without it, and the fitted slopes put no weight on NBM once ECMWF, GFS and GEFS are in.

## KLGA, decision 06:00 local

| station   |   decision_hour_local |   feature_days |   label_days | sources_with_coverage                        |   obs_days |   share_max_before_decision |   market_buckets |
|:----------|----------------------:|---------------:|-------------:|:---------------------------------------------|-----------:|----------------------------:|-----------------:|
| KLGA      |                     6 |            577 |          577 | ['ecmwf', 'gfs', 'gefs_mean', 'gefs_spread'] |        577 |                      0.0324 |            10515 |

### Continuous scores (C), all days

|   lead | model   |   days |   crps |    mae |   mean_sigma |   median_nu | pit_bins                       |   coverage_90 |
|-------:|:--------|-------:|-------:|-------:|-------------:|------------:|:-------------------------------|--------------:|
|      1 | clim    |    567 | 3.0773 | 4.3230 |       4.6568 |    nan      | [0.23, 0.19, 0.15, 0.18, 0.26] |        0.8377 |
|      1 | raw     |    577 | 0.9670 | 1.3093 |       2.1721 |    nan      | [0.03, 0.18, 0.27, 0.31, 0.21] |        0.9515 |
|      1 | emos    |    557 | 0.8057 | 1.1008 |       1.5285 |    230.6620 | [0.17, 0.27, 0.23, 0.17, 0.17] |        0.9048 |
|      1 | obs     |    557 | 0.7329 | 1.0095 |       1.2602 |    nan      |                                |        0.8600 |
|      2 | clim    |    566 | 3.1921 | 4.4473 |       4.6576 |    nan      | [0.22, 0.19, 0.15, 0.17, 0.27] |        0.8180 |
|      2 | raw     |    576 | 1.0924 | 1.5138 |       2.2307 |    nan      | [0.04, 0.15, 0.24, 0.31, 0.27] |        0.9323 |
|      2 | emos    |    555 | 0.9371 | 1.2728 |       1.8294 |     26.7712 | [0.18, 0.24, 0.23, 0.18, 0.17] |        0.9117 |
|      3 | clim    |    565 | 3.2691 | 4.5294 |       4.6586 |    nan      | [0.23, 0.18, 0.15, 0.17, 0.27] |        0.8071 |
|      3 | raw     |    570 | 1.2245 | 1.7304 |       2.3142 |    nan      | [0.05, 0.16, 0.19, 0.28, 0.32] |        0.9175 |
|      3 | emos    |    548 | 1.0890 | 1.4873 |       2.1648 |    268.4885 | [0.19, 0.23, 0.24, 0.18, 0.17] |        0.8814 |

### Market comparison at the decision time (disagreement = |p_model - p_market| >= 0.10)

|   lead | model   |   buckets |   days |   brier_market |   brier_model |   logloss_market |   logloss_model |   n_disagree |   market_minus_model_on_disagree |   ci_low |   ci_high |
|-------:|:--------|----------:|-------:|---------------:|--------------:|-----------------:|----------------:|-------------:|---------------------------------:|---------:|----------:|
|      1 | clim    |      4435 |    548 |         0.0730 |        0.1451 |           0.2342 |          0.5082 |         2040 |                          -0.1544 |  -0.1667 |   -0.1422 |
|      1 | raw     |      4435 |    548 |         0.0730 |        0.0981 |           0.2342 |          0.3247 |         1878 |                          -0.0567 |  -0.0654 |   -0.0474 |
|      1 | emos    |      4435 |    548 |         0.0730 |        0.0900 |           0.2342 |          0.2973 |         1423 |                          -0.0499 |  -0.0609 |   -0.0380 |
|      1 | obs     |      4435 |    548 |         0.0730 |        0.0849 |           0.2342 |          0.2792 |         1202 |                          -0.0430 |  -0.0548 |   -0.0317 |
|      2 | clim    |      4272 |    526 |         0.0902 |        0.1456 |           0.2941 |          0.5157 |         2263 |                          -0.1027 |  -0.1115 |   -0.0939 |
|      2 | raw     |      4272 |    526 |         0.0902 |        0.1006 |           0.2941 |          0.3350 |         1619 |                          -0.0244 |  -0.0322 |   -0.0172 |
|      2 | emos    |      4272 |    526 |         0.0902 |        0.0947 |           0.2941 |          0.3113 |         1455 |                          -0.0108 |  -0.0185 |   -0.0032 |
|      3 | clim    |      1808 |    215 |         0.1108 |        0.1371 |           0.3518 |          0.5021 |         1094 |                          -0.0422 |  -0.0570 |   -0.0275 |
|      3 | raw     |      1794 |    213 |         0.1109 |        0.0975 |           0.3515 |          0.3263 |          750 |                           0.0309 |   0.0162 |    0.0443 |
|      3 | emos    |      1794 |    213 |         0.1109 |        0.0954 |           0.3515 |          0.3206 |          779 |                           0.0374 |   0.0240 |    0.0504 |

## KLGA, decision 08:00 local

| station   |   decision_hour_local |   feature_days |   label_days | sources_with_coverage                        |   obs_days |   share_max_before_decision |   market_buckets |
|:----------|----------------------:|---------------:|-------------:|:---------------------------------------------|-----------:|----------------------------:|-----------------:|
| KLGA      |                     8 |            577 |          577 | ['ecmwf', 'gfs', 'gefs_mean', 'gefs_spread'] |        577 |                      0.0336 |            11313 |

### Continuous scores (C), all days

|   lead | model   |   days |   crps |    mae |   mean_sigma |   median_nu | pit_bins                       |   coverage_90 |
|-------:|:--------|-------:|-------:|-------:|-------------:|------------:|:-------------------------------|--------------:|
|      1 | clim    |    567 | 3.0773 | 4.3230 |       4.6568 |    nan      | [0.23, 0.19, 0.15, 0.18, 0.26] |        0.8377 |
|      1 | raw     |    577 | 0.9610 | 1.2996 |       2.1659 |    nan      | [0.03, 0.18, 0.28, 0.3, 0.21]  |        0.9515 |
|      1 | emos    |    557 | 0.8006 | 1.0939 |       1.5313 |    375.2050 | [0.17, 0.26, 0.24, 0.16, 0.17] |        0.8977 |
|      1 | obs     |    557 | 0.7283 | 1.0041 |       1.2507 |    nan      |                                |        0.8546 |
|      2 | clim    |    566 | 3.1921 | 4.4473 |       4.6576 |    nan      | [0.22, 0.19, 0.15, 0.17, 0.27] |        0.8180 |
|      2 | raw     |    576 | 1.0891 | 1.5107 |       2.2194 |    nan      | [0.03, 0.16, 0.24, 0.29, 0.27] |        0.9306 |
|      2 | emos    |    555 | 0.9414 | 1.2844 |       1.8083 |     23.4321 | [0.17, 0.25, 0.22, 0.18, 0.18] |        0.9153 |
|      3 | clim    |    565 | 3.2691 | 4.5294 |       4.6586 |    nan      | [0.23, 0.18, 0.15, 0.17, 0.27] |        0.8071 |
|      3 | raw     |    572 | 1.2037 | 1.6979 |       2.3035 |    nan      | [0.05, 0.17, 0.19, 0.28, 0.31] |        0.9266 |
|      3 | emos    |    550 | 1.0697 | 1.4725 |       2.0531 |    333.7465 | [0.21, 0.21, 0.22, 0.19, 0.16] |        0.9018 |

### Market comparison at the decision time (disagreement = |p_model - p_market| >= 0.10)

|   lead | model   |   buckets |   days |   brier_market |   brier_model |   logloss_market |   logloss_model |   n_disagree |   market_minus_model_on_disagree |   ci_low |   ci_high |
|-------:|:--------|----------:|-------:|---------------:|--------------:|-----------------:|----------------:|-------------:|---------------------------------:|---------:|----------:|
|      1 | clim    |      4425 |    548 |         0.0714 |        0.1454 |           0.2282 |          0.5092 |         2024 |                          -0.1589 |  -0.1720 |   -0.1462 |
|      1 | raw     |      4425 |    548 |         0.0714 |        0.0982 |           0.2282 |          0.3246 |         1885 |                          -0.0607 |  -0.0697 |   -0.0516 |
|      1 | emos    |      4425 |    548 |         0.0714 |        0.0899 |           0.2282 |          0.2947 |         1434 |                          -0.0536 |  -0.0650 |   -0.0419 |
|      1 | obs     |      4425 |    548 |         0.0714 |        0.0847 |           0.2282 |          0.2780 |         1247 |                          -0.0443 |  -0.0549 |   -0.0331 |
|      2 | clim    |      4272 |    526 |         0.0891 |        0.1456 |           0.2904 |          0.5157 |         2229 |                          -0.1066 |  -0.1158 |   -0.0976 |
|      2 | raw     |      4272 |    526 |         0.0891 |        0.1006 |           0.2904 |          0.3346 |         1645 |                          -0.0267 |  -0.0334 |   -0.0201 |
|      2 | emos    |      4272 |    526 |         0.0891 |        0.0952 |           0.2904 |          0.3143 |         1421 |                          -0.0157 |  -0.0241 |   -0.0066 |
|      3 | clim    |      2616 |    323 |         0.1100 |        0.1435 |           0.3484 |          0.5166 |         1572 |                          -0.0542 |  -0.0667 |   -0.0428 |
|      3 | raw     |      2595 |    320 |         0.1099 |        0.1027 |           0.3479 |          0.3425 |         1161 |                           0.0167 |   0.0065 |    0.0279 |
|      3 | emos    |      2595 |    320 |         0.1099 |        0.0973 |           0.3479 |          0.3236 |         1076 |                           0.0325 |   0.0198 |    0.0441 |

## KLGA, decision 10:00 local

| station   |   decision_hour_local |   feature_days |   label_days | sources_with_coverage                        |   obs_days |   share_max_before_decision |   market_buckets |
|:----------|----------------------:|---------------:|-------------:|:---------------------------------------------|-----------:|----------------------------:|-----------------:|
| KLGA      |                    10 |            577 |          577 | ['ecmwf', 'gfs', 'gefs_mean', 'gefs_spread'] |        577 |                      0.0394 |            11347 |

### Continuous scores (C), all days

|   lead | model   |   days |   crps |    mae |   mean_sigma |   median_nu | pit_bins                       |   coverage_90 |
|-------:|:--------|-------:|-------:|-------:|-------------:|------------:|:-------------------------------|--------------:|
|      1 | clim    |    567 | 3.0773 | 4.3230 |       4.6568 |    nan      | [0.23, 0.19, 0.15, 0.18, 0.26] |        0.8377 |
|      1 | raw     |    577 | 0.9520 | 1.2811 |       2.1657 |    nan      | [0.03, 0.16, 0.29, 0.3, 0.21]  |        0.9532 |
|      1 | emos    |    557 | 0.7927 | 1.0793 |       1.5146 |    347.5706 | [0.17, 0.25, 0.24, 0.17, 0.17] |        0.9066 |
|      1 | obs     |    557 | 0.7036 | 0.9742 |       1.2209 |    nan      |                                |        0.8671 |
|      2 | clim    |    566 | 3.1921 | 4.4473 |       4.6576 |    nan      | [0.22, 0.19, 0.15, 0.17, 0.27] |        0.8180 |
|      2 | raw     |    576 | 1.0823 | 1.5010 |       2.2203 |    nan      | [0.03, 0.16, 0.25, 0.29, 0.27] |        0.9288 |
|      2 | emos    |    555 | 0.9410 | 1.2712 |       1.8443 |    209.1429 | [0.18, 0.22, 0.25, 0.18, 0.17] |        0.9117 |
|      3 | clim    |    565 | 3.2691 | 4.5294 |       4.6586 |    nan      | [0.23, 0.18, 0.15, 0.17, 0.27] |        0.8071 |
|      3 | raw     |    574 | 1.1770 | 1.6562 |       2.2826 |    nan      | [0.05, 0.15, 0.21, 0.28, 0.31] |        0.9390 |
|      3 | emos    |    552 | 1.0512 | 1.4381 |       1.9933 |    382.8946 | [0.18, 0.24, 0.22, 0.18, 0.17] |        0.8967 |

### Market comparison at the decision time (disagreement = |p_model - p_market| >= 0.10)

|   lead | model   |   buckets |   days |   brier_market |   brier_model |   logloss_market |   logloss_model |   n_disagree |   market_minus_model_on_disagree |   ci_low |   ci_high |
|-------:|:--------|----------:|-------:|---------------:|--------------:|-----------------:|----------------:|-------------:|---------------------------------:|---------:|----------:|
|      1 | clim    |      4280 |    546 |         0.0726 |        0.1487 |           0.2306 |          0.5200 |         1960 |                          -0.1632 |  -0.1772 |   -0.1502 |
|      1 | raw     |      4280 |    546 |         0.0726 |        0.1007 |           0.2306 |          0.3314 |         1854 |                          -0.0618 |  -0.0714 |   -0.0529 |
|      1 | emos    |      4280 |    546 |         0.0726 |        0.0919 |           0.2306 |          0.3006 |         1423 |                          -0.0541 |  -0.0661 |   -0.0425 |
|      1 | obs     |      4280 |    546 |         0.0726 |        0.0861 |           0.2306 |          0.2795 |         1213 |                          -0.0451 |  -0.0579 |   -0.0334 |
|      2 | clim    |      4272 |    526 |         0.0883 |        0.1456 |           0.2881 |          0.5157 |         2220 |                          -0.1086 |  -0.1176 |   -0.0993 |
|      2 | raw     |      4272 |    526 |         0.0883 |        0.1004 |           0.2881 |          0.3338 |         1655 |                          -0.0277 |  -0.0350 |   -0.0202 |
|      2 | emos    |      4272 |    526 |         0.0883 |        0.0950 |           0.2881 |          0.3143 |         1427 |                          -0.0176 |  -0.0264 |   -0.0085 |
|      3 | clim    |      2795 |    348 |         0.1047 |        0.1456 |           0.3352 |          0.5224 |         1663 |                          -0.0670 |  -0.0783 |   -0.0560 |
|      3 | raw     |      2788 |    347 |         0.1045 |        0.1024 |           0.3345 |          0.3404 |         1222 |                           0.0057 |  -0.0041 |    0.0158 |
|      3 | emos    |      2788 |    347 |         0.1045 |        0.0981 |           0.3345 |          0.3247 |         1128 |                           0.0174 |   0.0064 |    0.0283 |

## KLGA, decision 12:00 local

| station   |   decision_hour_local |   feature_days |   label_days | sources_with_coverage                        |   obs_days |   share_max_before_decision |   market_buckets |
|:----------|----------------------:|---------------:|-------------:|:---------------------------------------------|-----------:|----------------------------:|-----------------:|
| KLGA      |                    12 |            577 |          577 | ['ecmwf', 'gfs', 'gefs_mean', 'gefs_spread'] |        577 |                      0.0544 |            11493 |

### Continuous scores (C), all days

|   lead | model   |   days |   crps |    mae |   mean_sigma |   median_nu | pit_bins                       |   coverage_90 |
|-------:|:--------|-------:|-------:|-------:|-------------:|------------:|:-------------------------------|--------------:|
|      1 | clim    |    567 | 3.0773 | 4.3230 |       4.6568 |    nan      | [0.23, 0.19, 0.15, 0.18, 0.26] |        0.8377 |
|      1 | raw     |    577 | 0.9528 | 1.2820 |       2.1659 |    nan      | [0.03, 0.16, 0.29, 0.3, 0.21]  |        0.9532 |
|      1 | emos    |    557 | 0.7933 | 1.0779 |       1.5226 |    350.0273 | [0.17, 0.26, 0.24, 0.17, 0.17] |        0.9084 |
|      1 | obs     |    557 | 0.6055 | 0.8402 |       1.1050 |    nan      |                                |        0.8905 |
|      2 | clim    |    566 | 3.1921 | 4.4473 |       4.6576 |    nan      | [0.22, 0.19, 0.15, 0.17, 0.27] |        0.8180 |
|      2 | raw     |    576 | 1.0748 | 1.4855 |       2.2208 |    nan      | [0.03, 0.15, 0.26, 0.29, 0.26] |        0.9323 |
|      2 | emos    |    555 | 0.9295 | 1.2767 |       1.7579 |    364.5323 | [0.19, 0.23, 0.22, 0.19, 0.17] |        0.8955 |
|      3 | clim    |    565 | 3.2691 | 4.5294 |       4.6586 |    nan      | [0.23, 0.18, 0.15, 0.17, 0.27] |        0.8071 |
|      3 | raw     |    575 | 1.1669 | 1.6433 |       2.2798 |    nan      | [0.05, 0.15, 0.2, 0.3, 0.3]    |        0.9339 |
|      3 | emos    |    553 | 1.0473 | 1.4156 |       1.9982 |    305.6121 | [0.2, 0.21, 0.24, 0.18, 0.17]  |        0.9096 |

### Market comparison at the decision time (disagreement = |p_model - p_market| >= 0.10)

|   lead | model   |   buckets |   days |   brier_market |   brier_model |   logloss_market |   logloss_model |   n_disagree |   market_minus_model_on_disagree |   ci_low |   ci_high |
|-------:|:--------|----------:|-------:|---------------:|--------------:|-----------------:|----------------:|-------------:|---------------------------------:|---------:|----------:|
|      1 | clim    |      3953 |    537 |         0.0746 |        0.1579 |           0.2339 |          0.5522 |         1848 |                          -0.1753 |  -0.1908 |   -0.1610 |
|      1 | raw     |      3953 |    537 |         0.0746 |        0.1064 |           0.2339 |          0.3459 |         1764 |                          -0.0684 |  -0.0787 |   -0.0579 |
|      1 | emos    |      3953 |    537 |         0.0746 |        0.0984 |           0.2339 |          0.3199 |         1453 |                          -0.0621 |  -0.0753 |   -0.0491 |
|      1 | obs     |      3953 |    537 |         0.0746 |        0.0870 |           0.2339 |          0.2778 |         1148 |                          -0.0414 |  -0.0553 |   -0.0274 |
|      2 | clim    |      4325 |    534 |         0.0882 |        0.1460 |           0.2869 |          0.5179 |         2199 |                          -0.1118 |  -0.1213 |   -0.1026 |
|      2 | raw     |      4325 |    534 |         0.0882 |        0.1003 |           0.2869 |          0.3337 |         1663 |                          -0.0298 |  -0.0376 |   -0.0221 |
|      2 | emos    |      4318 |    533 |         0.0880 |        0.0949 |           0.2863 |          0.3150 |         1362 |                          -0.0177 |  -0.0267 |   -0.0092 |
|      3 | clim    |      3215 |    408 |         0.1079 |        0.1508 |           0.3448 |          0.5378 |         1988 |                          -0.0682 |  -0.0780 |   -0.0587 |
|      3 | raw     |      3215 |    408 |         0.1079 |        0.1046 |           0.3448 |          0.3476 |         1442 |                           0.0084 |  -0.0010 |    0.0175 |
|      3 | emos    |      3215 |    408 |         0.1079 |        0.1004 |           0.3448 |          0.3331 |         1332 |                           0.0206 |   0.0112 |    0.0309 |
