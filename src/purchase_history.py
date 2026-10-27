"""Load the Steam purchase history page saved by the user (ticket 08).

Usage (the file never leaves the computer):
    python -m src.purchase_history data/private/purchase_history.html --user <nickname>
"""
import argparse
import collections
import csv
import hashlib
import html
import os
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from bs4 import BeautifulSoup

ALIASES_FILE = Path(__file__).parent.parent / "data" / "product_aliases.csv"
ACCEPTED_TYPES = {"Purchase": "purchase", "In-Game Purchase": "in_game", "Refund": "refund"}


# --- 1. Reading the page --------------------------------------------------------------------

def clean_text(text):
    """Visible text: HTML entities decoded (the page double-encodes some, like &amp;trade;),
    non-breaking spaces turned into spaces and spaces collapsed. Signs like ™ are kept."""
    return re.sub(r"\s+", " ", html.unescape(text).replace("\xa0", " ")).strip()


def parse_money(text):
    """'R$ 1.234,56' -> Decimal('1234.56'); anything not in reais -> None."""
    match = re.match(r"R\$\s*([\d.]+,\d{2})", text)
    return Decimal(match.group(1).replace(".", "").replace(",", ".")) if match else None


def parse_history(page):
    """Return one dict per row of the history table, newest first (as on the page)."""
    soup = BeautifulSoup(page, "html.parser")
    button = soup.find(id="load_more_button")
    if button is not None and "display:none" not in (button.get("style") or "").replace(" ", ""):
        raise ValueError("Incomplete page: click 'Load more' until the button disappears "
                         "and save it as 'Webpage, Complete'")

    rows = []
    for tr in soup.select("tr.wallet_table_row"):
        cell = lambda name: tr.find("td", class_=name)
        link = tr.get("onclick", "")

        items = []
        items_cell = cell("wht_items")
        for div in items_cell.find_all("div", recursive=False):
            text = clean_text(div.get_text(" "))
            classes = div.get("class") or []
            if text.lower() == "gift sent to":
                break  # what follows is the recipient's name: never read
            if text and "wth_payment" not in classes and "wth_item_refunded" not in classes:
                items.append(text)
        if not items:
            # Some rows (wallet credit, gift card, Market) have the text directly in the cell, without <div>
            direct_text = clean_text(" ".join(items_cell.find_all(string=True, recursive=False)))
            if direct_text:
                items.append(direct_text)

        type_div = cell("wht_type").find("div")
        date_text = clean_text(cell("wht_date").get_text())
        try:
            date = datetime.strptime(date_text, "%d %b, %Y").date()
        except ValueError:
            date = None

        total_text = clean_text(cell("wht_total").get_text(" "))
        original_price, discount_pct = None, None
        discounted = cell("wht_base_price").find("div", class_="wht_base_price_discounted")
        if discounted is not None:
            original_price = parse_money(clean_text(discounted.find(class_="wht_original_price").get_text()))
            discount_pct = int(re.sub(r"\D", "", discounted.find(class_="wht_discount_pct").get_text()))

        transaction = re.search(r"transid=(\d+)", link)
        app = re.search(r"appid=(\d+)", link)
        rows.append({
            "date": date,
            "date_text": date_text,
            "type_text": clean_text(type_div.get_text()) if type_div else "",
            "items": items,
            "total": parse_money(total_text),
            "total_text": total_text,
            "original_price": original_price,
            "discount_pct": discount_pct,
            "app_id": int(app.group(1)) if app else None,
            "transaction_id": transaction.group(1) if transaction else None,
        })
    if not rows:
        raise ValueError("No history rows found: is this the Steam purchase history page?")
    return rows


# --- 2. Linking items to games (spec, rule 22) ------------------------------------------------

def normalize(name):
    """Name for comparison: no trademark signs, lowercase, single spaces."""
    return clean_text(html.unescape(name).replace("™", "").replace("®", "")).lower()


def build_name_index(games, aliases):
    """Normalized name -> app_id, from game names, public aliases and short names.

    Short name: the part before ':' or ' - ' (e.g. 'Dying Light 2' from 'Dying Light 2: Reloaded
    Edition'), only with 2+ words so it is not too generic. A name shared by two games is ambiguous
    and left out (None).
    """
    index = {}

    def add(name, app_id, overwrite):
        key = normalize(name)
        if key in index and index[key] != app_id and not overwrite:
            index[key] = None  # ambiguous
        elif key not in index or overwrite:
            index[key] = app_id

    for app_id, name in games.items():
        add(name, app_id, overwrite=False)
    for alias, app_id in aliases.items():
        add(alias, app_id, overwrite=True)  # an explicit alias wins
    for app_id, name in games.items():
        short = re.split(r":| - ", name)[0]
        if short != name and len(short.split()) >= 2 and normalize(short) not in index:
            add(short, app_id, overwrite=False)
    return index


