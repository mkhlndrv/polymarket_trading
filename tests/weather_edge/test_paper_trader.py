"""Known-answer checks for the paper trader's order, fill and gating logic."""

from datetime import date, datetime

import numpy as np
import pandas as pd
import pytest

import weather_edge.paper_trader as pt


def _buckets():
    return pd.DataFrame(
        {
            "market_id": ["a", "b", "c", "d"],
            "station": "EGLC",
            "date": date(2026, 10, 3),
            "condition_id": ["ca", "cb", "cc", "cd"],
            "token_yes": ["ya", "yb", "yc", "yd"],
            "token_no": ["na", "nb", "nc", "nd"],
            "unit": "C",
            "lo": [16, 18, 20, 22],
            "hi": [17, 19, 21, 23],
        }
    )


def _row():
    return pd.Series({"emos_mu": 20.4, "emos_sigma": 1.2, "emos_nu": 50.0, "emos_scale": 1.1})


def test_bucket_probs_sum_to_one_in_the_market_unit():
    p = pt.bucket_probs(_row(), _buckets())
    assert 0.9 < p.sum() < 1.0  # tails below 16 and above 23 are outside these four buckets
    assert p[2] == max(p)  # 20 to 21 C holds the mode


def test_make_orders_edges_and_post_only():
    t = datetime(2026, 10, 1, 12, 0)
    probs = np.array([0.05, 0.20, 0.50, 0.20])
    books = {
        "ya": {
            "bid": 0.20,
            "ask": 0.24,
        },  # mid 0.22, model 0.05: sell YES at max(0.23, 0.15) = 0.23
        "yb": {
            "bid": 0.05,
            "ask": 0.07,
        },  # mid 0.06, model 0.20: buy YES at min(0.05, 0.10) = 0.05 crosses? no, 0.05 < ask
        "yc": {"bid": 0.44, "ask": 0.46},  # mid 0.45, model 0.50: edge 0.05, no order
        "yd": {
            "bid": 0.45,
            "ask": 0.47,
        },  # mid 0.46, model 0.20: sell at max(0.47, 0.30) = 0.47 -> above bid, ok
    }
    o = pd.DataFrame(pt.make_orders(_buckets(), probs, books, _row(), t)).set_index("market_id")
    assert o.loc["a", "side"] == "sell_yes" and o.loc["a", "price"] == pytest.approx(0.23)
    assert o.loc["b", "side"] == "buy_yes" and o.loc["b", "price"] == pytest.approx(0.05)
    assert "c" not in o.index
    assert o.loc["d", "side"] == "sell_yes" and o.loc["d", "price"] == pytest.approx(0.47)
    assert (o.expires_at == t + pd.Timedelta(hours=24)).all() and (o["size"] == 5).all()
    # a bid that would cross the ask moves one tick under it, and is dropped if that kills the edge
    books2 = {"yb": {"bid": 0.02, "ask": 0.04}}  # min(0.02, 0.10) = 0.02 < ask: fine at 0.02
    o2 = pt.make_orders(_buckets().iloc[[1]], np.array([0.20]), books2, _row(), t)
    assert o2[0]["price"] == pytest.approx(0.02)
    books3 = {"yb": {"bid": 0.14, "ask": 0.16}}  # mid 0.15: edge 0.05 only, no order
    assert pt.make_orders(_buckets().iloc[[1]], np.array([0.20]), books3, _row(), t) == []


