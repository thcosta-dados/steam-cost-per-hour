-- Fact checks for the dashboard (ticket 11b).
-- Every number on the dashboard comes from a DAX measure. Each query below recomputes one of those
-- facts straight from the database views, without Power BI, so the two can be compared.
-- The pages are read without filters. The dashboard has one user, so the queries do not group by user.
--
-- Run (Supabase):  docker compose run --rm -T app-cloud python -m src.fact_checks
-- Run (local):     docker compose exec -T app python -m src.fact_checks
--
-- Each query starts with a "-- F00 | page | text on the dashboard" line, used by the runner as the title.


-- ============================== Minha Steam ==============================

-- F01 | Minha Steam | Total de horas jogadas na Steam (8.173 h)
SELECT round(sum(minutes_played) / 60.0) AS total_hours
FROM game_costs;

-- F02 | Minha Steam | durante 11 anos (cerca de 1,9 h por dia), Estou na Steam desde ... (11 anos)
WITH span AS (
    SELECT (SELECT min(purchase_date) FROM purchase_discounts) AS first_purchase,
           (SELECT max(last_snapshot_date) FROM game_costs) AS last_snapshot,
           (SELECT sum(minutes_played) / 60.0 FROM game_costs) AS hours
)
SELECT first_purchase, last_snapshot,
       floor((last_snapshot - first_purchase) / 365.25) AS years,
       round(hours / (last_snapshot - first_purchase), 1) AS hours_per_day
FROM span;

-- F03 | Minha Steam | Jogos na conta: 40 pagos, 25 grátis, 9 sem compra (74)
SELECT value_origin, count(*) AS games
FROM game_costs
GROUP BY value_origin
ORDER BY games DESC;

-- F04 | Minha Steam | Gastei na Steam, pelo meu histórico de compras (R$ 3.134,44)
SELECT sum(total_spend_brl) AS total_spend  -- unknown values are NULL and left out (rule 18)
FROM game_costs;

-- F05 | Minha Steam | Cada hora de jogo pago me custou, em média (R$ 0,75), spec rule 25
SELECT round(sum(total_spend_brl) / (sum(minutes_played) / 60.0), 2) AS average_cost_per_hour
FROM game_costs
WHERE value_origin IN ('paid', 'estimated');

-- F06 | Minha Steam | Meu jogo mais jogado e Os 6 jogos que mais joguei (horas, fatia, gasto)
SELECT name, round(minutes_played / 60.0) AS hours,
       round(100.0 * minutes_played / sum(minutes_played) OVER (), 1) AS share_pct,
       total_spend_brl
FROM game_costs
ORDER BY minutes_played DESC
LIMIT 6;

-- F07 | Minha Steam | 9 de cada 10 horas foram em jogos de ação (horas por gênero)
-- A game counts in each of its genres; Free To Play and Early Access are business models, not styles.
SELECT gg.genre, round(sum(gc.minutes_played) / 60.0) AS hours,
       round(100.0 * sum(gc.minutes_played) / (SELECT sum(minutes_played) FROM game_costs), 1) AS share_of_all_hours_pct
FROM game_genres gg
JOIN game_costs gc USING (user_id, app_id)
WHERE gg.genre NOT IN ('Free To Play', 'Free to Play', 'Early Access')
GROUP BY gg.genre
ORDER BY hours DESC
LIMIT 5;

-- F08 | Minha Steam | Estou na Steam desde 30/12/2014, quando comprei GRID Autosport
SELECT purchase_date, items, paid_brl
FROM purchase_discounts
ORDER BY purchase_date, paid_brl DESC
LIMIT 1;

-- F09 | Minha Steam | Porcentagem das minhas horas em jogos que não paguei para jogar (49,9%)
SELECT round(100.0 * sum(minutes_played) FILTER (WHERE value_origin IN ('free', 'no_purchase'))
             / sum(minutes_played), 1) AS share_pct
FROM game_costs;

-- F10 | Minha Steam e Compras | Economizei com promoções (R$ 2.216,91), pagando R$ 2.732,86 em vez de R$ 4.949,77
SELECT sum(savings_brl) AS savings, sum(paid_brl) AS paid, sum(original_price_brl) AS full_price
FROM purchase_discounts;

-- F11 | Minha Steam e Compras | Minha maior pechincha / O maior desconto (The Crew 2, 98%)
SELECT items, discount_pct, paid_brl, original_price_brl
FROM purchase_discounts
ORDER BY discount_pct DESC, savings_brl DESC
LIMIT 1;

