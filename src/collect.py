"""Collect the Steam library and playtime of one user. Run for all users by src.run_daily."""
import hashlib
import hmac
from datetime import datetime
from zoneinfo import ZoneInfo

from src.steam_api import get_owned_games


def hash_steam_id(steam_id, secret_key):
    """Anonymous user code: HMAC-SHA256 of the SteamID.

    A plain SHA-256 is not enough: SteamIDs fall in a known range, so anyone
    with the database could hash every possible SteamID until one matches.
    With a secret key (kept only in .env), that guessing is not possible.
    """
    return hmac.new(secret_key.encode(), steam_id.encode(), hashlib.sha256).hexdigest()


def save_collection(conn, user_id, nickname, games, licensed_app_ids, snapshot_date):
    """Save one collection: user, games, library and the day's snapshot.

    `games` uses the Steam API format: {"appid", "name", "playtime_forever"}.
    `licensed_app_ids`: games the user has a license for; the others are played for free.
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
        # Library: keep the date the game first appeared; the license status can change
        cur.executemany(
            """INSERT INTO library (user_id, app_id, first_seen_date, has_license) VALUES (%s, %s, %s, %s)
               ON CONFLICT (user_id, app_id) DO UPDATE SET has_license = EXCLUDED.has_license""",
            [(user_id, g["appid"], snapshot_date, g["appid"] in licensed_app_ids) for g in games],
        )
        # Removed games (rule 14): missing from today's response -> removed; back again -> not removed.
        # Only reached when the API answered normally (a private profile raises an error before),
        # so a failure never marks the whole library as removed. History stays untouched.
        cur.execute(
            "UPDATE library SET is_removed = NOT (app_id = ANY(%s)) WHERE user_id = %s",
            ([g["appid"] for g in games], user_id),
        )
        # Snapshot: one row per user, game and day; a second run that day keeps the latest value
        cur.executemany(
            """INSERT INTO playtime_snapshots (user_id, app_id, snapshot_date, minutes_played)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (user_id, app_id, snapshot_date)
               DO UPDATE SET minutes_played = EXCLUDED.minutes_played""",
            [(user_id, g["appid"], snapshot_date, g["playtime_forever"]) for g in games],
        )


def today_in_brazil():
    """Brazil's date, not the server's (GitHub Actions runs in UTC)."""
    return datetime.now(ZoneInfo("America/Sao_Paulo")).date()


def collect_user(conn, api_key, hash_key, steam_id, nickname, snapshot_date):
    """Collect one user's library and playtime. Returns the number of games.

    Two queries: all games (with free ones played) and only licensed games.
    A game in the first list but not in the second is played without a license.
    """
    games = get_owned_games(api_key, steam_id, include_played_free_games=True)
    licensed_app_ids = {g["appid"] for g in get_owned_games(api_key, steam_id, include_played_free_games=False)}
    save_collection(conn, hash_steam_id(steam_id, hash_key), nickname, games, licensed_app_ids, snapshot_date)
    return len(games)
