-- Tables of the project (model in docs/spec.md).
-- IF NOT EXISTS: safe to run again, and the same script creates the tables
-- in the local database and in Supabase.

CREATE TABLE IF NOT EXISTS users (
    user_id    TEXT PRIMARY KEY,  -- HMAC-SHA256 of the SteamID, never the SteamID itself
    nickname   TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS games (
    app_id            INTEGER PRIMARY KEY,  -- game id on Steam
    name              TEXT NOT NULL,
    list_price_brl    NUMERIC(10, 2),       -- price, image and is_free are filled by the catalog (ticket 03)
    price_recorded_at DATE,
    header_image_url  TEXT,
    is_free           BOOLEAN
);

CREATE TABLE IF NOT EXISTS library (
    user_id         TEXT    NOT NULL REFERENCES users (user_id),
    app_id          INTEGER NOT NULL REFERENCES games (app_id),
    first_seen_date DATE    NOT NULL,
    is_removed      BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (user_id, app_id)
);

-- One row per user, game and day: the primary key blocks duplicates.
CREATE TABLE IF NOT EXISTS playtime_snapshots (
    user_id        TEXT    NOT NULL,
    app_id         INTEGER NOT NULL,
    snapshot_date  DATE    NOT NULL,
    minutes_played INTEGER NOT NULL CHECK (minutes_played >= 0),  -- accumulated total, as returned by the API
    PRIMARY KEY (user_id, app_id, snapshot_date),
    FOREIGN KEY (user_id, app_id) REFERENCES library (user_id, app_id)
);