-- F12 | Minha Steam | O ano em que mais gastei (2025: R$ 882,68 em 6 compras)
SELECT extract(year FROM purchase_date) AS year, sum(paid_brl) AS paid, count(*) AS purchases
FROM purchase_discounts
GROUP BY year
ORDER BY paid DESC
LIMIT 1;

-- F13 | Minha Steam | Gastei dentro do Counter-Strike 2, um jogo que me custou R$ 16,74 (R$ 296,44)
SELECT name, game_value_brl, extra_spend_brl
FROM game_costs
ORDER BY extra_spend_brl DESC
LIMIT 1;


-- ============================== Valeu a pena? ==============================

-- F14 | Valeu a pena? | ... foi o jogo que mais valeu a pena: R$ 0,16 por hora
SELECT name, round(cost_per_hour_brl, 2) AS cost_per_hour
FROM game_costs
WHERE hours_group = 'played' AND value_origin IN ('paid', 'estimated')
ORDER BY cost_per_hour_brl
LIMIT 1;

-- F15 | Valeu a pena? | 1 hora de Phasmophobia custou o mesmo que 163 horas desse jogo
WITH eligible AS (
    SELECT name, cost_per_hour_brl
    FROM game_costs
    WHERE hours_group = 'played' AND value_origin IN ('paid', 'estimated')
)
SELECT (SELECT name FROM eligible ORDER BY cost_per_hour_brl DESC LIMIT 1) AS priciest_game,
       floor(max(cost_per_hour_brl) / min(cost_per_hour_brl)) AS hours_of_the_cheapest
FROM eligible;

-- F16 | Valeu a pena? | Selos da tabela (Platina até R$ 0,50 por hora, Ouro até R$ 1, Prata até R$ 3, Bronze acima)
SELECT CASE WHEN cost_per_hour_brl <= 0.5 THEN 'Platina'
            WHEN cost_per_hour_brl <= 1 THEN 'Ouro'
            WHEN cost_per_hour_brl <= 3 THEN 'Prata'
            ELSE 'Bronze' END AS badge,
       count(*) AS games
FROM game_costs
WHERE hours_group = 'played' AND value_origin IN ('paid', 'estimated')
GROUP BY badge
ORDER BY min(cost_per_hour_brl);

-- F17 | Valeu a pena? | Metade das minhas horas me custou R$ 86,73 (placar comprei x não comprei)
SELECT CASE WHEN value_origin IN ('paid', 'estimated') THEN 'comprei'
            WHEN value_origin IN ('free', 'no_purchase') THEN 'não comprei'
            ELSE 'sem preço conhecido' END AS cost_group,
       round(sum(minutes_played) / 60.0) AS hours,
       coalesce(sum(total_spend_brl), 0) AS spent,
       round(sum(total_spend_brl) / (sum(minutes_played) / 60.0), 2) AS cost_per_hour
FROM game_costs
GROUP BY cost_group
ORDER BY cost_group;

-- F18 | Valeu a pena? | Comprei e joguei menos de 1 hora: The Crew 2 (8 min) e Plague Inc: Evolved (25 min) (R$ 7,69)
SELECT string_agg(name || ' (' || minutes_played || ' min)', ', ' ORDER BY minutes_played) AS games,
       sum(game_value_brl) AS value
FROM game_costs
WHERE hours_group = 'barely_started' AND value_origin IN ('paid', 'estimated');

-- F19 | Valeu a pena? | Comprei e nunca abri. Nenhum jogo ficou parado (R$ 0,00)
SELECT count(*) AS games, coalesce(sum(game_value_brl), 0) AS value
FROM game_costs
WHERE hours_group = 'not_played' AND value_origin IN ('paid', 'estimated');


-- ============================== Compras ==============================

-- F20 | Compras | Desconto médio sobre o preço cheio e quantas compras tiveram desconto
SELECT round(100.0 * sum(savings_brl) / sum(original_price_brl), 1) AS average_discount_pct,
       round(100.0 * count(*) FILTER (WHERE discount_pct > 0) / count(*)) AS purchases_with_discount_pct
FROM purchase_discounts;

-- F21 | Compras | Mês em que mais compro, com N compras somando todos os anos
SELECT extract(month FROM purchase_date) AS month, count(*) AS purchases
FROM purchase_discounts
GROUP BY month
ORDER BY purchases DESC, month
LIMIT 1;

-- F22 | Compras | A compra mais cara
SELECT items, paid_brl, purchase_date
FROM purchase_discounts
ORDER BY paid_brl DESC, purchase_date
LIMIT 1;

