-- Premier League Atlas 2026/27: PostGIS schema, loaders and every query behind the page
-- psql "$DATABASE_URL" -f atlas_schema.sql
-- then, from the folder holding the CSV files:
--   \copy clubs_stage   FROM 'clubs.csv'              CSV HEADER
--   \copy fixtures_stage FROM 'fixtures_2026_27.csv'  CSV HEADER
--   and run the "LOAD" block at the bottom.
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS clubs (
  code text PRIMARY KEY, name text NOT NULL, stadium text,
  geom geometry(Point, 4326) NOT NULL);
CREATE INDEX IF NOT EXISTS clubs_geom_gix ON clubs USING gist (geom);

CREATE TABLE IF NOT EXISTS fixtures (
  id serial PRIMARY KEY,
  gameweek int NOT NULL,
  home text NOT NULL REFERENCES clubs(code),
  away text NOT NULL REFERENCES clubs(code),
  kickoff timestamptz NOT NULL,              -- stored in UTC, shown in Europe/London
  home_goals int, away_goals int,
  source text DEFAULT 'published');          -- 'deduced' marks matches completed by elimination
CREATE INDEX IF NOT EXISTS fixtures_gw_idx ON fixtures (gameweek);

CREATE TABLE IF NOT EXISTS england (geom geometry(MultiPolygon, 4326));  -- load Natural Earth / OS Boundary-Line

CREATE TABLE IF NOT EXISTS clubs_stage (code text, name text, stadium text, lat float8, lon float8);
CREATE TABLE IF NOT EXISTS fixtures_stage (gameweek int, date_london date, time_london time,
  home text, away text, home_goals int, away_goals int, source text);

-- 1. Away-day distance on the ellipsoid (km) and bearing
CREATE OR REPLACE VIEW away_days AS
SELECT f.id, f.gameweek, f.kickoff, f.away, f.home, f.home_goals, f.away_goals,
       ST_Distance(a.geom::geography, h.geom::geography) / 1000 AS km,
       degrees(ST_Azimuth(a.geom, h.geom)) AS bearing
FROM fixtures f JOIN clubs a ON a.code = f.away JOIN clubs h ON h.code = f.home;

-- 2. Gameweek summary
CREATE OR REPLACE VIEW gameweek_summary AS
SELECT gameweek, count(*) AS matches, round(sum(km))::int AS total_km,
       round(avg(km))::int AS avg_km, round(max(km))::int AS longest_km
FROM away_days GROUP BY gameweek ORDER BY gameweek;

-- 3. Territories (nearest stadium wins), in British National Grid metres
CREATE MATERIALIZED VIEW IF NOT EXISTS territories AS
WITH cells AS (
  SELECT (ST_Dump(ST_VoronoiPolygons(ST_Collect(ST_Transform(geom, 27700))))).geom AS cell FROM clubs)
SELECT c.code, ST_Intersection(cells.cell, ST_Transform(e.geom, 27700)) AS geom
FROM cells JOIN clubs c ON ST_Contains(cells.cell, ST_Transform(c.geom, 27700))
CROSS JOIN england e;

SELECT code, round((100 * ST_Area(geom) / sum(ST_Area(geom)) OVER ())::numeric, 1) AS pct
FROM territories ORDER BY pct DESC;                                   -- territory share

-- 4. Three nearest rivals (KNN, index-assisted). Replace 'NEW'.
SELECT o.name, ST_Distance(o.geom::geography, me.geom::geography) / 1000 AS km
FROM clubs me JOIN LATERAL (
  SELECT * FROM clubs c WHERE c.code <> me.code ORDER BY c.geom <-> me.geom LIMIT 3) o ON true
WHERE me.code = 'NEW';

-- 5. Derby radar: the closest pairs of stadiums and when they meet
SELECT a.name AS club_a, b.name AS club_b,
       round((ST_Distance(a.geom::geography, b.geom::geography) / 1000)::numeric, 1) AS km,
       (SELECT string_agg(to_char(f.kickoff AT TIME ZONE 'Europe/London', 'Dy DD Mon HH24:MI'), '; ' ORDER BY f.kickoff)
          FROM fixtures f WHERE (f.home = a.code AND f.away = b.code) OR (f.home = b.code AND f.away = a.code)) AS dates
FROM clubs a JOIN clubs b ON a.code < b.code
ORDER BY ST_Distance(a.geom::geography, b.geom::geography) LIMIT 12;

-- 6. Season miles: cumulative away distance by club after each gameweek (the bar race)
SELECT away AS club, gameweek,
       round(sum(km) OVER (PARTITION BY away ORDER BY gameweek))::int AS cumulative_km
FROM (SELECT away, gameweek, sum(km) AS km FROM away_days GROUP BY away, gameweek) t
ORDER BY gameweek, cumulative_km DESC;

-- 7. Hardest three-gameweek stretch per club
WITH w AS (
  SELECT away, gameweek, sum(km) AS km FROM away_days GROUP BY away, gameweek),
