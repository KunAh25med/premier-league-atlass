"""Export clubs and fixtures from PostGIS to atlas.json for the Premier League Atlas page
(use "Load your PostGIS data" in the side panel).

    pip install psycopg2-binary
    export DATABASE_URL=postgresql://user:pass@localhost:5432/atlas
    python export_atlas.py              # whole season
    python export_atlas.py --out my.json
"""
import argparse, json, os
import psycopg2

ap = argparse.ArgumentParser()
ap.add_argument("--out", default="atlas.json")
args = ap.parse_args()

cur = psycopg2.connect(os.environ["DATABASE_URL"]).cursor()

cur.execute("SELECT code, name, ST_Y(geom), ST_X(geom) FROM clubs ORDER BY code")
clubs = [[c, n, float(lat), float(lon)] for c, n, lat, lon in cur.fetchall()]

# fixture = [away, home, gameweek, "MMDD", "HHMM" (London time), "hg-ag" or null]
cur.execute("""
  SELECT away, home, gameweek,
         to_char(kickoff AT TIME ZONE 'Europe/London', 'MMDD'),
         to_char(kickoff AT TIME ZONE 'Europe/London', 'HH24MI'),
         CASE WHEN home_goals IS NULL THEN NULL ELSE home_goals || '-' || away_goals END
  FROM fixtures ORDER BY kickoff, id""")
fixtures = [list(r) for r in cur.fetchall()]

with open(args.out, "w", encoding="utf-8") as f:
    json.dump({"clubs": clubs, "fixtures": fixtures}, f, ensure_ascii=False)
print(f"wrote {args.out}: {len(clubs)} clubs, {len(fixtures)} fixtures")
