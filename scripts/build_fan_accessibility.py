#!/usr/bin/env python3
"""Build population-weighted driving accessibility for all English LSOAs.

Outputs (GitHub Pages friendly):
  data/fan-accessibility/fan_accessibility.geojson.gz
  data/fan-accessibility/fan_accessibility_summary.json

Routing is resumable. Successful ORS chunks are checkpointed under .cache/ and
are reused after quota limits or interrupted GitHub Actions runs.
"""
from __future__ import annotations

import csv
import datetime as dt
import gzip
import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from shapely.geometry import mapping, shape

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "fan-accessibility"
CACHE = ROOT / ".cache" / "fan-accessibility"
POP_URL = "https://www.ons.gov.uk/file?uri=%2Fpeoplepopulationandcommunity%2Fpopulationestimates%2Fdatasets%2Flowersuperoutputareamidyearpopulationestimatesnationalstatistics%2Fmid2022revisednov2025tomid2024%2Fsapelsoabroadage20222024.xlsx"CENTROIDS_URL = "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/LSOA_PopCentroids_EW_2021_V4/FeatureServer/0"
BOUNDARIES_URL = ("https://opendata.arcgis.com/api/v3/datasets/04c65a08ecff4858bffc16e9ca9356f4_0/downloads/data?format=geojson&spatialRefId=4326")
ORS_URL = "https://api.heigit.org/v2/matrix/driving-car"
CHUNK_ORIGINS = 150  # 150 x 20 = 3,000 matrix pairs (< 3,500 hosted limit)
REQUEST_GAP = 1.6    # stay below the hosted API's per-minute request limit
TIMEOUT = (30, 180)
UA = "PremierLeagueAtlas-FanAccessibility/2.0 (research portfolio)"


def log(message: str) -> None:
    print(message, flush=True)


def atomic_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    tmp.replace(path)


