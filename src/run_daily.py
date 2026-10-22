"""Daily pipeline: collect every user, then update the catalog. Usage: python -m src.run_daily"""
import os
import sys

from src.catalog import update_catalog
from src.collect import collect_user, today_in_brazil
from src.db import get_connection


def parse_users(text):
    """Parse STEAM_USERS: "steamid:nickname;steamid:nickname" -> [(steamid, nickname), ...].

    Error messages give the item position, never the SteamID: they may reach public logs.
    """
    users = []
    items = [item.strip() for item in text.split(";") if item.strip()]
    for position, item in enumerate(items, start=1):
        steam_id, _, nickname = item.partition(":")
        steam_id, nickname = steam_id.strip(), nickname.strip()
        if not (steam_id.isdigit() and len(steam_id) == 17) or not nickname:
            raise ValueError(f"STEAM_USERS item {position} must be '<17-digit SteamID>:<nickname>'")
        users.append((steam_id, nickname))
    if not users:
        raise ValueError("STEAM_USERS is empty")
    return users


def run_pipeline(conn, api_key, hash_key, users, today):
    """Run the daily pipeline and record it in pipeline_runs. Returns (run_id, status)."""
    # Committed right away: if the process dies midway, the run stays visible as "running"
    with conn.transaction():
        run_id = conn.execute("INSERT INTO pipeline_runs (status) VALUES ('running') RETURNING run_id").fetchone()[0]

    errors = []  # "nickname: message", never the SteamID
    games_collected = 0
    users_failed = 0
    for steam_id, nickname in users:
        try:
            # One transaction per user: a failure undoes only that user's partial data
            with conn.transaction():
                games = collect_user(conn, api_key, hash_key, steam_id, nickname, today)
            games_collected += games
            print(f"{nickname}: {games} games collected")
        except Exception as error:  # any failure of one user must not stop the others (spec, rule 15)
            users_failed += 1
            errors.append(f"{nickname}: {error}")
            print(f"{nickname}: FAILED ({error})")

    try:
        update_catalog(conn, today)
    except Exception as error:  # the collection above is already saved
        errors.append(f"catalog: {error}")
        print(f"catalog: FAILED ({error})")

    if not errors:
        status = "success"
    elif games_collected > 0:
        status = "partial"  # something failed, but some data was collected
    else:
        status = "failed"
    with conn.transaction():
        conn.execute(
            """UPDATE pipeline_runs
               SET finished_at = now(), status = %s, users_total = %s, users_failed = %s,
                   games_collected = %s, error_message = %s
               WHERE run_id = %s""",
            (status, len(users), users_failed, games_collected, "; ".join(errors) or None, run_id),
        )
    print(f"Run {run_id}: {status} ({len(users)} users, {users_failed} failed, {games_collected} games)")
    return run_id, status


def main():
    users = parse_users(os.environ["STEAM_USERS"])
    with get_connection() as conn:
        _, status = run_pipeline(
            conn, os.environ["STEAM_API_KEY"], os.environ["STEAM_ID_HASH_KEY"], users, today_in_brazil()
        )
    # Any failure, even partial, ends with an error code: GitHub marks the run red and sends the e-mail
    if status != "success":
        sys.exit(1)


if __name__ == "__main__":
    main()
