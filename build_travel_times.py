"""Build travel.json: real road travel times and distances between every pair of stadiums.

Uses one request to the OSRM "table" service, which returns the whole 20 x 20 matrix.

    pip install requests
    python build_travel_times.py                       # public OSRM demo server (light use only)
    python build_travel_times.py --server http://localhost:5000   # your own OSRM instance

Put travel.json next to index.html: the Atlas then shows road time next to kilometres and the
"Road time" tab compares the two rankings. The matrix is for cars. Fans travel by coach and train,
so treat it as the road network's view of distance, and say so when you publish.
For rail you would need timetable data (GTFS) and a router such as OpenTripPlanner. That is a separate project.
"""
import argparse, csv, datetime, json, sys
import requests

ap = argparse.ArgumentParser()
ap.add_argument("--server", default="https://router.project-osrm.org")
ap.add_argument("--profile", default="driving")
ap.add_argument("--clubs", default="clubs.csv")
ap.add_argument("--out", default="travel.json")
args = ap.parse_args()

rows = list(csv.DictReader(open(args.clubs, encoding="utf-8")))
codes = [r["code"] for r in rows]
coords = ";".join(f'{float(r["lon"]):.6f},{float(r["lat"]):.6f}' for r in rows)
url = f"{args.server.rstrip('/')}/table/v1/{args.profile}/{coords}"
r = requests.get(url, params={"annotations": "duration,distance"}, timeout=120,
                 headers={"User-Agent": "spatial-football-analytics"})
r.raise_for_status()
d = r.json()
if d.get("code") != "Ok":
    sys.exit("OSRM answered: " + json.dumps(d)[:300])

def grid(m, f):
    if any(v is None for row in m for v in row):
        sys.exit("OSRM could not route between some stadium pair. Check the coordinates in clubs.csv.")
    return [[round(v / f, 1) for v in row] for row in m]

out = {
    "source": f"OSRM {args.profile} ({args.server})",
    "generated": datetime.date.today().isoformat(),
    "codes": codes,
    "minutes": grid(d["durations"], 60),
    "km": grid(d["distances"], 1000),
}
with open(args.out, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)
i, j = codes.index("NEW") if "NEW" in codes else 0, codes.index("BOU") if "BOU" in codes else 1
print(f"wrote {args.out}: {len(codes)} stadiums. Example {codes[i]} to {codes[j]}: "
      f"{out['km'][i][j]} km, {out['minutes'][i][j]} min")
