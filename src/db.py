import os

import psycopg


def get_connection():
    """Open a connection using only environment variables (local or cloud database)."""
    return psycopg.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ["POSTGRES_PORT"],
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        # "require" for the cloud database (encrypted over the internet);
        # missing or empty = "prefer": encryption only when the server offers it (local Docker does not)
        sslmode=os.environ.get("POSTGRES_SSLMODE") or "prefer",
    )
