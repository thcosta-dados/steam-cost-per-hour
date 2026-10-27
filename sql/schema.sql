-- Tables of the project (model in docs/spec.md).
-- IF NOT EXISTS: safe to run again, and the same script creates the tables
-- in the local database and in Supabase.

CREATE TABLE IF NOT EXISTS users (
    user_id    TEXT PRIMARY KEY,  -- HMAC-SHA256 of the SteamID, never the SteamID itself
    nickname   TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Store columns are filled once by the catalog (src/catalog.py), raw as the store returns them.
-- Migration (ticket 08b): column added to a table that already has data in Supabase.
-- ADD COLUMN IF NOT EXISTS keeps the data and does nothing when the column is already there.
-- Set when the user loads the complete purchase history: enables rule 24 (spec).
ALTER TABLE users ADD COLUMN IF NOT EXISTS purchase_history_loaded_at TIMESTAMPTZ;

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

-- Purchase history (ticket 08), loaded from the page saved by the user (src/load_purchases.py).
-- purchase_key: SHA-256 "fingerprint" of the row (Steam transaction id, or the row content):
-- loading the same file twice never duplicates a purchase. The transaction id itself is not stored.
CREATE TABLE IF NOT EXISTS purchases (
    purchase_key       TEXT PRIMARY KEY,
    user_id            TEXT NOT NULL REFERENCES users (user_id),
    purchase_date      DATE NOT NULL,
    purchase_type      TEXT NOT NULL CHECK (purchase_type IN ('purchase', 'in_game', 'refund')),
    total_brl          NUMERIC(10, 2) NOT NULL CHECK (total_brl >= 0),
    original_price_brl NUMERIC(10, 2),  -- price at purchase time, before the discount (when there was one)
    discount_pct       INTEGER CHECK (discount_pct BETWEEN 0 AND 100)
);
-- Migration (ticket 09): a refund points to the purchase it cancels (spec, rule 5)
ALTER TABLE purchases ADD COLUMN IF NOT EXISTS refunded_purchase_key TEXT;

-- Items of each purchase, each one linked to a game of the library (spec, rule 22).
CREATE TABLE IF NOT EXISTS purchase_items (
    purchase_key  TEXT    NOT NULL REFERENCES purchases (purchase_key),
    item_position INTEGER NOT NULL,           -- order of the item in the row
    item_name     TEXT    NOT NULL,           -- product name as shown by Steam
    app_id        INTEGER NOT NULL REFERENCES games (app_id),
    value_brl     NUMERIC(10, 2),             -- share of the row total (rule 4)
    PRIMARY KEY (purchase_key, item_position)
);

-- Rows rejected on load, with the reason (spec, rules 7 and 8). Nothing is dropped silently.
-- original_content never includes payment method, wallet balance or gift recipient.
CREATE TABLE IF NOT EXISTS quarantine (
    quarantine_key   TEXT PRIMARY KEY,        -- same fingerprint as purchase_key
    user_id          TEXT NOT NULL REFERENCES users (user_id),
    origin           TEXT NOT NULL CHECK (origin IN ('purchase_history', 'licenses')),
    row_date         DATE,
    original_content TEXT NOT NULL,
    reason           TEXT NOT NULL CHECK (reason <> ''),
    loaded_at        TIMESTAMPTZ NOT NULL DEFAULT now()
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
ALTER TABLE purchases ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchase_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE quarantine ENABLE ROW LEVEL SECURITY;

-- Views (analysis layer) are in sql/views.sql.
