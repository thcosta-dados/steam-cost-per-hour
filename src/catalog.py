"""Fill the catalog with store data, once per game. Usage: python -m src.catalog"""
import time
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from src.db import get_connection
from src.steam_store import get_app_details

# Pause between store requests: the store blocks clients that ask too fast
REQUEST_INTERVAL_SECONDS = 1.5


def parse_app_details(raw):
    """Turn a raw store response into the catalog columns."""
    if not raw.get("success"):
        # No store page (test servers, removed items): nothing to record
        return {"store_type": None, "store_genres": [], "list_price_brl": None,
                "header_image_url": None, "is_free": None}

    data = raw["data"]
    price = data.get("price_overview")
    # "initial" is the full price in cents, before any discount ("final" is the sale price).
    # Decimal, not float: money must be exact.
    if price and price["currency"] == "BRL":
        list_price = Decimal(price["initial"]) / 100
    else:
        list_price = None  # not on sale, free, or another currency
    return {
        "store_type": data.get("type"),
        "store_genres": [g["description"] for g in data.get("genres", [])],
        "list_price_brl": list_price,
        "header_image_url": data.get("header_image"),
        "is_free": data.get("is_free"),
    }


def games_to_check(conn):
    """Games never checked in the store."""
    rows = conn.execute("SELECT app_id FROM games WHERE price_recorded_at IS NULL ORDER BY app_id")
    return [row[0] for row in rows]


def save_details(conn, app_id, details, recorded_at):
    # "price_recorded_at IS NULL": a recorded price is never overwritten (spec, rule 3)
    conn.execute(
        """UPDATE games
           SET store_type = %(store_type)s, store_genres = %(store_genres)s,
               list_price_brl = %(list_price_brl)s, header_image_url = %(header_image_url)s,
               is_free = %(is_free)s, price_recorded_at = %(recorded_at)s
           WHERE app_id = %(app_id)s AND price_recorded_at IS NULL""",
        {**details, "app_id": app_id, "recorded_at": recorded_at},
    )


def update_catalog(conn, recorded_at):
    """Check every new game in the store, once. Returns the number of games checked."""
    with conn.transaction():
        app_ids = games_to_check(conn)
    print(f"{len(app_ids)} games to check in the store.")
    for app_id in app_ids:
        details = parse_app_details(get_app_details(app_id))
        # Each game in its own transaction: progress is kept if a later request fails
        with conn.transaction():
            save_details(conn, app_id, details, recorded_at)
        time.sleep(REQUEST_INTERVAL_SECONDS)
    return len(app_ids)


def main():
    today = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    with get_connection() as conn:
        update_catalog(conn, today)

        # Games without a list price: input for the open question on games no longer sold
        without_price = conn.execute(
            """SELECT g.name, c.item_category FROM games g JOIN games_classified c USING (app_id)
               WHERE g.list_price_brl IS NULL AND g.is_free IS NOT TRUE ORDER BY c.item_category, g.name"""
        ).fetchall()
    print(f"{len(without_price)} games without a list price:")
    for name, category in without_price:
        print(f"  [{category}] {name}")


if __name__ == "__main__":
    main()
