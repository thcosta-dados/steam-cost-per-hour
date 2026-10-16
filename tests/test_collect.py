import datetime

import pytest

from src.collect import hash_steam_id, save_collection
from src.db import get_connection

# Fictional SteamID, keys and games: tests never use real data.
FAKE_STEAM_ID = "76561190000000001"
FAKE_GAMES = [  # same format as the Steam API response
    {"appid": 900001, "name": "Fake Game One", "playtime_forever": 120},
    {"appid": 900002, "name": "Fake Game Two", "playtime_forever": 0},
]


@pytest.fixture
def conn():
    """Database connection that undoes everything at the end (rollback):
    the fake data never mixes with the real data."""
    connection = get_connection()
    yield connection
    connection.rollback()
    connection.close()


def test_hash_does_not_contain_the_steam_id():
    user_id = hash_steam_id(FAKE_STEAM_ID, "secret-key")
    assert FAKE_STEAM_ID not in user_id
    assert len(user_id) == 64  # SHA-256 in hexadecimal


def test_same_steam_id_always_gives_same_hash():
    assert hash_steam_id(FAKE_STEAM_ID, "secret-key") == hash_steam_id(FAKE_STEAM_ID, "secret-key")


def test_different_secret_key_gives_different_hash():
    assert hash_steam_id(FAKE_STEAM_ID, "secret-key") != hash_steam_id(FAKE_STEAM_ID, "other-key")


def test_running_twice_same_day_keeps_one_snapshot_per_game(conn):
    day = datetime.date(2026, 1, 1)
    user_id = hash_steam_id(FAKE_STEAM_ID, "secret-key")

    save_collection(conn, user_id, "fake_user", FAKE_GAMES, day)
    # Second run on the same day: game one was played 30 more minutes
    played_more = [{**FAKE_GAMES[0], "playtime_forever": 150}, FAKE_GAMES[1]]
    save_collection(conn, user_id, "fake_user", played_more, day)

    rows = conn.execute(
        "SELECT app_id, minutes_played FROM playtime_snapshots"
        " WHERE user_id = %s AND snapshot_date = %s ORDER BY app_id",
        (user_id, day),
    ).fetchall()
    assert rows == [(900001, 150), (900002, 0)]  # one row per game, latest value
