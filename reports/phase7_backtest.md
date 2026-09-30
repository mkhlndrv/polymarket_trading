# Phase 7: lead-3 EMOS backtest with tape fills

Phase 7: backtest of the two-days-out EMOS signal with fills taken from the trade tape.

Signal: phase5_model EMOS at lead 3 (decision at --decision-hours local, two days before the day).
Orders (maker only, 5 shares, resting LIFE_H hours), only on buckets with a market price at the decision:
  buy YES at min(last price - 1c, p_model - EDGE) when p_model - last price >= EDGE
  buy NO  at min(1 - last price - 1c, 1 - p_model - EDGE) when last price - p_model >= EDGE
Fills from the dataset fills (table trades, complete through 2026-04, about 80% coverage after):
  touch    a taker print at or through the order price in the window fills min(size, printed volume)
  through  only prints strictly beyond the price count (the whole level was cleared, so a resting
           order there was filled whatever its queue position)
  *_haircut  the same with winning fills halved (fills are more likely when the model is wrong)
Maker fee zero, rebates ignored. PnL per share = outcome - price for YES, (1 - outcome) - price for NO.
Holdout from 2026-08-01 excluded (the tape ends 2026-07-20 anyway).

## Findings (NYC KLGA, 2025-02 to 2026-07-20, calibrated t EMOS at lead 3, 5 shares per order)

Command: `python -m weather_edge.backtest --stations KLGA --decision-hours 6 12`. The tables below are from the calibrated model (out-of-sample scale inflation). The first run, before the calibration step, is in PLAN.md T13.

| decision (two days before) | orders | through fills | shares | PnL | c per share | PnL per order, day bootstrap 90% | with 50% haircut on winning fills |
|---|---|---|---|---|---|---|---|
| 06:00 local | 748 | 272 | 1,312 | +56 USD | +4.3 | -0.00 to +0.44 USD | -8.6c per share |
| 12:00 local | 1,279 | 564 | 2,698 | +25 USD | +0.9 | -0.11 to +0.20 USD | -11.6c per share |

- The uncalibrated model gave +8.3c and +2.5c per share on the same orders logic; calibrating the spread (which the section 10 Brier test needs) widens the tails, adds a few orders and lowers the realized edge. Neither version has a bootstrap interval that excludes zero at conservative fills.
- The model expects about 20c per share on the orders that fill and realizes 4c or less: most of the paper edge is adverse selection, which the tape captures without any haircut. The 50% haircut on winning fills on top of that turns everything clearly negative; for through fills it double counts (a print beyond the level proves the fill), for touch fills it stands in for queue position.
- The NO side carries what there is (bids on NO when the market prices a bucket 10c above the model): 681 orders at 06:00, 74% of fills win, +4.8c per share. The YES side (bids on underpriced buckets) fills often and wins 14 to 21% of the time: +2.4c at 06:00, -0.6c at noon.
- Capacity is not the constraint: 153,000 to 267,000 shares printed beyond the order levels over the period, against 1,300 to 2,700 shares filled at 5 per order. The constraint is that the edge per share is small and unstable across months.
- Verdict against section 10: Brier criterion passed (T10, T12), PnL criterion not passed at conservative fills. The two-days-out edge is real in probability terms but not tradeable on its own with maker orders at 10c of edge. It becomes interesting only if the same-day or one-day-ahead model improves (H16) or the signal is stronger in other cities (T14).

## Findings, London (EGLC, 2025-02 to 2026-07-20, calibrated t EMOS at lead 3, 5 shares per order)

Command: `python -m weather_edge.backtest --stations EGLC --decision-hours 6 12` (T16).

| decision (two days before) | orders | through fills | shares | PnL | c per share | PnL per order, day bootstrap 90% | with 50% haircut on winning fills |
|---|---|---|---|---|---|---|---|
| 06:00 local | 383 | 164 | 799 | +25 USD | +3.2 | -0.14 to +0.44 USD | -7.9c per share |
| 12:00 local | 1,041 | 412 | 1,993 | **+110 USD** | **+5.5** | **+0.08 to +0.45 USD** | -7.1c per share |