s AS (
  SELECT away, gameweek AS gw_from,
         sum(km) OVER (PARTITION BY away ORDER BY gameweek ROWS BETWEEN CURRENT ROW AND 2 FOLLOWING) AS km3,
         count(*) OVER (PARTITION BY away ORDER BY gameweek ROWS BETWEEN CURRENT ROW AND 2 FOLLOWING) AS n
  FROM w)
SELECT DISTINCT ON (away) away, gw_from, round(km3)::int AS km3 FROM s WHERE n = 3 ORDER BY away, km3 DESC;

-- 8. Does distance matter? Correlation of away goal difference with distance (completed matches)
SELECT count(*) AS matches,
       round(corr(km, away_goals - home_goals)::numeric, 2) AS r,
       round((regr_slope(away_goals - home_goals, km) * 100)::numeric, 2) AS goals_per_100km
FROM away_days WHERE home_goals IS NOT NULL;

-- 9. Gameweek centre: mean of match midpoints (replace 11)
SELECT ST_Centroid(ST_Collect(ST_LineInterpolatePoint(ST_MakeLine(a.geom, h.geom), 0.5))) AS gw_centre
FROM fixtures f JOIN clubs a ON a.code = f.away JOIN clubs h ON h.code = f.home WHERE f.gameweek = 11;

-- 10. Clubs within 100 km of a club
SELECT count(*) FROM clubs a, clubs b
WHERE a.code = 'ARS' AND a.code <> b.code AND ST_DWithin(a.geom::geography, b.geom::geography, 100000);

-- 11. Exact people per stadium (ONS LSOA 2021 population-weighted centroids joined to mid-year estimates)
--     Load the two ONS files into lsoa(code text primary key, pop int, geom geometry(Point,27700)) first.
CREATE TABLE IF NOT EXISTS lsoa (code text PRIMARY KEY, pop int, geom geometry(Point, 27700));
CREATE INDEX IF NOT EXISTS lsoa_gix ON lsoa USING gist (geom);
ALTER TABLE clubs ADD COLUMN IF NOT EXISTS geom_bng geometry(Point, 27700);
UPDATE clubs SET geom_bng = ST_Transform(geom, 27700);
CREATE INDEX IF NOT EXISTS clubs_bng_gix ON clubs USING gist (geom_bng);

SELECT c.code, sum(l.pop) AS people_closest
FROM lsoa l
CROSS JOIN LATERAL (SELECT code FROM clubs ORDER BY geom_bng <-> l.geom LIMIT 1) c
WHERE l.code LIKE 'E01%'
GROUP BY c.code ORDER BY people_closest DESC;

-- 12. People within 50 km of each stadium
SELECT c.code, sum(l.pop) AS people_within_50km
FROM clubs c JOIN lsoa l ON ST_DWithin(c.geom_bng, l.geom, 50000)
WHERE l.code LIKE 'E01%'
GROUP BY c.code ORDER BY people_within_50km DESC;

-- 13. Road time: build_travel_times.py calls OSRM for the full matrix. Inside PostgreSQL the equivalent is pgRouting
--     (pgr_dijkstraCost over an OpenStreetMap road graph imported with osm2pgrouting).

-- 14. Contested ground: people within 5 km of the border between two territories (the flagship analysis).
--     Distance from a point to the bisector between its nearest stadium and another stadium c is
--     (dc^2 - d1^2) / (2 * |stadium to stadium|). The smallest value over all c is the distance to the nearest border.
WITH k AS (
  SELECT l.code AS lsoa, l.pop, l.geom, b.code AS own, b.geom_bng AS own_geom
  FROM lsoa l
  CROSS JOIN LATERAL (SELECT code, geom_bng FROM clubs ORDER BY geom_bng <-> l.geom LIMIT 1) b
  WHERE l.code LIKE 'E01%'),
d AS (
  SELECT k.lsoa, k.pop, k.own, c.code AS other,
         (ST_Distance(c.geom_bng, k.geom)^2 - ST_Distance(k.own_geom, k.geom)^2)
           / (2 * ST_Distance(c.geom_bng, k.own_geom)) AS border_m
  FROM k JOIN clubs c ON c.code <> k.own),
m AS (SELECT DISTINCT ON (lsoa) lsoa, pop, own, other, border_m FROM d ORDER BY lsoa, border_m)
SELECT least(own, other) AS club_a, greatest(own, other) AS club_b, sum(pop) AS people_within_5km
FROM m WHERE border_m <= 5000
GROUP BY 1, 2 ORDER BY 3 DESC;

-- The band itself, for the map (clip it to the England outline with ST_Intersection):
SELECT code, ST_Buffer(ST_Boundary(geom), 5000) AS band FROM territories;

-- LOAD ------------------------------------------------------------------
-- INSERT INTO clubs SELECT code, name, stadium, ST_SetSRID(ST_MakePoint(lon, lat), 4326) FROM clubs_stage
--   ON CONFLICT (code) DO NOTHING;
-- INSERT INTO fixtures (gameweek, home, away, kickoff, home_goals, away_goals, source)
--   SELECT gameweek, home, away, (date_london + time_london) AT TIME ZONE 'Europe/London',
--          home_goals, away_goals, source FROM fixtures_stage;
-- Sun position is not in PostGIS: the page computes it in JavaScript (NOAA solar algorithm).
