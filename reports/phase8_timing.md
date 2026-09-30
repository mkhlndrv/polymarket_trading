# Phase 8: price reaction to model releases

Phase 8 timing study (T19, H17): does the market lag model releases?

For every London and NYC market day before the holdout and every ECMWF and GFS run that covers the
local day (at least 7 three-hourly steps inside it), the run's publication time is the Last-Modified
of its last in-day step. Model move = the run's daily maximum minus the previous run's of the same
model, in the market's unit. Market move = change of the market-implied expected high (sum of price x
bucket centre over sum of price, as-of prices) from one hour before publication to d minutes after,
for d in DELTAS; -30 is a control window before publication. Per station, model, horizon and d:
regression slope of market move on model move, correlation, and the mean absolute market move when
the model moved by at least one unit.

## Findings (T19, H17): the market does not react to run releases

Command: `python -m weather_edge timing`. London: 8,025 run publications on 552 days. New York: 8,331 on 549 days. 2025-01 to 2026-07, holdout untouched. Model move = the run's daily maximum minus the previous run's of the same model (median 0.36 °F in London, 0.56 °F in New York; 1,385 and 2,467 runs moved by a full degree or more). Market move = the change in the market-implied expected high from one hour before publication.

| horizon | slope of market move on model move at +15 min | at +240 min | correlation at +240 min | mean market move when the model moved 1 F or more, +240 min | same when it moved less |
|---|---|---|---|---|---|
| ECMWF, two days before (both cities) | 0.00 | 0.03 to 0.04 | 0.09 to 0.10 | 0.29 to 0.33 F | 0.24 to 0.29 F |
| ECMWF, day before | 0.00 | 0.04 to 0.05 | 0.10 to 0.13 | 0.30 to 0.39 F | 0.23 to 0.35 F |
| ECMWF, same day | 0.01 to 0.04 | 0.10 | 0.12 to 0.15 | 0.46 to 0.57 F | 0.35 to 0.52 F |
| GFS, all horizons | 0.00 | 0.01 to 0.04 | 0.03 to 0.10 | | |

- A run that moves its forecast high by one degree moves the market's implied high by about 0.04 °F four hours later, and by nothing measurable in the first 15 minutes. The sign of the market's move agrees with the model's 44 to 60% of the time, a coin flip. The control window 30 minutes before publication shows the same nothing, so there is no early leak either.
- The market drifts by 0.25 to 0.5 °F over four hours whether or not the newest run changed anything. So what moves prices is not the ECMWF or GFS daily maximum as it becomes public. Either the market reads other guidance (NWS forecasts, blended products, its own models) or it takes the runs in through slow re-quoting that this measure cannot tell from noise.
- H17 is rejected. There is no lag to exploit because there is no reaction. A fast quoter keyed to publication times would be trading against noise.
- Caveats. The implied high is a probability-weighted bucket centre from as-of prices, which is noisy where books are thin, and the two-days-before windows have fewer runs with quotes. Neither would hide a slope of 0.5 if it existed.

## EGLC

| station   |   runs_with_prices |   days |   runs_model_moved_1_unit_or_more |   median_abs_model_move | unit   |
|:----------|-------------------:|-------:|----------------------------------:|------------------------:|:-------|
| EGLC      |               8025 |    552 |                              1385 |                  0.3598 | F      |

