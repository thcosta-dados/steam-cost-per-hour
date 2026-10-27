-- Analysis layer: views read by Power BI. Rules from docs/spec.md.
-- CREATE OR REPLACE: safe to run again; each view only adds logic over the tables.
-- security_invoker: a view reads the tables with the permissions of whoever queries it,
-- not of its owner. Without it, Supabase's public API could read the tables through
-- the views, bypassing Row Level Security (schema.sql).

-- Classification rule (spec, rule 17). The store marks software and test servers
-- as "game", so the rule uses the genres. A rule in SQL can be fixed without
-- querying the store again.
CREATE OR REPLACE VIEW games_classified WITH (security_invoker = true) AS
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


-- Cost per hour of each game, one row per user and game (spec, rules 1, 2, 6, 9, 10, 18, 24).
CREATE OR REPLACE VIEW game_costs WITH (security_invoker = true) AS
WITH latest_snapshot AS (
    -- DISTINCT ON keeps the first row of each (user, game) in the ORDER BY: the latest day
    SELECT DISTINCT ON (user_id, app_id) user_id, app_id, snapshot_date, minutes_played
    FROM playtime_snapshots
    ORDER BY user_id, app_id, snapshot_date DESC
),
purchased_games AS (
    -- Games bought at least once (in-game purchases do not buy the game itself)
    SELECT DISTINCT p.user_id, i.app_id
    FROM purchases p
    JOIN purchase_items i USING (purchase_key)
    WHERE p.purchase_type = 'purchase'
),
origins AS (
    SELECT
        l.user_id,
        l.app_id,
        g.name,
        g.header_image_url,
        g.list_price_brl,
        s.snapshot_date,
        s.minutes_played,
        -- Value origin (rule 2). "paid" comes with the paid value (ticket 10).
        CASE
            WHEN NOT l.has_license THEN 'free'              -- played without a license (rule 6)
            -- Complete history loaded and no purchase of the game: gift, complimentary or
            -- promotion, nothing paid on Steam (rule 24). LEFT JOIN below: no match = no purchase.
            WHEN u.purchase_history_loaded_at IS NOT NULL AND pg.app_id IS NULL THEN 'no_purchase'
            WHEN g.list_price_brl IS NOT NULL THEN 'estimated'
            ELSE 'unknown'                                  -- licensed, no store price (rule 18)
        END AS value_origin
    FROM library l
    JOIN users u USING (user_id)
    JOIN games g USING (app_id)
    JOIN games_classified c USING (app_id)
    -- Inner join: every library row has a snapshot (both are saved in the same transaction)
    JOIN latest_snapshot s USING (user_id, app_id)
    LEFT JOIN purchased_games pg ON pg.user_id = l.user_id AND pg.app_id = l.app_id
    WHERE c.item_category = 'game'  -- software and other items are out of metrics (rule 17)
),
valued AS (
    SELECT
        o.*,
        -- NULL (not 0) for unknown value: sums ignore it instead of counting it as free
        CASE o.value_origin
            WHEN 'free' THEN 0
            WHEN 'no_purchase' THEN 0
            WHEN 'estimated' THEN o.list_price_brl
        END AS game_value_brl
    FROM origins o
)
SELECT
    v.user_id,
    u.nickname,
    v.app_id,
    v.name,
    v.header_image_url,
    v.snapshot_date AS last_snapshot_date,
    v.minutes_played,
    round(v.minutes_played / 60.0, 2) AS hours_played,
    v.value_origin,
    v.game_value_brl,
    -- From minutes, not rounded hours, to avoid rounding errors; only with hours and a known value
    CASE
        WHEN v.minutes_played > 0 AND v.game_value_brl IS NOT NULL
        THEN v.game_value_brl * 60 / v.minutes_played
    END AS cost_per_hour_brl,
    CASE
        WHEN v.minutes_played = 0 THEN 'not_played'      -- money parked (rule 9)
        WHEN v.minutes_played < 60 THEN 'barely_started' -- out of the main ranking (rule 10)
        ELSE 'played'
    END AS hours_group
FROM valued v
JOIN users u USING (user_id);