def identify(item, index):
    """app_id of the game the product belongs to: exact name, else the longest name it starts with."""
    key = normalize(item)
    if index.get(key):
        return index[key]
    best = None
    for name, app_id in index.items():
        # Prefix followed by a separator (space, ':', '-', '('), so 'Fake Racer' never matches 'Fake Racers'
        if app_id and key.startswith(name) and len(key) > len(name) and not key[len(name)].isalnum():
            if best is None or len(name) > len(best[0]):
                best = (name, app_id)
    return best[1] if best else None


# --- 2b. Splitting a row with several items (spec, rule 4) -----------------------------------

def split_total(total, weights):
    """Split a total proportionally to the weights, summing exactly to the total.

    Works in whole cents with the largest remainder method: every part is rounded down, and the
    cents left over go to the parts with the largest remainders. Weights all zero: equal parts.
    """
    cents = int(total * 100)
    if sum(weights) == 0:
        weights = [1] * len(weights)
    exact = [Decimal(cents) * Decimal(w) / Decimal(sum(weights)) for w in weights]
    parts = [int(x) for x in exact]  # rounded down
    leftover = cents - sum(parts)
    by_remainder = sorted(range(len(parts)), key=lambda i: exact[i] - parts[i], reverse=True)
    for i in by_remainder[:leftover]:
        parts[i] += 1
    return [Decimal(p) / 100 for p in parts]


def item_values(total, app_ids, prices):
    """Value of each item of a row: split between games by list price, then equally between the
    items of the same game. A free game has price 0 (gets nothing); any game without a list price
    makes the split between games equal."""
    games = list(dict.fromkeys(app_ids))  # distinct games, in order
    if any(prices.get(game) is None for game in games):
        game_parts = split_total(total, [1] * len(games))
    else:
        game_parts = split_total(total, [prices[game] for game in games])
    values = [None] * len(app_ids)
    for game, game_part in zip(games, game_parts):
        positions = [i for i, app_id in enumerate(app_ids) if app_id == game]
        for position, value in zip(positions, split_total(game_part, [1] * len(positions))):
            values[position] = value
    return values


# --- 3. Accepted or quarantined -------------------------------------------------------------

def classify(row, index, games):
    """Return (purchase_type, app_ids per item, None) for an accepted row, or (None, None, reason)."""
    kind = row["type_text"]
    if re.fullmatch(r"(\d+ )?Market Transactions?", kind):
        return None, None, "Community Market transaction: not spending on a game"
    if kind == "Gift Purchase":
        return None, None, "Gift sent to another person: not spending on the user's own library"
    if any(re.search(r"wallet credit|gift card", item, re.I) for item in row["items"]):
        return None, None, "Wallet credit: money only counts when it is spent on a game"
    if kind not in ACCEPTED_TYPES:
        return None, None, f"Unknown transaction type: {kind or '(empty)'}"
    if row["date"] is None:
        return None, None, f"Date in an unknown format: {row['date_text']}"
    if row["total"] is None:
        return None, None, f"Currency other than BRL: {row['total_text'] or '(empty)'}"

    purchase_type = ACCEPTED_TYPES[kind]
    if purchase_type == "in_game":
        if row["app_id"] not in games:
            return None, None, f"In-game purchase of a game not in the library (app {row['app_id']})"
        return purchase_type, [row["app_id"]] * len(row["items"]), None
    app_ids = [identify(item, index) for item in row["items"]]
    missing = [item for item, app_id in zip(row["items"], app_ids) if app_id is None]
    if missing or not app_ids:
        return None, None, f"Product not linked to a game of the library: {'; '.join(missing) or '(no item)'}"
    return purchase_type, app_ids, None


def transaction_key(user_id, transaction_id, type_text):
    """SHA-256 key of a row with a transaction id. The type is part of it because a refund reuses
    the transaction id of the purchase it refunds."""
    return hashlib.sha256(f"{user_id}|transaction|{transaction_id}|{type_text}".encode()).hexdigest()


def fingerprints(user_id, rows):
    """SHA-256 key of each row: from the transaction id and type, or from the row content.

    Identical rows without a transaction id (e.g. two Market sales on the same day) get their order
    of appearance, counted from the oldest row: new rows appear at the top of the page, so the keys
    of old rows never change.
    """
    seen = collections.Counter()
    keys = [None] * len(rows)
    for position in reversed(range(len(rows))):
        row = rows[position]
        if row["transaction_id"]:
            keys[position] = transaction_key(user_id, row["transaction_id"], row["type_text"])
        else:
            content = "|".join([row["date_text"], row["type_text"], ";".join(row["items"]), row["total_text"]])
            seen[content] += 1
            keys[position] = hashlib.sha256(f"{user_id}|row|{content}|{seen[content]}".encode()).hexdigest()
    return keys


# --- 4. Loading -------------------------------------------------------------------------------