| model   | horizon         |   minutes_after |   runs |   slope |    corr |   mean_abs_market_move_big |   mean_abs_market_move_small |   share_same_sign_big |
|:--------|:----------------|----------------:|-------:|--------:|--------:|---------------------------:|-----------------------------:|----------------------:|
| ecmwf   | day before      |             -30 |   2085 |  0.0013 |  0.0079 |                     0.0805 |                       0.0620 |                0.4390 |
| ecmwf   | day before      |               0 |   2086 | -0.0021 | -0.0098 |                     0.1249 |                       0.0944 |                0.4512 |
| ecmwf   | day before      |               5 |   2086 | -0.0045 | -0.0194 |                     0.1311 |                       0.0990 |                0.4604 |
| ecmwf   | day before      |              15 |   2085 | -0.0020 | -0.0080 |                     0.1497 |                       0.1076 |                0.5061 |
| ecmwf   | day before      |              30 |   2084 |  0.0050 |  0.0189 |                     0.1585 |                       0.1197 |                0.5213 |
| ecmwf   | day before      |              60 |   2084 |  0.0024 |  0.0082 |                     0.1749 |                       0.1381 |                0.5122 |
| ecmwf   | day before      |             120 |   2085 |  0.0138 |  0.0402 |                     0.2059 |                       0.1742 |                0.5457 |
| ecmwf   | day before      |             240 |   2083 |  0.0416 |  0.0967 |                     0.3043 |                       0.2278 |                0.5976 |
| ecmwf   | same day        |             -30 |   1080 |  0.0146 |  0.0786 |                     0.0848 |                       0.0773 |                0.5764 |
| ecmwf   | same day        |               0 |   1079 |  0.0311 |  0.1156 |                     0.1445 |                       0.1187 |                0.5625 |
| ecmwf   | same day        |               5 |   1080 |  0.0324 |  0.1109 |                     0.1581 |                       0.1255 |                0.5903 |
| ecmwf   | same day        |              15 |   1078 |  0.0379 |  0.1272 |                     0.1748 |                       0.1347 |                0.5833 |
| ecmwf   | same day        |              30 |   1078 |  0.0420 |  0.1311 |                     0.2141 |                       0.1467 |                0.5764 |
| ecmwf   | same day        |              60 |   1077 |  0.0551 |  0.1459 |                     0.2493 |                       0.1723 |                0.5208 |
| ecmwf   | same day        |             120 |   1063 |  0.0900 |  0.1781 |                     0.3096 |                       0.2220 |                0.5944 |
| ecmwf   | same day        |             240 |   1024 |  0.0987 |  0.1240 |                     0.4575 |                       0.3485 |                0.6028 |
| ecmwf   | two days before |             -30 |    966 |  0.0002 |  0.0011 |                     0.0656 |                       0.0772 |                0.4010 |
| ecmwf   | two days before |               0 |    962 | -0.0047 | -0.0246 |                     0.1009 |                       0.0992 |                0.4359 |
| ecmwf   | two days before |               5 |    964 |  0.0017 |  0.0086 |                     0.1065 |                       0.1044 |                0.4308 |
| ecmwf   | two days before |              15 |    961 |  0.0021 |  0.0103 |                     0.1077 |                       0.1125 |                0.4794 |
| ecmwf   | two days before |              30 |    963 |  0.0018 |  0.0082 |                     0.1236 |                       0.1246 |                0.4359 |
| ecmwf   | two days before |              60 |    962 | -0.0005 | -0.0018 |                     0.1593 |                       0.1463 |                0.4410 |
| ecmwf   | two days before |             120 |    961 |  0.0119 |  0.0406 |                     0.2102 |                       0.1824 |                0.5077 |
| ecmwf   | two days before |             240 |    956 |  0.0386 |  0.1037 |                     0.2851 |                       0.2444 |                0.6154 |
| gfs     | day before      |             -30 |   2122 |  0.0008 |  0.0058 |                     0.0850 |                       0.0614 |                0.4555 |
| gfs     | day before      |               0 |   2121 |  0.0025 |  0.0130 |                     0.1330 |                       0.0936 |                0.4707 |
| gfs     | day before      |               5 |   2122 |  0.0027 |  0.0143 |                     0.1358 |                       0.0970 |                0.4758 |
| gfs     | day before      |              15 |   2122 | -0.0023 | -0.0117 |                     0.1497 |                       0.1039 |                0.4784 |
| gfs     | day before      |              30 |   2121 | -0.0009 | -0.0042 |                     0.1669 |                       0.1168 |                0.4987 |
| gfs     | day before      |              60 |   2122 | -0.0040 | -0.0166 |                     0.1982 |                       0.1370 |                0.4835 |
| gfs     | day before      |             120 |   2120 | -0.0052 | -0.0175 |                     0.2467 |                       0.1739 |                0.5102 |
| gfs     | day before      |             240 |   2119 |  0.0125 |  0.0339 |                     0.3237 |                       0.2323 |                0.5115 |
| gfs     | same day        |             -30 |    551 |  0.0081 |  0.0661 |                     0.0700 |                       0.0505 |                0.5758 |
| gfs     | same day        |               0 |    551 | -0.0007 | -0.0038 |                     0.1075 |                       0.0786 |                0.4697 |
| gfs     | same day        |               5 |    551 |  0.0046 |  0.0259 |                     0.1154 |                       0.0826 |                0.4848 |
| gfs     | same day        |              15 |    551 |  0.0086 |  0.0442 |                     0.1219 |                       0.0885 |                0.4697 |
| gfs     | same day        |              30 |    551 |  0.0157 |  0.0803 |                     0.1332 |                       0.0924 |                0.5606 |
| gfs     | same day        |              60 |    551 |  0.0228 |  0.0881 |                     0.1728 |                       0.1263 |                0.5303 |
| gfs     | same day        |             120 |    551 | -0.0025 | -0.0071 |                     0.2574 |                       0.1716 |                0.5000 |
| gfs     | same day        |             240 |    550 |  0.0260 |  0.0512 |                     0.3306 |                       0.2720 |                0.5152 |
| gfs     | two days before |             -30 |   1213 | -0.0000 | -0.0002 |                     0.0583 |                       0.0686 |                0.4141 |
| gfs     | two days before |               0 |   1210 | -0.0010 | -0.0056 |                     0.1022 |                       0.1012 |                0.3945 |
| gfs     | two days before |               5 |   1212 | -0.0017 | -0.0090 |                     0.1086 |                       0.1077 |                0.3882 |
| gfs     | two days before |              15 |   1213 | -0.0003 | -0.0014 |                     0.1064 |                       0.1120 |                0.4141 |
| gfs     | two days before |              30 |   1209 | -0.0000 | -0.0002 |                     0.1111 |                       0.1223 |                0.4196 |
| gfs     | two days before |              60 |   1201 |  0.0016 |  0.0073 |                     0.1184 |                       0.1394 |                0.4980 |
| gfs     | two days before |             120 |   1202 | -0.0025 | -0.0091 |                     0.1953 |                       0.1778 |                0.4427 |
| gfs     | two days before |             240 |   1204 |  0.0010 |  0.0030 |                     0.2349 |                       0.2316 |                0.5490 |