def test_prints_and_book_rules_both_sides():
    t = datetime(2026, 10, 1, 12, 0)
    sell = pt.make_orders(
        _buckets().iloc[[0]], np.array([0.05]), {"ya": {"bid": 0.20, "ask": 0.24}}, _row(), t
    )[0]  # sell YES at 0.23
    buy = pt.make_orders(
        _buckets().iloc[[1]], np.array([0.20]), {"yb": {"bid": 0.05, "ask": 0.07}}, _row(), t
    )[0]  # buy YES at 0.05

    def tr(ts, asset, side, price, size):
        return {
            "timestamp": int(ts.timestamp()),
            "asset": asset,
            "side": side,
            "price": price,
            "size": size,
        }

    prints = [
        tr(
            datetime(2026, 10, 1, 13, 0, tzinfo=__import__("datetime").UTC), "ya", "BUY", 0.23, 3
        ),  # touch
        tr(
            datetime(2026, 10, 1, 14, 0, tzinfo=__import__("datetime").UTC), "na", "SELL", 0.76, 4
        ),  # NO sold at 0.76 = YES bought at 0.24: through
        tr(
            datetime(2026, 10, 1, 15, 0, tzinfo=__import__("datetime").UTC), "ya", "SELL", 0.30, 9
        ),  # taker sells YES: not a lift
        tr(
            datetime(2026, 10, 3, 15, 0, tzinfo=__import__("datetime").UTC), "ya", "BUY", 0.40, 9
        ),  # after expiry
        tr(
            datetime(2026, 10, 1, 11, 0, tzinfo=__import__("datetime").UTC), "ya", "BUY", 0.40, 9
        ),  # before placement
    ]
    s = pt.apply_prints(sell, prints)
    assert s["touch_volume"] == 7 and s["through_volume"] == 4
    assert s["first_touch"] == pd.Timestamp("2026-10-01 13:00") and s[
        "first_through"
    ] == pd.Timestamp("2026-10-01 14:00")
    b = pt.apply_prints(
        buy,
        [
            tr(
                datetime(2026, 10, 1, 13, 0, tzinfo=__import__("datetime").UTC),
                "yb",
                "SELL",
                0.05,
                2,
            ),  # touch
            tr(
                datetime(2026, 10, 1, 13, 5, tzinfo=__import__("datetime").UTC),
                "nb",
                "BUY",
                0.96,
                6,
            ),  # NO bought at 0.96 = YES sold at 0.04: through
        ],
    )
    assert b["touch_volume"] == 8 and b["through_volume"] == 6
    assert pt.apply_book(sell, bid=0.23, ask=0.25)["book_filled"] == 5
    assert pt.apply_book(sell, bid=0.22, ask=0.25)["book_filled"] == 0
    assert pt.apply_book(buy, bid=0.03, ask=0.05)["book_filled"] == 5


def test_summary_pnl_and_decision_gating():
    t = datetime(2026, 10, 1, 12, 0)
    sell = pt.make_orders(
        _buckets().iloc[[0]], np.array([0.05]), {"ya": {"bid": 0.20, "ask": 0.24}}, _row(), t
    )[0]
    sell.update(status="resolved", outcome=0.0, touch_volume=10, through_volume=2, book_filled=5)
    buy = pt.make_orders(
        _buckets().iloc[[1]], np.array([0.20]), {"yb": {"bid": 0.05, "ask": 0.07}}, _row(), t
    )[0]
    buy.update(status="resolved", outcome=1.0, touch_volume=3, through_volume=0, book_filled=0)
    s = pt.summarize(pd.DataFrame([sell, buy])).set_index(["station", "rule"])
    # touch: sell 5 shares at 0.23 that expire worthless (+0.23 each) and buy 3 at 0.05 that win (+0.95 each)
    assert s.loc[("all", "touch"), "pnl_usd"] == pytest.approx(5 * 0.23 + 3 * 0.95)
    assert s.loc[("all", "through"), "filled_shares"] == 2
    assert s.loc[("all", "book"), "pnl_usd"] == pytest.approx(5 * 0.23)
    assert s.loc[("EGLC", "touch"), "orders_filled"] == 2
    # decisions: noon local, first half hour, once per station and day; day = local today + 2
    assert pt.due_decisions(["EGLC", "KLGA"], [], datetime(2026, 10, 1, 11, 10)) == [
        ("EGLC", date(2026, 10, 3))
    ]  # 12:10 BST in London, 07:10 in New York
    assert pt.due_decisions(["EGLC"], [["EGLC", "2026-10-03"]], datetime(2026, 10, 1, 11, 10)) == []
    assert pt.due_decisions(["KLGA"], [], datetime(2026, 10, 1, 16, 5)) == [
        ("KLGA", date(2026, 10, 3))
    ]
    assert pt.due_decisions(["KLGA"], [], datetime(2026, 10, 1, 16, 45)) == []