def load_history(conn, user_id, page, games, aliases):
    """Load every row: accepted rows to purchases, the others to quarantine. All or nothing."""
    rows = parse_history(page)
    index = build_name_index(games, aliases)
    # List prices to split rows with several items; a free game counts as 0 (rule 4)
    prices = {app_id: (Decimal(0) if is_free else price)
              for app_id, price, is_free in conn.execute("SELECT app_id, list_price_brl, is_free FROM games")}
    # Transactions refunded in the page (a refund reuses the transaction id of its purchase)
    refunded = {row["transaction_id"] for row in rows if row["type_text"] == "Refund" and row["transaction_id"]}
    accepted = quarantined = 0
    # DO UPDATE (not DO NOTHING) on values, links and reasons: loading again applies new rules
    # to rows already stored, still without duplicating anything
    with conn.transaction():
        for row, key in zip(rows, fingerprints(user_id, rows)):
            purchase_type, app_ids, reason = classify(row, index, games)
            if reason and reason.startswith("Product not linked") and row["transaction_id"] in refunded:
                reason = "Refunded purchase: purchase and refund cancel each other (product no longer in the library)"
            if reason:
                content = " | ".join([row["date_text"], row["type_text"] or "(no type)",
                                      "; ".join(row["items"]), row["total_text"] or "(no total)"])
                conn.execute(
                    """INSERT INTO quarantine (quarantine_key, user_id, origin, row_date, original_content, reason)
                       VALUES (%s, %s, 'purchase_history', %s, %s, %s)
                       ON CONFLICT (quarantine_key) DO UPDATE
                       SET original_content = EXCLUDED.original_content, reason = EXCLUDED.reason""",
                    (key, user_id, row["date"], content, reason),
                )
                quarantined += 1
                continue
            # A refund points to the purchase it cancels (rule 5): same transaction id, type Purchase
            refunded_key = (transaction_key(user_id, row["transaction_id"], "Purchase")
                            if purchase_type == "refund" and row["transaction_id"] else None)
            conn.execute(
                """INSERT INTO purchases (purchase_key, user_id, purchase_date, purchase_type, total_brl,
                                          original_price_brl, discount_pct, refunded_purchase_key)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (purchase_key) DO UPDATE SET refunded_purchase_key = EXCLUDED.refunded_purchase_key""",
                (key, user_id, row["date"], purchase_type, row["total"], row["original_price"],
                 row["discount_pct"], refunded_key),
            )
            values = item_values(row["total"], app_ids, prices)
            for position, (item, app_id, value) in enumerate(zip(row["items"], app_ids, values), start=1):
                conn.execute(
                    """INSERT INTO purchase_items (purchase_key, item_position, item_name, app_id, value_brl)
                       VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (purchase_key, item_position) DO UPDATE SET value_brl = EXCLUDED.value_brl""",
                    (key, position, item, app_id, value),
                )
            accepted += 1
        # parse_history refuses incomplete pages, so the user now has the complete history (rule 24)
        conn.execute("UPDATE users SET purchase_history_loaded_at = now() WHERE user_id = %s", (user_id,))
    return {"rows": len(rows), "accepted": accepted, "quarantined": quarantined}


def read_aliases(path=ALIASES_FILE):
    """Public product aliases: old or alternative product name -> app_id."""
    with open(path, encoding="utf-8", newline="") as file:
        return {line["alias"]: int(line["app_id"]) for line in csv.DictReader(file)}


def main():
    # Imported here so the parsing functions above can be tested without these modules
    from src.collect import hash_steam_id
    from src.db import get_connection
    from src.run_daily import parse_users

    parser = argparse.ArgumentParser(description="Load the saved Steam purchase history page.")
    parser.add_argument("page", help="saved page, e.g. data/private/purchase_history.html")
    parser.add_argument("--user", required=True, help="nickname from STEAM_USERS")
    args = parser.parse_args()

    steam_ids = {nickname: steam_id for steam_id, nickname in parse_users(os.environ["STEAM_USERS"])}
    if args.user not in steam_ids:
        raise SystemExit(f"Nickname not found in STEAM_USERS: {args.user}")
    user_id = hash_steam_id(steam_ids[args.user], os.environ["STEAM_ID_HASH_KEY"])
    page = Path(args.page).read_text(encoding="utf-8")

    with get_connection() as conn:
        if conn.execute("SELECT 1 FROM users WHERE user_id = %s", (user_id,)).fetchone() is None:
            raise SystemExit("User not collected yet: run the daily pipeline first")
        games = dict(conn.execute("SELECT app_id, name FROM games"))
        summary = load_history(conn, user_id, page, games, read_aliases())
        reasons = conn.execute(
            """SELECT split_part(reason, ':', 1), count(*) FROM quarantine
               WHERE user_id = %s AND origin = 'purchase_history' GROUP BY 1 ORDER BY 2 DESC""",
            (user_id,),
        ).fetchall()
    print(f"{summary['rows']} rows: {summary['accepted']} accepted, {summary['quarantined']} quarantined")
    for reason, count in reasons:
        print(f"  quarantine | {reason}: {count}")


if __name__ == "__main__":
    main()