- London at noon is the first case with a bootstrap interval that excludes zero on through fills: 15 of 18 months positive, the three negative months lose 1.5 to 5.4 USD, and the gain is not front-loaded (2026-01 +36 USD, 2025-02 +24 USD, all of 2026-05 to 07 positive). Touch fills agree (+5.7c). The NO side does the work again (+6.7c per share, 71% of fills win); the YES side is +2.1c with an interval around zero.
- The model expects 18.6c per filled share and realizes 5.5c, the same 70% adverse selection as NYC. With the 50% haircut on winning fills on top the result is negative, as everywhere.
- London markets are quoted earlier than NYC (1,041 noon orders against 1,279 for NYC on a similar number of days) and the 06:00 decision has fewer orders and no clear edge.
- Capacity: 195,000 shares printed beyond the levels at noon against 1,993 filled at 5 per order; about 470 shares per filled order, so size could grow tenfold before the through rule stops describing reality.
- Verdict against section 10: Brier criterion passed (T14), PnL positive on through fills at noon (interval excludes zero), negative under the haircut. Marginal pass. The candidate for paper trading is London, noon two days before, NO side, at 10c of edge; it must show the same 5c per share in Phase 9 against live books before any live order.

## KLGA, decision 06:00 local two days before

Scored buckets with a market price at the decision: 1808; orders: 748.

### All orders

| fill_model      |   orders |   orders_filled |   filled_shares |   pnl_usd |   pnl_c_per_share |   pnl_usd_per_order_ci_low |   pnl_usd_per_order_ci_high |   win_rate_filled |   expected_c_per_share_filled |   capacity_shares |
|:----------------|---------:|----------------:|----------------:|----------:|------------------:|---------------------------:|----------------------------:|------------------:|------------------------------:|------------------:|
| touch           |      748 |             287 |       1373.7400 |   59.9782 |            4.3661 |                     0.0022 |                      0.4270 |            0.6272 |                       19.5501 |       161182.0200 |
| through         |      748 |             272 |       1311.9900 |   56.4018 |            4.2990 |                    -0.0045 |                      0.4362 |            0.6287 |                       19.3112 |       153100.0800 |
| touch_haircut   |      748 |             287 |        943.1450 |  -80.6382 |           -8.5499 |                    -0.4470 |                     -0.1225 |            0.6272 |                       19.5501 |       161182.0200 |
| through_haircut |      748 |             272 |        901.3000 |  -77.4400 |           -8.5920 |                    -0.4501 |                     -0.1151 |            0.6287 |                       19.3112 |       153100.0800 |

### By side

| side   | fill_model      |   orders |   orders_filled |   filled_shares |   pnl_usd |   pnl_c_per_share |   pnl_usd_per_order_ci_low |   pnl_usd_per_order_ci_high |   win_rate_filled |   expected_c_per_share_filled |   capacity_shares |
|:-------|:----------------|---------:|----------------:|----------------:|----------:|------------------:|---------------------------:|----------------------------:|------------------:|------------------------------:|------------------:|
| no     | touch           |      681 |             226 |       1084.5700 |   53.5392 |            4.9364 |                     0.0304 |                      0.4381 |            0.7434 |                       18.2550 |        72702.0500 |
| no     | through         |      681 |             214 |       1029.7600 |   49.4900 |            4.8060 |                    -0.0149 |                      0.4518 |            0.7430 |                       18.0518 |        65943.5300 |
| no     | touch_haircut   |      681 |             226 |        683.9750 |  -65.2772 |           -9.5438 |                    -0.4609 |                     -0.1239 |            0.7434 |                       18.2550 |        72702.0500 |
| no     | through_haircut |      681 |             214 |        649.0700 |  -62.5518 |           -9.6371 |                    -0.4934 |                     -0.1099 |            0.7430 |                       18.0518 |        65943.5300 |
| yes    | touch           |       67 |              61 |        289.1700 |    6.4390 |            2.2267 |                    -0.3393 |                      0.5538 |            0.1967 |                       24.3483 |        88479.9700 |
| yes    | through         |       67 |              58 |        282.2300 |    6.9118 |            2.4490 |                    -0.3400 |                      0.6110 |            0.2069 |                       23.9577 |        87156.5500 |
| yes    | touch_haircut   |       67 |              61 |        259.1700 |  -15.3610 |           -5.9270 |                    -0.5315 |                      0.0212 |            0.1967 |                       24.3483 |        88479.9700 |
| yes    | through_haircut |       67 |              58 |        252.2300 |  -14.8882 |           -5.9026 |                    -0.5385 |                      0.0471 |            0.2069 |                       23.9577 |        87156.5500 |

