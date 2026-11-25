# Premier League Atlas 2026/27 (Spatial Football Analytics)

An interactive, bilingual (English and Arabic, RTL) atlas that reads the league as geography.

## Files
| File | What it is |
|---|---|
| `index.html` | The atlas (map, gameweek dropdown, story mode, "my club", lab). One file, no build step. |
| `odyssey-satellite.html` | Season odyssey on satellite imagery (MapLibre). Needs `atlas.json` beside it. |
| `atlas.json` | Clubs, fixtures, kick-offs and results the pages read. Refreshed by `build_atlas.py`. |
| `build_atlas.py` | Builds `atlas.json` from the official Fantasy Premier League feed. |
| `population_pipeline.py` | Exact people-per-stadium catchments from ONS data. Writes `population.json`. |
| `build_travel_times.py` | Real road times between all stadiums from OSRM. Writes `travel.json`. |
| `fetch_stadiums.py` | Refines stadium coordinates from OpenStreetMap (writes `clubs_precise.csv`). |
| `clubs.csv`, `fixtures_2026_27.csv` | Source data for PostGIS and for `build_atlas.py`. |
| `atlas_schema.sql`, `export_atlas.py` | PostGIS schema, every query behind the page, and a DB exporter. |
| `.github/workflows/update-atlas.yml` | GitHub Action: refreshes `atlas.json` and `fixtures_2026_27.csv` on its schedule. |
| `arabic_review.csv` | Every Arabic string, for a native reader to check. |

## Repository layout
Keep the files in the supplied structure: application and data files in the repository root, and the workflow at `.github/workflows/update-atlas.yml`. Do not upload `pl-atlas.html` (a copy of `index.html`) or raw ONS downloads.

## Run it locally
```
python -m http.server 8000
```
Open http://localhost:8000/ (not the file directly, so `atlas.json` can load).

## Host it (GitHub Pages)
1. Upload all files while preserving the supplied folder structure.
2. Settings, Pages, deploy from the `main` branch and `/ (root)`.
3. Actions tab, "Update atlas data", Run workflow (once, by hand, to check it works).
4. Link: `https://<you>.github.io/<repo>/`. Deep links: `#gw=13&club=NEW`.

## Satellite imagery
Google's satellite tiles may only be shown through the Google Maps API, so this page uses MapLibre with:
- `esri` (default, no key). Check Esri's terms for production use and keep the attribution.
- `maptiler` or `mapbox` (free keys). Set `CFG.provider` and `CFG.key` at the top of the script, or use `?provider=maptiler&key=...` for a quick test.
Before using it for real, run `python fetch_stadiums.py`: zooming onto a pitch needs coordinates accurate to about 20 m.

## Population catchments ("Who is closest")
Without `population.json` the tab shows **indicative** figures (about 150 local-authority points, rounded, from the 2021 Census). Do not publish those as facts. For exact numbers:
1. Download two ONS files: "Lower layer Super Output Areas (December 2021) EW Population Weighted Centroids" (CSV, Open Geography Portal) and "Lower layer Super Output Area population estimates (supporting information)" (Excel, mid-2022 or later).
2. `pip install pandas numpy pyproj openpyxl`
3. `python population_pipeline.py --centroids <centroids.csv> --population <population.xlsx> --year mid-2022`
4. Check the printed total (England is about 57 million), put `population.json` beside `index.html`.
The same result in PostGIS is in `atlas_schema.sql` (sections 11 and 12).

## Contested ground
The tab works from geometry alone: for every point of England it measures the exact distance to the nearest territory border. People counts appear when `population.json` (from `population_pipeline.py`) holds a `contested` section. The same analysis in PostGIS is section 14 of `atlas_schema.sql`.

## Road time
Without `travel.json` times are estimates (distance x 1.2 at 75 km/h), so the two rankings match. For real road times:
1. `pip install requests`
2. `python build_travel_times.py` (one request to the OSRM public demo server, light use only; or `--server` with your own OSRM)
3. Put `travel.json` beside `index.html`. Times are for cars. Fans use coaches and trains, so say so when you publish. Rail needs GTFS timetables and a journey planner such as OpenTripPlanner.

## Things to do before you publish
- Run `python build_atlas.py` so kick-offs match the official feed (broadcast picks move matches).
- Have a native Arabic reader check `arabic_review.csv`.
- Ask the Premier League for permission before using its name, colours or data under their brand.
- This is an independent project, not affiliated with or endorsed by the Premier League.

## Honest limits
- Twelve matches in gameweeks 36 and 37 were completed by elimination until the feed confirms them.
- The England outline is traced by hand. The chart of distance against results has a small sample.
- `build_atlas.py`, `build_travel_times.py`, `population_pipeline.py` (tested only on synthetic files, and without the British National Grid conversion), `fetch_stadiums.py`, the GitHub Action and the PostGIS queries were written without network access to run them. Test each once.
