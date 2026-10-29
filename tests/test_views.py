"""Business rules of the analysis views (sql/views.sql), tested with a fictional library."""
import datetime
from decimal import Decimal

import pytest

from src.db import get_connection

USER = "fake_user_hash"
OLD_DAY = datetime.date(2026, 1, 1)
DAY = datetime.date(2026, 1, 2)

# app_id, name, genres, list price, has license, minutes on DAY
FAKE_LIBRARY = [
    (900001, "Paid Played",    ["Action"],    Decimal("100.00"), True,  600),
    (900002, "Free Played",    ["Action"],    None,              False, 120),
    (900003, "Never Played",   ["Action"],    Decimal("50.00"),  True,  0),
    (900004, "Barely Started", ["Action"],    Decimal("30.00"),  True,  30),
    (900005, "No Price",       ["Action"],    None,              True,  600),
    (900006, "Some Software",  ["Utilities"], Decimal("20.00"),  True,  60),
    (900007, "Test Server",    [],            None,              True,  60),
]


@pytest.fixture
def conn():
    """Fictional library inserted in a transaction that is undone at the end (rollback)."""
    connection = get_connection()
    connection.execute("INSERT INTO users (user_id, nickname) VALUES (%s, 'fake_user')", (USER,))
    for app_id, name, genres, price, has_license, minutes in FAKE_LIBRARY:
        connection.execute(
            "INSERT INTO games (app_id, name, store_genres, list_price_brl) VALUES (%s, %s, %s, %s)",
            (app_id, name, genres, price),
        )
        connection.execute(
            "INSERT INTO library (user_id, app_id, first_seen_date, has_license) VALUES (%s, %s, %s, %s)",
            (USER, app_id, OLD_DAY, has_license),
        )
        connection.execute(
            "INSERT INTO playtime_snapshots VALUES (%s, %s, %s, %s)", (USER, app_id, DAY, minutes)
        )
    # Older snapshot with fewer minutes: the views must use the latest one
    connection.execute("INSERT INTO playtime_snapshots VALUES (%s, 900001, %s, 300)", (USER, OLD_DAY))
    yield connection
    connection.rollback()
    connection.close()


def game_costs(conn):
    rows = conn.execute(
        """SELECT name, value_origin, game_value_brl, minutes_played, cost_per_hour_brl, hours_group
           FROM game_costs WHERE user_id = %s""",
        (USER,),
    ).fetchall()
    return {row[0]: row[1:] for row in rows}


def test_estimated_game_uses_store_price_and_latest_snapshot(conn):
    # R$ 100 / 10 h (600 min on the latest day, not 300 min on the old day)
    assert game_costs(conn)["Paid Played"] == ("estimated", Decimal("100.00"), 600, Decimal("10"), "played")


def test_free_game_costs_zero_per_hour(conn):
    assert game_costs(conn)["Free Played"] == ("free", Decimal("0"), 120, Decimal("0"), "played")


def test_game_with_zero_hours_has_value_but_no_cost_per_hour(conn):
    assert game_costs(conn)["Never Played"] == ("estimated", Decimal("50.00"), 0, None, "not_played")


def test_game_under_one_hour_is_barely_started(conn):
    # R$ 30 / 0.5 h
    assert game_costs(conn)["Barely Started"] == ("estimated", Decimal("30.00"), 30, Decimal("60"), "barely_started")


def test_licensed_game_without_store_price_has_unknown_value(conn):
    assert game_costs(conn)["No Price"] == ("unknown", None, 600, None, "played")


def test_with_complete_history_a_licensed_game_without_purchase_costs_zero(conn):
    # The user loaded the complete purchase history, which has a purchase of "Paid Played" only
    conn.execute("UPDATE users SET purchase_history_loaded_at = now() WHERE user_id = %s", (USER,))
    conn.execute(
        """INSERT INTO purchases (purchase_key, user_id, purchase_date, purchase_type, total_brl)
           VALUES ('fake_purchase', %s, %s, 'purchase', 80.00)""",
        (USER, OLD_DAY),
    )
    conn.execute(
        "INSERT INTO purchase_items VALUES ('fake_purchase', 1, 'Paid Played', 900001, 80.00)"
    )
    costs = game_costs(conn)
    # No purchase: gift, complimentary or promotion -> R$ 0, out of the money parked (rule 24)
    assert costs["Never Played"] == ("no_purchase", Decimal("0"), 0, None, "not_played")
    assert costs["No Price"][:2] == ("no_purchase", Decimal("0"))
    # With a purchase: the paid value from the history (ticket 10)
    assert costs["Paid Played"][:2] == ("paid", Decimal("80.00"))
    # Played without a license: still free
    assert costs["Free Played"][0] == "free"