-- F23 | Compras | A maior economia
SELECT items, savings_brl, discount_pct
FROM purchase_discounts
ORDER BY savings_brl DESC
LIMIT 1;

-- F24 | Compras | Subtítulo do gráfico: o ano com mais compras e os anos em que economizei mais do que paguei
WITH years AS (
    SELECT extract(year FROM purchase_date) AS year, count(*) AS purchases,
           sum(paid_brl) AS paid, sum(savings_brl) AS saved
    FROM purchase_discounts
    GROUP BY year
)
SELECT (SELECT year || ': ' || purchases FROM years ORDER BY purchases DESC, year DESC LIMIT 1) AS year_with_most_purchases,
       (SELECT string_agg(year::text, ', ' ORDER BY year) FROM years WHERE saved > paid) AS years_saved_more_than_paid;


-- ============================== Dia a dia ==============================

-- F25 | Dia a dia | Horas jogadas em N de M dias anotados, e Jogos que abri
SELECT (SELECT sum(hours_played) FROM daily_playtime) AS hours,
       (SELECT count(DISTINCT play_date) FROM daily_playtime) AS days_with_play,
       (SELECT count(*) FROM collection_days) AS days_noted,
       (SELECT min(play_date) FROM collection_days) AS noted_since,
       (SELECT count(DISTINCT app_id) FROM daily_playtime) AS games_opened;

-- F26 | Dia a dia | Meu melhor dia (only intervals of 1 day, rule 11)
SELECT play_date, to_char(play_date, 'DD/MM/YYYY') AS shown_as, sum(hours_played) AS hours
FROM daily_playtime
WHERE days_covered = 1
GROUP BY play_date
ORDER BY hours DESC, play_date DESC
LIMIT 1;

-- F27 | Dia a dia | Maior sequência de dias (a noted day without play breaks it; a day not noted does not count)
WITH days AS (
    SELECT cd.play_date, coalesce(sum(dp.minutes_played), 0) AS minutes
    FROM collection_days cd
    LEFT JOIN daily_playtime dp ON dp.user_id = cd.user_id AND dp.play_date = cd.play_date
    GROUP BY cd.play_date
),
breaks AS (
    SELECT d.play_date, d.minutes,
           (SELECT max(x.play_date) FROM days x WHERE x.minutes = 0 AND x.play_date < d.play_date) AS last_break
    FROM days d
)
SELECT min(play_date) AS starts, max(play_date) AS ends, count(*) AS days
FROM breaks
WHERE minutes > 0
GROUP BY last_break
ORDER BY days DESC
LIMIT 1;

-- F28 | Dia a dia | [dia da semana] é o meu dia: X h em média (average over noted days with play, 1-day intervals)
WITH per_day AS (
    SELECT play_date, sum(hours_played) AS hours
    FROM daily_playtime
    WHERE days_covered = 1
    GROUP BY play_date
)
SELECT (ARRAY['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo'])[extract(isodow FROM play_date)] AS weekday,
       round(avg(hours), 1) AS average_hours, count(*) AS days
FROM per_day
GROUP BY weekday
ORDER BY average_hours DESC;

-- F29 | Dia a dia | [jogo] ficou com X% das minhas horas (whole period)
SELECT name, round(100.0 * sum(hours_played) / (SELECT sum(hours_played) FROM daily_playtime)) AS share_pct
FROM daily_playtime
GROUP BY name
ORDER BY sum(hours_played) DESC
LIMIT 1;


-- ============================== Bastidores ==============================

-- F30 | Bastidores | Itens fora das métricas, jogos sem valor conhecido e dias anotados
SELECT (SELECT count(*) FROM items_out_of_metrics) AS items_out_of_metrics,
       (SELECT count(*) FROM game_costs WHERE value_origin = 'unknown') AS games_without_known_value,
       (SELECT count(*) FROM collection_days) AS days_noted;


-- ============================== Ficha do jogo ==============================

-- F31 | Ficha do jogo | Posição entre os meus 74 jogos, fatia das horas e gasto (first 10 games)
-- Position = games with more minutes + 1, like the measure (a tie shares the position).
SELECT rank() OVER (ORDER BY minutes_played DESC) AS position, name,
       round(100.0 * minutes_played / sum(minutes_played) OVER (), 1) AS share_pct,
       game_value_brl, extra_spend_brl,
       round(cost_per_hour_brl, 2) AS cost_per_hour
FROM game_costs
ORDER BY minutes_played DESC
LIMIT 10;