def download(url: str, target: Path, min_bytes: int = 10_000) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size >= min_bytes:
        if target.suffix == ".geojson":
            try:
                obj = json.loads(target.read_text(encoding="utf-8"))
                if obj.get("type") == "FeatureCollection" and obj.get("features"):
                    log(f"Using cached {target.name}")
                    return
            except Exception:
                pass
        else:
            log(f"Using cached {target.name}")
            return
    tmp = target.with_name(target.name + ".part")
    delays = [5, 10, 20, 40, 60]
    last_error: Exception | None = None
    for attempt in range(len(delays) + 1):
        try:
            with requests.get(url, stream=True, timeout=(30, 240), headers={"User-Agent": UA}) as r:
                r.raise_for_status()
                size = 0
                with tmp.open("wb") as f:
                    for block in r.iter_content(1024 * 1024):
                        if block:
                            f.write(block)
                            size += len(block)
            if size < min_bytes:
                raise RuntimeError(f"{target.name} download too small: {size:,} bytes")
            if target.suffix == ".geojson":
                obj = json.loads(tmp.read_text(encoding="utf-8"))
                if obj.get("type") != "FeatureCollection" or not obj.get("features"):
                    raise RuntimeError(f"{target.name} is not a non-empty GeoJSON FeatureCollection")
            tmp.replace(target)
            log(f"Downloaded {target.name}: {size:,} bytes")
            return
        except Exception as exc:
            last_error = exc
            if tmp.exists():
                tmp.unlink()
            if attempt == len(delays):
                break
            wait = delays[attempt]
            log(f"Download failed ({exc}); retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"Could not download {target.name}: {last_error}")


def download_centroids(target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 100_000:
        try:
            cached = json.loads(target.read_text(encoding="utf-8"))
            if cached.get("type") == "FeatureCollection" and cached.get("features"):
                log(f"Using cached {target.name}")
                return
        except Exception:
            pass
    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    def query(params: dict[str, str]) -> dict:
        response = session.get(f"{CENTROIDS_URL}/query", params=params, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise RuntimeError(f"ONS FeatureServer error: {data['error']}")
        return data

    total = int(query({"where": "1=1", "returnCountOnly": "true", "f": "json"})["count"])
    if total < 30_000:
        raise RuntimeError(f"ONS centroid layer unexpectedly small: {total:,}")
    log(f"ONS centroid records available: {total:,}")
    features: list[dict] = []
    offset = 0
    page_size = 2_000
    while offset < total:
        page = query({
            "where": "1=1", "outFields": "*", "returnGeometry": "true",
            "outSR": "4326", "resultOffset": str(offset),
            "resultRecordCount": str(page_size), "orderByFields": "OBJECTID", "f": "geojson",
        }).get("features", [])
        if not page:
            break
        features.extend(page)
        offset += len(page)
        log(f"Downloaded centroids: {len(features):,}/{total:,}")
    if len(features) != total:
        raise RuntimeError(f"Incomplete centroid download: {len(features):,}/{total:,}")
    atomic_json(target, {"type": "FeatureCollection", "features": features})


def norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def find_col(columns, patterns: list[str]):
    for col in columns:
        n = norm(col)
        if any(re.search(p, n) for p in patterns):
            return col
    return None


def read_population(path: Path) -> dict[str, int]:
    xls = pd.ExcelFile(path, engine="openpyxl")
    selected = None
    for sheet in xls.sheet_names:
        preview = pd.read_excel(xls, sheet_name=sheet, header=None, nrows=40)
        for row in range(len(preview)):
            values = [norm(v) for v in preview.iloc[row].tolist()]
            if any(("lsoa" in v and ("code" in v or "cd" in v)) or v == "lsoa21cd" for v in values):
                selected = (sheet, row)
                break
        if selected:
            break
    if not selected:
        raise RuntimeError(f"Could not find LSOA code header. Workbook sheets: {xls.sheet_names}")
    sheet, header = selected
    df = pd.read_excel(xls, sheet_name=sheet, header=header)
    code_col = find_col(df.columns, [r"lsoa.*code", r"lsoa21cd", r"lsoacd"])
    if code_col is None:
        raise RuntimeError(f"Could not identify LSOA code column in {sheet}")
    year_col = next((c for c in df.columns if "2024" in norm(c) or norm(c) in {"mid2024", "2024"}), None)
    if year_col is None:
        raise RuntimeError(f"No mid-2024 population column found. Columns: {list(df.columns)}")
    work = df.copy()
    work["_code"] = work[code_col].astype(str).str.strip()
    work = work[work["_code"].str.startswith("E01")]
    sex_col = find_col(work.columns, [r"^sex$"])
    age_col = find_col(work.columns, [r"^age$", r"agegroup", r"ageband"])
    combined_total = False
    if sex_col is not None:
        sex_values = work[sex_col].astype(str).str.lower().str.strip()
        persons = work[sex_values.isin({"persons", "all persons", "both sexes", "total"})]
        if len(persons):
            work = persons
            if age_col is None:
                combined_total = True
    if age_col is not None:
        age_values = work[age_col].astype(str).str.lower().str.strip()
        all_ages = work[age_values.isin({"all ages", "all", "total", "all age groups"})]
        if len(all_ages):
            work = all_ages
            combined_total = True
    work["_pop"] = pd.to_numeric(work[year_col], errors="coerce")
    work = work.dropna(subset=["_pop"])
    # If ONS supplies an explicit all-ages total, use it once. Otherwise sum
    # mutually exclusive age rows (and, if needed, sex rows) per LSOA.
    grouped = work.groupby("_code")["_pop"]
    result = (grouped.max() if combined_total or (sex_col is None and age_col is None) else grouped.sum()).round().astype(int).to_dict()
    result = {k: v for k, v in result.items() if k.startswith("E01") and v >= 0}
    total = sum(result.values())
    if len(result) < 30_000 or not 45_000_000 <= total <= 65_000_000:
        raise RuntimeError(f"Population QA failed: {len(result):,} LSOAs, total {total:,}; expected England mid-2024 coverage")
    log(f"Population QA passed: {len(result):,} LSOAs; total {total:,}")
    return result


def prop_code(props: dict) -> str | None:
    for key, value in props.items():
        nk = norm(key)
        if nk in {"lsoa21cd", "lsoa2021code", "lsoacd", "lsoacode"}:
            return str(value).strip()
    for key, value in props.items():
        nk = norm(key)
        if "lsoa" in nk and ("cd" in nk or "code" in nk):
            return str(value).strip()
    return None


def read_fc(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("type") != "FeatureCollection" or not isinstance(data.get("features"), list):
        raise RuntimeError(f"Invalid FeatureCollection: {path}")
    return data["features"]


def read_clubs(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        clubs = list(csv.DictReader(f))
    if len(clubs) != 20:
        raise RuntimeError(f"Expected exactly 20 clubs in clubs.csv; found {len(clubs)}")
    for club in clubs:
        club["lat"] = float(club["lat"])
        club["lon"] = float(club["lon"])
    return clubs


def weighted_percentile(values: list[float], weights: list[int], percentile: float) -> float | None:
    pairs = sorted((float(v), float(w)) for v, w in zip(values, weights) if v is not None and w > 0)
    if not pairs:
        return None
    threshold = sum(w for _, w in pairs) * percentile
    cumulative = 0.0
    for value, weight in pairs:
        cumulative += weight
        if cumulative >= threshold:
            return value
    return pairs[-1][0]


def weighted_gini(values: list[float], weights: list[int]) -> float:
    pairs = sorted((float(v), float(w)) for v, w in zip(values, weights) if v is not None and w > 0)
    total_w = sum(w for _, w in pairs)
    weighted_sum = sum(v * w for v, w in pairs)
    if total_w <= 0 or weighted_sum <= 0:
        return 0.0
    cumulative = numerator = 0.0
    for value, weight in pairs:
        numerator += weight * value * (2 * cumulative + weight - total_w)
        cumulative += weight
    return max(0.0, min(1.0, numerator / (total_w * weighted_sum)))


def ors_matrix(api_key: str, origins: list[list[float]], destinations: list[list[float]]) -> tuple[list, list]:
    if len(origins) * len(destinations) > 3_500:
        raise RuntimeError("Matrix request exceeds ORS hosted limit of 3,500 origin-destination pairs")
    locations = origins + destinations
    payload = {
        "locations": locations,
        "sources": list(range(len(origins))),
        "destinations": list(range(len(origins), len(locations))),
        "metrics": ["duration", "distance"],
        "units": "km",
    }
    headers = {"Authorization": api_key, "Content-Type": "application/json", "User-Agent": UA}
    for attempt in range(6):
        response = requests.post(ORS_URL, json=payload, headers=headers, timeout=TIMEOUT)
        if response.status_code == 403:
            raise RuntimeError("ORS returned 403 (daily quota/plan restriction). Progress is checkpointed; rerun after quota reset.")
        if response.status_code == 429 or response.status_code >= 500:
            wait = min(90, int(response.headers.get("Retry-After", 2 ** attempt)))
            log(f"ORS HTTP {response.status_code}; retrying in {wait}s")
            time.sleep(wait)
            continue
        if not response.ok:
            raise RuntimeError(f"ORS HTTP {response.status_code}: {response.text[:700]}")
        data = response.json()
        if "durations" not in data or "distances" not in data:
            raise RuntimeError(f"Unexpected ORS matrix response: {str(data)[:700]}")
        return data["durations"], data["distances"]
    raise RuntimeError("ORS retry limit reached; saved progress can be resumed")


def main() -> None:
    api_key = os.environ.get("ORS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ORS_API_KEY is missing. Add it in GitHub Settings → Secrets and variables → Actions.")
    CACHE.mkdir(parents=True, exist_ok=True)
    pop_file = CACHE / "lsoa_population_mid2024.xlsx"
    centroid_file = CACHE / "lsoa_population_weighted_centroids.geojson"
    boundary_file = CACHE / "lsoa_boundaries_2021.geojson"
    download(POP_URL, pop_file, 100_000)
    download_centroids(centroid_file)  # target is the same file read below
    download(BOUNDARIES_URL, boundary_file, 100_000)
    population = read_population(pop_file)
    centroids = read_fc(centroid_file)
    boundaries = read_fc(boundary_file)
    clubs = read_clubs(ROOT / "clubs.csv")

    origins_by_code: dict[str, dict] = {}
    for feature in centroids:
        code = prop_code(feature.get("properties") or {})
        geom = feature.get("geometry") or {}
        coords = geom.get("coordinates") or []
        if not code or not code.startswith("E01") or code not in population or len(coords) < 2:
            continue
        lon, lat = float(coords[0]), float(coords[1])
        if -6.5 <= lon <= 2.2 and 49.5 <= lat <= 56.0:
            origins_by_code.setdefault(code, {"code": code, "lon": lon, "lat": lat, "population": population[code]})
    origins = sorted(origins_by_code.values(), key=lambda x: x["code"])
    if len(origins) < 30_000:
        raise RuntimeError(f"Centroid/population match too small: {len(origins):,}; refusing partial output")
    log(f"Matched origins: {len(origins):,}")

    checkpoint = CACHE / "ors_routing_checkpoint.json"
    routed: dict[str, dict] = {}
    if checkpoint.exists():
        try:
            saved = json.loads(checkpoint.read_text(encoding="utf-8"))
            if saved.get("club_codes") == [c["code"] for c in clubs]:
                routed = saved.get("routed", {})
                log(f"Resuming {len(routed):,} previously routed LSOAs")
        except Exception:
            log("Ignoring invalid routing checkpoint")
    destinations = [[c["lon"], c["lat"]] for c in clubs]
    pending = [p for p in origins if p["code"] not in routed]
    calls = math.ceil(len(pending) / CHUNK_ORIGINS)
    log(f"Routing remaining {len(pending):,} origins in {calls} ORS matrix requests")
    for start in range(0, len(pending), CHUNK_ORIGINS):
        chunk = pending[start:start + CHUNK_ORIGINS]
        durations, distances = ors_matrix(api_key, [[p["lon"], p["lat"]] for p in chunk], destinations)
        if len(durations) != len(chunk) or len(distances) != len(chunk):
            raise RuntimeError("ORS matrix returned an unexpected row count")
        for p, drow, krow in zip(chunk, durations, distances):
            valid = [(j, float(seconds)) for j, seconds in enumerate(drow) if seconds is not None and math.isfinite(float(seconds))]
            if not valid:
                continue
            j, seconds = min(valid, key=lambda item: item[1])
            km = krow[j]
            routed[p["code"]] = {
                **p, "minutes": seconds / 60.0,
                "distance_km": float(km) if km is not None else None,
                "club_code": clubs[j]["code"], "club_name": clubs[j]["name"],
            }
        atomic_json(checkpoint, {"club_codes": [c["code"] for c in clubs], "routed": routed})
        log(f"Routing checkpoint: {len(routed):,}/{len(origins):,}")
        if start + len(chunk) < len(pending):
            time.sleep(REQUEST_GAP)

    rows = [routed[p["code"]] for p in origins if p["code"] in routed]
    if len(rows) < 0.95 * len(origins):
        raise RuntimeError(f"Only {len(rows):,}/{len(origins):,} LSOAs routed. Checkpoint retained; refusing publication")
    by_code = {r["code"]: r for r in rows}
    output_features = []
    for feature in boundaries:
        props = feature.get("properties") or {}
        code = prop_code(props)
        if not code or not code.startswith("E01") or code not in by_code or not feature.get("geometry"):
            continue
        row = by_code[code]
        minutes = row["minutes"]
        band = "0-30" if minutes <= 30 else "30-60" if minutes <= 60 else "60-90" if minutes <= 90 else "90+"
        geom = shape(feature["geometry"]).simplify(0.00018, preserve_topology=True)
        output_features.append({
            "type": "Feature", "geometry": mapping(geom),
            "properties": {
                "lsoa": code, "population": int(row["population"]),
                "minutes": round(minutes, 1),
                "distance_km": round(row["distance_km"], 1) if row["distance_km"] is not None else None,
                "club_code": row["club_code"], "club_name": row["club_name"], "access_band": band,
            },
        })
    if len(output_features) < 0.95 * len(rows):
        raise RuntimeError(f"Only {len(output_features):,}/{len(rows):,} LSOAs matched boundaries; refusing publication")

    weights = [int(r["population"]) for r in rows]
    minutes = [float(r["minutes"]) for r in rows]
    total_pop = sum(weights)
    coverage = {}
    for threshold in (30, 60, 90):
        covered = sum(int(r["population"]) for r in rows if r["minutes"] <= threshold)
        coverage[str(threshold)] = {"population": covered, "share_pct": round(100 * covered / total_pop, 2)}
    catchments = []
    for club in clubs:
        subset = [r for r in rows if r["club_code"] == club["code"]]
        w = [int(r["population"]) for r in subset]
        m = [float(r["minutes"]) for r in subset]
        assigned = sum(w)
        catchments.append({
            "code": club["code"], "name": club["name"],
            "assigned_population": assigned, "lsoa_count": len(subset),
            "weighted_median_minutes": round(weighted_percentile(m, w, .5), 1) if subset else None,
            "weighted_p90_minutes": round(weighted_percentile(m, w, .9), 1) if subset else None,
            "within_30_pct": round(100 * sum(x for x, t in zip(w, m) if t <= 30) / assigned, 2) if assigned else None,
            "within_60_pct": round(100 * sum(x for x, t in zip(w, m) if t <= 60) / assigned, 2) if assigned else None,
            "within_90_pct": round(100 * sum(x for x, t in zip(w, m) if t <= 90) / assigned, 2) if assigned else None,
        })
    summary = {
        "title": "Fan Accessibility & Equity", "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "population_reference": "ONS LSOA mid-2024 population estimates",
        "geography_reference": "ONS LSOA 2021 population-weighted centroids and LSOA 2021 boundaries",
        "routing": "OpenRouteService driving-car matrix using OpenStreetMap road network",
        "model": "Fastest modeled driving time; not live traffic, matchday congestion, parking, public transport, or observed fan journeys.",
        "origin_count": len(origins), "routed_lsoa_count": len(rows), "mapped_lsoa_count": len(output_features),
        "population_total": total_pop, "coverage_by_minutes": coverage,
        "weighted_median_minutes": round(weighted_percentile(minutes, weights, .5), 1),
        "weighted_p90_minutes": round(weighted_percentile(minutes, weights, .9), 1),
        "population_weighted_gini": round(weighted_gini(minutes, weights), 4),
        "club_catchments": sorted(catchments, key=lambda x: x["assigned_population"], reverse=True),
        "sources": {
            "population": "https://www.ons.gov.uk/peoplepopulationandcommunity/populationestimates/datasets/lowersuperoutputareamidyearpopulationestimates",
            "centroids": "https://www.data.gov.uk/dataset/e3e903a6-1864-4083-8837-017b6bdf8cc5/lower-layer-super-output-areas-december-2021-ew-population-weighted-centroids1",
            "boundaries": "https://www.data.gov.uk/dataset/04c65a08ecff4858bffc16e9ca9356f4/lower-layer-super-output-areas-december-2021-boundaries-ew-bsc-v4",
            "routing": "https://openrouteservice.org/", "road_network": "https://www.openstreetmap.org/copyright",
        },
        "attribution": "Contains National Statistics data © Crown copyright and database right. Contains OS data © Crown copyright and database right. Routing: © openrouteservice.org by HeiGIT | Map data © OpenStreetMap contributors.",
        "limitations": ["LSOA centroid represents an area, not every resident.", "Population year (mid-2024) and geography vintage (2021) differ.", "Driving time is modeled and excludes live traffic, matchday congestion, parking, public transport, and observed fan behaviour.", "Nearest stadium catchment is based on fastest modeled driving time, not supporter allegiance."],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    geo_path = OUT_DIR / "fan_accessibility.geojson.gz"
    tmp_geo = geo_path.with_name(geo_path.name + ".part")
    with gzip.open(tmp_geo, "wt", encoding="utf-8", compresslevel=8) as f:
        json.dump({"type": "FeatureCollection", "name": "Fan Accessibility & Equity", "features": output_features}, f, separators=(",", ":"), ensure_ascii=False)
    tmp_geo.replace(geo_path)
    atomic_json(OUT_DIR / "fan_accessibility_summary.json", summary)
    # Final integrity checks: re-open both outputs before reporting success.
    with gzip.open(geo_path, "rt", encoding="utf-8") as f:
        check = json.load(f)
    check_summary = json.loads((OUT_DIR / "fan_accessibility_summary.json").read_text(encoding="utf-8"))
    if len(check.get("features", [])) != len(output_features) or check_summary["mapped_lsoa_count"] != len(output_features):
        raise RuntimeError("Output integrity check failed")
    log(f"SUCCESS: {len(output_features):,} LSOA polygons; population={total_pop:,}")
    log("Summary: " + json.dumps({k: summary[k] for k in ("weighted_median_minutes", "weighted_p90_minutes", "population_weighted_gini", "coverage_by_minutes")}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