## KLGA

| station   |   runs_with_prices |   days |   runs_model_moved_1_unit_or_more |   median_abs_model_move | unit   |
|:----------|-------------------:|-------:|----------------------------------:|------------------------:|:-------|
| KLGA      |               8331 |    549 |                              2467 |                  0.5644 | F      |

| model   | horizon         |   minutes_after |   runs |   slope |    corr |   mean_abs_market_move_big |   mean_abs_market_move_small |   share_same_sign_big |
|:--------|:----------------|----------------:|-------:|--------:|--------:|---------------------------:|-----------------------------:|----------------------:|
| ecmwf   | day before      |             -30 |   2088 | -0.0009 | -0.0070 |                     0.0950 |                       0.0965 |                0.4715 |
| ecmwf   | day before      |               0 |   2090 | -0.0003 | -0.0019 |                     0.1447 |                       0.1451 |                0.4945 |
| ecmwf   | day before      |               5 |   2090 |  0.0012 |  0.0063 |                     0.1534 |                       0.1515 |                0.4834 |
| ecmwf   | day before      |              15 |   2088 |  0.0041 |  0.0216 |                     0.1644 |                       0.1609 |                0.4803 |
| ecmwf   | day before      |              30 |   2089 |  0.0083 |  0.0401 |                     0.1877 |                       0.1770 |                0.4882 |
| ecmwf   | day before      |              60 |   2089 |  0.0169 |  0.0733 |                     0.2286 |                       0.1998 |                0.5237 |
| ecmwf   | day before      |             120 |   2087 |  0.0327 |  0.1115 |                     0.2952 |                       0.2538 |                0.5452 |
| ecmwf   | day before      |             240 |   2086 |  0.0510 |  0.1283 |                     0.3887 |                       0.3544 |                0.5730 |
| ecmwf   | same day        |             -30 |   1073 |  0.0104 |  0.0476 |                     0.1066 |                       0.1252 |                0.5000 |
| ecmwf   | same day        |               0 |   1072 |  0.0193 |  0.0737 |                     0.1569 |                       0.1803 |                0.5423 |
| ecmwf   | same day        |               5 |   1072 |  0.0189 |  0.0717 |                     0.1644 |                       0.1836 |                0.5392 |
| ecmwf   | same day        |              15 |   1071 |  0.0133 |  0.0528 |                     0.1768 |                       0.1930 |                0.5455 |
| ecmwf   | same day        |              30 |   1070 |  0.0127 |  0.0446 |                     0.1924 |                       0.2207 |                0.5047 |
| ecmwf   | same day        |              60 |   1063 |  0.0260 |  0.0791 |                     0.2323 |                       0.2519 |                0.5331 |
| ecmwf   | same day        |             120 |   1047 |  0.0527 |  0.1203 |                     0.3276 |                       0.3370 |                0.5641 |
| ecmwf   | same day        |             240 |   1019 |  0.1040 |  0.1514 |                     0.5735 |                       0.5181 |                0.6254 |
| ecmwf   | two days before |             -30 |   1061 | -0.0045 | -0.0320 |                     0.1036 |                       0.0990 |                0.3922 |
| ecmwf   | two days before |               0 |   1058 | -0.0027 | -0.0151 |                     0.1552 |                       0.1480 |                0.4494 |
| ecmwf   | two days before |               5 |   1057 | -0.0031 | -0.0171 |                     0.1651 |                       0.1510 |                0.4792 |
| ecmwf   | two days before |              15 |   1058 | -0.0016 | -0.0086 |                     0.1740 |                       0.1586 |                0.4779 |
| ecmwf   | two days before |              30 |   1060 |  0.0016 |  0.0081 |                     0.1905 |                       0.1683 |                0.5000 |
| ecmwf   | two days before |              60 |   1059 |  0.0008 |  0.0039 |                     0.2136 |                       0.1891 |                0.4870 |
| ecmwf   | two days before |             120 |   1056 |  0.0097 |  0.0405 |                     0.2538 |                       0.2290 |                0.5196 |
| ecmwf   | two days before |             240 |   1055 |  0.0250 |  0.0867 |                     0.3259 |                       0.2873 |                0.5538 |
| gfs     | day before      |             -30 |   2306 |  0.0033 |  0.0235 |                     0.1071 |                       0.0932 |                0.5049 |
| gfs     | day before      |               0 |   2306 |  0.0034 |  0.0177 |                     0.1638 |                       0.1472 |                0.5147 |
| gfs     | day before      |               5 |   2305 |  0.0024 |  0.0117 |                     0.1730 |                       0.1542 |                0.5220 |
| gfs     | day before      |              15 |   2306 |  0.0026 |  0.0115 |                     0.1893 |                       0.1728 |                0.5163 |
| gfs     | day before      |              30 |   2305 |  0.0071 |  0.0289 |                     0.2137 |                       0.1875 |                0.5458 |
| gfs     | day before      |              60 |   2304 |  0.0097 |  0.0344 |                     0.2597 |                       0.2209 |                0.5155 |
| gfs     | day before      |             120 |   2304 |  0.0136 |  0.0406 |                     0.3403 |                       0.2675 |                0.5277 |
| gfs     | day before      |             240 |   2304 |  0.0409 |  0.0973 |                     0.4237 |                       0.3583 |                0.5595 |
| gfs     | same day        |             -30 |    559 |  0.0126 |  0.0679 |                     0.1318 |                       0.1039 |                0.4495 |
| gfs     | same day        |               0 |    558 |  0.0192 |  0.0813 |                     0.1585 |                       0.1467 |                0.4954 |
| gfs     | same day        |               5 |    558 |  0.0267 |  0.1052 |                     0.1777 |                       0.1558 |                0.5229 |
| gfs     | same day        |              15 |    558 |  0.0276 |  0.1064 |                     0.1909 |                       0.1635 |                0.5321 |
| gfs     | same day        |              30 |    558 |  0.0404 |  0.1302 |                     0.2146 |                       0.1927 |                0.5138 |
| gfs     | same day        |              60 |    557 |  0.0470 |  0.1416 |                     0.2415 |                       0.2132 |                0.5321 |
| gfs     | same day        |             120 |    557 |  0.0549 |  0.1107 |                     0.3428 |                       0.2833 |                0.5963 |
| gfs     | same day        |             240 |    552 |  0.1084 |  0.1820 |                     0.4538 |                       0.3920 |                0.5981 |
| gfs     | two days before |             -30 |   1228 | -0.0021 | -0.0157 |                     0.0972 |                       0.0939 |                0.4000 |
| gfs     | two days before |               0 |   1225 | -0.0050 | -0.0318 |                     0.1249 |                       0.1323 |                0.4322 |
| gfs     | two days before |               5 |   1227 | -0.0056 | -0.0339 |                     0.1336 |                       0.1408 |                0.4332 |
| gfs     | two days before |              15 |   1225 | -0.0052 | -0.0282 |                     0.1568 |                       0.1517 |                0.4799 |
| gfs     | two days before |              30 |   1221 | -0.0050 | -0.0262 |                     0.1648 |                       0.1666 |                0.4596 |
| gfs     | two days before |              60 |   1218 | -0.0086 | -0.0402 |                     0.2007 |                       0.1890 |                0.4759 |
| gfs     | two days before |             120 |   1219 |  0.0011 |  0.0044 |                     0.2799 |                       0.2325 |                0.4886 |
| gfs     | two days before |             240 |   1223 |  0.0141 |  0.0419 |                     0.3832 |                       0.3154 |                0.5163 |
