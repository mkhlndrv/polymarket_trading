# Phase 0 inventory: Polymarket daily temperature markets

Source: data/raw/gamma_events_20260929T214912Z.jsonl

Trade history is not part of this inventory; it comes from the dataset in Phase 1.

Events (city-days): 11375  |  Bucket markets: 118990  |  Cities: 56  |  Date range: 2025-01-20 to 2026-10-01  |  Total volume USD: 916,208,177

## Cities (gate: enough_history = at least 90 event-days)

| city          | stations           | unit   | first      | last       |   n_days |   n_resolved |   n_disputed |   volume_usd | sources                   | enough_history   |
|:--------------|:-------------------|:-------|:-----------|:-----------|---------:|-------------:|-------------:|-------------:|:--------------------------|:-----------------|
| London        | EGLC               | C,F    | 2025-01-22 | 2026-10-01 |      615 |          613 |           36 |   97,355,778 | noaa_wrh,wunderground     | True             |
| NYC           | KLGA               | F      | 2025-01-22 | 2026-10-01 |      613 |          611 |           21 |   79,423,125 | noaa_wrh,wunderground     | True             |
| Dallas        | KDAL               | F      | 2025-12-04 | 2026-10-01 |      300 |          298 |            3 |   20,361,624 | noaa_wrh,wunderground     | True             |
| Seoul         | RKSI               | C      | 2025-12-06 | 2026-10-01 |      299 |          298 |            5 |   57,186,727 | noaa_wrh,wunderground     | True             |
| Toronto       | CYYZ               | C      | 2025-12-06 | 2026-10-01 |      299 |          297 |            0 |   20,140,885 | noaa_wrh,wunderground     | True             |
| Atlanta       | KATL               | F      | 2025-12-05 | 2026-10-01 |      298 |          296 |            4 |   20,578,411 | noaa_wrh,wunderground     | True             |
| Seattle       | KSEA               | F      | 2025-12-05 | 2026-10-01 |      298 |          295 |            3 |   18,737,838 | noaa_wrh,wunderground     | True             |
| Buenos Aires  | SAEZ               | C      | 2025-12-06 | 2026-10-01 |      296 |          294 |            3 |   16,824,037 | noaa_wrh,wunderground     | True             |
| Miami         | KMIA               | F      | 2025-12-04 | 2026-10-01 |      253 |          251 |            0 |   20,551,659 | noaa_wrh,wunderground     | True             |
| Chicago       | KORD               | F      | 2025-12-04 | 2026-10-01 |      253 |          251 |            0 |   18,561,045 | noaa_wrh,wunderground     | True             |
| Wellington    | NZWN               | C      | 2026-01-22 | 2026-10-01 |      252 |          251 |            2 |   24,133,514 | noaa_wrh,wunderground     | True             |
| Ankara        | LTAC               | C      | 2026-01-22 | 2026-10-01 |      252 |          251 |            1 |   18,257,168 | noaa_wrh,wunderground     | True             |
| Paris         | LFPB,LFPG          | C      | 2026-02-11 | 2026-10-01 |      229 |          227 |            2 |   27,996,132 | noaa_wrh,wunderground     | True             |
| Sao Paulo     | SBGR               | C      | 2026-02-11 | 2026-10-01 |      227 |          224 |            0 |   12,171,797 | noaa_wrh,wunderground     | True             |
| Munich        | EDDM               | C      | 2026-03-05 | 2026-10-01 |      210 |          208 |            1 |   17,620,339 | noaa_wrh,wunderground     | True             |
| Lucknow       | VILK               | C      | 2026-03-05 | 2026-10-01 |      210 |          209 |            0 |    9,414,933 | noaa_wrh,wunderground     | True             |
| Tokyo         | RJTT               | C      | 2026-03-10 | 2026-10-01 |      205 |          204 |            0 |   20,742,897 | noaa_wrh,wunderground     | True             |
| Tel Aviv      | LLBG               | C      | 2026-03-10 | 2026-10-01 |      205 |          203 |            2 |   10,380,948 | noaa_wrh,wunderground     | True             |
| Shanghai      | ZSPD               | C      | 2026-03-13 | 2026-10-01 |      202 |          201 |            1 |   33,708,083 | noaa_wrh,wunderground     | True             |
| Singapore     | WSSS               | C      | 2026-03-13 | 2026-10-01 |      202 |          201 |            1 |   14,873,149 | noaa_wrh,wunderground     | True             |
| Hong Kong     | HKO,VHHH           | C      | 2026-03-13 | 2026-10-01 |      200 |          198 |            1 |   45,699,116 | hko,wunderground          | True             |
| Madrid        | LEMD               | C      | 2026-03-16 | 2026-10-01 |      199 |          197 |            1 |   18,495,928 | noaa_wrh,wunderground     | True             |
| Taipei        | CWA46692,RCSS,RCTP | C      | 2026-03-16 | 2026-10-01 |      199 |          198 |            1 |   15,963,948 | cwa,noaa_wrh,wunderground | True             |
| Milan         | LIMC               | C      | 2026-03-16 | 2026-10-01 |      199 |          197 |            0 |   12,839,751 | noaa_wrh,wunderground     | True             |
| Warsaw        | EPWA               | C      | 2026-03-16 | 2026-10-01 |      199 |          197 |            0 |   10,647,409 | noaa_wrh,wunderground     | True             |
| Beijing       | ZBAA               | C      | 2026-03-20 | 2026-10-01 |      195 |          194 |            0 |   20,125,926 | noaa_wrh,wunderground     | True             |
| Shenzhen      | ZGSZ               | C      | 2026-03-20 | 2026-10-01 |      195 |          194 |            1 |   19,726,171 | noaa_wrh,wunderground     | True             |
| Chongqing     | ZUCK               | C      | 2026-03-20 | 2026-10-01 |      195 |          194 |            0 |   12,484,238 | noaa_wrh,wunderground     | True             |
| Wuhan         | ZHHH               | C      | 2026-03-20 | 2026-10-01 |      195 |          194 |            0 |   11,293,405 | noaa_wrh,wunderground     | True             |
| Chengdu       | ZUUU               | C      | 2026-03-20 | 2026-10-01 |      194 |          193 |            0 |   14,912,819 | noaa_wrh,wunderground     | True             |
| Los Angeles   | KLAX               | F      | 2025-12-04 | 2026-10-01 |      192 |          190 |            0 |   13,826,734 | noaa_wrh,wunderground     | True             |
| Denver        | KBKF               | F      | 2025-12-04 | 2026-10-01 |      192 |          190 |            0 |    9,941,223 | noaa_wrh,wunderground     | True             |
| San Francisco | KSFO               | F      | 2026-03-24 | 2026-10-01 |      190 |          188 |            1 |   10,422,650 | noaa_wrh,wunderground     | True             |
| Houston       | KHOU               | F      | 2026-03-24 | 2026-10-01 |      190 |          188 |            1 |    8,880,524 | noaa_wrh,wunderground     | True             |
| Austin        | KAUS               | F      | 2026-03-24 | 2026-10-01 |      189 |          187 |            1 |    9,380,010 | noaa_wrh,wunderground     | True             |
| Istanbul      | LTFM               | C      | 2026-03-30 | 2026-10-01 |      186 |          185 |            1 |    9,077,944 | noaa_wrh                  | True             |
| Moscow        | UUWW               | C      | 2026-03-30 | 2026-10-01 |      185 |          183 |            1 |   10,311,323 | noaa_wrh                  | True             |
| Mexico City   | MMMX               | C      | 2026-03-30 | 2026-10-01 |      184 |          182 |            0 |    7,243,618 | noaa_wrh,wunderground     | True             |
| Amsterdam     | EHAM               | C      | 2026-04-03 | 2026-10-01 |      182 |          180 |            1 |   11,333,505 | noaa_wrh,wunderground     | True             |
| Kuala Lumpur  | WMKK               | C      | 2026-04-03 | 2026-10-01 |      182 |          181 |            1 |    9,934,838 | noaa_wrh,wunderground     | True             |
| Busan         | RKPK               | C      | 2026-04-03 | 2026-10-01 |      182 |          181 |            0 |    9,628,819 | noaa_wrh,wunderground     | True             |
| Helsinki      | EFHK               | C      | 2026-04-03 | 2026-10-01 |      182 |          181 |            0 |    9,279,753 | noaa_wrh,wunderground     | True             |
| Panama City   | MPMG               | C      | 2026-04-03 | 2026-10-01 |      180 |          178 |            0 |    4,512,900 | noaa_wrh,wunderground     | True             |
| Jeddah        | OEJN               | C      | 2026-04-09 | 2026-10-01 |      176 |          174 |            0 |    6,319,784 | noaa_wrh,wunderground     | True             |
| Cape Town     | FACT               | C      | 2026-04-09 | 2026-10-01 |      174 |          171 |            0 |    7,376,330 | noaa_wrh,wunderground     | True             |
| Guangzhou     | ZGGG               | C      | 2026-04-15 | 2026-10-01 |      170 |          169 |            0 |   12,210,185 | noaa_wrh,wunderground     | True             |
| Manila        | RPLL               | C      | 2026-04-15 | 2026-10-01 |      170 |          169 |            1 |    6,318,352 | noaa_wrh,wunderground     | True             |
| Karachi       | OPKC               | C      | 2026-04-15 | 2026-10-01 |      170 |          169 |            0 |    5,297,609 | noaa_wrh,wunderground     | True             |
| Qingdao       | ZSQD               | C      | 2026-04-27 | 2026-10-01 |      158 |          157 |            0 |    6,803,166 | noaa_wrh,wunderground     | True             |
| Zhengzhou     | ZHCC               | C      | 2026-05-20 | 2026-09-30 |       58 |           54 |            0 |      392,100 | noaa_wrh,wunderground     | False            |
| Jinan         | ZSJN               | C      | 2026-05-20 | 2026-09-29 |       57 |           54 |            0 |      315,352 | wunderground              | False            |
| Jakarta       | WIHH               | C      | 2026-04-03 | 2026-05-21 |       49 |           49 |            1 |    3,328,523 | wunderground              | False            |
| Lagos         | DNMM               | C      | 2026-04-09 | 2026-05-15 |       37 |           37 |            0 |    2,711,402 | wunderground              | False            |
| Phoenix       | KPHX               | F      | 2025-12-04 | 2025-12-05 |        2 |            2 |            0 |       30,076 | wunderground              | False            |
| DC            | KDCA               | F      | 2025-01-20 | 2025-01-20 |        1 |            1 |            0 |      116,706 | wunderground              | False            |
| Dubai         | OMDB               | F      | 2025-05-31 | 2025-05-31 |        1 |            1 |            0 |        5,949 | wunderground              | False            |

## Rule eras per city (station, unit, resolution source, fallback)

