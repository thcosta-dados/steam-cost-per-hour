"""Create the project tables and views. Usage: python -m src.create_tables"""
from pathlib import Path

from src.db import get_connection

SQL_DIR = Path(__file__).parent.parent / "sql"
# Order matters: the views read the tables
SQL_FILES = ["schema.sql", "views.sql"]


def main():
    with get_connection() as conn:
        for file_name in SQL_FILES:
            conn.execute((SQL_DIR / file_name).read_text(encoding="utf-8"))
    print("Tables and views created (or updated).")


if __name__ == "__main__":
    main()