def test_refunded_game_still_in_the_library_without_other_purchase_costs_zero(conn):
    # Bought, refunded, and still in the library (e.g. received later as a gift): rule 5 + rule 24
    conn.execute("UPDATE users SET purchase_history_loaded_at = now() WHERE user_id = %s", (USER,))
    conn.execute(
        """INSERT INTO purchases (purchase_key, user_id, purchase_date, purchase_type, total_brl)
           VALUES ('fake_purchase', %s, %s, 'purchase', 80.00)""",
        (USER, OLD_DAY),
    )
    conn.execute("INSERT INTO purchase_items VALUES ('fake_purchase', 1, 'Paid Played', 900001, 80.00)")
    conn.execute(
        """INSERT INTO purchases (purchase_key, user_id, purchase_date, purchase_type, total_brl, refunded_purchase_key)
           VALUES ('fake_refund', %s, %s, 'refund', 80.00, 'fake_purchase')""",
        (USER, DAY),
    )
    conn.execute("INSERT INTO purchase_items VALUES ('fake_refund', 1, 'Paid Played', 900001, 80.00)")

    assert game_costs(conn)["Paid Played"][:2] == ("no_purchase", Decimal("0"))
    net = conn.execute(
        "SELECT total_brl, refunded_brl, net_total_brl FROM net_purchases WHERE purchase_key = 'fake_purchase'"
    ).fetchone()
    assert net == (Decimal("80.00"), Decimal("80.00"), Decimal("0.00"))


def add_purchase(conn, key, day, kind, app_id, name, total, original=None, pct=None):
    """Fictional purchase with one item (the item is the whole total)."""
    conn.execute(
        """INSERT INTO purchases (purchase_key, user_id, purchase_date, purchase_type, total_brl,
                                  original_price_brl, discount_pct)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (key, USER, day, kind, total, original, pct),
    )
    conn.execute("INSERT INTO purchase_items VALUES (%s, 1, %s, %s, %s)", (key, name, app_id, total))


def spending(conn):
    rows = conn.execute(
        """SELECT name, value_origin, game_value_brl, extra_spend_brl, total_spend_brl, cost_per_hour_brl,
                  purchase_history_loaded
           FROM game_costs WHERE user_id = %s""",
        (USER,),
    ).fetchall()
    return {row[0]: row[1:] for row in rows}


def test_paid_game_first_purchase_is_the_game_value_and_later_ones_are_extra(conn):
    conn.execute("UPDATE users SET purchase_history_loaded_at = now() WHERE user_id = %s", (USER,))
    add_purchase(conn, "p1", datetime.date(2025, 1, 1), "purchase", 900001, "Paid Played", Decimal("80.00"))
    add_purchase(conn, "p2", datetime.date(2025, 6, 1), "purchase", 900001, "Paid Played - DLC", Decimal("20.00"))
    add_purchase(conn, "p3", datetime.date(2025, 7, 1), "in_game", 900001, "Paid Played", Decimal("10.00"))
    # Game R$ 80 (first purchase) + extra R$ 30 (DLC + in-game) = R$ 110 over 10 h = R$ 11/h (rule 1, 23)
    assert spending(conn)["Paid Played"] == (
        "paid", Decimal("80.00"), Decimal("30.00"), Decimal("110.00"), Decimal("11"), True)


def test_free_game_with_in_game_purchases_has_a_real_cost_per_hour(conn):
    conn.execute("UPDATE users SET purchase_history_loaded_at = now() WHERE user_id = %s", (USER,))
    add_purchase(conn, "p4", datetime.date(2025, 7, 1), "in_game", 900002, "Free Played", Decimal("30.00"))
    # Access was free (R$ 0), but R$ 30 inside the game over 2 h = R$ 15/h (rule 16)
    assert spending(conn)["Free Played"] == (
        "free", Decimal("0"), Decimal("30.00"), Decimal("30.00"), Decimal("15"), True)


def test_without_history_values_stay_estimated_and_the_level_is_basic(conn):
    # Only the SteamID: no purchase history loaded (rule 2)
    assert spending(conn)["Paid Played"] == (
        "estimated", Decimal("100.00"), Decimal("0"), Decimal("100.00"), Decimal("10"), False)


def test_discount_compares_paid_value_with_the_price_at_purchase_time(conn):
    add_purchase(conn, "d1", datetime.date(2025, 1, 1), "purchase", 900001, "Paid Played",
                 Decimal("14.00"), original=Decimal("20.00"), pct=30)
    add_purchase(conn, "d2", datetime.date(2025, 2, 1), "purchase", 900003, "Never Played", Decimal("50.00"))
    rows = dict((key, rest) for key, *rest in conn.execute(
        """SELECT purchase_key, paid_brl, original_price_brl, discount_pct, savings_brl
           FROM purchase_discounts WHERE user_id = %s""",
        (USER,),
    ))
    assert rows["d1"] == [Decimal("14.00"), Decimal("20.00"), 30, Decimal("6.00")]
    # No discount on the page: the price at purchase time is the price paid
    assert rows["d2"] == [Decimal("50.00"), Decimal("50.00"), 0, Decimal("0.00")]


def test_software_and_other_items_are_out_of_metrics(conn):
    costs = game_costs(conn)
    assert "Some Software" not in costs
    assert "Test Server" not in costs

    out = conn.execute(
        "SELECT name, item_category FROM items_out_of_metrics WHERE user_id = %s ORDER BY name", (USER,)
    ).fetchall()
    assert out == [("Some Software", "software"), ("Test Server", "other")]
