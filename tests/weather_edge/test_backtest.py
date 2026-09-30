"""Known-answer checks for the tape fill model."""

from datetime import date, datetime

import duckdb
import pandas as pd
import pytest

import weather_edge.backtest as p7


def _scored():
    t = datetime(2026, 6, 8, 16)
    return pd.DataFrame(
        {
            "market_id": ["a", "b", "c", "d"],
            "day": [pd.Timestamp("2026-06-10")] * 4,
            "lead": 3,
            "t": [t] * 4,
            "unit": "F",
            "lo": [70, 72, 74, 76],
            "hi": [71, 73, 75, 77],
            "outcome": [1, 0, 0, 1],
            "market_p": [0.20, 0.50, 0.30, 0.40],
            "p_emos": [0.45, 0.30, 0.35, 0.10],
        }
    )


def test_orders_prices_and_sides():
    o = p7.orders_from_signal(_scored()).set_index("market_id")
    assert o.loc["a", "side"] == "yes" and o.loc["a", "price"] == pytest.approx(
        0.19
    )  # min(0.19, 0.35)
    assert o.loc["b", "side"] == "no" and o.loc["b", "price"] == pytest.approx(
        0.49
    )  # min(0.49, 0.60)
    assert "c" not in o.index  # edge 0.05 < 0.10
    assert o.loc["d", "side"] == "no" and o.loc["d", "price"] == pytest.approx(0.59)
    assert o.loc["a", "expected_pnl_share"] == pytest.approx(0.26)
    assert (o.t_end - o.t_start).iloc[0] == pd.Timedelta(hours=24)


def test_fills_touch_through_direction_and_window(tmp_path):
    con = duckdb.connect(str(tmp_path / "r.duckdb"))
    con.execute(
        "CREATE TABLE trades (market_id VARCHAR, ts TIMESTAMP, price DOUBLE, token_amount DOUBLE, "
        "taker_direction VARCHAR, nonusdc_side VARCHAR)"
    )
    # order a: buy YES at 0.19 from 06-08 16:00 to 06-09 16:00
    # order b: buy NO at 0.49 = sell YES at 0.51; order d: buy NO at 0.59 = sell YES at 0.41
    rows = [
        (
            "a",
            datetime(2026, 6, 8, 17),
            0.19,
            3,
            "SELL",
            "token1",
        ),  # taker sells YES at 0.19: touch
        (
            "a",
            datetime(2026, 6, 8, 18),
            0.82,
            4,
            "BUY",
            "token2",
        ),  # taker buys NO at 0.82 = sells YES at 0.18: through
        (
            "a",
            datetime(2026, 6, 8, 19),
            0.15,
            9,
            "BUY",
            "token1",
        ),  # taker BUYS YES at 0.15: not a fill for a bid
        ("a", datetime(2026, 6, 9, 17), 0.10, 9, "SELL", "token1"),  # after the window
        (
            "b",
            datetime(2026, 6, 8, 20),
            0.51,
            2,
            "BUY",
            "token1",
        ),  # taker buys YES at 0.51: touch only
        (
            "d",
            datetime(2026, 6, 8, 20),
            0.45,
            8,
            "BUY",
            "token1",
        ),  # taker buys YES at 0.45 > 0.41: through
    ]
    con.executemany("INSERT INTO trades VALUES (?, ?, ?, ?, ?, ?)", rows)
    o = p7.score_fills(p7.fills_from_tape(con, p7.orders_from_signal(_scored()))).set_index(
        "market_id"
    )
    assert o.loc["a", "touch_volume"] == 7 and o.loc["a", "through_volume"] == 4
    assert o.loc["a", "touch_ts"] == datetime(2026, 6, 8, 17)
    assert o.loc["b", "touch_volume"] == 2 and o.loc["b", "through_volume"] == 0
    assert o.loc["d", "through_volume"] == 8
    # a wins (outcome 1): 5 shares touch, 4 through, haircut halves winning fills
    assert o.loc["a", "filled_touch"] == 5 and o.loc["a", "filled_through"] == 4
    assert o.loc["a", "filled_through_haircut"] == 2 and o.loc["a", "pnl_through"] == pytest.approx(
        4 * 0.81
    )
    # b: NO bought at 0.49, outcome 0 so NO pays 1: pnl per share 0.51, 2 shares touched
    assert o.loc["b", "pnl_touch"] == pytest.approx(2 * 0.51) and o.loc["b", "pnl_through"] == 0
    # d: NO bought at 0.59, outcome 1 so NO pays 0: loses 0.59 per share on 5 shares, no haircut on a loss
    assert o.loc["d", "pnl_through"] == pytest.approx(-5 * 0.59)
    assert o.loc["d", "filled_through_haircut"] == 5
    s = p7.summarize(o.reset_index()).set_index("fill_model")
    assert s.loc["through", "filled_shares"] == 9 and s.loc["through", "orders_filled"] == 2
    assert s.loc["through", "pnl_usd"] == pytest.approx(4 * 0.81 - 5 * 0.59)
    con.close()
    assert date(2026, 6, 10) == o.loc["a", "day"].date()
