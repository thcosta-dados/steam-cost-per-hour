"""Create the project tables. Usage: python -m src.create_tables"""
from pathlib import Path

from src.db import get_connection

SCHEMA_FILE = Path(__file__).parent.parent / "sql" / "schema.sql"


def main():
    with get_connection() as conn:
        conn.execute(SCHEMA_FILE.read_text(encoding="utf-8"))
    print("Tables created (or already existed).")


if __name__ == "__main__":
    main()