### By month, through fills (the tape is complete through 2026-04, about 80% after)

| month   | fill_model   |   orders |   orders_filled |   filled_shares |   pnl_usd |   pnl_c_per_share |   pnl_usd_per_order_ci_low |   pnl_usd_per_order_ci_high |   win_rate_filled |   expected_c_per_share_filled |   capacity_shares |
|:--------|:-------------|---------:|----------------:|----------------:|----------:|------------------:|---------------------------:|----------------------------:|------------------:|------------------------------:|------------------:|
| 2025-02 | through      |       35 |              18 |         90.0000 |   13.2500 |           14.7222 |                    -0.0706 |                      1.6503 |            0.7222 |                       24.6692 |        64907.6100 |
| 2025-03 | through      |       45 |              25 |        115.7900 |   18.7316 |           16.1772 |                     0.0027 |                      1.5982 |            0.7600 |                       23.1316 |         3952.1900 |
| 2025-04 | through      |       39 |              16 |         63.9000 |    8.5960 |           13.4523 |                    -0.3063 |                      1.3408 |            0.6875 |                       17.3036 |          610.9500 |
| 2025-05 | through      |       51 |              25 |        119.5600 |    1.1832 |            0.9896 |                    -0.5456 |                      0.5714 |            0.6000 |                       19.4051 |         4984.0900 |
| 2025-06 | through      |       86 |              14 |         69.3300 |   -3.6108 |           -5.2081 |                    -1.0292 |                      0.3557 |            0.4286 |                       24.0386 |         2078.0600 |
| 2025-07 | through      |      159 |              13 |         55.2400 |   14.2351 |           25.7696 |                     0.0693 |                      2.0693 |            0.6923 |                       26.8860 |         1825.1900 |
| 2025-08 | through      |      100 |               5 |         22.0000 |   -8.1800 |          -37.1818 |                    -2.5000 |                     -0.8360 |            0.0000 |                       17.8208 |          339.0500 |
| 2025-09 | through      |       35 |               5 |         23.7700 |   11.4227 |           48.0551 |                     1.4500 |                      3.0571 |            1.0000 |                       19.8798 |           98.7100 |
| 2025-10 | through      |       35 |              13 |         65.0000 |   -1.7500 |           -2.6923 |                    -1.1893 |                      1.0800 |            0.4615 |                       18.9019 |         1880.2000 |
| 2025-11 | through      |       23 |              13 |         65.0000 |   -5.9500 |           -9.1538 |                    -1.0833 |                      0.5155 |            0.4615 |                       21.3711 |         9142.0400 |
| 2025-12 | through      |       13 |              11 |         52.4000 |   -1.0260 |           -1.9580 |                    -1.3652 |                      1.4682 |            0.4545 |                       23.5403 |         4947.9400 |
| 2026-03 | through      |       25 |              23 |        115.0000 |   -7.7000 |           -6.6957 |                    -1.1026 |                      0.3714 |            0.6087 |                       15.1620 |        18422.0700 |
| 2026-04 | through      |       53 |              50 |        250.0000 |   11.4000 |            4.5600 |                    -0.2274 |                      0.7276 |            0.6800 |                       16.9248 |        27111.7100 |
| 2026-05 | through      |       45 |              37 |        185.0000 |    6.4500 |            3.4865 |                    -0.3937 |                      0.7382 |            0.7027 |                       15.0191 |        11565.0000 |
| 2026-06 | through      |        4 |               4 |         20.0000 |   -0.6500 |           -3.2500 |                   nan      |                    nan      |            0.5000 |                       15.1475 |         1235.2700 |

## KLGA, decision 12:00 local two days before

Scored buckets with a market price at the decision: 3215; orders: 1279.

### All orders

