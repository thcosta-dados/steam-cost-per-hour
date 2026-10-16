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
    store_genres      TEXT[],               -- store genres, used by the games_classified view
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

-- Classification rule (spec, rule 17). The store marks software and test servers
-- as "game", so the rule uses the genres. A rule in SQL can be fixed without
-- querying the store again.
CREATE OR REPLACE VIEW games_classified AS
SELECT
    app_id,
    name,
    CASE
        WHEN store_genres && ARRAY[  -- && = the two lists share at least one item
            'Utilities', 'Design & Illustration', 'Photo Editing', 'Animation & Modeling',
            'Video Production', 'Audio Production', 'Software Training', 'Web Publishing',
            'Accounting', 'Education', 'Game Development'
        ] THEN 'software'
        WHEN cardinality(store_genres) > 0 THEN 'game'
        ELSE 'other'  -- no genres or no store page: test servers, playtests
    END AS item_category
FROM games;
