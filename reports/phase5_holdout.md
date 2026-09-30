# Phase 5 holdout: the one-shot test (T17)

Command: `python -m weather_edge model --stations EGLC --decision-hours 12 --leads 3 --holdout`, and the same for KLGA. Run once, on 2026-09-30. The configuration was fixed before: calibrated t EMOS, two days out, decision at noon local. Scored only on days from 2026-08-01 (59 resolved days per city, prices to 2026-09-29). The walk-forward still trains on the days before each decision, as everywhere else. The trade tape ends on 2026-07-20, so the fill backtest could not run on the holdout. This is the Brier test of section 10 of the research log.

| station | holdout days with quotes | buckets | disagreement buckets | market Brier | model Brier | market minus model on disagreement (90% day bootstrap) |
|---|---|---|---|---|---|---|
| London EGLC | 57 | 627 | 69 | 0.0670 | 0.0666 | -0.007 (-0.036 to +0.021) |
| NYC KLGA | 29 | 319 | 52 | 0.0624 | 0.0697 | -0.038 (-0.078 to +0.005) |

- Before the holdout the same configuration beat the market two days out by +0.042 in London and +0.021 in New York, with intervals well above zero. On the holdout London is level and New York is behind. The criterion "it holds on the holdout" is not met.
- The market got sharper. Two days out its Brier is 0.067 and 0.062, against 0.102 and 0.108 over 2025-01 to 2026-07, and it disagrees with the model on 1.2 buckets a day instead of about 3. The model itself did not get worse: London's lead-3 CRPS is 0.54 °C on the holdout against 0.74 °C in sample, New York's 0.75 against 1.05. Both are better because August and September are easy months. The edge went away because the market caught up, not because the model broke.
- New York has only 29 holdout days with a quote at noon two days before, because its markets were listed just 27 hours ahead in August (research log section 12). Since September it is 44 hours again.
- The New York run had the NBM inputs in its source list, because the forecast database now carries them. T15 showed NBM moves every score by less than 0.002, so this does not change the reading, but it is a deviation from the registered configuration and I record it here.
- Verdict: no tradeable edge. The two-days-out signal that survived Phases 5 to 7 in sample does not hold on unseen 2026 data. Paper trading it would be a zero-stakes check, not a step toward live money.

## Method (from weather_edge/model.py)

Phase 5: EMOS per station and lead, fit by CRPS, scored against the market.

Features per station, day and lead K at the decision time (default 12:00 local on day D - (K - 1)):
for each source in ecmwf, gfs, gefs_mean, gefs_spread, nbm_tmax, nbm_tmax_spread the latest run all of
whose steps inside the local day were public by the decision; the feature is the maximum over those
steps (for a spread, its value at the step of its mean's maximum; NBM has one 12-hour daytime maximum
per run). Everything is in degrees C.
Label: daily_truth.max_c, every station-day, market or not (weather_edge/labels.py).
Models, walk-forward with trailing windows only:
  clim  N(mean, sd) of the last 30 labels
  raw   N(mean of the deterministic maxima, sd across sources with a 2 C floor)
  emos  y ~ t_nu(a0 + a.x, scale^2 = exp(b0) + exp(b1) * spread^2), nu = 2 + exp(c), all fit by minimizing
        the mean CRPS (closed form for the t) over the last 90 days; x = available maxima (ecmwf, gfs,
        gefs_mean, nbm_tmax; one spread term per ensemble). The scale is then multiplied by the root mean square of the last 90 out-of-sample
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

## EGLC, decision 12:00 local

| station   |   decision_hour_local | period                  |   feature_days |   label_days | sources_with_coverage                        |   obs_days |   share_max_before_decision |   market_buckets |
|:----------|----------------------:|:------------------------|---------------:|-------------:|:---------------------------------------------|-----------:|----------------------------:|-----------------:|
| EGLC      |                    12 | holdout from 2026-08-01 |            638 |          638 | ['ecmwf', 'gfs', 'gefs_mean', 'gefs_spread'] |        638 |                         nan |              627 |

### Continuous scores (C), all days