| fill_model      |   orders |   orders_filled |   filled_shares |   pnl_usd |   pnl_c_per_share |   pnl_usd_per_order_ci_low |   pnl_usd_per_order_ci_high |   win_rate_filled |   expected_c_per_share_filled |   capacity_shares |
|:----------------|---------:|----------------:|----------------:|----------:|------------------:|---------------------------:|----------------------------:|------------------:|------------------------------:|------------------:|
| touch           |     1279 |             591 |       2833.8800 |   53.0361 |            1.8715 |                    -0.0653 |                      0.2474 |            0.5685 |                       20.1260 |       289066.7400 |
| through         |     1279 |             564 |       2697.9700 |   25.2067 |            0.9343 |                    -0.1149 |                      0.2010 |            0.5621 |                       20.0539 |       266926.7400 |
| touch_haircut   |     1279 |             591 |       2038.6050 | -216.6789 |          -10.6288 |                    -0.4882 |                     -0.2397 |            0.5685 |                       20.1260 |       289066.7400 |
| through_haircut |     1279 |             564 |       1950.9850 | -226.7774 |          -11.6237 |                    -0.5277 |                     -0.2781 |            0.5621 |                       20.0539 |       266926.7400 |

### By side

| side   | fill_model      |   orders |   orders_filled |   filled_shares |   pnl_usd |   pnl_c_per_share |   pnl_usd_per_order_ci_low |   pnl_usd_per_order_ci_high |   win_rate_filled |   expected_c_per_share_filled |   capacity_shares |
|:-------|:----------------|---------:|----------------:|----------------:|----------:|------------------:|---------------------------:|----------------------------:|------------------:|------------------------------:|------------------:|
| no     | touch           |     1119 |             450 |       2140.1800 |   54.2590 |            2.5353 |                    -0.0503 |                      0.2915 |            0.7022 |                       18.8729 |       127905.8800 |
| no     | through         |     1119 |             429 |       2041.8000 |   29.2164 |            1.4309 |                    -0.1116 |                      0.2551 |            0.6946 |                       18.6592 |       113485.9200 |
| no     | touch_haircut   |     1119 |             450 |       1394.9050 | -181.4310 |          -13.0067 |                    -0.5428 |                     -0.2578 |            0.7022 |                       18.8729 |       127905.8800 |
| no     | through_haircut |     1119 |             429 |       1340.4950 | -191.2807 |          -14.2694 |                    -0.5978 |                     -0.2930 |            0.6946 |                       18.6592 |       113485.9200 |
| yes    | touch           |      160 |             141 |        693.7000 |   -1.2229 |           -0.1763 |                    -0.2578 |                      0.2558 |            0.1418 |                       24.1254 |       161160.8600 |
| yes    | through         |      160 |             135 |        656.1700 |   -4.0097 |           -0.6111 |                    -0.2765 |                      0.2559 |            0.1407 |                       24.4859 |       153440.8200 |
| yes    | touch_haircut   |      160 |             141 |        643.7000 |  -35.2479 |           -5.4758 |                    -0.4013 |                     -0.0893 |            0.1418 |                       24.1254 |       161160.8600 |
| yes    | through_haircut |      160 |             135 |        610.4900 |  -35.4967 |           -5.8145 |                    -0.4151 |                     -0.0971 |            0.1407 |                       24.4859 |       153440.8200 |

### By month, through fills (the tape is complete through 2026-04, about 80% after)

