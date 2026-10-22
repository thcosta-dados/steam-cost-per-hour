import datetime

import pytest

from src.collect import hash_steam_id
from src.db import get_connection
from src.run_daily import parse_users, run_pipeline

# Fictional SteamIDs, keys and games: tests never use real data.
FAKE_ID_A = "76561190000000001"
FAKE_ID_B = "76561190000000002"
HASH_KEY = "secret-key"
DAY = datetime.date(2026, 1, 1)
PRIVATE_PROFILE_ERROR = "Steam API returned an empty response: are the profile's game details public?"


def fake_owned_games(api_key, steam_id, include_played_free_games):
    """Stand-in for the Steam API: user A has one game, user B has a private profile."""
    if steam_id == FAKE_ID_B:
        raise RuntimeError(PRIVATE_PROFILE_ERROR)
    return [{"appid": 900001, "name": "Fake Game One", "playtime_forever": 60}]


@pytest.fixture
def conn(monkeypatch):
    # monkeypatch swaps real functions for stand-ins during the test only
    monkeypatch.setattr("src.collect.get_owned_games", fake_owned_games)
    monkeypatch.setattr("src.catalog.get_app_details", lambda app_id: {"success": False})
    monkeypatch.setattr("src.catalog.REQUEST_INTERVAL_SECONDS", 0)

    connection = get_connection()
    # Opens an outer transaction: the pipeline's own transactions become savepoints,
    # so the final rollback undoes everything the test wrote.
    connection.execute("SELECT 1")
    yield connection
    connection.rollback()
    connection.close()


def get_run(conn, run_id):
    return conn.execute(
        """SELECT status, users_total, users_failed, games_collected, error_message, finished_at IS NOT NULL
           FROM pipeline_runs WHERE run_id = %s""",
        (run_id,),
    ).fetchone()


def test_private_profile_fails_only_that_user(conn):
    run_id, status = run_pipeline(conn, "fake-api-key", HASH_KEY, [(FAKE_ID_A, "alice"), (FAKE_ID_B, "bob")], DAY)

    assert status == "partial"
    status, users_total, users_failed, games, error_message, finished = get_run(conn, run_id)
    assert (status, users_total, users_failed, games, finished) == ("partial", 2, 1, 1, True)
    assert "bob" in error_message and FAKE_ID_B not in error_message
    # alice was collected even though bob failed
    alice = hash_steam_id(FAKE_ID_A, HASH_KEY)
    assert conn.execute("SELECT count(*) FROM playtime_snapshots WHERE user_id = %s", (alice,)).fetchone()[0] == 1


def test_run_where_nothing_is_collected_is_failed(conn):
    run_id, status = run_pipeline(conn, "fake-api-key", HASH_KEY, [(FAKE_ID_B, "bob")], DAY)
    assert status == "failed"
    assert get_run(conn, run_id)[:4] == ("failed", 1, 1, 0)


def test_run_without_errors_is_success(conn):
    run_id, status = run_pipeline(conn, "fake-api-key", HASH_KEY, [(FAKE_ID_A, "alice")], DAY)
    assert status == "success"
    assert get_run(conn, run_id)[:5] == ("success", 1, 0, 1, None)


def test_parse_one_user():
    assert parse_users(f"{FAKE_ID_A}:alice") == [(FAKE_ID_A, "alice")]


def test_parse_several_users_ignoring_spaces_and_empty_items():
    users = parse_users(f" {FAKE_ID_A}:alice ; {FAKE_ID_B}:bob ;")
    assert users == [(FAKE_ID_A, "alice"), (FAKE_ID_B, "bob")]


@pytest.mark.parametrize("bad", ["", "alice", f"{FAKE_ID_A}:", "123:alice", f"{FAKE_ID_A}"])
def test_malformed_user_list_is_rejected(bad):
    with pytest.raises(ValueError):
        parse_users(bad)


def test_error_message_never_contains_the_steam_id():
    with pytest.raises(ValueError) as error:
        parse_users(f"{FAKE_ID_A}")  # missing nickname
    assert FAKE_ID_A not in str(error.value)
