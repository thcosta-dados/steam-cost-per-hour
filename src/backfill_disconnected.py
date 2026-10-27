"""One-off data fix (27/10/2026): add disconnected playtime to the existing snapshots.

Until then the collection stored only playtime_forever, while the Steam library shows
playtime_forever + playtime_disconnected (spec, open question 7). Changing only the collection
would make the next snapshot jump and show hours that were never played. So the current
disconnected minutes are added to every past snapshot of each game, assuming they did not
change during the history (they only change when playing offline; Deadlock had 30 min at the
three points measured).

Run right after a collection made with the old code, before playing again:
    python -m src.backfill_disconnected
Safe to run twice: snapshots already adjusted are left alone.
"""
import os

from src.collect import hash_steam_id, library_minutes
from src.db import get_connection
from src.run_daily import parse_users
from src.steam_api import get_owned_games


def minutes_to_add(latest_snapshot_minutes, game):
    """Minutes to add to the game's snapshots, from its latest snapshot and the API today."""
    disconnected = game.get("playtime_disconnected", 0)
    if disconnected == 0 or latest_snapshot_minutes == library_minutes(game):
        return 0  # nothing to add, or already adjusted
    if latest_snapshot_minutes == game["playtime_forever"]:
        return disconnected
    # Played after the last collection (or anything unexpected): the history cannot be adjusted safely
    raise ValueError(
        f"{game['name']}: latest snapshot has {latest_snapshot_minutes} min, API has "
        f"{game['playtime_forever']} online + {disconnected} disconnected. "
        "Run a collection with the old code first, without playing."
    )


def main():
    users = parse_users(os.environ["STEAM_USERS"])
    # One connection block: every adjustment is committed together, or none is
    with get_connection() as conn:
        for steam_id, nickname in users:
            user_id = hash_steam_id(steam_id, os.environ["STEAM_ID_HASH_KEY"])
            games = get_owned_games(os.environ["STEAM_API_KEY"], steam_id, include_played_free_games=True)

            # 1. Plan every game first: an error here stops before anything is written
            plan = []
            for game in games:
                latest = conn.execute(
                    """SELECT minutes_played FROM playtime_snapshots
                       WHERE user_id = %s AND app_id = %s ORDER BY snapshot_date DESC LIMIT 1""",
                    (user_id, game["appid"]),
                ).fetchone()
                if latest is not None:
                    add = minutes_to_add(latest[0], game)
                    if add:
                        plan.append((game["appid"], game["name"], add))

            # 2. Apply: same minutes added to every snapshot of the game, so daily differences do not change
            for app_id, name, add in plan:
                updated = conn.execute(
                    "UPDATE playtime_snapshots SET minutes_played = minutes_played + %s WHERE user_id = %s AND app_id = %s",
                    (add, user_id, app_id),
                ).rowcount
                print(f"{nickname} | {name}: +{add} min in {updated} snapshots")
            print(f"{nickname}: {len(plan)} games adjusted")


if __name__ == "__main__":
    main()