| month   | fill_model   |   orders |   orders_filled |   filled_shares |   pnl_usd |   pnl_c_per_share |   pnl_usd_per_order_ci_low |   pnl_usd_per_order_ci_high |   win_rate_filled |   expected_c_per_share_filled |   capacity_shares |
|:--------|:-------------|---------:|----------------:|----------------:|----------:|------------------:|---------------------------:|----------------------------:|------------------:|------------------------------:|------------------:|
| 2025-02 | through      |       39 |              15 |         75.0000 |   -0.4000 |           -0.5333 |                    -1.2533 |                      1.2317 |            0.5333 |                       25.5046 |         4858.2500 |
| 2025-03 | through      |       65 |              38 |        186.4400 |    9.2608 |            4.9672 |                    -0.4676 |                      0.9533 |            0.5263 |                       23.7037 |        14601.1300 |
| 2025-04 | through      |       75 |              30 |        134.2700 |   28.7353 |           21.4011 |                     0.3858 |                      1.6482 |            0.7667 |                       20.0222 |         3612.2300 |
| 2025-05 | through      |      114 |              44 |        212.3800 |    4.4481 |            2.0944 |                    -0.4374 |                      0.6143 |            0.6136 |                       19.9158 |         4186.4400 |
| 2025-06 | through      |      147 |              44 |        197.2900 |  -19.5793 |           -9.9241 |                    -0.8299 |                      0.0060 |            0.5000 |                       24.5112 |         5031.5100 |
| 2025-07 | through      |      147 |              27 |        106.7900 |   12.3058 |           11.5234 |                    -0.4022 |                      1.1231 |            0.7037 |                       25.4481 |         2800.7400 |
| 2025-08 | through      |       95 |              13 |         54.6800 |   -5.1195 |           -9.3627 |                    -1.2665 |                      0.4452 |            0.3077 |                       17.1197 |         3633.1700 |
| 2025-09 | through      |       90 |              16 |         66.1300 |   14.4316 |           21.8231 |                     0.1114 |                      1.3907 |            0.8750 |                       19.3306 |          693.0900 |
| 2025-10 | through      |      113 |              28 |        138.6400 |  -12.4744 |           -8.9977 |                    -1.3003 |                      0.3568 |            0.4643 |                       20.4042 |         2588.6200 |
| 2025-11 | through      |       65 |              38 |        186.1100 |   -0.8109 |           -0.4357 |                    -0.5430 |                      0.5357 |            0.4474 |                       18.9784 |        24511.3300 |
| 2025-12 | through      |       64 |              37 |        182.4400 |   -6.7228 |           -3.6849 |                    -0.8842 |                      0.4817 |            0.3784 |                       18.9121 |        27067.9300 |
| 2026-01 | through      |       52 |              37 |        174.9300 |   14.6741 |            8.3886 |                    -0.3016 |                      1.0841 |            0.5946 |                       20.8681 |        17520.4900 |
| 2026-02 | through      |       43 |              41 |        203.0800 |  -16.9912 |           -8.3668 |                    -0.9012 |                      0.0634 |            0.3659 |                       19.6008 |        57168.8600 |
| 2026-03 | through      |       48 |              45 |        225.0000 |   11.6000 |            5.1556 |                    -0.3396 |                      0.7924 |            0.6667 |                       17.3374 |        35364.9000 |
| 2026-04 | through      |       58 |              54 |        270.0000 |    5.3000 |            1.9630 |                    -0.3559 |                      0.5635 |            0.6296 |                       17.7541 |        46057.8600 |
| 2026-05 | through      |       57 |              51 |        254.7900 |  -16.3509 |           -6.4174 |                    -0.6967 |                      0.0599 |            0.6078 |                       16.5076 |        15453.8000 |
| 2026-06 | through      |        7 |               6 |         30.0000 |    2.9000 |            9.6667 |                    -1.3300 |                      1.5900 |            0.6667 |                       17.3131 |         1776.3900 |

## EGLC, decision 06:00 local two days before

Scored buckets with a market price at the decision: 1805; orders: 383.

### All orders

| fill_model      |   orders |   orders_filled |   filled_shares |   pnl_usd |   pnl_c_per_share |   pnl_usd_per_order_ci_low |   pnl_usd_per_order_ci_high |   win_rate_filled |   expected_c_per_share_filled |   capacity_shares |
|:----------------|---------:|----------------:|----------------:|----------:|------------------:|---------------------------:|----------------------------:|------------------:|------------------------------:|------------------:|
| touch           |      383 |             178 |        864.8900 |   31.2934 |            3.6182 |                    -0.0964 |                      0.4597 |            0.5449 |                       16.6829 |        80454.0400 |
| through         |      383 |             164 |        798.5500 |   25.3716 |            3.1772 |                    -0.1351 |                      0.4422 |            0.5427 |                       16.5797 |        72610.6600 |
| touch_haircut   |      383 |             178 |        633.6950 |  -47.9533 |           -7.5673 |                    -0.4911 |                     -0.0555 |            0.5449 |                       16.6829 |        80454.0400 |
| through_haircut |      383 |             164 |        586.7750 |  -46.4392 |           -7.9143 |                    -0.5108 |                     -0.0610 |            0.5427 |                       16.5797 |        72610.6600 |

### By side

