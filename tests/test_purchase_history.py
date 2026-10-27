"""Purchase history (ticket 08), tested with a fictional page (tests/fixtures/purchase_history_fake.html)."""
import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from src.db import get_connection
from src.purchase_history import load_history, parse_history

PAGE = (Path(__file__).parent / "fixtures" / "purchase_history_fake.html").read_text(encoding="utf-8")
USER = "fake_user_hash"
# Fictional library: app_id -> name
GAMES = {
    900001: "Fake Quest",
    900002: "Fake Racer",
    900003: "Fake Shooter",
    900004: "Fake Battlegrounds",
    900005: "Fake Racer™ 2: Turbo Edition",  # trademark sign, like HITMAN™ 2
}
# Fictional alias: old product name -> game
ALIASES = {"FAKEUNKNOWN'S BATTLEGROUNDS": 900004}


# --- Reading the page -------------------------------------------------------------------

def test_every_row_of_the_page_is_read():
    assert len(parse_history(PAGE)) == 16


def test_row_with_discount_keeps_date_total_original_price_and_percentage():
    row = parse_history(PAGE)[0]
    assert row["date"] == datetime.date(2026, 8, 25)
    assert row["type_text"] == "Purchase"
    assert row["items"] == ["Fake Quest - Bonus Chapter"]
    assert (row["total"], row["original_price"], row["discount_pct"]) == (Decimal("14.00"), Decimal("20.00"), 30)


def test_in_game_purchase_has_the_game_number_from_the_link():
    assert parse_history(PAGE)[1]["app_id"] == 900003


def test_gift_recipient_is_not_read_as_an_item():
    assert parse_history(PAGE)[6]["items"] == ["Fake Quest"]


def test_incomplete_page_is_refused():
    incomplete = PAGE.replace('style="display: none;"', "")  # "Load more" button still visible
    with pytest.raises(ValueError, match="Load more"):
        parse_history(incomplete)


# --- Loading into the database ------------------------------------------------------------

@pytest.fixture
def conn():
    """Fictional user and library in a transaction that is undone at the end (rollback)."""
    connection = get_connection()
    connection.execute("INSERT INTO users (user_id, nickname) VALUES (%s, 'fake_user')", (USER,))
    for app_id, name in GAMES.items():
        connection.execute("INSERT INTO games (app_id, name) VALUES (%s, %s)", (app_id, name))
    yield connection
    connection.rollback()
    connection.close()


def load(conn):
    return load_history(conn, USER, PAGE, GAMES, ALIASES)


def accepted_items(conn):
    rows = conn.execute(
        """SELECT p.purchase_date, p.purchase_type, i.item_name, i.app_id, i.value_brl
           FROM purchases p JOIN purchase_items i USING (purchase_key)
           WHERE p.user_id = %s ORDER BY p.purchase_date, i.item_position""",
        (USER,),
    ).fetchall()
    return rows


def test_accepted_plus_quarantined_rows_equal_the_rows_of_the_page(conn):
    summary = load(conn)
    assert summary == {"rows": 16, "accepted": 7, "quarantined": 9}
    count = lambda table: conn.execute(f"SELECT count(*) FROM {table} WHERE user_id = %s", (USER,)).fetchone()[0]
    assert (count("purchases"), count("quarantine")) == (7, 9)


def test_each_accepted_item_is_linked_to_the_right_game(conn):
    load(conn)
    items = {(name, kind): app_id for _, kind, name, app_id, _ in accepted_items(conn)}
    assert items == {
        ("Fake Quest", "purchase"): 900001,                       # exact name
        ("Fake Racer", "purchase"): 900002,                       # exact name
        ("Fake Racer", "refund"): 900002,                         # refund of the same game
        ("FAKEUNKNOWN'S BATTLEGROUNDS - Worldwide Package", "purchase"): 900004,  # alias
        ("Fake Racer™ 2 - Track Pack A", "purchase"): 900005,     # longest prefix: Fake Racer 2, not Fake Racer
        ("Fake Racer™ 2 - Track Pack B", "purchase"): 900005,     # (trademark sign double-encoded on the page)
        ("Fake Shooter", "in_game"): 900003,                      # game number from the link
        ("Fake Quest - Bonus Chapter", "purchase"): 900001,       # DLC: starts with the game name
    }


def test_single_item_gets_the_row_total_and_several_items_wait_for_the_split(conn):
    load(conn)
    values = {name: value for _, _, name, _, value in accepted_items(conn)}
    assert values["Fake Quest - Bonus Chapter"] == Decimal("14.00")
    assert values["Fake Racer™ 2 - Track Pack A"] is None  # split in ticket 09
    assert values["Fake Racer™ 2 - Track Pack B"] is None


def test_discount_at_purchase_time_is_stored(conn):
    load(conn)
    row = conn.execute(
        "SELECT total_brl, original_price_brl, discount_pct FROM purchases WHERE user_id = %s AND purchase_date = '2026-08-25'",
        (USER,),
    ).fetchone()
    assert row == (Decimal("14.00"), Decimal("20.00"), 30)


def test_every_quarantined_row_has_the_right_reason(conn):
    load(conn)
    reasons = [r[0] for r in conn.execute(
        "SELECT reason FROM quarantine WHERE user_id = %s ORDER BY row_date DESC, quarantine_key", (USER,)
    )]
    assert all(reasons)
    joined = " | ".join(reasons)
    for expected in ["Product not linked to a game of the library: Unknown Indie Game",
                     "Wallet credit", "Gift sent to another person", "Community Market",
                     "Currency other than BRL", "Unknown transaction type: Subscription"]:
        assert expected in joined, expected
    assert sum("Community Market" in r for r in reasons) == 3  # the two identical rows are both kept
    assert sum("Wallet credit" in r for r in reasons) == 2     # wallet credit purchase + gift card


def test_loading_marks_the_user_as_having_the_complete_history(conn):
    marked = lambda: conn.execute(
        "SELECT purchase_history_loaded_at IS NOT NULL FROM users WHERE user_id = %s", (USER,)
    ).fetchone()[0]
    assert marked() is False
    load(conn)
    assert marked() is True  # rule 24 applies from now on (the loader refuses incomplete pages)


def test_loading_the_same_page_twice_does_not_duplicate(conn):
    load(conn)
    assert load(conn) == {"rows": 16, "accepted": 7, "quarantined": 9}
    count = lambda table: conn.execute(f"SELECT count(*) FROM {table} WHERE user_id = %s", (USER,)).fetchone()[0]
    assert (count("purchases"), count("quarantine")) == (7, 9)


def test_payment_method_recipient_wallet_balance_and_transaction_id_are_not_stored(conn):
    load(conn)
    stored = " ".join(str(v) for row in conn.execute(
        """SELECT p.*, i.* FROM purchases p JOIN purchase_items i USING (purchase_key) WHERE p.user_id = %s""", (USER,)
    ) for v in row)
    stored += " ".join(str(v) for row in conn.execute("SELECT * FROM quarantine WHERE user_id = %s", (USER,)) for v in row)
    for secret in ["Visa", "friendname", "76561190000000999", "312,27", "9000000000000000001"]:
        assert secret not in stored, secret
