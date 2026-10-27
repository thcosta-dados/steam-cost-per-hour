import pytest

from src.backfill_disconnected import minutes_to_add

GAME = {"appid": 900001, "name": "Fake Game One", "playtime_forever": 120, "playtime_disconnected": 30}


def test_game_without_disconnected_time_is_left_alone():
    assert minutes_to_add(120, {**GAME, "playtime_disconnected": 0}) == 0


def test_snapshot_with_online_time_only_gets_the_disconnected_time():
    assert minutes_to_add(120, GAME) == 30


def test_snapshot_already_adjusted_is_left_alone_so_running_twice_is_safe():
    assert minutes_to_add(150, GAME) == 0


def test_any_other_value_stops_everything():
    # e.g. the user played after the last collection: the history cannot be adjusted safely
    with pytest.raises(ValueError, match="Fake Game One"):
        minutes_to_add(100, GAME)