| side   | fill_model      |   orders |   orders_filled |   filled_shares |   pnl_usd |   pnl_c_per_share |   pnl_usd_per_order_ci_low |   pnl_usd_per_order_ci_high |   win_rate_filled |   expected_c_per_share_filled |   capacity_shares |
|:-------|:----------------|---------:|----------------:|----------------:|----------:|------------------:|---------------------------:|----------------------------:|------------------:|------------------------------:|------------------:|
| no     | touch           |      314 |             123 |        596.8100 |   27.8182 |            4.6611 |                    -0.1257 |                      0.5594 |            0.7317 |                       16.4758 |        40208.5100 |
| no     | through         |      314 |             114 |        552.3700 |   27.6804 |            5.0112 |                    -0.1202 |                      0.5920 |            0.7368 |                       16.5891 |        34936.4100 |
| no     | touch_haircut   |      314 |             123 |        379.6550 |  -39.2659 |          -10.3425 |                    -0.6076 |                     -0.0395 |            0.7317 |                       16.4758 |        40208.5100 |
| no     | through_haircut |      314 |             114 |        351.1850 |  -35.0848 |           -9.9904 |                    -0.6173 |                     -0.0159 |            0.7368 |                       16.5891 |        34936.4100 |
| yes    | touch           |       69 |              55 |        268.0800 |    3.4752 |            1.2963 |                    -0.2958 |                      0.4201 |            0.1273 |                       17.1460 |        40245.5300 |
| yes    | through         |       69 |              50 |        246.1800 |   -2.3088 |           -0.9379 |                    -0.3602 |                      0.3426 |            0.1000 |                       16.5582 |        37674.2500 |
| yes    | touch_haircut   |       69 |              55 |        254.0400 |   -8.6874 |           -3.4197 |                    -0.3664 |                      0.0482 |            0.1273 |                       17.1460 |        40245.5300 |
| yes    | through_haircut |       69 |              50 |        235.5900 |  -11.3544 |           -4.8196 |                    -0.4102 |                     -0.0173 |            0.1000 |                       16.5582 |        37674.2500 |

### By month, through fills (the tape is complete through 2026-04, about 80% after)

| month   | fill_model   |   orders |   orders_filled |   filled_shares |   pnl_usd |   pnl_c_per_share |   pnl_usd_per_order_ci_low |   pnl_usd_per_order_ci_high |   win_rate_filled |   expected_c_per_share_filled |   capacity_shares |
|:--------|:-------------|---------:|----------------:|----------------:|----------:|------------------:|---------------------------:|----------------------------:|------------------:|------------------------------:|------------------:|
| 2025-03 | through      |       11 |               1 |          5.0000 |   -0.5500 |          -11.0000 |                   nan      |                    nan      |            0.0000 |                       18.4431 |           70.4400 |
| 2025-04 | through      |       22 |               5 |         22.9500 |   -1.8880 |           -8.2266 |                    -1.4167 |                      1.3000 |            0.4000 |                       20.3511 |         2077.7000 |
| 2025-05 | through      |       26 |              13 |         65.0000 |   -0.6000 |           -0.9231 |                    -0.5112 |                      0.5501 |            0.5385 |                       17.2111 |         1953.2300 |
| 2025-06 | through      |       35 |               3 |         13.9200 |   -2.7268 |          -19.5891 |                   nan      |                    nan      |            0.3333 |                       14.8569 |           95.8200 |
| 2025-07 | through      |       39 |               5 |         22.7800 |   -3.5272 |          -15.4838 |                    -3.5750 |                      1.2076 |            0.6000 |                       17.8564 |          119.8400 |
| 2025-08 | through      |       19 |               2 |          6.0400 |   -0.1088 |           -1.8013 |                   nan      |                    nan      |            0.5000 |                       21.0637 |           47.1300 |
| 2025-09 | through      |       23 |               9 |         45.0000 |    0.1500 |            0.3333 |                    -0.6503 |                      1.3585 |            0.5556 |                       15.2168 |          766.4000 |
| 2025-10 | through      |       20 |               3 |         15.0000 |   -1.2000 |           -8.0000 |                   nan      |                    nan      |            0.3333 |                       13.9036 |          161.2400 |
| 2025-11 | through      |       13 |               7 |         31.3200 |    3.1948 |           10.2005 |                    -0.8546 |                      1.9707 |            0.5714 |                       17.1196 |          790.1200 |
| 2025-12 | through      |        8 |               5 |         25.0000 |    0.8000 |            3.2000 |                    -1.4750 |                      2.0750 |            0.6000 |                       21.6557 |          303.7900 |
| 2026-03 | through      |       18 |              12 |         60.0000 |   -6.0000 |          -10.0000 |                    -1.5185 |                      0.3615 |            0.2500 |                       14.0115 |         5717.2200 |
| 2026-04 | through      |       41 |              26 |        130.0000 |   -1.2500 |           -0.9615 |                    -0.7238 |                      0.5480 |            0.4615 |                       16.1852 |        27592.8300 |
| 2026-05 | through      |       42 |              25 |        120.3600 |    8.0864 |            6.7185 |                    -0.3897 |                      1.0109 |            0.6400 |                       14.6806 |        10651.4700 |
| 2026-06 | through      |       39 |              32 |        156.1800 |   13.7412 |            8.7983 |                    -0.3148 |                      1.2060 |            0.5938 |                       18.2854 |        17248.4400 |
| 2026-07 | through      |       27 |              16 |         80.0000 |   17.2500 |           21.5625 |                     0.2568 |                      2.0900 |            0.7500 |                       15.7044 |         5014.9900 |

