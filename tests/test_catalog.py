import datetime
from decimal import Decimal

import pytest

from src.catalog import games_to_check, parse_app_details, save_details
from src.db import get_connection

# Fictional store responses, in the same format as the Steam store API.
PAID_ON_SALE = {
    "success": True,
    "data": {
        "type": "game",
        "is_free": False,
        "genres": [{"id": "1", "description": "Action"}, {"id": "23", "description": "Indie"}],
        "price_overview": {"currency": "BRL", "initial": 9990, "final": 4995, "discount_percent": 50},
        "header_image": "https://example.com/header.jpg",
    },
}
FREE_GAME = {
    "success": True,
    "data": {"type": "game", "is_free": True, "genres": [{"id": "1", "description": "Action"}],
             "header_image": "https://example.com/free.jpg"},
}
NO_STORE_PAGE = {"success": False}
FOREIGN_CURRENCY = {
    "success": True,
    "data": {"type": "game", "is_free": False, "genres": [],
             "price_overview": {"currency": "USD", "initial": 1999, "final": 1999, "discount_percent": 0}},
}


def test_paid_game_uses_full_price_not_discounted_price():
    details = parse_app_details(PAID_ON_SALE)
    assert details["list_price_brl"] == Decimal("99.90")
    assert details["is_free"] is False
    assert details["store_type"] == "game"
    assert details["store_genres"] == ["Action", "Indie"]
    assert details["header_image_url"] == "https://example.com/header.jpg"


def test_free_game_is_marked_free_without_price():
    details = parse_app_details(FREE_GAME)
    assert details["is_free"] is True
    assert details["list_price_brl"] is None


def test_item_without_store_page_has_empty_details():
    details = parse_app_details(NO_STORE_PAGE)
    assert details == {"store_type": None, "store_genres": [], "list_price_brl": None,
                       "header_image_url": None, "is_free": None}


def test_price_in_other_currency_is_ignored():
    assert parse_app_details(FOREIGN_CURRENCY)["list_price_brl"] is None


@pytest.fixture
def conn():
    """Database connection that undoes everything at the end (rollback)."""
    connection = get_connection()
    yield connection
    connection.rollback()
    connection.close()


def test_game_is_checked_once_and_price_never_overwritten(conn):
    conn.execute("INSERT INTO games (app_id, name) VALUES (900001, 'Fake Game One')")
    assert 900001 in games_to_check(conn)

    save_details(conn, 900001, parse_app_details(PAID_ON_SALE), datetime.date(2026, 1, 1))
    assert 900001 not in games_to_check(conn)  # already checked: not queried again

    # Even if called again with another price, the first record stays
    other_price = {**PAID_ON_SALE, "data": {**PAID_ON_SALE["data"],
                   "price_overview": {"currency": "BRL", "initial": 100, "final": 100, "discount_percent": 0}}}
    save_details(conn, 900001, parse_app_details(other_price), datetime.date(2026, 2, 1))
    row = conn.execute(
        "SELECT list_price_brl, price_recorded_at FROM games WHERE app_id = 900001"
    ).fetchone()
    assert row == (Decimal("99.90"), datetime.date(2026, 1, 1))
