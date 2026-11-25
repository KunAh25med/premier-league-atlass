"""Exact people-per-stadium catchments from ONS data. Writes population.json for the Atlas page.

Inputs (both free from the Office for National Statistics):
  1. "Lower layer Super Output Areas (December 2021) EW Population Weighted Centroids"
     (ONS Open Geography Portal). Download as CSV. Columns include LSOA21CD, x, y (British National Grid).
  2. "Lower layer Super Output Area population estimates (supporting information)", mid-2022 or later
     (ONS, Excel). The script looks for the sheet that has an "LSOA 2021 Code" column and a "Total" column.

    pip install pandas numpy pyproj openpyxl
    python population_pipeline.py --centroids lsoa_centroids.csv --population lsoa_population.xlsx --year mid-2022

Every LSOA in England goes to its nearest stadium (the same rule as the Voronoi territories), and the
script also totals the people living within 50 km of each stadium. Put population.json next to index.html.
It has not been run by its author on the real ONS files, so check the printed totals: England is about 57 million.
"""
import argparse, json, re, sys
import numpy as np
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--centroids", required=True)
ap.add_argument("--population", required=True)
ap.add_argument("--clubs", default="clubs.csv")
ap.add_argument("--out", default="population.json")
ap.add_argument("--year", default="mid-2022")
args = ap.parse_args()

def find(cols, pattern):
    for c in cols:
        if re.search(pattern, str(c), re.I):
            return c
    return None

def header_row(raw):
    for i in range(len(raw)):
        if any(re.search(r"lsoa.*code|lsoa\d*cd", str(v), re.I) for v in raw.iloc[i].tolist()):
            return i
    return None

def extract(df):
    code = find(df.columns, r"lsoa.*code|lsoa\d*cd")
    tot = next((c for c in df.columns if str(c).strip().lower() in ("total", "all ages", "total population", "persons", "all persons")), None)
    if code is None or tot is None:
        return None
    s = pd.Series(pd.to_numeric(df[tot], errors="coerce").values, index=df[code].astype(str).str.strip())
    return s.dropna()

def read_population(path):
    if path.lower().endswith((".xlsx", ".xls")):
        xl = pd.ExcelFile(path)
        for sh in xl.sheet_names:
            r = header_row(xl.parse(sh, header=None, nrows=40))
            if r is None:
                continue
            out = extract(xl.parse(sh, header=r))
            if out is not None:
                print("population sheet:", sh)
                return out
        sys.exit("No sheet had an LSOA code column and a Total column. Sheets: " + ", ".join(xl.sheet_names))
    raw = pd.read_csv(path, header=None, dtype=str)
    r = header_row(raw)
    if r is None:
        sys.exit("No LSOA code column found in " + path)
    out = extract(pd.read_csv(path, header=r))
    if out is None:
        sys.exit("No Total column found in " + path)
    return out

pop = read_population(args.population)
pts = pd.read_csv(args.centroids)
ccode = find(pts.columns, r"lsoa\d*cd|lsoa.*code")
if ccode is None:
    sys.exit("No LSOA code column in the centroids file. Columns: " + ", ".join(map(str, pts.columns)))
pts[ccode] = pts[ccode].astype(str).str.strip()
pts = pts[pts[ccode].str.startswith("E01")].copy()          # England only

lat = find(pts.columns, r"^(lat|latitude)$"); lon = find(pts.columns, r"^(lon|long|longitude)$")
if lat is None or lon is None:                               # British National Grid easting/northing
    ex = find(pts.columns, r"^(x|bng_e|easting)$"); ny = find(pts.columns, r"^(y|bng_n|northing)$")
    if ex is None or ny is None:
        sys.exit("Could not find coordinates. Columns: " + ", ".join(map(str, pts.columns)))
    from pyproj import Transformer
    t = Transformer.from_crs(27700, 4326, always_xy=True)
    lo, la = t.transform(pts[ex].astype(float).values, pts[ny].astype(float).values)
else:
    lo, la = pts[lon].astype(float).values, pts[lat].astype(float).values

pts["lat"], pts["lon"] = la, lo
pts["pop"] = pts[ccode].map(pop)
missing = int(pts["pop"].isna().sum())
if missing:
    print(f"warning: {missing} LSOAs have no population value and are skipped")
pts = pts.dropna(subset=["pop"])

clubs = pd.read_csv(args.clubs)
R = np.radians
dlat = R(clubs["lat"].values)[None, :] - R(pts["lat"].values)[:, None]
dlon = R(clubs["lon"].values)[None, :] - R(pts["lon"].values)[:, None]
a = np.sin(dlat / 2) ** 2 + np.cos(R(pts["lat"].values))[:, None] * np.cos(R(clubs["lat"].values))[None, :] * np.sin(dlon / 2) ** 2
km = 12742 * np.arcsin(np.sqrt(a))
nearest = km.argmin(axis=1)
w = pts["pop"].values
closest = np.bincount(nearest, weights=w, minlength=len(clubs))
within = ((km <= 50) * w[:, None]).sum(axis=0)

# Contested ground: people living within w km of the border between two stadium territories.
# Distance to the bisector between the nearest stadium b and another stadium c is (dc^2 - db^2) / (2 * |bc|).
lat0 = 53.0
X = pts["lon"].values * np.cos(np.radians(lat0)) * 111.32; Y = pts["lat"].values * 110.57
cx = clubs["lon"].values * np.cos(np.radians(lat0)) * 111.32; cy = clubs["lat"].values * 110.57
Dp = np.sqrt((X[:, None] - cx[None, :]) ** 2 + (Y[:, None] - cy[None, :]) ** 2)
own = Dp.argmin(axis=1); rows = np.arange(len(own)); d1 = Dp[rows, own]
Lm = np.sqrt((cx[:, None] - cx[None, :]) ** 2 + (cy[:, None] - cy[None, :]) ** 2); np.fill_diagonal(Lm, np.inf)
dd = (Dp ** 2 - d1[:, None] ** 2) / (2 * Lm[own]); dd[rows, own] = np.inf
border = dd.min(axis=1); other = dd.argmin(axis=1)
codes = clubs["code"].values
contested = {}
for wkm in (2, 5, 10):
    m = border <= wkm
    pairs = {}
    for a_, b_, v in zip(own[m], other[m], w[m]):
        key = "-".join(sorted([codes[a_], codes[b_]]))
        pairs[key] = pairs.get(key, 0) + int(round(v))
    contested[str(wkm)] = {"total": int(round(w[m].sum())), "pairs": pairs}

out = {
    "source": f"ONS LSOA 2021 population-weighted centroids and {args.year} population estimates (England, {len(pts)} LSOAs)",
    "total": int(w.sum()),
    "clubs": {c: int(round(v)) for c, v in zip(clubs["code"], closest)},
    "radius50": {c: int(round(v)) for c, v in zip(clubs["code"], within)},
    "contested": contested,
}
with open(args.out, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)
print(f"wrote {args.out}: total {out['total']:,} people over {len(pts)} LSOAs")
for c, v in sorted(out["clubs"].items(), key=lambda x: -x[1])[:5]:
    print(f"  {c}: {v:,}")
print("contested within 5 km:", f"{out['contested']['5']['total']:,}", "people")