-- Minutes played between each snapshot and the previous one (spec, rules 11 to 13).
-- Shared by daily_playtime (increases) and collection_quarantine (decreases).
CREATE OR REPLACE VIEW snapshot_intervals WITH (security_invoker = true) AS
WITH user_collections AS (
    -- Previous collection of the user (any game): tells a new game from the first collection ever
    SELECT user_id, snapshot_date,
           LAG(snapshot_date) OVER (PARTITION BY user_id ORDER BY snapshot_date) AS previous_collection_date
    FROM (SELECT DISTINCT user_id, snapshot_date FROM playtime_snapshots) AS days
),
with_previous AS (
    -- LAG looks at the previous row of the same user and game
    SELECT s.user_id, s.app_id, s.snapshot_date, s.minutes_played,
           LAG(s.snapshot_date) OVER w AS previous_game_date,
           LAG(s.minutes_played) OVER w AS previous_game_minutes,
           c.previous_collection_date
    FROM playtime_snapshots s
    JOIN user_collections c USING (user_id, snapshot_date)
    WINDOW w AS (PARTITION BY s.user_id, s.app_id ORDER BY s.snapshot_date)
)
SELECT
    user_id,
    app_id,
    snapshot_date,
    -- Game seen before: compare with its own previous snapshot.
    -- New game: it was not in the previous collection, so it had 0 minutes then (rule 12).
    coalesce(previous_game_date, previous_collection_date) AS previous_snapshot_date,
    coalesce(previous_game_minutes, 0) AS previous_minutes,
    minutes_played AS minutes,
    minutes_played - coalesce(previous_game_minutes, 0) AS minutes_difference
FROM with_previous
-- First collection ever of the user: nothing to compare with, so no interval
WHERE coalesce(previous_game_date, previous_collection_date) IS NOT NULL;


-- Hours played per day and game, games only (rules 11, 12 and 17).
-- The collection runs in the morning (scheduled at 03:17, usually started by GitHub between
-- 08:00 and 10:00), so a snapshot taken on day N covers the play of day N-1: a "play day"
-- that ends in the morning, like the play of a night owl. With a missing collection day, the whole interval goes
-- to the last day and days_covered tells how many days it spans: nothing is invented.
CREATE OR REPLACE VIEW daily_playtime WITH (security_invoker = true) AS
SELECT
    i.user_id,
    i.app_id,
    g.name,
    i.snapshot_date - 1 AS play_date,
    i.previous_snapshot_date,
    i.snapshot_date,
    i.snapshot_date - i.previous_snapshot_date AS days_covered,
    i.minutes_difference AS minutes_played,
    round(i.minutes_difference / 60.0, 2) AS hours_played
FROM snapshot_intervals i
JOIN games g USING (app_id)
JOIN games_classified c USING (app_id)
WHERE c.item_category = 'game'
  AND i.minutes_difference > 0;  -- days without play are left out; decreases go to the quarantine


-- Collection quarantine: a total that decreased is kept out of the hours, with the reason (rule 13).
-- The original snapshots stay untouched in playtime_snapshots.
CREATE OR REPLACE VIEW collection_quarantine WITH (security_invoker = true) AS
SELECT
    i.user_id,
    'collection' AS origin,
    i.app_id,
    g.name,
    i.previous_snapshot_date,
    i.snapshot_date,
    i.previous_minutes,
    i.minutes,
    format('Playtime decreased from %s to %s minutes', i.previous_minutes, i.minutes) AS reason
FROM snapshot_intervals i
JOIN games g USING (app_id)
WHERE i.minutes_difference < 0;


-- Items left out of the metrics, with the reason, so nothing disappears silently (rule 19).
CREATE OR REPLACE VIEW items_out_of_metrics WITH (security_invoker = true) AS
SELECT
    l.user_id,
    l.app_id,
    g.name,
    c.item_category,
    CASE c.item_category
        WHEN 'software' THEN 'Software genre in the store (e.g. Utilities)'
        ELSE 'No genres or no store page (test server, playtest or removed item)'
    END AS reason
FROM library l
JOIN games g USING (app_id)
JOIN games_classified c USING (app_id)
WHERE c.item_category <> 'game';