|   lead | model   |   days |   crps |    mae |   mean_sigma |   median_nu | pit_bins                       |   coverage_90 |
|-------:|:--------|-------:|-------:|-------:|-------------:|------------:|:-------------------------------|--------------:|
|      3 | clim    |     61 | 1.7945 | 2.5448 |       2.9732 |    nan      | [0.34, 0.34, 0.16, 0.07, 0.08] |        0.8525 |
|      3 | raw     |     61 | 0.7288 | 0.8857 |       2.2128 |    nan      | [0.0, 0.11, 0.41, 0.38, 0.1]   |        1.0000 |
|      3 | emos    |     61 | 0.5407 | 0.7404 |       1.3596 |    200.9079 | [0.11, 0.26, 0.23, 0.28, 0.11] |        1.0000 |

### Market comparison at the decision time (disagreement = |p_model - p_market| >= 0.10)

|   lead | model   |   buckets |   days |   brier_market |   brier_model |   logloss_market |   logloss_model |   n_disagree |   market_minus_model_on_disagree |   ci_low |   ci_high |
|-------:|:--------|----------:|-------:|---------------:|--------------:|-----------------:|----------------:|-------------:|---------------------------------:|---------:|----------:|
|      3 | clim    |       627 |     57 |         0.0670 |        0.0922 |           0.2153 |          0.3301 |          247 |                          -0.0606 |  -0.0765 |   -0.0414 |
|      3 | raw     |       627 |     57 |         0.0670 |        0.0734 |           0.2153 |          0.2481 |          121 |                          -0.0243 |  -0.0487 |    0.0001 |
|      3 | emos    |       627 |     57 |         0.0670 |        0.0666 |           0.2153 |          0.2116 |           69 |                          -0.0072 |  -0.0355 |    0.0207 |

## KLGA, decision 12:00 local

| station   |   decision_hour_local | period                  |   feature_days |   label_days | sources_with_coverage                                                       |   obs_days |   share_max_before_decision |   market_buckets |
|:----------|----------------------:|:------------------------|---------------:|-------------:|:----------------------------------------------------------------------------|-----------:|----------------------------:|-----------------:|
| KLGA      |                    12 | holdout from 2026-08-01 |            637 |          637 | ['ecmwf', 'gfs', 'gefs_mean', 'gefs_spread', 'nbm_tmax', 'nbm_tmax_spread'] |        637 |                         nan |              319 |

### Continuous scores (C), all days

|   lead | model   |   days |   crps |    mae |   mean_sigma |   median_nu | pit_bins                       |   coverage_90 |
|-------:|:--------|-------:|-------:|-------:|-------------:|------------:|:-------------------------------|--------------:|
|      3 | clim    |     60 | 2.0794 | 2.7676 |       2.5753 |    nan      | [0.47, 0.12, 0.25, 0.05, 0.12] |        0.7333 |
|      3 | raw     |     60 | 0.9808 | 1.0854 |       3.3696 |    nan      | [0.02, 0.08, 0.47, 0.43, 0.0]  |        1.0000 |
|      3 | emos    |     60 | 0.7463 | 1.0420 |       1.4773 |    213.3058 | [0.22, 0.15, 0.27, 0.2, 0.17]  |        0.9333 |

### Market comparison at the decision time (disagreement = |p_model - p_market| >= 0.10)

|   lead | model   |   buckets |   days |   brier_market |   brier_model |   logloss_market |   logloss_model |   n_disagree |   market_minus_model_on_disagree |   ci_low |   ci_high |
|-------:|:--------|----------:|-------:|---------------:|--------------:|-----------------:|----------------:|-------------:|---------------------------------:|---------:|----------:|
|      3 | clim    |       319 |     29 |         0.0624 |        0.1024 |           0.2103 |          0.3949 |          106 |                          -0.1120 |  -0.1394 |   -0.0801 |
|      3 | raw     |       319 |     29 |         0.0624 |        0.0804 |           0.2103 |          0.2821 |           83 |                          -0.0622 |  -0.0886 |   -0.0347 |
|      3 | emos    |       319 |     29 |         0.0624 |        0.0697 |           0.2103 |          0.2344 |           52 |                          -0.0379 |  -0.0778 |    0.0053 |