## EGLC, decision 12:00 local two days before

Scored buckets with a market price at the decision: 3118; orders: 1041.

### All orders

| fill_model      |   orders |   orders_filled |   filled_shares |   pnl_usd |   pnl_c_per_share |   pnl_usd_per_order_ci_low |   pnl_usd_per_order_ci_high |   win_rate_filled |   expected_c_per_share_filled |   capacity_shares |
|:----------------|---------:|----------------:|----------------:|----------:|------------------:|---------------------------:|----------------------------:|------------------:|------------------------------:|------------------:|
| touch           |     1041 |             439 |       2122.2500 |  121.2048 |            5.7111 |                     0.1010 |                      0.4529 |            0.5718 |                       18.5800 |       221096.2100 |
| through         |     1041 |             412 |       1992.9700 |  110.3217 |            5.5355 |                     0.0776 |                      0.4469 |            0.5728 |                       18.5960 |       194578.7100 |
| touch_haircut   |     1041 |             439 |       1520.0450 | -103.8351 |           -6.8311 |                    -0.3650 |                     -0.0988 |            0.5718 |                       18.5800 |       221096.2100 |
| through_haircut |     1041 |             412 |       1426.8200 | -101.3475 |           -7.1030 |                    -0.3860 |                     -0.1091 |            0.5728 |                       18.5960 |       194578.7100 |

### By side

| side   | fill_model      |   orders |   orders_filled |   filled_shares |   pnl_usd |   pnl_c_per_share |   pnl_usd_per_order_ci_low |   pnl_usd_per_order_ci_high |   win_rate_filled |   expected_c_per_share_filled |   capacity_shares |
|:-------|:----------------|---------:|----------------:|----------------:|----------:|------------------:|---------------------------:|----------------------------:|------------------:|------------------------------:|------------------:|
| no     | touch           |      914 |             332 |       1591.6600 |  109.0604 |            6.8520 |                     0.1412 |                      0.5185 |            0.7078 |                       19.0443 |       139448.5400 |
| no     | through         |      914 |             313 |       1502.3800 |  100.0273 |            6.6579 |                     0.1040 |                      0.5233 |            0.7061 |                       19.0403 |       119454.6200 |
| no     | touch_haircut   |      914 |             332 |       1029.4550 |  -87.5295 |           -8.5025 |                    -0.4165 |                     -0.1108 |            0.7078 |                       19.0443 |       139448.5400 |
| no     | through_haircut |      914 |             313 |        973.7300 |  -85.4419 |           -8.7747 |                    -0.4439 |                     -0.1129 |            0.7061 |                       19.0403 |       119454.6200 |
| yes    | touch           |      127 |             107 |        530.5900 |   12.1444 |            2.2888 |                    -0.1412 |                      0.4230 |            0.1495 |                       17.1395 |        81647.6700 |
| yes    | through         |      127 |              99 |        490.5900 |   10.2944 |            2.0984 |                    -0.1758 |                      0.4214 |            0.1515 |                       17.1913 |        75124.0900 |
| yes    | touch_haircut   |      127 |             107 |        490.5900 |  -16.3056 |           -3.3237 |                    -0.3007 |                      0.0281 |            0.1495 |                       17.1395 |        81647.6700 |
| yes    | through_haircut |      127 |              99 |        453.0900 |  -15.9056 |           -3.5105 |                    -0.3219 |                      0.0237 |            0.1515 |                       17.1913 |        75124.0900 |

