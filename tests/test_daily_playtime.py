"""Hours per day (views daily_playtime and collection_quarantine), tested with a fictional history.

Collections on days 1, 2 and 4: day 3 has no collection on purpose (missing day).
A snapshot taken on day N (at 03:17) covers the play of day N-1, so hours are labeled N-1.
"""
import datetime

import pytest

from src.db import get_connection

USER = "fake_user_hash"
D1, D2, D4 = datetime.date(2026, 1, 1), datetime.date(2026, 1, 2), datetime.date(2026, 1, 4)
PLAY_D1, PLAY_D3 = datetime.date(2026, 1, 1), datetime.date(2026, 1, 3)

# app_id, name, genres, minutes per collection day (None = not in the library yet)
FAKE_HISTORY = [
    (900001, "Normal",   ["Action"],    {D1: 100, D2: 160, D4: 220}),
    (900002, "New",      ["Action"],    {D2: 30, D4: 30}),
    (900003, "Decrease", ["Action"],    {D1: 600, D2: 540, D4: 545}),
    (900004, "Software", ["Utilities"], {D1: 0, D2: 50}),
]


@pytest.fixture
def conn():
    """Fictional history inserted in a transaction that is undone at the end (rollback)."""
    connection = get_connection()
    connection.execute("INSERT INTO users (user_id, nickname) VALUES (%s, 'fake_user')", (USER,))
    for app_id, name, genres, minutes_by_day in FAKE_HISTORY:
        connection.execute("INSERT INTO games (app_id, name, store_genres) VALUES (%s, %s, %s)", (app_id, name, genres))
        connection.execute(
            "INSERT INTO library (user_id, app_id, first_seen_date, has_license) VALUES (%s, %s, %s, true)",
            (USER, app_id, min(minutes_by_day)),
        )
        for day, minutes in minutes_by_day.items():
            connection.execute("INSERT INTO playtime_snapshots VALUES (%s, %s, %s, %s)", (USER, app_id, day, minutes))
    yield connection
    connection.rollback()
    connection.close()


def daily(conn, name):
    return conn.execute(
        """SELECT play_date, minutes_played, days_covered FROM daily_playtime
           WHERE user_id = %s AND name = %s ORDER BY play_date""",
        (USER, name),
    ).fetchall()


def test_normal_day_is_the_difference_between_snapshots(conn):
    # 100 -> 160 = 60 min, labeled day 1; 160 -> 220 = 60 min over the missing day (see below)
    assert daily(conn, "Normal")[0] == (PLAY_D1, 60, 1)


def test_missing_collection_day_goes_to_the_last_day_with_days_covered(conn):
    # No collection on day 3: the day-4 snapshot covers 2 days, all attributed to play day 3
    assert daily(conn, "Normal")[1] == (PLAY_D3, 60, 2)


def test_new_game_counts_from_zero_when_the_user_had_a_previous_collection(conn):
    # Not in the library on day 1 (0 min), 30 min on day 2; no change afterwards (no row)
    assert daily(conn, "New") == [(PLAY_D1, 30, 1)]


def test_first_collection_of_the_user_has_no_hours(conn):
    # Day 1 is the first collection ever: nothing to compare with, so no row is labeled day 0
    assert conn.execute(
        "SELECT count(*) FROM daily_playtime WHERE user_id = %s AND play_date < %s", (USER, PLAY_D1)
    ).fetchone()[0] == 0


def test_decrease_goes_to_quarantine_with_reason_and_never_negative(conn):
    # 600 -> 540 is excluded from the hours; 540 -> 545 counts as 5 min
    assert daily(conn, "Decrease") == [(PLAY_D3, 5, 2)]
    quarantine = conn.execute(
        """SELECT origin, snapshot_date, previous_minutes, minutes, reason FROM collection_quarantine
           WHERE user_id = %s""",
        (USER,),
    ).fetchall()
    assert len(quarantine) == 1
    origin, snapshot_date, previous_minutes, minutes, reason = quarantine[0]
    assert (origin, snapshot_date, previous_minutes, minutes) == ("collection", D2, 600, 540)
    assert "600" in reason and "540" in reason


def test_software_is_out_of_hours_per_day(conn):
    assert daily(conn, "Software") == []
