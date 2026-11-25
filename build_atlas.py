"""Build atlas.json for the Premier League Atlas page from the official Fantasy Premier League feed.

The feed is the one the Premier League publishes for its own app: it carries every fixture with
its gameweek, kick-off time (UTC) and score. Run it weekly (or after any schedule change):

    python build_atlas.py                 # writes atlas.json
    python build_atlas.py --csv           # also writes fixtures_2026_27.csv (for PostGIS \\copy)

Then open the Atlas page, "Load your PostGIS data", and pick atlas.json.
Needs Python 3.9+ and the requests package:  pip install requests
"""
import argparse, csv, json, sys
from zoneinfo import ZoneInfo
from datetime import datetime
import requests

API = "https://fantasy.premierleague.com/api/"
LONDON = ZoneInfo("Europe/London")

ap = argparse.ArgumentParser()
ap.add_argument("--clubs", default="clubs.csv", help="CSV with code,name,stadium,lat,lon")
ap.add_argument("--out", default="atlas.json")
ap.add_argument("--csv", action="store_true", help="also write fixtures_2026_27.csv")
args = ap.parse_args()

def get(path):
    r = requests.get(API + path, timeout=30, headers={"User-Agent": "spatial-football-analytics"})
    r.raise_for_status()
    return r.json()

teams = {t["id"]: t["short_name"] for t in get("bootstrap-static/")["teams"]}

clubs = []
with open(args.clubs, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        clubs.append([row["code"], row["name"], float(row["lat"]), float(row["lon"])])
known = {c[0] for c in clubs}

fixtures, rows = [], []
for fx in get("fixtures/"):
    if not fx.get("event") or not fx.get("kickoff_time"):
        continue                                   # postponed or not yet scheduled
    home, away = teams[fx["team_h"]], teams[fx["team_a"]]
    if home not in known or away not in known:
        print(f"warning: {home} or {away} is missing from {args.clubs}", file=sys.stderr)
        continue
    ko = datetime.fromisoformat(fx["kickoff_time"].replace("Z", "+00:00")).astimezone(LONDON)
    hg, ag = fx.get("team_h_score"), fx.get("team_a_score")
    score = f"{hg}-{ag}" if fx.get("finished") and hg is not None else None
    # page format: [away, home, gameweek, "MMDD", "HHMM" (London time), "hg-ag" or None]
    fixtures.append([away, home, fx["event"], ko.strftime("%m%d"), ko.strftime("%H%M"), score])
    rows.append([fx["event"], ko.strftime("%Y-%m-%d"), ko.strftime("%H:%M"), home, away,
                 hg if score else "", ag if score else "", "published"])

fixtures.sort(key=lambda f: (f[2], f[3], f[4]))
with open(args.out, "w", encoding="utf-8") as f:
    json.dump({"source": "Fantasy Premier League feed", "generated": datetime.now().strftime("%Y-%m-%d"), "clubs": clubs, "fixtures": fixtures}, f, ensure_ascii=False)
print(f"wrote {args.out}: {len(clubs)} clubs, {len(fixtures)} fixtures, "
      f"{sum(1 for x in fixtures if x[5])} with results")

if args.csv:
    rows.sort()
    with open("fixtures_2026_27.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["gameweek", "date_london", "time_london", "home", "away", "home_goals", "away_goals", "source"])
        w.writerows(rows)
    print("wrote fixtures_2026_27.csv")
