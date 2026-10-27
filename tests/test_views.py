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
    # With a purchase: still the store price until the paid value arrives (ticket 10)
    assert costs["Paid Played"][:2] == ("estimated", Decimal("100.00"))
    # Played without a license: still free
    assert costs["Free Played"][0] == "free"


def test_software_and_other_items_are_out_of_metrics(conn):
    costs = game_costs(conn)
    assert "Some Software" not in costs
    assert "Test Server" not in costs

    out = conn.execute(
        "SELECT name, item_category FROM items_out_of_metrics WHERE user_id = %s ORDER BY name", (USER,)
    ).fetchall()
    assert out == [("Some Software", "software"), ("Test Server", "other")]
