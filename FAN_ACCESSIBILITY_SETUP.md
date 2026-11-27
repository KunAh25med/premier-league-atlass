# Fan Accessibility & Equity — automated build

This package adds an automated data pipeline to Premier League Atlas. It does **not** edit `index.html` yet. The first milestone is to generate and validate the data products; the interactive map is the next integration step after a successful run.

## What it builds

- `data/fan-accessibility/fan_accessibility.geojson.gz`
  - One LSOA 2021 polygon per matched English LSOA.
  - Population estimate (ONS mid-2024), fastest modeled driving time to the nearest of the 20 stadiums, routed distance, and assigned club.
- `data/fan-accessibility/fan_accessibility_summary.json`
  - Population-weighted 30/60/90-minute coverage.
  - Population-weighted median and 90th percentile access time.
  - Population-weighted Gini coefficient of access time.
  - Club catchment summaries.

## Data and method

1. ONS mid-2024 LSOA population estimates, England.
2. ONS 2021 LSOA population-weighted centroids as origins.
3. ONS 2021 LSOA boundaries as the mapped polygons.
4. OpenRouteService `driving-car` matrix, based on OpenStreetMap road data.
5. Each LSOA is assigned to the stadium with the lowest modeled driving duration.

The result is **potential road accessibility**, not actual supporters, ticket holders, attendance, live traffic, matchday congestion, parking availability, rail or bus accessibility.

The geometry is simplified for web delivery. Raw source files are fetched by the GitHub Actions runner and are not committed to the repository.

## One-time setup

### 1. Create an OpenRouteService API key

1. Open https://openrouteservice.org/dev/#/signup
2. Create a free account and generate an API key.
3. Keep the key private. Do not paste it into `index.html`, Python files, README files, or a public issue.

The script batches 150 LSOA origins against 20 stadiums per matrix request (3,000 origin-destination pairs). It waits between calls to respect the documented standard-plan request rate and checks the daily matrix-call budget before routing.

### 2. Add the key to GitHub Actions Secrets

In `KunAh25med/premier-league-atlass`:

1. Open **Settings**.
2. Open **Secrets and variables → Actions**.
3. Choose **New repository secret**.
4. Name: `ORS_API_KEY`
5. Value: paste the key from OpenRouteService.
6. Save.

Never add the API key to the repository itself.

### 3. Upload these package files into the repository root

Keep the paths exactly as shown:

```text
.github/
  workflows/
    build-fan-accessibility.yml
scripts/
  build_fan_accessibility.py
requirements-fan-accessibility.txt
docs/
  FAN_ACCESSIBILITY_SETUP.md
```

The `clubs.csv` file already exists in the repository and is used as the 20 stadium destination list.

### 4. Run the workflow

1. Open the repository's **Actions** tab.
2. Select **Build Fan Accessibility & Equity**.
3. Click **Run workflow**.
4. Open the run and inspect each step.
5. On success, the workflow commits the generated files under `data/fan-accessibility/`.

The workflow also runs monthly. You can run it manually whenever you want to refresh the data.

## Validation checks

The script deliberately stops instead of publishing a partial or suspicious result if:

- fewer than 30,000 England LSOA population records are found;
- fewer than 30,000 population-weighted centroids match the population table;
- fewer than 95% of matched origins receive a route;
- fewer than 95% of routed origins match a boundary polygon;
- the OpenRouteService quota or API returns an error.

If the workflow fails on the population workbook parser, inspect the ONS workbook's sheet/header layout and update the parser rather than weakening these checks.

## Attribution and licensing

- Population and statistical geography: Office for National Statistics (ONS).
- LSOA boundaries and population-weighted centroids contain ONS and Ordnance Survey intellectual property; retain the relevant ONS Geography Licence attribution and check the current terms before redistribution.
- Routing network: © OpenStreetMap contributors, Open Database Licence (ODbL).
- Routing engine/API: OpenRouteService; comply with its current API terms and quotas.

## Important interpretation note

Population estimates are for mid-2024; LSOA geography and population-weighted centroids are Census 2021 geography. Routing times are modeled fastest driving times, not observed journey times. A population-weighted centroid is a representative point for an area, not the exact location of every resident.
