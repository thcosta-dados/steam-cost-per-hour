"""Run docs/fact_checks.sql and print each fact, to compare with the dashboard (ticket 11b).

Usage: python -m src.fact_checks   (read-only: the session cannot write to the database)
"""
import re
from pathlib import Path

from src.db import get_connection

SQL_FILE = Path(__file__).resolve().parent.parent / "docs" / "fact_checks.sql"
HEADER = re.compile(r"^-- (F\d+ \|.*)$", re.M)


def load_checks(text):
    """Split the file into (title, query) pairs, one per "-- F00 | page | text" header."""
    parts = HEADER.split(text)
    # parts = [preamble, title1, body1, title2, body2, ...]
    return [(title.strip(), body.strip()) for title, body in zip(parts[1::2], parts[2::2])]


def main():
    checks = load_checks(SQL_FILE.read_text(encoding="utf-8"))
    with get_connection() as conn:
        conn.read_only = True
        for title, query in checks:
            with conn.cursor() as cur:
                cur.execute(query)
                columns = [c.name for c in cur.description]
                print(f"\n{title}")
                for row in cur.fetchall():
                    print("   " + " | ".join(f"{c}={v}" for c, v in zip(columns, row)))


if __name__ == "__main__":
    main()