### By month, through fills (the tape is complete through 2026-04, about 80% after)

| month   | fill_model   |   orders |   orders_filled |   filled_shares |   pnl_usd |   pnl_c_per_share |   pnl_usd_per_order_ci_low |   pnl_usd_per_order_ci_high |   win_rate_filled |   expected_c_per_share_filled |   capacity_shares |
|:--------|:-------------|---------:|----------------:|----------------:|----------:|------------------:|---------------------------:|----------------------------:|------------------:|------------------------------:|------------------:|
| 2025-02 | through      |       26 |              19 |         89.4200 |   23.7562 |           26.5670 |                     0.3070 |                      2.5128 |            0.6316 |                       22.0786 |         5068.3800 |
| 2025-03 | through      |       21 |               9 |         45.0000 |    1.6000 |            3.5556 |                    -0.8613 |                      1.2714 |            0.5556 |                       16.9824 |         1361.5600 |
| 2025-04 | through      |       28 |              10 |         42.0300 |    0.6332 |            1.5065 |                    -1.5709 |                      1.3995 |            0.5000 |                       20.2636 |         2464.9800 |
| 2025-05 | through      |       40 |              17 |         82.7000 |    4.9180 |            5.9468 |                    -0.4401 |                      1.1088 |            0.5882 |                       22.1434 |         4092.6900 |
| 2025-06 | through      |      100 |              13 |         55.1300 |    1.3469 |            2.4431 |                    -0.9409 |                      1.2486 |            0.6923 |                       20.6025 |          722.5600 |
| 2025-07 | through      |      164 |              13 |         57.4800 |    5.6900 |            9.8991 |                    -0.5784 |                      1.8091 |            0.5385 |                       24.2423 |         1535.3100 |
| 2025-08 | through      |       94 |              10 |         37.2800 |    0.8904 |            2.3884 |                    -0.7272 |                      0.9212 |            0.5000 |                       18.3123 |          375.5000 |
| 2025-09 | through      |       36 |              10 |         50.0000 |    5.6000 |           11.2000 |                    -0.6000 |                      1.8116 |            0.7000 |                       17.0831 |          763.7900 |
| 2025-10 | through      |       26 |               6 |         30.0000 |   -3.8500 |          -12.8333 |                    -2.1100 |                      0.8167 |            0.5000 |                       15.2529 |          828.1900 |
| 2025-11 | through      |       13 |              10 |         50.0000 |    1.9500 |            3.9000 |                    -0.9550 |                      1.7145 |            0.5000 |                       16.3229 |         4403.1700 |
| 2025-12 | through      |       66 |              19 |         87.0100 |   -5.3810 |           -6.1843 |                    -1.0606 |                      0.3951 |            0.4737 |                       21.8117 |         4426.7200 |
| 2026-01 | through      |      107 |              51 |        246.1400 |   36.3702 |           14.7762 |                     0.2265 |                      1.1608 |            0.6863 |                       22.3108 |        12749.8300 |
| 2026-02 | through      |       74 |              45 |        220.7800 |    6.2978 |            2.8525 |                    -0.3211 |                      0.6337 |            0.4889 |                       17.0913 |        16931.8700 |
| 2026-03 | through      |       40 |              30 |        150.0000 |    7.9500 |            5.3000 |                    -0.2303 |                      0.8240 |            0.6000 |                       17.0603 |        25812.0600 |
| 2026-04 | through      |       51 |              48 |        240.0000 |   -1.5500 |           -0.6458 |                    -0.5413 |                      0.5423 |            0.5417 |                       17.1166 |        53500.5700 |
| 2026-05 | through      |       51 |              41 |        205.0000 |   10.3000 |            5.0244 |                    -0.3493 |                      0.8298 |            0.6341 |                       16.6547 |        24850.2200 |
| 2026-06 | through      |       58 |              38 |        190.0000 |    4.1000 |            2.1579 |                    -0.4803 |                      0.8615 |            0.5000 |                       16.1130 |        16234.9900 |
| 2026-07 | through      |       46 |              23 |        115.0000 |    9.7000 |            8.4348 |                    -0.2077 |                      1.1555 |            0.5652 |                       16.0237 |        18456.3200 |