| city          | station   | unit   | resolution_source   | resolution_fallback   | first      | last       |   n_days |
|:--------------|:----------|:-------|:--------------------|:----------------------|:-----------|:-----------|---------:|
| Amsterdam     | EHAM      | C      | wunderground        | nan                   | 2026-04-03 | 2026-08-23 |      143 |
| Amsterdam     | EHAM      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Amsterdam     | EHAM      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Ankara        | LTAC      | C      | wunderground        | nan                   | 2026-01-22 | 2026-08-23 |      213 |
| Ankara        | LTAC      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Ankara        | LTAC      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Atlanta       | KATL      | F      | wunderground        | nan                   | 2025-12-05 | 2026-08-22 |      258 |
| Atlanta       | KATL      | F      | noaa_wrh            | nan                   | 2026-08-23 | 2026-08-25 |        3 |
| Atlanta       | KATL      | F      | noaa_wrh            | wunderground          | 2026-08-26 | 2026-10-01 |       37 |
| Austin        | KAUS      | F      | wunderground        | nan                   | 2026-03-24 | 2026-08-22 |      149 |
| Austin        | KAUS      | F      | noaa_wrh            | nan                   | 2026-08-23 | 2026-08-25 |        3 |
| Austin        | KAUS      | F      | noaa_wrh            | wunderground          | 2026-08-26 | 2026-10-01 |       37 |
| Beijing       | ZBAA      | C      | wunderground        | nan                   | 2026-03-20 | 2026-08-23 |      156 |
| Beijing       | ZBAA      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Beijing       | ZBAA      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Buenos Aires  | SAEZ      | C      | wunderground        | nan                   | 2025-12-06 | 2026-08-22 |      256 |
| Buenos Aires  | SAEZ      | C      | noaa_wrh            | nan                   | 2026-08-23 | 2026-08-25 |        3 |
| Buenos Aires  | SAEZ      | C      | noaa_wrh            | wunderground          | 2026-08-26 | 2026-10-01 |       37 |
| Busan         | RKPK      | C      | wunderground        | nan                   | 2026-04-03 | 2026-08-23 |      143 |
| Busan         | RKPK      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Busan         | RKPK      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Cape Town     | FACT      | C      | wunderground        | nan                   | 2026-04-09 | 2026-08-23 |      135 |
| Cape Town     | FACT      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Cape Town     | FACT      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Chengdu       | ZUUU      | C      | wunderground        | nan                   | 2026-03-20 | 2026-08-23 |      155 |
| Chengdu       | ZUUU      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Chengdu       | ZUUU      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Chicago       | KORD      | F      | wunderground        | nan                   | 2025-12-04 | 2026-08-22 |      213 |
| Chicago       | KORD      | F      | noaa_wrh            | nan                   | 2026-08-23 | 2026-08-25 |        3 |
| Chicago       | KORD      | F      | noaa_wrh            | wunderground          | 2026-08-26 | 2026-10-01 |       37 |
| Chongqing     | ZUCK      | C      | wunderground        | nan                   | 2026-03-20 | 2026-08-23 |      156 |
| Chongqing     | ZUCK      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Chongqing     | ZUCK      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| DC            | KDCA      | F      | wunderground        | nan                   | 2025-01-20 | 2025-01-20 |        1 |
| Dallas        | KDAL      | F      | wunderground        | nan                   | 2025-12-04 | 2026-08-22 |      260 |
| Dallas        | KDAL      | F      | noaa_wrh            | nan                   | 2026-08-23 | 2026-08-25 |        3 |
| Dallas        | KDAL      | F      | noaa_wrh            | wunderground          | 2026-08-26 | 2026-10-01 |       37 |
| Denver        | KBKF      | F      | wunderground        | nan                   | 2025-12-04 | 2026-08-22 |      152 |
| Denver        | KBKF      | F      | noaa_wrh            | nan                   | 2026-08-23 | 2026-08-25 |        3 |
| Denver        | KBKF      | F      | noaa_wrh            | wunderground          | 2026-08-26 | 2026-10-01 |       37 |
| Dubai         | OMDB      | F      | wunderground        | nan                   | 2025-05-31 | 2025-05-31 |        1 |
| Guangzhou     | ZGGG      | C      | wunderground        | nan                   | 2026-04-15 | 2026-08-23 |      131 |
| Guangzhou     | ZGGG      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Guangzhou     | ZGGG      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Helsinki      | EFHK      | C      | wunderground        | nan                   | 2026-04-03 | 2026-08-23 |      143 |
| Helsinki      | EFHK      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Helsinki      | EFHK      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Hong Kong     | VHHH      | C      | wunderground        | nan                   | 2026-03-13 | 2026-03-14 |        2 |
| Hong Kong     | HKO       | C      | hko                 | nan                   | 2026-03-16 | 2026-10-01 |      198 |
| Houston       | KHOU      | F      | wunderground        | nan                   | 2026-03-24 | 2026-08-22 |      150 |
| Houston       | KHOU      | F      | noaa_wrh            | nan                   | 2026-08-23 | 2026-08-25 |        3 |
| Houston       | KHOU      | F      | noaa_wrh            | wunderground          | 2026-08-26 | 2026-10-01 |       37 |
| Istanbul      | LTFM      | C      | noaa_wrh            | nan                   | 2026-03-30 | 2026-08-26 |      150 |
| Istanbul      | LTFM      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Jakarta       | WIHH      | C      | wunderground        | nan                   | 2026-04-03 | 2026-05-21 |       49 |
| Jeddah        | OEJN      | C      | wunderground        | nan                   | 2026-04-09 | 2026-08-23 |      137 |
| Jeddah        | OEJN      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Jeddah        | OEJN      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Jinan         | ZSJN      | C      | wunderground        | nan                   | 2026-05-20 | 2026-09-29 |       57 |
| Karachi       | OPKC      | C      | wunderground        | nan                   | 2026-04-15 | 2026-08-23 |      131 |
| Karachi       | OPKC      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Karachi       | OPKC      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Kuala Lumpur  | WMKK      | C      | wunderground        | nan                   | 2026-04-03 | 2026-08-23 |      143 |
| Kuala Lumpur  | WMKK      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Kuala Lumpur  | WMKK      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Lagos         | DNMM      | C      | wunderground        | nan                   | 2026-04-09 | 2026-05-15 |       37 |
| London        | EGLC      | F      | wunderground        | nan                   | 2025-01-22 | 2025-12-10 |      321 |
| London        | EGLC      | C      | wunderground        | nan                   | 2025-12-11 | 2026-08-23 |      255 |
| London        | EGLC      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| London        | EGLC      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Los Angeles   | KLAX      | F      | wunderground        | nan                   | 2025-12-04 | 2026-08-22 |      152 |
| Los Angeles   | KLAX      | F      | noaa_wrh            | nan                   | 2026-08-23 | 2026-08-25 |        3 |
| Los Angeles   | KLAX      | F      | noaa_wrh            | wunderground          | 2026-08-26 | 2026-10-01 |       37 |
| Lucknow       | VILK      | C      | wunderground        | nan                   | 2026-03-05 | 2026-08-23 |      171 |
| Lucknow       | VILK      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Lucknow       | VILK      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Madrid        | LEMD      | C      | wunderground        | nan                   | 2026-03-16 | 2026-08-23 |      160 |
| Madrid        | LEMD      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Madrid        | LEMD      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Manila        | RPLL      | C      | wunderground        | nan                   | 2026-04-15 | 2026-08-23 |      131 |
| Manila        | RPLL      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Manila        | RPLL      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Mexico City   | MMMX      | C      | wunderground        | nan                   | 2026-03-30 | 2026-08-22 |      144 |
| Mexico City   | MMMX      | C      | noaa_wrh            | nan                   | 2026-08-23 | 2026-08-25 |        3 |
| Mexico City   | MMMX      | C      | noaa_wrh            | wunderground          | 2026-08-26 | 2026-10-01 |       37 |
| Miami         | KMIA      | F      | wunderground        | nan                   | 2025-12-04 | 2026-08-22 |      213 |
| Miami         | KMIA      | F      | noaa_wrh            | nan                   | 2026-08-23 | 2026-08-25 |        3 |
| Miami         | KMIA      | F      | noaa_wrh            | wunderground          | 2026-08-26 | 2026-10-01 |       37 |
| Milan         | LIMC      | C      | wunderground        | nan                   | 2026-03-16 | 2026-08-23 |      160 |
| Milan         | LIMC      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Milan         | LIMC      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Moscow        | UUWW      | C      | noaa_wrh            | nan                   | 2026-03-30 | 2026-08-26 |      149 |
| Moscow        | UUWW      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Munich        | EDDM      | C      | wunderground        | nan                   | 2026-03-05 | 2026-08-23 |      171 |
| Munich        | EDDM      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Munich        | EDDM      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| NYC           | KLGA      | F      | wunderground        | nan                   | 2025-01-22 | 2026-08-22 |      573 |
| NYC           | KLGA      | F      | noaa_wrh            | nan                   | 2026-08-23 | 2026-08-25 |        3 |
| NYC           | KLGA      | F      | noaa_wrh            | wunderground          | 2026-08-26 | 2026-10-01 |       37 |
| Panama City   | MPMG      | C      | wunderground        | nan                   | 2026-04-03 | 2026-08-22 |      140 |
| Panama City   | MPMG      | C      | noaa_wrh            | nan                   | 2026-08-23 | 2026-08-25 |        3 |
| Panama City   | MPMG      | C      | noaa_wrh            | wunderground          | 2026-08-26 | 2026-10-01 |       37 |
| Paris         | LFPG      | C      | wunderground        | nan                   | 2026-02-11 | 2026-04-18 |       63 |
| Paris         | LFPB      | C      | wunderground        | nan                   | 2026-04-19 | 2026-08-23 |      127 |
| Paris         | LFPB      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Paris         | LFPB      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Phoenix       | KPHX      | F      | wunderground        | nan                   | 2025-12-04 | 2025-12-05 |        2 |
| Qingdao       | ZSQD      | C      | wunderground        | nan                   | 2026-04-27 | 2026-08-23 |      119 |
| Qingdao       | ZSQD      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Qingdao       | ZSQD      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| San Francisco | KSFO      | F      | wunderground        | nan                   | 2026-03-24 | 2026-08-22 |      150 |
| San Francisco | KSFO      | F      | noaa_wrh            | nan                   | 2026-08-23 | 2026-08-25 |        3 |
| San Francisco | KSFO      | F      | noaa_wrh            | wunderground          | 2026-08-26 | 2026-10-01 |       37 |
| Sao Paulo     | SBGR      | C      | wunderground        | nan                   | 2026-02-11 | 2026-08-22 |      187 |
| Sao Paulo     | SBGR      | C      | noaa_wrh            | nan                   | 2026-08-23 | 2026-08-25 |        3 |
| Sao Paulo     | SBGR      | C      | noaa_wrh            | wunderground          | 2026-08-26 | 2026-10-01 |       37 |
| Seattle       | KSEA      | F      | wunderground        | nan                   | 2025-12-05 | 2026-08-22 |      258 |
| Seattle       | KSEA      | F      | noaa_wrh            | nan                   | 2026-08-23 | 2026-08-25 |        3 |
| Seattle       | KSEA      | F      | noaa_wrh            | wunderground          | 2026-08-26 | 2026-10-01 |       37 |
| Seoul         | RKSI      | C      | wunderground        | nan                   | 2025-12-06 | 2026-08-23 |      260 |
| Seoul         | RKSI      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Seoul         | RKSI      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Shanghai      | ZSPD      | C      | wunderground        | nan                   | 2026-03-13 | 2026-08-23 |      163 |
| Shanghai      | ZSPD      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Shanghai      | ZSPD      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Shenzhen      | ZGSZ      | C      | wunderground        | nan                   | 2026-03-20 | 2026-08-23 |      155 |
| Shenzhen      | ZGSZ      | C      | noaa_wrh            | nan                   | 2026-03-29 | 2026-08-26 |        4 |
| Shenzhen      | ZGSZ      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Singapore     | WSSS      | C      | wunderground        | nan                   | 2026-03-13 | 2026-08-23 |      163 |
| Singapore     | WSSS      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Singapore     | WSSS      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Taipei        | CWA46692  | C      | cwa                 | nan                   | 2026-03-16 | 2026-03-22 |        7 |
| Taipei        | RCTP      | C      | noaa_wrh            | nan                   | 2026-03-23 | 2026-04-04 |       12 |
| Taipei        | RCSS      | C      | wunderground        | nan                   | 2026-04-05 | 2026-10-01 |      179 |
| Taipei        | RCSS      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-24 |        1 |
| Tel Aviv      | LLBG      | C      | wunderground        | nan                   | 2026-03-10 | 2026-03-22 |       13 |
| Tel Aviv      | LLBG      | C      | noaa_wrh            | nan                   | 2026-03-23 | 2026-08-26 |      156 |
| Tel Aviv      | LLBG      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Tokyo         | RJTT      | C      | wunderground        | nan                   | 2026-03-10 | 2026-08-23 |      166 |
| Tokyo         | RJTT      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Tokyo         | RJTT      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Toronto       | CYYZ      | C      | wunderground        | nan                   | 2025-12-06 | 2026-08-22 |      259 |
| Toronto       | CYYZ      | C      | noaa_wrh            | nan                   | 2026-08-23 | 2026-08-25 |        3 |
| Toronto       | CYYZ      | C      | noaa_wrh            | wunderground          | 2026-08-26 | 2026-10-01 |       37 |
| Warsaw        | EPWA      | C      | wunderground        | nan                   | 2026-03-16 | 2026-08-23 |      160 |
| Warsaw        | EPWA      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Warsaw        | EPWA      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Wellington    | NZWN      | C      | wunderground        | nan                   | 2026-01-22 | 2026-08-23 |      213 |
| Wellington    | NZWN      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Wellington    | NZWN      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Wuhan         | ZHHH      | C      | wunderground        | nan                   | 2026-03-20 | 2026-08-23 |      156 |
| Wuhan         | ZHHH      | C      | noaa_wrh            | nan                   | 2026-08-24 | 2026-08-26 |        3 |
| Wuhan         | ZHHH      | C      | noaa_wrh            | wunderground          | 2026-08-27 | 2026-10-01 |       36 |
| Zhengzhou     | ZHCC      | C      | wunderground        | nan                   | 2026-05-20 | 2026-08-22 |       19 |
| Zhengzhou     | ZHCC      | C      | noaa_wrh            | nan                   | 2026-08-23 | 2026-08-25 |        3 |
| Zhengzhou     | ZHCC      | C      | noaa_wrh            | wunderground          | 2026-08-26 | 2026-09-30 |       36 |

