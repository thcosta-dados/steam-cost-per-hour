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
        # "require" for Supabase: TLS on, but the server certificate is not verified
        # (that would be "verify-full" with Supabase's root CA, as the Power BI tunnel does).
        # Missing or empty = "prefer": TLS only if the server offers it, and local Docker does not.
        sslmode=os.environ.get("POSTGRES_SSLMODE") or "prefer",
    )
