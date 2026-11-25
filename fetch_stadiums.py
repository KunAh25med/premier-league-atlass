"""Refine stadium coordinates from OpenStreetMap and write clubs_precise.csv.

Why: the satellite page zooms in until the pitch is visible, so the coordinates must be accurate
to roughly 20 metres. The ones in clubs.csv are approximate (about 100 to 200 metres).

    pip install requests
    python fetch_stadiums.py              # reads clubs.csv, writes clubs_precise.csv

Open clubs_precise.csv and check every row marked "check" (more than 500 m away from the old value,
or not found). When you are happy, replace clubs.csv with it (keep the same columns) and run
build_atlas.py again. Data: (c) OpenStreetMap contributors, ODbL.
This script uses the public Overpass API, so it waits between requests. It has not been run by its author.
"""
import csv, math, sys, time
import requests

OVERPASS = "https://overpass-api.de/api/interpreter"
PATTERN = {
    "ARS": "Emirates", "AVL": "Villa Park", "BOU": "Vitality|Dean Court", "BRE": "Gtech|Brentford Community",
    "BHA": "Amex|Falmer", "CHE": "Stamford Bridge", "COV": "Coventry Building Society|Ricoh",
    "CRY": "Selhurst", "EVE": "Hill Dickinson|Everton", "FUL": "Craven Cottage", "HUL": "MKM|KC Stadium",
    "IPS": "Portman Road", "LEE": "Elland Road", "LIV": "Anfield", "MCI": "Etihad|City of Manchester",
    "MUN": "Old Trafford", "NEW": "St James|St. James", "NFO": "City Ground", "SUN": "Stadium of Light",
    "TOT": "Tottenham Hotspur Stadium",
}

def metres(a, b):
    r = math.pi / 180
    q = math.sin((b[0]-a[0])*r/2)**2 + math.cos(a[0]*r)*math.cos(b[0]*r)*math.sin((b[1]-a[1])*r/2)**2
    return 12742000 * math.asin(math.sqrt(q))

def find(code, lat, lon):
    pat = PATTERN.get(code)
    if not pat:
        return None
    s, w, n, e = lat - .06, lon - .09, lat + .06, lon + .09
    q = f'[out:json][timeout:30];(way["leisure"="stadium"]["name"~"{pat}",i]({s},{w},{n},{e});' \
        f'relation["leisure"="stadium"]["name"~"{pat}",i]({s},{w},{n},{e}););out center;'
    r = requests.post(OVERPASS, data={"data": q}, timeout=60, headers={"User-Agent": "spatial-football-analytics"})
    r.raise_for_status()
    best = None
    for el in r.json().get("elements", []):
        c = el.get("center")
        if not c:
            continue
        d = metres((lat, lon), (c["lat"], c["lon"]))
        if best is None or d < best[0]:
            best = (d, c["lat"], c["lon"], el.get("tags", {}).get("name", ""))
    return best

rows = list(csv.DictReader(open("clubs.csv", encoding="utf-8")))
out = []
for row in rows:
    lat, lon = float(row["lat"]), float(row["lon"])
    try:
        hit = find(row["code"], lat, lon)
    except Exception as ex:
        print(row["code"], "error:", ex, file=sys.stderr)
        hit = None
    if hit:
        d, la, lo, name = hit
        out.append({**row, "lat": f"{la:.6f}", "lon": f"{lo:.6f}", "osm_name": name,
                    "delta_m": round(d), "status": "ok" if d < 500 else "check"})
        print(f'{row["code"]}: moved {d:.0f} m ({name})')
    else:
        out.append({**row, "osm_name": "", "delta_m": "", "status": "check"})
        print(f'{row["code"]}: not found, kept the old value')
    time.sleep(2)

with open("clubs_precise.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["code", "name", "stadium", "lat", "lon", "osm_name", "delta_m", "status"])
    w.writeheader()
    w.writerows(out)
print("wrote clubs_precise.csv")