## Per city per month, grouped by resolution source

| city          | station   | unit   | month   | resolution_source   |   n_days |   n_resolved |   volume_usd |
|:--------------|:----------|:-------|:--------|:--------------------|---------:|-------------:|-------------:|
| Amsterdam     | EHAM      | C      | 2026-04 | wunderground        |       28 |           28 |    1,913,161 |
| Amsterdam     | EHAM      | C      | 2026-05 | wunderground        |       31 |           32 |    1,757,315 |
| Amsterdam     | EHAM      | C      | 2026-06 | wunderground        |       30 |           30 |    2,165,735 |
| Amsterdam     | EHAM      | C      | 2026-07 | wunderground        |       31 |           31 |    2,196,266 |
| Amsterdam     | EHAM      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      398,057 |
| Amsterdam     | EHAM      | C      | 2026-08 | wunderground        |       23 |           23 |    1,599,676 |
| Amsterdam     | EHAM      | C      | 2026-09 | noaa_wrh            |       30 |           28 |    1,301,957 |
| Amsterdam     | EHAM      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        1,338 |
| Ankara        | LTAC      | C      | 2026-01 | wunderground        |       10 |           10 |      602,203 |
| Ankara        | LTAC      | C      | 2026-02 | wunderground        |       28 |           28 |    3,546,258 |
| Ankara        | LTAC      | C      | 2026-03 | wunderground        |       30 |           30 |    1,979,151 |
| Ankara        | LTAC      | C      | 2026-04 | wunderground        |       30 |           30 |    3,473,504 |
| Ankara        | LTAC      | C      | 2026-05 | wunderground        |       31 |           32 |    2,320,854 |
| Ankara        | LTAC      | C      | 2026-06 | wunderground        |       30 |           30 |    2,014,903 |
| Ankara        | LTAC      | C      | 2026-07 | wunderground        |       31 |           31 |    1,980,874 |
| Ankara        | LTAC      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      326,615 |
| Ankara        | LTAC      | C      | 2026-08 | wunderground        |       23 |           23 |      908,347 |
| Ankara        | LTAC      | C      | 2026-09 | noaa_wrh            |       30 |           29 |    1,102,751 |
| Ankara        | LTAC      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        1,708 |
| Atlanta       | KATL      | F      | 2025-12 | wunderground        |       27 |           27 |    1,164,413 |
| Atlanta       | KATL      | F      | 2026-01 | wunderground        |       31 |           31 |    1,794,621 |
| Atlanta       | KATL      | F      | 2026-02 | wunderground        |       28 |           28 |    3,547,925 |
| Atlanta       | KATL      | F      | 2026-03 | wunderground        |       30 |           30 |    1,654,455 |
| Atlanta       | KATL      | F      | 2026-04 | wunderground        |       30 |           30 |    3,885,281 |
| Atlanta       | KATL      | F      | 2026-05 | wunderground        |       30 |           31 |    2,370,040 |
| Atlanta       | KATL      | F      | 2026-06 | wunderground        |       29 |           29 |    1,928,850 |
| Atlanta       | KATL      | F      | 2026-07 | wunderground        |       31 |           31 |    1,619,092 |
| Atlanta       | KATL      | F      | 2026-08 | noaa_wrh            |        9 |            9 |      350,874 |
| Atlanta       | KATL      | F      | 2026-08 | wunderground        |       22 |           22 |      993,640 |
| Atlanta       | KATL      | F      | 2026-09 | noaa_wrh            |       30 |           28 |    1,259,830 |
| Atlanta       | KATL      | F      | 2026-10 | noaa_wrh            |        1 |            0 |        9,391 |
| Austin        | KAUS      | F      | 2026-03 | wunderground        |        7 |            7 |      474,343 |
| Austin        | KAUS      | F      | 2026-04 | wunderground        |       30 |           30 |    2,479,910 |
| Austin        | KAUS      | F      | 2026-05 | wunderground        |       31 |           32 |    1,852,568 |
| Austin        | KAUS      | F      | 2026-06 | wunderground        |       29 |           29 |    1,260,308 |
| Austin        | KAUS      | F      | 2026-07 | wunderground        |       30 |           30 |    1,369,435 |
| Austin        | KAUS      | F      | 2026-08 | noaa_wrh            |        9 |            9 |      243,791 |
| Austin        | KAUS      | F      | 2026-08 | wunderground        |       22 |           22 |      675,975 |
| Austin        | KAUS      | F      | 2026-09 | noaa_wrh            |       30 |           28 |    1,021,932 |
| Austin        | KAUS      | F      | 2026-10 | noaa_wrh            |        1 |            0 |        1,748 |
| Beijing       | ZBAA      | C      | 2026-03 | wunderground        |       11 |           11 |      630,009 |
| Beijing       | ZBAA      | C      | 2026-04 | wunderground        |       30 |           30 |    4,783,705 |
| Beijing       | ZBAA      | C      | 2026-05 | wunderground        |       31 |           32 |    3,363,991 |
| Beijing       | ZBAA      | C      | 2026-06 | wunderground        |       30 |           30 |    3,918,315 |
| Beijing       | ZBAA      | C      | 2026-07 | wunderground        |       31 |           31 |    3,202,485 |
| Beijing       | ZBAA      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      537,065 |
| Beijing       | ZBAA      | C      | 2026-08 | wunderground        |       23 |           23 |    1,694,014 |
| Beijing       | ZBAA      | C      | 2026-09 | noaa_wrh            |       30 |           29 |    1,992,238 |
| Beijing       | ZBAA      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        4,103 |
| Buenos Aires  | SAEZ      | C      | 2025-12 | wunderground        |       26 |           26 |      892,825 |
| Buenos Aires  | SAEZ      | C      | 2026-01 | wunderground        |       31 |           31 |    1,494,959 |
| Buenos Aires  | SAEZ      | C      | 2026-02 | wunderground        |       28 |           28 |    2,766,881 |
| Buenos Aires  | SAEZ      | C      | 2026-03 | wunderground        |       30 |           30 |    1,436,882 |
| Buenos Aires  | SAEZ      | C      | 2026-04 | wunderground        |       30 |           30 |    3,362,991 |
| Buenos Aires  | SAEZ      | C      | 2026-05 | wunderground        |       31 |           32 |    1,883,694 |
| Buenos Aires  | SAEZ      | C      | 2026-06 | wunderground        |       28 |           28 |    1,195,872 |
| Buenos Aires  | SAEZ      | C      | 2026-07 | wunderground        |       30 |           30 |    1,517,509 |
| Buenos Aires  | SAEZ      | C      | 2026-08 | noaa_wrh            |        9 |            9 |      296,516 |
| Buenos Aires  | SAEZ      | C      | 2026-08 | wunderground        |       22 |           22 |      877,329 |
| Buenos Aires  | SAEZ      | C      | 2026-09 | noaa_wrh            |       30 |           28 |    1,097,465 |
| Buenos Aires  | SAEZ      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        1,113 |
| Busan         | RKPK      | C      | 2026-04 | wunderground        |       28 |           28 |    1,855,547 |
| Busan         | RKPK      | C      | 2026-05 | wunderground        |       31 |           32 |    1,567,565 |
| Busan         | RKPK      | C      | 2026-06 | wunderground        |       30 |           30 |    1,776,519 |
| Busan         | RKPK      | C      | 2026-07 | wunderground        |       31 |           31 |    1,766,673 |
| Busan         | RKPK      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      282,280 |
| Busan         | RKPK      | C      | 2026-08 | wunderground        |       23 |           23 |    1,248,368 |
| Busan         | RKPK      | C      | 2026-09 | noaa_wrh            |       30 |           29 |    1,129,531 |
| Busan         | RKPK      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        2,336 |
| Cape Town     | FACT      | C      | 2026-04 | wunderground        |       22 |           22 |      946,268 |
| Cape Town     | FACT      | C      | 2026-05 | wunderground        |       29 |           29 |      982,462 |
| Cape Town     | FACT      | C      | 2026-06 | wunderground        |       30 |           30 |    1,358,601 |
| Cape Town     | FACT      | C      | 2026-07 | wunderground        |       31 |           31 |    1,591,207 |
| Cape Town     | FACT      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      267,369 |
| Cape Town     | FACT      | C      | 2026-08 | wunderground        |       23 |           23 |    1,019,168 |
| Cape Town     | FACT      | C      | 2026-09 | noaa_wrh            |       30 |           28 |    1,208,582 |
| Cape Town     | FACT      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        2,672 |
| Chengdu       | ZUUU      | C      | 2026-03 | wunderground        |       10 |           10 |      370,852 |
| Chengdu       | ZUUU      | C      | 2026-04 | wunderground        |       30 |           30 |    3,267,105 |
| Chengdu       | ZUUU      | C      | 2026-05 | wunderground        |       31 |           32 |    2,028,995 |
| Chengdu       | ZUUU      | C      | 2026-06 | wunderground        |       30 |           30 |    2,471,905 |
| Chengdu       | ZUUU      | C      | 2026-07 | wunderground        |       31 |           31 |    3,066,518 |
| Chengdu       | ZUUU      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      495,028 |
| Chengdu       | ZUUU      | C      | 2026-08 | wunderground        |       23 |           23 |    1,750,722 |
| Chengdu       | ZUUU      | C      | 2026-09 | noaa_wrh            |       30 |           29 |    1,461,102 |
| Chengdu       | ZUUU      | C      | 2026-10 | noaa_wrh            |        1 |            0 |          592 |
| Chicago       | KORD      | F      | 2025-12 | wunderground        |        2 |            2 |       17,985 |
| Chicago       | KORD      | F      | 2026-01 | wunderground        |       10 |           10 |      500,907 |
| Chicago       | KORD      | F      | 2026-02 | wunderground        |       28 |           28 |    2,915,107 |
| Chicago       | KORD      | F      | 2026-03 | wunderground        |       30 |           30 |    2,156,064 |
| Chicago       | KORD      | F      | 2026-04 | wunderground        |       30 |           30 |    4,405,693 |
| Chicago       | KORD      | F      | 2026-05 | wunderground        |       31 |           32 |    2,122,015 |
| Chicago       | KORD      | F      | 2026-06 | wunderground        |       29 |           29 |    1,754,936 |
| Chicago       | KORD      | F      | 2026-07 | wunderground        |       31 |           31 |    1,877,803 |
| Chicago       | KORD      | F      | 2026-08 | noaa_wrh            |        9 |            9 |      346,810 |
| Chicago       | KORD      | F      | 2026-08 | wunderground        |       22 |           22 |    1,057,550 |
| Chicago       | KORD      | F      | 2026-09 | noaa_wrh            |       30 |           28 |    1,404,479 |
| Chicago       | KORD      | F      | 2026-10 | noaa_wrh            |        1 |            0 |        1,697 |
| Chongqing     | ZUCK      | C      | 2026-03 | wunderground        |       11 |           11 |      401,065 |
| Chongqing     | ZUCK      | C      | 2026-04 | wunderground        |       30 |           30 |    2,903,807 |
| Chongqing     | ZUCK      | C      | 2026-05 | wunderground        |       31 |           32 |    1,846,041 |
| Chongqing     | ZUCK      | C      | 2026-06 | wunderground        |       30 |           30 |    2,129,790 |
| Chongqing     | ZUCK      | C      | 2026-07 | wunderground        |       31 |           31 |    2,353,617 |
| Chongqing     | ZUCK      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      310,340 |
| Chongqing     | ZUCK      | C      | 2026-08 | wunderground        |       23 |           23 |    1,441,371 |
| Chongqing     | ZUCK      | C      | 2026-09 | noaa_wrh            |       30 |           29 |    1,095,648 |
| Chongqing     | ZUCK      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        2,560 |
| DC            | KDCA      | F      | 2025-01 | wunderground        |        1 |            1 |      116,706 |
| Dallas        | KDAL      | F      | 2025-12 | wunderground        |       28 |           28 |    1,015,743 |
| Dallas        | KDAL      | F      | 2026-01 | wunderground        |       31 |           31 |    2,152,411 |
| Dallas        | KDAL      | F      | 2026-02 | wunderground        |       28 |           28 |    3,329,683 |
| Dallas        | KDAL      | F      | 2026-03 | wunderground        |       30 |           30 |    1,848,811 |
| Dallas        | KDAL      | F      | 2026-04 | wunderground        |       30 |           30 |    3,518,992 |
| Dallas        | KDAL      | F      | 2026-05 | wunderground        |       31 |           32 |    1,427,910 |
| Dallas        | KDAL      | F      | 2026-06 | wunderground        |       29 |           29 |    1,864,004 |
| Dallas        | KDAL      | F      | 2026-07 | wunderground        |       31 |           31 |    2,137,405 |
| Dallas        | KDAL      | F      | 2026-08 | noaa_wrh            |        9 |            9 |      484,330 |
| Dallas        | KDAL      | F      | 2026-08 | wunderground        |       22 |           22 |    1,172,777 |
| Dallas        | KDAL      | F      | 2026-09 | noaa_wrh            |       30 |           28 |    1,408,207 |
| Dallas        | KDAL      | F      | 2026-10 | noaa_wrh            |        1 |            0 |        1,351 |
| Denver        | KBKF      | F      | 2025-12 | wunderground        |        2 |            2 |       11,493 |
| Denver        | KBKF      | F      | 2026-03 | wunderground        |        7 |            7 |      644,236 |
| Denver        | KBKF      | F      | 2026-04 | wunderground        |       30 |           30 |    2,582,936 |
| Denver        | KBKF      | F      | 2026-05 | wunderground        |       31 |           32 |    1,859,259 |
| Denver        | KBKF      | F      | 2026-06 | wunderground        |       29 |           29 |    1,280,255 |
| Denver        | KBKF      | F      | 2026-07 | wunderground        |       31 |           31 |    1,474,731 |
| Denver        | KBKF      | F      | 2026-08 | noaa_wrh            |        9 |            9 |      251,382 |
| Denver        | KBKF      | F      | 2026-08 | wunderground        |       22 |           22 |      774,981 |
| Denver        | KBKF      | F      | 2026-09 | noaa_wrh            |       30 |           28 |    1,059,235 |
| Denver        | KBKF      | F      | 2026-10 | noaa_wrh            |        1 |            0 |        2,715 |
| Dubai         | OMDB      | F      | 2025-05 | wunderground        |        1 |            1 |        5,949 |
| Guangzhou     | ZGGG      | C      | 2026-04 | wunderground        |       16 |           16 |      969,326 |
| Guangzhou     | ZGGG      | C      | 2026-05 | wunderground        |       31 |           32 |    1,488,689 |
| Guangzhou     | ZGGG      | C      | 2026-06 | wunderground        |       30 |           30 |    3,115,601 |
| Guangzhou     | ZGGG      | C      | 2026-07 | wunderground        |       31 |           31 |    3,045,831 |
| Guangzhou     | ZGGG      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      506,765 |
| Guangzhou     | ZGGG      | C      | 2026-08 | wunderground        |       23 |           23 |    1,477,476 |
| Guangzhou     | ZGGG      | C      | 2026-09 | noaa_wrh            |       30 |           29 |    1,595,508 |
| Guangzhou     | ZGGG      | C      | 2026-10 | noaa_wrh            |        1 |            0 |       10,988 |
| Helsinki      | EFHK      | C      | 2026-04 | wunderground        |       28 |           28 |    1,676,400 |
| Helsinki      | EFHK      | C      | 2026-05 | wunderground        |       31 |           32 |    1,563,998 |
| Helsinki      | EFHK      | C      | 2026-06 | wunderground        |       30 |           30 |    1,934,453 |
| Helsinki      | EFHK      | C      | 2026-07 | wunderground        |       31 |           31 |    1,890,218 |
| Helsinki      | EFHK      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      286,771 |
| Helsinki      | EFHK      | C      | 2026-08 | wunderground        |       23 |           23 |      961,217 |
| Helsinki      | EFHK      | C      | 2026-09 | noaa_wrh            |       30 |           29 |      964,861 |
| Helsinki      | EFHK      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        1,836 |
| Hong Kong     | HKO       | C      | 2026-03 | hko                 |       14 |           14 |    1,110,988 |
| Hong Kong     | VHHH      | C      | 2026-03 | wunderground        |        2 |            2 |            0 |
| Hong Kong     | HKO       | C      | 2026-04 | hko                 |       30 |           30 |   10,289,407 |
| Hong Kong     | HKO       | C      | 2026-05 | hko                 |       31 |           32 |    8,843,089 |
| Hong Kong     | HKO       | C      | 2026-06 | hko                 |       30 |           30 |    7,568,398 |
| Hong Kong     | HKO       | C      | 2026-07 | hko                 |       31 |           31 |    7,441,057 |
| Hong Kong     | HKO       | C      | 2026-08 | hko                 |       31 |           31 |    6,624,517 |
| Hong Kong     | HKO       | C      | 2026-09 | hko                 |       30 |           28 |    3,812,247 |
| Hong Kong     | HKO       | C      | 2026-10 | hko                 |        1 |            0 |        9,414 |
| Houston       | KHOU      | F      | 2026-03 | wunderground        |        7 |            7 |      361,769 |
| Houston       | KHOU      | F      | 2026-04 | wunderground        |       30 |           30 |    1,902,699 |
| Houston       | KHOU      | F      | 2026-05 | wunderground        |       31 |           32 |    1,513,556 |
| Houston       | KHOU      | F      | 2026-06 | wunderground        |       29 |           29 |    1,339,832 |
| Houston       | KHOU      | F      | 2026-07 | wunderground        |       31 |           31 |    1,412,062 |
| Houston       | KHOU      | F      | 2026-08 | noaa_wrh            |        9 |            9 |      318,264 |
| Houston       | KHOU      | F      | 2026-08 | wunderground        |       22 |           22 |      856,459 |
| Houston       | KHOU      | F      | 2026-09 | noaa_wrh            |       30 |           28 |    1,175,328 |
| Houston       | KHOU      | F      | 2026-10 | noaa_wrh            |        1 |            0 |          555 |
| Istanbul      | LTFM      | C      | 2026-03 | noaa_wrh            |        2 |            2 |      245,147 |
| Istanbul      | LTFM      | C      | 2026-04 | noaa_wrh            |       30 |           30 |    2,230,394 |
| Istanbul      | LTFM      | C      | 2026-05 | noaa_wrh            |       31 |           32 |    1,510,731 |
| Istanbul      | LTFM      | C      | 2026-06 | noaa_wrh            |       30 |           30 |    1,513,154 |
| Istanbul      | LTFM      | C      | 2026-07 | noaa_wrh            |       31 |           31 |    1,734,590 |
| Istanbul      | LTFM      | C      | 2026-08 | noaa_wrh            |       31 |           31 |    1,175,245 |
| Istanbul      | LTFM      | C      | 2026-09 | noaa_wrh            |       30 |           29 |      666,574 |
| Istanbul      | LTFM      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        2,108 |
| Jakarta       | WIHH      | C      | 2026-04 | wunderground        |       28 |           28 |    1,925,253 |
| Jakarta       | WIHH      | C      | 2026-05 | wunderground        |       21 |           21 |    1,403,269 |
| Jeddah        | OEJN      | C      | 2026-04 | wunderground        |       22 |           22 |      721,863 |
| Jeddah        | OEJN      | C      | 2026-05 | wunderground        |       31 |           32 |    1,071,533 |
| Jeddah        | OEJN      | C      | 2026-06 | wunderground        |       30 |           30 |    1,343,260 |
| Jeddah        | OEJN      | C      | 2026-07 | wunderground        |       31 |           31 |    1,474,552 |
| Jeddah        | OEJN      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      224,762 |
| Jeddah        | OEJN      | C      | 2026-08 | wunderground        |       23 |           23 |      730,734 |
| Jeddah        | OEJN      | C      | 2026-09 | noaa_wrh            |       30 |           28 |      749,276 |
| Jeddah        | OEJN      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        3,804 |
| Jinan         | ZSJN      | C      | 2026-05 | wunderground        |        3 |            0 |            0 |
| Jinan         | ZSJN      | C      | 2026-08 | wunderground        |       25 |           25 |      195,244 |
| Jinan         | ZSJN      | C      | 2026-09 | wunderground        |       29 |           29 |      120,108 |
| Karachi       | OPKC      | C      | 2026-04 | wunderground        |       16 |           16 |      541,126 |
| Karachi       | OPKC      | C      | 2026-05 | wunderground        |       31 |           32 |      724,301 |
| Karachi       | OPKC      | C      | 2026-06 | wunderground        |       30 |           30 |    1,124,820 |
| Karachi       | OPKC      | C      | 2026-07 | wunderground        |       31 |           31 |    1,269,659 |
| Karachi       | OPKC      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      181,911 |
| Karachi       | OPKC      | C      | 2026-08 | wunderground        |       23 |           23 |      701,009 |
| Karachi       | OPKC      | C      | 2026-09 | noaa_wrh            |       30 |           29 |      752,038 |
| Karachi       | OPKC      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        2,745 |
| Kuala Lumpur  | WMKK      | C      | 2026-04 | wunderground        |       28 |           28 |    1,669,441 |
| Kuala Lumpur  | WMKK      | C      | 2026-05 | wunderground        |       31 |           32 |    1,241,348 |
| Kuala Lumpur  | WMKK      | C      | 2026-06 | wunderground        |       30 |           30 |    1,926,683 |
| Kuala Lumpur  | WMKK      | C      | 2026-07 | wunderground        |       31 |           31 |    2,309,325 |
| Kuala Lumpur  | WMKK      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      379,675 |
| Kuala Lumpur  | WMKK      | C      | 2026-08 | wunderground        |       23 |           23 |    1,249,638 |
| Kuala Lumpur  | WMKK      | C      | 2026-09 | noaa_wrh            |       30 |           29 |    1,156,529 |
| Kuala Lumpur  | WMKK      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        2,200 |
| Lagos         | DNMM      | C      | 2026-04 | wunderground        |       22 |           22 |    1,420,093 |
| Lagos         | DNMM      | C      | 2026-05 | wunderground        |       15 |           15 |    1,291,309 |
| London        | EGLC      | F      | 2025-01 | wunderground        |        9 |            9 |      765,050 |
| London        | EGLC      | F      | 2025-02 | wunderground        |       27 |           27 |    3,705,724 |
| London        | EGLC      | F      | 2025-03 | wunderground        |       31 |           31 |    5,246,775 |
| London        | EGLC      | F      | 2025-04 | wunderground        |       30 |           30 |    2,299,221 |
| London        | EGLC      | F      | 2025-05 | wunderground        |       31 |           31 |    3,211,326 |
| London        | EGLC      | F      | 2025-06 | wunderground        |       30 |           30 |    2,411,909 |
| London        | EGLC      | F      | 2025-07 | wunderground        |       31 |           31 |    1,986,294 |
| London        | EGLC      | F      | 2025-08 | wunderground        |       31 |           31 |    2,361,750 |
| London        | EGLC      | F      | 2025-09 | wunderground        |       30 |           30 |    1,986,943 |
| London        | EGLC      | F      | 2025-10 | wunderground        |       31 |           31 |    2,831,719 |
| London        | EGLC      | F      | 2025-11 | wunderground        |       30 |           30 |    9,035,720 |
| London        | EGLC      | C      | 2025-12 | wunderground        |       21 |           21 |    2,655,048 |
| London        | EGLC      | F      | 2025-12 | wunderground        |       10 |           10 |    3,567,243 |
| London        | EGLC      | C      | 2026-01 | wunderground        |       31 |           31 |    6,372,170 |
| London        | EGLC      | C      | 2026-02 | wunderground        |       28 |           28 |    8,269,779 |
| London        | EGLC      | C      | 2026-03 | wunderground        |       30 |           30 |    2,966,817 |
| London        | EGLC      | C      | 2026-04 | wunderground        |       30 |           30 |   10,301,682 |
| London        | EGLC      | C      | 2026-05 | wunderground        |       31 |           32 |    8,246,698 |
| London        | EGLC      | C      | 2026-06 | wunderground        |       30 |           30 |    6,888,539 |
| London        | EGLC      | C      | 2026-07 | wunderground        |       31 |           31 |    5,442,229 |
| London        | EGLC      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      847,722 |
| London        | EGLC      | C      | 2026-08 | wunderground        |       23 |           23 |    3,393,621 |
| London        | EGLC      | C      | 2026-09 | noaa_wrh            |       30 |           28 |    2,557,079 |
| London        | EGLC      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        4,720 |
| Los Angeles   | KLAX      | F      | 2025-12 | wunderground        |        2 |            2 |       17,304 |
| Los Angeles   | KLAX      | F      | 2026-03 | wunderground        |        7 |            7 |      551,847 |
| Los Angeles   | KLAX      | F      | 2026-04 | wunderground        |       30 |           30 |    2,976,155 |
| Los Angeles   | KLAX      | F      | 2026-05 | wunderground        |       31 |           32 |    1,987,903 |
| Los Angeles   | KLAX      | F      | 2026-06 | wunderground        |       29 |           29 |    2,139,958 |
| Los Angeles   | KLAX      | F      | 2026-07 | wunderground        |       31 |           31 |    2,666,106 |
| Los Angeles   | KLAX      | F      | 2026-08 | noaa_wrh            |        9 |            9 |      447,123 |
| Los Angeles   | KLAX      | F      | 2026-08 | wunderground        |       22 |           22 |    1,484,663 |
| Los Angeles   | KLAX      | F      | 2026-09 | noaa_wrh            |       30 |           28 |    1,553,572 |
| Los Angeles   | KLAX      | F      | 2026-10 | noaa_wrh            |        1 |            0 |        2,104 |
| Lucknow       | VILK      | C      | 2026-03 | wunderground        |       26 |           26 |      608,978 |
| Lucknow       | VILK      | C      | 2026-04 | wunderground        |       30 |           30 |    2,527,477 |
| Lucknow       | VILK      | C      | 2026-05 | wunderground        |       31 |           32 |    1,141,644 |
| Lucknow       | VILK      | C      | 2026-06 | wunderground        |       30 |           30 |    1,798,574 |
| Lucknow       | VILK      | C      | 2026-07 | wunderground        |       31 |           31 |    1,532,541 |
| Lucknow       | VILK      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      176,020 |
| Lucknow       | VILK      | C      | 2026-08 | wunderground        |       23 |           23 |      729,935 |
| Lucknow       | VILK      | C      | 2026-09 | noaa_wrh            |       30 |           29 |      896,386 |
| Lucknow       | VILK      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        3,378 |
| Madrid        | LEMD      | C      | 2026-03 | wunderground        |       15 |           15 |    1,004,439 |
| Madrid        | LEMD      | C      | 2026-04 | wunderground        |       30 |           30 |    3,843,430 |
| Madrid        | LEMD      | C      | 2026-05 | wunderground        |       31 |           32 |    3,468,342 |
| Madrid        | LEMD      | C      | 2026-06 | wunderground        |       30 |           30 |    3,059,032 |
| Madrid        | LEMD      | C      | 2026-07 | wunderground        |       31 |           31 |    2,973,790 |
| Madrid        | LEMD      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      605,078 |
| Madrid        | LEMD      | C      | 2026-08 | wunderground        |       23 |           23 |    1,959,706 |
| Madrid        | LEMD      | C      | 2026-09 | noaa_wrh            |       30 |           28 |    1,578,561 |
| Madrid        | LEMD      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        3,550 |
| Manila        | RPLL      | C      | 2026-04 | wunderground        |       16 |           16 |      610,253 |
| Manila        | RPLL      | C      | 2026-05 | wunderground        |       31 |           32 |      983,589 |
| Manila        | RPLL      | C      | 2026-06 | wunderground        |       30 |           30 |    1,185,365 |
| Manila        | RPLL      | C      | 2026-07 | wunderground        |       31 |           31 |    1,481,765 |
| Manila        | RPLL      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      223,336 |
| Manila        | RPLL      | C      | 2026-08 | wunderground        |       23 |           23 |      799,530 |
| Manila        | RPLL      | C      | 2026-09 | noaa_wrh            |       30 |           29 |    1,031,228 |
| Manila        | RPLL      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        3,285 |
| Mexico City   | MMMX      | C      | 2026-03 | wunderground        |        1 |            1 |       27,618 |
| Mexico City   | MMMX      | C      | 2026-04 | wunderground        |       30 |           30 |    2,104,827 |
| Mexico City   | MMMX      | C      | 2026-05 | wunderground        |       31 |           32 |    1,236,927 |
| Mexico City   | MMMX      | C      | 2026-06 | wunderground        |       29 |           29 |    1,204,402 |
| Mexico City   | MMMX      | C      | 2026-07 | wunderground        |       31 |           31 |    1,221,017 |
| Mexico City   | MMMX      | C      | 2026-08 | noaa_wrh            |        9 |            9 |      173,033 |
| Mexico City   | MMMX      | C      | 2026-08 | wunderground        |       22 |           22 |      567,412 |
| Mexico City   | MMMX      | C      | 2026-09 | noaa_wrh            |       30 |           28 |      706,238 |
| Mexico City   | MMMX      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        2,146 |
| Miami         | KMIA      | F      | 2025-12 | wunderground        |        2 |            2 |       24,619 |
| Miami         | KMIA      | F      | 2026-01 | wunderground        |       10 |           10 |      705,245 |
| Miami         | KMIA      | F      | 2026-02 | wunderground        |       28 |           28 |    3,049,518 |
| Miami         | KMIA      | F      | 2026-03 | wunderground        |       30 |           30 |    1,823,296 |
| Miami         | KMIA      | F      | 2026-04 | wunderground        |       30 |           30 |    4,136,012 |
| Miami         | KMIA      | F      | 2026-05 | wunderground        |       31 |           32 |    2,788,286 |
| Miami         | KMIA      | F      | 2026-06 | wunderground        |       29 |           29 |    2,070,853 |
| Miami         | KMIA      | F      | 2026-07 | wunderground        |       31 |           31 |    1,759,415 |
| Miami         | KMIA      | F      | 2026-08 | noaa_wrh            |        9 |            9 |      760,466 |
| Miami         | KMIA      | F      | 2026-08 | wunderground        |       22 |           22 |    1,167,316 |
| Miami         | KMIA      | F      | 2026-09 | noaa_wrh            |       30 |           28 |    2,262,443 |
| Miami         | KMIA      | F      | 2026-10 | noaa_wrh            |        1 |            0 |        4,190 |
| Milan         | LIMC      | C      | 2026-03 | wunderground        |       15 |           15 |      549,411 |
| Milan         | LIMC      | C      | 2026-04 | wunderground        |       30 |           30 |    2,876,692 |
| Milan         | LIMC      | C      | 2026-05 | wunderground        |       31 |           32 |    1,938,587 |
| Milan         | LIMC      | C      | 2026-06 | wunderground        |       30 |           30 |    1,658,479 |
| Milan         | LIMC      | C      | 2026-07 | wunderground        |       31 |           31 |    2,258,428 |
| Milan         | LIMC      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      461,937 |
| Milan         | LIMC      | C      | 2026-08 | wunderground        |       23 |           23 |    1,685,998 |
| Milan         | LIMC      | C      | 2026-09 | noaa_wrh            |       30 |           28 |    1,409,613 |
| Milan         | LIMC      | C      | 2026-10 | noaa_wrh            |        1 |            0 |          608 |
| Moscow        | UUWW      | C      | 2026-03 | noaa_wrh            |        1 |            1 |       63,942 |
| Moscow        | UUWW      | C      | 2026-04 | noaa_wrh            |       30 |           30 |    2,689,961 |
| Moscow        | UUWW      | C      | 2026-05 | noaa_wrh            |       31 |           32 |    2,095,937 |
| Moscow        | UUWW      | C      | 2026-06 | noaa_wrh            |       30 |           30 |    1,621,656 |
| Moscow        | UUWW      | C      | 2026-07 | noaa_wrh            |       31 |           31 |    1,714,793 |
| Moscow        | UUWW      | C      | 2026-08 | noaa_wrh            |       31 |           31 |    1,090,964 |
| Moscow        | UUWW      | C      | 2026-09 | noaa_wrh            |       30 |           28 |    1,032,009 |
| Moscow        | UUWW      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        2,060 |
| Munich        | EDDM      | C      | 2026-03 | wunderground        |       26 |           26 |      683,643 |
| Munich        | EDDM      | C      | 2026-04 | wunderground        |       30 |           30 |    3,466,589 |
| Munich        | EDDM      | C      | 2026-05 | wunderground        |       31 |           32 |    2,218,622 |
| Munich        | EDDM      | C      | 2026-06 | wunderground        |       30 |           30 |    2,834,489 |
| Munich        | EDDM      | C      | 2026-07 | wunderground        |       31 |           31 |    3,439,087 |
| Munich        | EDDM      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      622,483 |
| Munich        | EDDM      | C      | 2026-08 | wunderground        |       23 |           23 |    2,716,926 |
| Munich        | EDDM      | C      | 2026-09 | noaa_wrh            |       30 |           28 |    1,629,454 |
| Munich        | EDDM      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        9,045 |
| NYC           | KLGA      | F      | 2025-01 | wunderground        |        9 |            9 |      511,661 |
| NYC           | KLGA      | F      | 2025-02 | wunderground        |       27 |           27 |    5,794,549 |
| NYC           | KLGA      | F      | 2025-03 | wunderground        |       31 |           31 |    2,841,637 |
| NYC           | KLGA      | F      | 2025-04 | wunderground        |       28 |           28 |    1,380,443 |
| NYC           | KLGA      | F      | 2025-05 | wunderground        |       31 |           31 |    2,484,946 |
| NYC           | KLGA      | F      | 2025-06 | wunderground        |       30 |           30 |    1,307,522 |
| NYC           | KLGA      | F      | 2025-07 | wunderground        |       31 |           31 |    1,392,632 |
| NYC           | KLGA      | F      | 2025-08 | wunderground        |       31 |           31 |    1,565,998 |
| NYC           | KLGA      | F      | 2025-09 | wunderground        |       30 |           30 |    1,682,169 |
| NYC           | KLGA      | F      | 2025-10 | wunderground        |       31 |           31 |    2,420,138 |
| NYC           | KLGA      | F      | 2025-11 | wunderground        |       30 |           30 |    9,274,050 |
| NYC           | KLGA      | F      | 2025-12 | wunderground        |       31 |           31 |    6,529,675 |
| NYC           | KLGA      | F      | 2026-01 | wunderground        |       31 |           31 |    5,594,900 |
| NYC           | KLGA      | F      | 2026-02 | wunderground        |       28 |           28 |    7,287,524 |
| NYC           | KLGA      | F      | 2026-03 | wunderground        |       31 |           31 |    3,172,388 |
| NYC           | KLGA      | F      | 2026-04 | wunderground        |       30 |           30 |    7,959,074 |
| NYC           | KLGA      | F      | 2026-05 | wunderground        |       31 |           32 |    4,660,223 |
| NYC           | KLGA      | F      | 2026-06 | wunderground        |       29 |           29 |    3,725,946 |
| NYC           | KLGA      | F      | 2026-07 | wunderground        |       31 |           31 |    4,705,613 |
| NYC           | KLGA      | F      | 2026-08 | noaa_wrh            |        9 |            9 |      740,734 |
| NYC           | KLGA      | F      | 2026-08 | wunderground        |       22 |           22 |    2,295,645 |
| NYC           | KLGA      | F      | 2026-09 | noaa_wrh            |       30 |           28 |    2,093,793 |
| NYC           | KLGA      | F      | 2026-10 | noaa_wrh            |        1 |            0 |        1,864 |
| Panama City   | MPMG      | C      | 2026-04 | wunderground        |       28 |           28 |      719,959 |
| Panama City   | MPMG      | C      | 2026-05 | wunderground        |       30 |           31 |      737,108 |
| Panama City   | MPMG      | C      | 2026-06 | wunderground        |       29 |           29 |      752,888 |
| Panama City   | MPMG      | C      | 2026-07 | wunderground        |       31 |           31 |    1,003,614 |
| Panama City   | MPMG      | C      | 2026-08 | noaa_wrh            |        9 |            9 |      168,756 |
| Panama City   | MPMG      | C      | 2026-08 | wunderground        |       22 |           22 |      492,307 |
| Panama City   | MPMG      | C      | 2026-09 | noaa_wrh            |       30 |           28 |      637,538 |
| Panama City   | MPMG      | C      | 2026-10 | noaa_wrh            |        1 |            0 |          731 |
| Paris         | LFPG      | C      | 2026-02 | wunderground        |       15 |           15 |    1,357,790 |
| Paris         | LFPG      | C      | 2026-03 | wunderground        |       30 |           30 |    1,417,313 |
| Paris         | LFPB      | C      | 2026-04 | wunderground        |       12 |           12 |    2,002,363 |
| Paris         | LFPG      | C      | 2026-04 | wunderground        |       18 |           18 |    5,323,760 |
| Paris         | LFPB      | C      | 2026-05 | wunderground        |       31 |           32 |    4,031,078 |
| Paris         | LFPB      | C      | 2026-06 | wunderground        |       30 |           30 |    4,396,212 |
| Paris         | LFPB      | C      | 2026-07 | wunderground        |       31 |           31 |    3,958,545 |
| Paris         | LFPB      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      807,949 |
| Paris         | LFPB      | C      | 2026-08 | wunderground        |       23 |           23 |    2,565,833 |
| Paris         | LFPB      | C      | 2026-09 | noaa_wrh            |       30 |           28 |    2,132,920 |
| Paris         | LFPB      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        2,370 |
| Phoenix       | KPHX      | F      | 2025-12 | wunderground        |        2 |            2 |       30,076 |
| Qingdao       | ZSQD      | C      | 2026-04 | wunderground        |        4 |            4 |      322,051 |
| Qingdao       | ZSQD      | C      | 2026-05 | wunderground        |       31 |           32 |    1,248,794 |
| Qingdao       | ZSQD      | C      | 2026-06 | wunderground        |       30 |           30 |    1,437,596 |
| Qingdao       | ZSQD      | C      | 2026-07 | wunderground        |       31 |           31 |    1,723,191 |
| Qingdao       | ZSQD      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      240,262 |
| Qingdao       | ZSQD      | C      | 2026-08 | wunderground        |       23 |           23 |      851,759 |
| Qingdao       | ZSQD      | C      | 2026-09 | noaa_wrh            |       30 |           29 |      977,222 |
| Qingdao       | ZSQD      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        2,292 |
| San Francisco | KSFO      | F      | 2026-03 | wunderground        |        7 |            7 |      481,424 |
| San Francisco | KSFO      | F      | 2026-04 | wunderground        |       30 |           30 |    2,113,322 |
| San Francisco | KSFO      | F      | 2026-05 | wunderground        |       31 |           32 |    1,374,066 |
| San Francisco | KSFO      | F      | 2026-06 | wunderground        |       29 |           29 |    1,996,958 |
| San Francisco | KSFO      | F      | 2026-07 | wunderground        |       31 |           31 |    1,852,978 |
| San Francisco | KSFO      | F      | 2026-08 | noaa_wrh            |        9 |            9 |      401,507 |
| San Francisco | KSFO      | F      | 2026-08 | wunderground        |       22 |           22 |      977,770 |
| San Francisco | KSFO      | F      | 2026-09 | noaa_wrh            |       30 |           28 |    1,219,445 |
| San Francisco | KSFO      | F      | 2026-10 | noaa_wrh            |        1 |            0 |        5,180 |
| Sao Paulo     | SBGR      | C      | 2026-02 | wunderground        |       15 |           15 |    1,044,718 |
| Sao Paulo     | SBGR      | C      | 2026-03 | wunderground        |       30 |           30 |      848,394 |
| Sao Paulo     | SBGR      | C      | 2026-04 | wunderground        |       30 |           30 |    2,736,935 |
| Sao Paulo     | SBGR      | C      | 2026-05 | wunderground        |       31 |           31 |    1,824,849 |
| Sao Paulo     | SBGR      | C      | 2026-06 | wunderground        |       28 |           28 |    1,708,227 |
| Sao Paulo     | SBGR      | C      | 2026-07 | wunderground        |       31 |           31 |    1,594,251 |
| Sao Paulo     | SBGR      | C      | 2026-08 | noaa_wrh            |        9 |            9 |      309,271 |
| Sao Paulo     | SBGR      | C      | 2026-08 | wunderground        |       22 |           22 |      944,981 |
| Sao Paulo     | SBGR      | C      | 2026-09 | noaa_wrh            |       30 |           28 |    1,158,385 |
| Sao Paulo     | SBGR      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        1,785 |
| Seattle       | KSEA      | F      | 2025-12 | wunderground        |       27 |           27 |    1,155,727 |
| Seattle       | KSEA      | F      | 2026-01 | wunderground        |       30 |           30 |    1,501,663 |
| Seattle       | KSEA      | F      | 2026-02 | wunderground        |       28 |           28 |    2,422,084 |
| Seattle       | KSEA      | F      | 2026-03 | wunderground        |       30 |           30 |    1,587,910 |
| Seattle       | KSEA      | F      | 2026-04 | wunderground        |       30 |           30 |    3,508,547 |
| Seattle       | KSEA      | F      | 2026-05 | wunderground        |       31 |           31 |    2,251,460 |
| Seattle       | KSEA      | F      | 2026-06 | wunderground        |       29 |           29 |    1,823,665 |
| Seattle       | KSEA      | F      | 2026-07 | wunderground        |       31 |           31 |    1,811,639 |
| Seattle       | KSEA      | F      | 2026-08 | noaa_wrh            |        9 |            9 |      289,659 |
| Seattle       | KSEA      | F      | 2026-08 | wunderground        |       22 |           22 |    1,093,669 |
| Seattle       | KSEA      | F      | 2026-09 | noaa_wrh            |       30 |           28 |    1,288,208 |
| Seattle       | KSEA      | F      | 2026-10 | noaa_wrh            |        1 |            0 |        3,608 |
| Seoul         | RKSI      | C      | 2025-12 | wunderground        |       26 |           26 |    1,583,005 |
| Seoul         | RKSI      | C      | 2026-01 | wunderground        |       31 |           31 |    4,537,189 |
| Seoul         | RKSI      | C      | 2026-02 | wunderground        |       28 |           28 |    6,828,641 |
| Seoul         | RKSI      | C      | 2026-03 | wunderground        |       30 |           30 |    3,475,105 |
| Seoul         | RKSI      | C      | 2026-04 | wunderground        |       30 |           30 |   14,034,851 |
| Seoul         | RKSI      | C      | 2026-05 | wunderground        |       31 |           32 |    7,193,552 |
| Seoul         | RKSI      | C      | 2026-06 | wunderground        |       30 |           30 |    8,047,996 |
| Seoul         | RKSI      | C      | 2026-07 | wunderground        |       31 |           31 |    5,957,005 |
| Seoul         | RKSI      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      584,518 |
| Seoul         | RKSI      | C      | 2026-08 | wunderground        |       23 |           23 |    2,968,273 |
| Seoul         | RKSI      | C      | 2026-09 | noaa_wrh            |       30 |           29 |    1,971,111 |
| Seoul         | RKSI      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        5,481 |
| Shanghai      | ZSPD      | C      | 2026-03 | wunderground        |       18 |           18 |    1,897,610 |
| Shanghai      | ZSPD      | C      | 2026-04 | wunderground        |       30 |           30 |    9,410,881 |
| Shanghai      | ZSPD      | C      | 2026-05 | wunderground        |       31 |           32 |    5,693,399 |
| Shanghai      | ZSPD      | C      | 2026-06 | wunderground        |       30 |           30 |    5,280,136 |
| Shanghai      | ZSPD      | C      | 2026-07 | wunderground        |       31 |           31 |    5,392,110 |
| Shanghai      | ZSPD      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      552,083 |
| Shanghai      | ZSPD      | C      | 2026-08 | wunderground        |       23 |           23 |    3,139,355 |
| Shanghai      | ZSPD      | C      | 2026-09 | noaa_wrh            |       30 |           29 |    2,334,956 |
| Shanghai      | ZSPD      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        7,552 |
| Shenzhen      | ZGSZ      | C      | 2026-03 | noaa_wrh            |        1 |            1 |      256,644 |
| Shenzhen      | ZGSZ      | C      | 2026-03 | wunderground        |       10 |           10 |      959,834 |
| Shenzhen      | ZGSZ      | C      | 2026-04 | wunderground        |       30 |           30 |    3,859,376 |
| Shenzhen      | ZGSZ      | C      | 2026-05 | wunderground        |       31 |           32 |    2,945,862 |
| Shenzhen      | ZGSZ      | C      | 2026-06 | wunderground        |       30 |           30 |    3,791,394 |
| Shenzhen      | ZGSZ      | C      | 2026-07 | wunderground        |       31 |           31 |    3,463,480 |
| Shenzhen      | ZGSZ      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      413,796 |
| Shenzhen      | ZGSZ      | C      | 2026-08 | wunderground        |       23 |           23 |    2,532,800 |
| Shenzhen      | ZGSZ      | C      | 2026-09 | noaa_wrh            |       30 |           29 |    1,497,604 |
| Shenzhen      | ZGSZ      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        5,383 |
| Singapore     | WSSS      | C      | 2026-03 | wunderground        |       18 |           18 |      618,818 |
| Singapore     | WSSS      | C      | 2026-04 | wunderground        |       30 |           30 |    3,723,021 |
| Singapore     | WSSS      | C      | 2026-05 | wunderground        |       31 |           32 |    2,792,156 |
| Singapore     | WSSS      | C      | 2026-06 | wunderground        |       30 |           30 |    2,389,372 |
| Singapore     | WSSS      | C      | 2026-07 | wunderground        |       31 |           31 |    2,208,343 |
| Singapore     | WSSS      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      440,857 |
| Singapore     | WSSS      | C      | 2026-08 | wunderground        |       23 |           23 |    1,295,804 |
| Singapore     | WSSS      | C      | 2026-09 | noaa_wrh            |       30 |           29 |    1,402,604 |
| Singapore     | WSSS      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        2,173 |
| Taipei        | CWA46692  | C      | 2026-03 | cwa                 |        7 |            7 |       22,994 |
| Taipei        | RCTP      | C      | 2026-03 | noaa_wrh            |        8 |            8 |      662,884 |
| Taipei        | RCTP      | C      | 2026-04 | noaa_wrh            |        4 |            4 |      584,957 |
| Taipei        | RCSS      | C      | 2026-04 | wunderground        |       26 |           26 |    3,000,018 |
| Taipei        | RCSS      | C      | 2026-05 | wunderground        |       31 |           32 |    2,439,782 |
| Taipei        | RCSS      | C      | 2026-06 | wunderground        |       30 |           30 |    2,987,507 |
| Taipei        | RCSS      | C      | 2026-07 | wunderground        |       31 |           31 |    2,826,613 |
| Taipei        | RCSS      | C      | 2026-08 | noaa_wrh            |        1 |            1 |      169,478 |
| Taipei        | RCSS      | C      | 2026-08 | wunderground        |       30 |           30 |    1,991,619 |
| Taipei        | RCSS      | C      | 2026-09 | wunderground        |       30 |           29 |    1,273,998 |
| Taipei        | RCSS      | C      | 2026-10 | wunderground        |        1 |            0 |        4,099 |
| Tel Aviv      | LLBG      | C      | 2026-03 | noaa_wrh            |        8 |            8 |      370,137 |
| Tel Aviv      | LLBG      | C      | 2026-03 | wunderground        |       13 |           13 |    1,521,476 |
| Tel Aviv      | LLBG      | C      | 2026-04 | noaa_wrh            |       30 |           30 |    2,473,377 |
| Tel Aviv      | LLBG      | C      | 2026-05 | noaa_wrh            |       31 |           32 |    1,544,941 |
| Tel Aviv      | LLBG      | C      | 2026-06 | noaa_wrh            |       30 |           30 |    1,168,580 |
| Tel Aviv      | LLBG      | C      | 2026-07 | noaa_wrh            |       31 |           31 |    1,352,305 |
| Tel Aviv      | LLBG      | C      | 2026-08 | noaa_wrh            |       31 |           31 |      989,480 |
| Tel Aviv      | LLBG      | C      | 2026-09 | noaa_wrh            |       30 |           28 |      954,720 |
| Tel Aviv      | LLBG      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        5,932 |
| Tokyo         | RJTT      | C      | 2026-03 | wunderground        |       21 |           21 |    1,042,012 |
| Tokyo         | RJTT      | C      | 2026-04 | wunderground        |       30 |           30 |    5,411,613 |
| Tokyo         | RJTT      | C      | 2026-05 | wunderground        |       31 |           32 |    3,238,838 |
| Tokyo         | RJTT      | C      | 2026-06 | wunderground        |       30 |           30 |    3,304,103 |
| Tokyo         | RJTT      | C      | 2026-07 | wunderground        |       31 |           31 |    3,091,267 |
| Tokyo         | RJTT      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      605,288 |
| Tokyo         | RJTT      | C      | 2026-08 | wunderground        |       23 |           23 |    1,914,925 |
| Tokyo         | RJTT      | C      | 2026-09 | noaa_wrh            |       30 |           29 |    2,131,482 |
| Tokyo         | RJTT      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        3,369 |
| Toronto       | CYYZ      | C      | 2025-12 | wunderground        |       26 |           26 |      925,968 |
| Toronto       | CYYZ      | C      | 2026-01 | wunderground        |       31 |           31 |    1,406,136 |
| Toronto       | CYYZ      | C      | 2026-02 | wunderground        |       28 |           28 |    2,340,915 |
| Toronto       | CYYZ      | C      | 2026-03 | wunderground        |       31 |           31 |    1,485,265 |
| Toronto       | CYYZ      | C      | 2026-04 | wunderground        |       30 |           30 |    5,005,784 |
| Toronto       | CYYZ      | C      | 2026-05 | wunderground        |       31 |           32 |    2,424,195 |
| Toronto       | CYYZ      | C      | 2026-06 | wunderground        |       29 |           29 |    1,633,268 |
| Toronto       | CYYZ      | C      | 2026-07 | wunderground        |       31 |           31 |    1,940,723 |
| Toronto       | CYYZ      | C      | 2026-08 | noaa_wrh            |        9 |            9 |      425,312 |
| Toronto       | CYYZ      | C      | 2026-08 | wunderground        |       22 |           22 |    1,170,276 |
| Toronto       | CYYZ      | C      | 2026-09 | noaa_wrh            |       30 |           28 |    1,381,734 |
| Toronto       | CYYZ      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        1,308 |
| Warsaw        | EPWA      | C      | 2026-03 | wunderground        |       15 |           15 |      445,293 |
| Warsaw        | EPWA      | C      | 2026-04 | wunderground        |       30 |           30 |    2,378,463 |
| Warsaw        | EPWA      | C      | 2026-05 | wunderground        |       31 |           32 |    1,908,897 |
| Warsaw        | EPWA      | C      | 2026-06 | wunderground        |       30 |           30 |    1,836,847 |
| Warsaw        | EPWA      | C      | 2026-07 | wunderground        |       31 |           31 |    1,686,807 |
| Warsaw        | EPWA      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      235,184 |
| Warsaw        | EPWA      | C      | 2026-08 | wunderground        |       23 |           23 |      970,318 |
| Warsaw        | EPWA      | C      | 2026-09 | noaa_wrh            |       30 |           28 |    1,177,256 |
| Warsaw        | EPWA      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        8,343 |
| Wellington    | NZWN      | C      | 2026-01 | wunderground        |       10 |           10 |      462,560 |
| Wellington    | NZWN      | C      | 2026-02 | wunderground        |       28 |           28 |    3,314,082 |
| Wellington    | NZWN      | C      | 2026-03 | wunderground        |       30 |           30 |    2,052,600 |
| Wellington    | NZWN      | C      | 2026-04 | wunderground        |       30 |           30 |    5,101,492 |
| Wellington    | NZWN      | C      | 2026-05 | wunderground        |       31 |           32 |    2,291,702 |
| Wellington    | NZWN      | C      | 2026-06 | wunderground        |       30 |           30 |    3,021,490 |
| Wellington    | NZWN      | C      | 2026-07 | wunderground        |       31 |           31 |    3,336,237 |
| Wellington    | NZWN      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      562,652 |
| Wellington    | NZWN      | C      | 2026-08 | wunderground        |       23 |           23 |    2,308,626 |
| Wellington    | NZWN      | C      | 2026-09 | noaa_wrh            |       30 |           29 |    1,675,727 |
| Wellington    | NZWN      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        6,347 |
| Wuhan         | ZHHH      | C      | 2026-03 | wunderground        |       11 |           11 |      334,780 |
| Wuhan         | ZHHH      | C      | 2026-04 | wunderground        |       30 |           30 |    2,677,212 |
| Wuhan         | ZHHH      | C      | 2026-05 | wunderground        |       31 |           32 |    2,048,688 |
| Wuhan         | ZHHH      | C      | 2026-06 | wunderground        |       30 |           30 |    1,792,368 |
| Wuhan         | ZHHH      | C      | 2026-07 | wunderground        |       31 |           31 |    1,975,291 |
| Wuhan         | ZHHH      | C      | 2026-08 | noaa_wrh            |        8 |            8 |      312,986 |
| Wuhan         | ZHHH      | C      | 2026-08 | wunderground        |       23 |           23 |    1,088,246 |
| Wuhan         | ZHHH      | C      | 2026-09 | noaa_wrh            |       30 |           29 |    1,059,676 |
| Wuhan         | ZHHH      | C      | 2026-10 | noaa_wrh            |        1 |            0 |        4,156 |
| Zhengzhou     | ZHCC      | C      | 2026-05 | wunderground        |        3 |            0 |            0 |
| Zhengzhou     | ZHCC      | C      | 2026-08 | noaa_wrh            |        9 |            9 |       78,151 |
| Zhengzhou     | ZHCC      | C      | 2026-08 | wunderground        |       16 |           16 |      116,424 |
| Zhengzhou     | ZHCC      | C      | 2026-09 | noaa_wrh            |       30 |           29 |      197,524 |

