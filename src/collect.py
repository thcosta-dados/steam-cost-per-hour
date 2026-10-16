"""Collect the Steam library and playtime. Usage: python -m src.collect"""
import hashlib
import hmac
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from src.db import get_connection
from src.steam_api import get_owned_games


def hash_steam_id(steam_id, secret_key):
    """Anonymous user code: HMAC-SHA256 of the SteamID.

    A plain SHA-256 is not enough: SteamIDs fall in a known range, so anyone
    with the database could hash every possible SteamID until one matches.
    With a secret key (kept only in .env), that guessing is not possible.
    """
    return hmac.new(secret_key.encode(), steam_id.encode(), hashlib.sha256).hexdigest()


def save_collection(conn, user_id, nickname, games, snapshot_date):
    """Save one collection: user, games, library and the day's snapshot.

    `games` uses the Steam API format: {"appid", "name", "playtime_forever"}.
    Does not commit: the caller decides (all or nothing).
    """
    with conn.cursor() as cur:
        # Same user again: keep it, only refresh the nickname
        cur.execute(
            """INSERT INTO users (user_id, nickname) VALUES (%s, %s)
               ON CONFLICT (user_id) DO UPDATE SET nickname = EXCLUDED.nickname""",
            (user_id, nickname),
        )
        # Catalog: each game is registered once and never overwritten
        cur.executemany(
            """INSERT INTO games (app_id, name) VALUES (%s, %s)
               ON CONFLICT (app_id) DO NOTHING""",
            [(g["appid"], g["name"]) for g in games],
        )
        # Library: keep the date the game first appeared
        cur.executemany(
            """INSERT INTO library (user_id, app_id, first_seen_date) VALUES (%s, %s, %s)
               ON CONFLICT (user_id, app_id) DO NOTHING""",
            [(user_id, g["appid"], snapshot_date) for g in games],
        )
        # Snapshot: one row per user, game and day; a second run that day keeps the latest value
        cur.executemany(
            """INSERT INTO playtime_snapshots (user_id, app_id, snapshot_date, minutes_played)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (user_id, app_id, snapshot_date)
               DO UPDATE SET minutes_played = EXCLUDED.minutes_played""",
            [(user_id, g["appid"], snapshot_date, g["playtime_forever"]) for g in games],
        )


def main():
    steam_id = os.environ["STEAM_ID"]
    user_id = hash_steam_id(steam_id, os.environ["STEAM_ID_HASH_KEY"])
    nickname = os.environ["STEAM_NICKNAME"]

    games = get_owned_games(os.environ["STEAM_API_KEY"], steam_id)
    # Brazil's date, not the server's (GitHub Actions runs in UTC)
    today = datetime.now(ZoneInfo("America/Sao_Paulo")).date()

    # The connection block commits only if everything works (all or nothing)
    with get_connection() as conn:
        save_collection(conn, user_id, nickname, games, today)
    print(f"{len(games)} games collected for {nickname} on {today}.")


if __name__ == "__main__":
    main()
