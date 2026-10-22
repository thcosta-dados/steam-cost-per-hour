-- Tables of the project (model in docs/spec.md).
-- IF NOT EXISTS: safe to run again, and the same script creates the tables
-- in the local database and in Supabase.

CREATE TABLE IF NOT EXISTS users (
    user_id    TEXT PRIMARY KEY,  -- HMAC-SHA256 of the SteamID, never the SteamID itself
    nickname   TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Store columns are filled once by the catalog (src/catalog.py), raw as the store returns them.
CREATE TABLE IF NOT EXISTS games (
    app_id            INTEGER PRIMARY KEY,  -- game id on Steam
    name              TEXT NOT NULL,
    store_type        TEXT,                 -- store "type" (not enough to tell games from software)
    store_genres      TEXT[],               -- store genres, used by the games_classified view (views.sql)
    list_price_brl    NUMERIC(10, 2),       -- full list price, without discount; NULL when not on sale
    price_recorded_at DATE,                 -- date the store was checked (set even when there is no price)
    header_image_url  TEXT,
    is_free           BOOLEAN
);

CREATE TABLE IF NOT EXISTS library (
    user_id         TEXT    NOT NULL REFERENCES users (user_id),
    app_id          INTEGER NOT NULL REFERENCES games (app_id),
    first_seen_date DATE    NOT NULL,
    is_removed      BOOLEAN NOT NULL DEFAULT FALSE,
    -- FALSE = played without a license: "free" for this user (spec, rule 6).
    -- Per user, from the API: the store's is_free is the game's status today, for anyone.
    has_license     BOOLEAN NOT NULL,
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

-- One row per pipeline execution (spec, rule 15). Status: running while it works, then
-- success (no errors), partial (some user or step failed, some data collected) or failed.
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,  -- automatic increasing number
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    status          TEXT NOT NULL CHECK (status IN ('running', 'success', 'partial', 'failed')),
    users_total     INTEGER,
    users_failed    INTEGER,
    games_collected INTEGER,
    error_message   TEXT  -- nicknames only, never SteamIDs
);

-- Row Level Security with no policies: nobody but the table owner can read or write.
-- Supabase publishes every table in "public" through an automatic API; this blocks it.
-- The pipeline and Power BI connect as the owner, which RLS does not restrict.
-- On the local database it changes nothing (same owner), so one script serves both.
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE games ENABLE ROW LEVEL SECURITY;
ALTER TABLE library ENABLE ROW LEVEL SECURITY;
ALTER TABLE playtime_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_runs ENABLE ROW LEVEL SECURITY;

-- Views (analysis layer) are in sql/views.sql.