## Parsing issues (96 events)

Missing station/unit/date, mixed stations or sources within one event, closed but unresolved, unknown resolution source, or several events for one city-day.

|   event_id | city          | station   | unit   | date                | resolution_source   |   resolution_fallback |   n_buckets |   volume_usd | resolved   | disputed   | closed   | month   |
|-----------:|:--------------|:----------|:-------|:--------------------|:--------------------|----------------------:|------------:|-------------:|:-----------|:-----------|:---------|:--------|
|     493651 | London        | EGLC      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |    11642.4   | True       | False      | True     | 2026-05 |
|     493652 | Paris         | LFPB      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     9716.95  | True       | False      | True     | 2026-05 |
|     493653 | Sao Paulo     | SBGR      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     5703.72  | True       | False      | True     | 2026-05 |
|     493654 | Buenos Aires  | SAEZ      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     2939.51  | True       | False      | True     | 2026-05 |
|     493655 | Seoul         | RKSI      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |    22904.5   | True       | False      | True     | 2026-05 |
|     493656 | Toronto       | CYYZ      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     4061.7   | True       | False      | True     | 2026-05 |
|     493658 | NYC           | KLGA      | F      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     8947.15  | True       | False      | True     | 2026-05 |
|     493659 | Dallas        | KDAL      | F      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     6725.16  | True       | False      | True     | 2026-05 |
|     493660 | Atlanta       | KATL      | F      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     5840.02  | True       | False      | True     | 2026-05 |
|     493661 | Miami         | KMIA      | F      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     7028.71  | True       | False      | True     | 2026-05 |
|     493662 | Chicago       | KORD      | F      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     6207.56  | True       | False      | True     | 2026-05 |
|     493663 | Ankara        | LTAC      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     3549.52  | True       | False      | True     | 2026-05 |
|     493664 | Wellington    | NZWN      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     5174.51  | True       | False      | True     | 2026-05 |
|     493665 | Lucknow       | VILK      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     5422.39  | True       | False      | True     | 2026-05 |
|     493666 | Munich        | EDDM      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     4274.21  | True       | False      | True     | 2026-05 |
|     493667 | Tel Aviv      | LLBG      | C      | 2026-05-19 00:00:00 | noaa_wrh            |                   nan |          11 |     6357.21  | True       | False      | True     | 2026-05 |
|     493668 | Tokyo         | RJTT      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |    11010.5   | True       | False      | True     | 2026-05 |
|     493669 | Hong Kong     | HKO       | C      | 2026-05-19 00:00:00 | hko                 |                   nan |          11 |     8976.19  | True       | False      | True     | 2026-05 |
|     493670 | Shanghai      | ZSPD      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |    15836.3   | True       | False      | True     | 2026-05 |
|     493671 | Singapore     | WSSS      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     5209.5   | True       | False      | True     | 2026-05 |
|     493672 | Milan         | LIMC      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     4486.69  | True       | False      | True     | 2026-05 |
|     493673 | Madrid        | LEMD      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     5900.26  | True       | False      | True     | 2026-05 |
|     493674 | Warsaw        | EPWA      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     5790.55  | True       | False      | True     | 2026-05 |
|     493675 | Taipei        | RCSS      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     7074.86  | True       | False      | True     | 2026-05 |
|     493676 | Chongqing     | ZUCK      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     5794.7   | True       | False      | True     | 2026-05 |
|     493677 | Beijing       | ZBAA      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |    12844.6   | True       | False      | True     | 2026-05 |
|     493678 | Wuhan         | ZHHH      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     5470.32  | True       | False      | True     | 2026-05 |
|     493679 | Chengdu       | ZUUU      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     5752.34  | True       | False      | True     | 2026-05 |
|     493680 | Shenzhen      | ZGSZ      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     9722.53  | True       | False      | True     | 2026-05 |
|     493681 | Austin        | KAUS      | F      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |    12013.3   | True       | False      | True     | 2026-05 |
|     493682 | Denver        | KBKF      | F      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     5416.15  | True       | False      | True     | 2026-05 |
|     493683 | Houston       | KHOU      | F      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |    10821.9   | True       | False      | True     | 2026-05 |
|     493684 | Los Angeles   | KLAX      | F      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     7751.17  | True       | False      | True     | 2026-05 |
|     493685 | San Francisco | KSFO      | F      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |    48335.5   | True       | False      | True     | 2026-05 |
|     493686 | Moscow        | UUWW      | C      | 2026-05-19 00:00:00 | noaa_wrh            |                   nan |          11 |     4312.64  | True       | False      | True     | 2026-05 |
|     493687 | Istanbul      | LTFM      | C      | 2026-05-19 00:00:00 | noaa_wrh            |                   nan |          11 |     4496.55  | True       | False      | True     | 2026-05 |
|     493688 | Mexico City   | MMMX      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     9699.34  | True       | False      | True     | 2026-05 |
|     493689 | Busan         | RKPK      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     2823.93  | True       | False      | True     | 2026-05 |
|     493690 | Amsterdam     | EHAM      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     2724.66  | True       | False      | True     | 2026-05 |
|     493691 | Helsinki      | EFHK      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     4616.67  | True       | False      | True     | 2026-05 |
|     493692 | Panama City   | MPMG      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     5134.24  | True       | False      | True     | 2026-05 |
|     493693 | Kuala Lumpur  | WMKK      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     3129.57  | True       | False      | True     | 2026-05 |
|     493695 | Jeddah        | OEJN      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     5770.62  | True       | False      | True     | 2026-05 |
|     493696 | Cape Town     | FACT      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     3329.69  | False      | False      | False    | 2026-05 |
|     493697 | Guangzhou     | ZGGG      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     3128.28  | True       | False      | True     | 2026-05 |
|     493699 | Qingdao       | ZSQD      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     3220.99  | True       | False      | True     | 2026-05 |
|     493722 | Karachi       | OPKC      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     2414.7   | True       | False      | True     | 2026-05 |
|     493723 | Manila        | RPLL      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     2693.79  | True       | False      | True     | 2026-05 |
|     503460 | London        | EGLC      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |    15493.9   | True       | False      | True     | 2026-05 |
|     503494 | Paris         | LFPB      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     2939.51  | True       | False      | True     | 2026-05 |
|     503528 | Sao Paulo     | SBGR      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |           1 |      740.249 | False      | False      | True     | 2026-05 |
|     503547 | Buenos Aires  | SAEZ      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     5039.4   | True       | False      | True     | 2026-05 |
|     503558 | Seoul         | RKSI      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |           3 |      395.75  | True       | False      | True     | 2026-05 |
|     503569 | Toronto       | CYYZ      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     2624.87  | True       | False      | True     | 2026-05 |
|     503590 | NYC           | KLGA      | F      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     8201.46  | True       | False      | True     | 2026-05 |
|     503602 | Dallas        | KDAL      | F      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     4167.86  | True       | False      | True     | 2026-05 |
|     503612 | Atlanta       | KATL      | F      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     2402.31  | True       | False      | True     | 2026-05 |
|     503624 | Miami         | KMIA      | F      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     3177.79  | True       | False      | True     | 2026-05 |
|     503629 | Chicago       | KORD      | F      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     5174.2   | True       | False      | True     | 2026-05 |
|     503631 | Ankara        | LTAC      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     5628.97  | True       | False      | True     | 2026-05 |
|     503632 | Wellington    | NZWN      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     3969.35  | True       | False      | True     | 2026-05 |
|     503633 | Lucknow       | VILK      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     6828.16  | True       | False      | True     | 2026-05 |
|     503634 | Munich        | EDDM      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     1056.18  | True       | False      | True     | 2026-05 |
|     503635 | Tel Aviv      | LLBG      | C      | 2026-05-19 00:00:00 | noaa_wrh            |                   nan |          11 |     1740.59  | True       | False      | True     | 2026-05 |
|     503636 | Tokyo         | RJTT      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     1704.42  | True       | False      | True     | 2026-05 |
|     503637 | Hong Kong     | HKO       | C      | 2026-05-19 00:00:00 | hko                 |                   nan |          11 |     1525.51  | True       | False      | True     | 2026-05 |
|     503638 | Shanghai      | ZSPD      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     1914.32  | True       | False      | True     | 2026-05 |
|     503639 | Singapore     | WSSS      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |      641.623 | True       | False      | True     | 2026-05 |
|     503640 | Milan         | LIMC      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |      430     | True       | False      | True     | 2026-05 |
|     503641 | Madrid        | LEMD      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     1297.94  | True       | False      | True     | 2026-05 |
|     503642 | Warsaw        | EPWA      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     1285.38  | True       | False      | True     | 2026-05 |
|     503643 | Taipei        | RCSS      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     1867.75  | True       | False      | True     | 2026-05 |
|     503644 | Chongqing     | ZUCK      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |      664.41  | True       | False      | True     | 2026-05 |
|     503645 | Beijing       | ZBAA      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     1063.63  | True       | False      | True     | 2026-05 |
|     503646 | Wuhan         | ZHHH      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     1745.88  | True       | False      | True     | 2026-05 |
|     503654 | Chengdu       | ZUUU      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |      366.951 | True       | False      | True     | 2026-05 |
|     503655 | Shenzhen      | ZGSZ      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |      988.942 | True       | False      | True     | 2026-05 |
|     503656 | Austin        | KAUS      | F      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     2869.46  | True       | False      | True     | 2026-05 |
|     503657 | Denver        | KBKF      | F      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     3374.49  | True       | False      | True     | 2026-05 |
|     503658 | Houston       | KHOU      | F      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     2560.26  | True       | False      | True     | 2026-05 |
|     503659 | Los Angeles   | KLAX      | F      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     2628.48  | True       | False      | True     | 2026-05 |
|     503660 | San Francisco | KSFO      | F      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     3675.27  | True       | False      | True     | 2026-05 |
|     503661 | Moscow        | UUWW      | C      | 2026-05-19 00:00:00 | noaa_wrh            |                   nan |          11 |      977.2   | True       | False      | True     | 2026-05 |
|     503662 | Istanbul      | LTFM      | C      | 2026-05-19 00:00:00 | noaa_wrh            |                   nan |          11 |     1910     | True       | False      | True     | 2026-05 |
|     503663 | Mexico City   | MMMX      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     2527.82  | True       | False      | True     | 2026-05 |
|     503664 | Busan         | RKPK      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |      302     | True       | False      | True     | 2026-05 |
|     503665 | Amsterdam     | EHAM      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     1041.45  | True       | False      | True     | 2026-05 |
|     503666 | Helsinki      | EFHK      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |      539.71  | True       | False      | True     | 2026-05 |
|     503667 | Panama City   | MPMG      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     3605.37  | True       | False      | True     | 2026-05 |
|     503668 | Kuala Lumpur  | WMKK      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |      910.846 | True       | False      | True     | 2026-05 |
|     503669 | Jeddah        | OEJN      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     1403.5   | True       | False      | True     | 2026-05 |
|     503670 | Cape Town     | FACT      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     2113.92  | True       | False      | True     | 2026-05 |
|     503671 | Guangzhou     | ZGGG      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |      449.609 | True       | False      | True     | 2026-05 |
|     503672 | Qingdao       | ZSQD      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     1975.98  | True       | False      | True     | 2026-05 |
|     503673 | Karachi       | OPKC      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |      234.991 | True       | False      | True     | 2026-05 |
|     503674 | Manila        | RPLL      | C      | 2026-05-19 00:00:00 | wunderground        |                   nan |          11 |     1299.85  | True       | False      | True     | 2026-05 |

## Unparsed bucket labels (0 markets)

None.
