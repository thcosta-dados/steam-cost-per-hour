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


-- Cost per hour of each game, one row per user and game (spec, rules 1, 2, 6, 9, 10, 18).
CREATE OR REPLACE VIEW game_costs WITH (security_invoker = true) AS
WITH latest_snapshot AS (
    -- DISTINCT ON keeps the first row of each (user, game) in the ORDER BY: the latest day
    SELECT DISTINCT ON (user_id, app_id) user_id, app_id, snapshot_date, minutes_played
    FROM playtime_snapshots
    ORDER BY user_id, app_id, snapshot_date DESC
),
valued AS (
    SELECT
        l.user_id,
        l.app_id,
        g.name,
        g.header_image_url,
        s.snapshot_date,
        s.minutes_played,
        -- Value origin (rule 2). "paid" and "gift" come with the purchase history (ticket 10).
        CASE
            WHEN NOT l.has_license THEN 'free'              -- played without a license (rule 6)
            WHEN g.list_price_brl IS NOT NULL THEN 'estimated'
            ELSE 'unknown'                                  -- licensed, no store price (rule 18)
        END AS value_origin,
        -- NULL (not 0) for unknown value: sums ignore it instead of counting it as free
        CASE WHEN NOT l.has_license THEN 0 ELSE g.list_price_brl END AS game_value_brl
    FROM library l
    JOIN games g USING (app_id)
    JOIN games_classified c USING (app_id)
    -- Inner join: every library row has a snapshot (both are saved in the same transaction)
    JOIN latest_snapshot s USING (user_id, app_id)
    WHERE c.item_category = 'game'  -- software and other items are out of metrics (rule 17)
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
