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
        # "verify-full" for Supabase: the server certificate chain must lead to Supabase's root CA
        # (PGSSLROOTCERT, read by libpq) and the certificate must carry the host name, as the Power BI tunnel checks.
        # Missing or empty = "prefer": TLS only if the server offers it, and local Docker does not.
        sslmode=os.environ.get("POSTGRES_SSLMODE") or "prefer",
    )
