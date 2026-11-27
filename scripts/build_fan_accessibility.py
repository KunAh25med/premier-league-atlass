#!/usr/bin/env python3
"""Build population-weighted, road-network accessibility for Premier League stadiums.

Downloads ONS source data automatically, requests batched driving matrices from
OpenRouteService, and writes a compact GeoJSON.gz plus summary JSON for GitHub Pages.
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
from shapely.geometry import shape, mapping

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "fan-accessibility"
POP_URL = (
    "https://www.ons.gov.uk/file?uri=%2Fpeoplepopulationandcommunity%2Fpopulationandmigration%2Fpopulationestimates%2Fdatasets%2Flowersuperoutputareamidyearpopulationestimates%2Fmid2022revisednov2025tomid2024%2Fsapelsoasyoa20222024.xlsx"
)
CENTROIDS_URL = (
    CENTROIDS_FILE = DATA_DIR / "lsoa_population_weighted_centroids.geojson"
)
BOUNDARIES_URL = (
    "https://opendata.arcgis.com/api/v3/datasets/"
    "04c65a08ecff4858bffc16e9ca9356f4_0/downloads/data"
    "?format=geojson&spatialRefId=4326"
)
ORS_URL = "https://api.openrouteservice.org/v2/matrix/driving-car"
YEAR = "mid-2024"
CHUNK_ORIGINS = 150  # 150 x 20 = 3,000 matrix cells; ORS standard max is 3,500.
REQUEST_GAP_SECONDS = 1.6  # Stay below the standard 40 matrix requests/minute limit.
TIMEOUT = 180
UA = "PremierLeagueAtlas-FanAccessibility/1.0 (research portfolio)"


def log(message: str) -> None:
    print(message, flush=True)


     
def download(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)

    
def download_arcgis_layer(endpoint: str, target: Path) -> None:
    """Download an ArcGIS FeatureServer layer as GeoJSON in pages."""
    target.parent.mkdir(parents=True, exist_ok=True)

    # Reuse a valid cached file
    if target.exists() and target.stat().st_size > 100_000:
        try:
            with target.open("r", encoding="utf-8") as f:
                cached = json.load(f)

            if cached.get("type") == "FeatureCollection" and cached.get("features"):
                log(f"Using cached {target.name}")
                return
        except (OSError, json.JSONDecodeError):
            pass

    log(f"Downloading {target.name} from ONS FeatureServer ...")

    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    def get_json(params):
        response = session.get(
            f"{endpoint}/query",
            params=params,
            timeout=(30, 180),
        )
        response.raise_for_status()

        data = response.json()

        if "error" in data:
            raise RuntimeError(f"ArcGIS error: {data['error']}")

        return data

    # Get total feature count
    count_data = get_json({
        "where": "1=1",
        "returnCountOnly": "true",
        "f": "json",
    })

    total = int(count_data["count"])

    if total == 0:
        raise RuntimeError("ONS centroid layer returned zero records.")

    log(f"ONS centroid records available: {total:,}")

    features = []
    page_size = 2000
    offset = 0

    while offset < total:
        data = get_json({
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": "4326",
            "resultOffset": offset,
            "resultRecordCount": page_size,
            "orderByFields": "OBJECTID",
            "f": "geojson",
        })

        page = data.get("features", [])

        if not page:
            break

        features.extend(page)
        offset += len(page)

        log(f"Downloaded centroid records: {len(features):,}/{total:,}")

    if len(features) != total:
        raise RuntimeError(
            f"Incomplete centroid download: {len(features):,}/{total:,}"
        )

    output = {
        "type": "FeatureCollection",
        "features": features,
    }

    temp_target = target.with_name(target.name + ".part")

    try:
        with temp_target.open("w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False)

        temp_target.replace(target)

    finally:
        if temp_target.exists():
            temp_target.unlink()

    log(f"Downloaded {target.name}: {target.stat().st_size:,} bytes")


    # Validate an existing cached GeoJSON before reusing it.
    if target.exists() and target.stat().st_size > 100_000:
        if target.suffix == ".geojson":
            try:
                with target.open("r", encoding="utf-8") as f:
                    cached = json.load(f)
                if cached.get("type") == "FeatureCollection":
                    log(f"Using cached {target.name} ({target.stat().st_size:,} bytes)")
                    return
            except (json.JSONDecodeError, OSError):
                log(f"Cached {target.name} is invalid; downloading again.")
        else:
            log(f"Using cached {target.name} ({target.stat().st_size:,} bytes)")
            return

    log(f"Downloading {target.name} ...")

    temp_target = target.with_name(target.name + ".part")
    retry_delays = [5, 10, 20, 40, 60, 60, 60]

    for attempt in range(len(retry_delays) + 1):
        total = 0

        try:
            if temp_target.exists():
                temp_target.unlink()

            with requests.get(
                url,
                stream=True,
                timeout=(30, 240),
                headers={
                    "User-Agent": UA,
                    "Accept": "application/geo+json, application/json, */*",
                },
            ) as response:

                if response.status_code in (429, 500, 502, 503, 504):
                    raise requests.HTTPError(
                        f"Temporary server error: HTTP {response.status_code}",
                        response=response,
                    )

                response.raise_for_status()

                with temp_target.open("wb") as f:
                    for block in response.iter_content(1024 * 1024):
                        if block:
                            f.write(block)
                            total += len(block)

            if total < 10_000:
                raise RuntimeError(
                    f"{target.name} download too small: {total} bytes"
                )

            # Validate GeoJSON before replacing the final file.
            if target.suffix == ".geojson":
                with temp_target.open("r", encoding="utf-8") as f:
                    data = json.load(f)

                if (
                    data.get("type") != "FeatureCollection"
                    or not isinstance(data.get("features"), list)
                    or not data["features"]
                ):
                    raise RuntimeError(
                        f"{target.name} is not a valid non-empty GeoJSON FeatureCollection."
                    )

            temp_target.replace(target)
            log(f"Downloaded {target.name}: {total:,} bytes")
            return

        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None

            if status not in (429, 500, 502, 503, 504):
                raise

            error = exc

        except (requests.RequestException, RuntimeError, json.JSONDecodeError) as exc:
            error = exc

        finally:
            if temp_target.exists():
                temp_target.unlink()

        if attempt >= len(retry_delays):
            raise RuntimeError(
                f"Could not download {target.name} after "
                f"{attempt + 1} attempts. Last error: {error}"
            )

        wait = retry_delays[attempt]
        log(
            f"Download attempt {attempt + 1} failed: {error}. "
            f"Retrying in {wait} seconds..."
        )
        time.sleep(wait)
    target.parent.mkdir(parents=True, exist_ok=True)      # Validate an existing cached GeoJSON before reusing it.     if target.exists() and target.stat().st_size > 100_000:         if target.suffix == ".geojson":             try:                 with target.open("r", encoding="utf-8") as f:                     cached = json.load(f)                 if cached.get("type") == "FeatureCollection":                     log(f"Using cached {target.name} ({target.stat().st_size:,} bytes)")                     return             except (json.JSONDecodeError, OSError):                 log(f"Cached {target.name} is invalid; downloading again.")         else:             log(f"Using cached {target.name} ({target.stat().st_size:,} bytes)")             return      log(f"Downloading {target.name} ...")      temp_target = target.with_name(target.name + ".part")     retry_delays = [5, 10, 20, 40, 60, 60, 60]      for attempt in range(len(retry_delays) + 1):         total = 0          try:             if temp_target.exists():                 temp_target.unlink()              with requests.get(                 url,                 stream=True,                 timeout=(30, 240),                 headers={                     "User-Agent": UA,                     "Accept": "application/geo+json, application/json, */*",                 },             ) as response:                  if response.status_code in (429, 500, 502, 503, 504):                     raise requests.HTTPError(                         f"Temporary server error: HTTP {response.status_code}",                         response=response,                     )                  response.raise_for_status()                  with temp_target.open("wb") as f:                     for block in response.iter_content(1024 * 1024):                         if block:                             f.write(block)                             total += len(block)              if total < 10_000:                 raise RuntimeError(                     f"{target.name} download too small: {total} bytes"                 )              # Validate GeoJSON before replacing the final file.             if target.suffix == ".geojson":                 with temp_target.open("r", encoding="utf-8") as f:                     data = json.load(f)                  if (                     data.get("type") != "FeatureCollection"                     or not isinstance(data.get("features"), list)                     or not data["features"]                 ):                     raise RuntimeError(                         f"{target.name} is not a valid non-empty GeoJSON FeatureCollection."                     )              temp_target.replace(target)             log(f"Downloaded {target.name}: {total:,} bytes")             return          except requests.HTTPError as exc:             status = exc.response.status_code if exc.response is not None else None              if status not in (429, 500, 502, 503, 504):                 raise              error = exc          except (requests.RequestException, RuntimeError, json.JSONDecodeError) as exc:             error = exc          finally:             if temp_target.exists():                 temp_target.unlink()          if attempt >= len(retry_delays):             raise RuntimeError(                 f"Could not download {target.name} after "                 f"{attempt + 1} attempts. Last error: {error}"             )          wait = retry_delays[attempt]         log(             f"Download attempt {attempt + 1} failed: {error}. "             f"Retrying in {wait} seconds..."         )         time.sleep(wait)     target.parent.mkdir(parents=True, exist_ok=True)      # Validate an existing cached GeoJSON before reusing it.     if target.exists() and target.stat().st_size > 100_000:         if target.suffix == ".geojson":             try:                 with target.open("r", encoding="utf-8") as f:                     cached = json.load(f)                 if cached.get("type") == "FeatureCollection":                     log(f"Using cached {target.name} ({target.stat().st_size:,} bytes)")                     return             except (json.JSONDecodeError, OSError):                 log(f"Cached {target.name} is invalid; downloading again.")         else:             log(f"Using cached {target.name} ({target.stat().st_size:,} bytes)")             return      log(f"Downloading {target.name} ...")      temp_target = target.with_name(target.name + ".part")     retry_delays = [5, 10, 20, 40, 60, 60, 60]      for attempt in range(len(retry_delays) + 1):         total = 0          try:             if temp_target.exists():                 temp_target.unlink()              with requests.get(                 url,                 stream=True,                 timeout=(30, 240),                 headers={                     "User-Agent": UA,                     "Accept": "application/geo+json, application/json, */*",                 },             ) as response:                  if response.status_code in (429, 500, 502, 503, 504):                     raise requests.HTTPError(                         f"Temporary server error: HTTP {response.status_code}",                         response=response,                     )                  response.raise_for_status()                  with temp_target.open("wb") as f:                     for block in response.iter_content(1024 * 1024):                         if block:                             f.write(block)                             total += len(block)              if total < 10_000:                 raise RuntimeError(                     f"{target.name} download too small: {total} bytes"                 )              # Validate GeoJSON before replacing the final file.             if target.suffix == ".geojson":                 with temp_target.open("r", encoding="utf-8") as f:                     data = json.load(f)                  if (                     data.get("type") != "FeatureCollection"                     or not isinstance(data.get("features"), list)                     or not data["features"]                 ):                     raise RuntimeError(                         f"{target.name} is not a valid non-empty GeoJSON FeatureCollection."                     )              temp_target.replace(target)             log(f"Downloaded {target.name}: {total:,} bytes")             return          except requests.HTTPError as exc:             status = exc.response.status_code if exc.response is not None else None              if status not in (429, 500, 502, 503, 504):                 raise              error = exc          except (requests.RequestException, RuntimeError, json.JSONDecodeError) as exc:             error = exc          finally:             if temp_target.exists():                 temp_target.unlink()          if attempt >= len(retry_delays):             raise RuntimeError(                 f"Could not download {target.name} after "                 f"{attempt + 1} attempts. Last error: {error}"             )          wait = retry_delays[attempt]         log(             f"Download attempt {attempt + 1} failed: {error}. "             f"Retrying in {wait} seconds..."         )         time.sleep(wait)     target.parent.mkdir(parents=True, exist_ok=True)      # Validate an existing cached GeoJSON before reusing it.     if target.exists() and target.stat().st_size > 100_000:         if target.suffix == ".geojson":             try:                 with target.open("r", encoding="utf-8") as f:                     cached = json.load(f)                 if cached.get("type") == "FeatureCollection":                     log(f"Using cached {target.name} ({target.stat().st_size:,} bytes)")                     return             except (json.JSONDecodeError, OSError):                 log(f"Cached {target.name} is invalid; downloading again.")         else:             log(f"Using cached {target.name} ({target.stat().st_size:,} bytes)")             return      log(f"Downloading {target.name} ...")      temp_target = target.with_name(target.name + ".part")     retry_delays = [5, 10, 20, 40, 60, 60, 60]      for attempt in range(len(retry_delays) + 1):         total = 0          try:             if temp_target.exists():                 temp_target.unlink()              with requests.get(                 url,                 stream=True,                 timeout=(30, 240),                 headers={                     "User-Agent": UA,                     "Accept": "application/geo+json, application/json, */*",                 },             ) as response:                  if response.status_code in (429, 500, 502, 503, 504):                     raise requests.HTTPError(                         f"Temporary server error: HTTP {response.status_code}",                         response=response,                     )                  response.raise_for_status()                  with temp_target.open("wb") as f:                     for block in response.iter_content(1024 * 1024):                         if block:                             f.write(block)                             total += len(block)              if total < 10_000:                 raise RuntimeError(                     f"{target.name} download too small: {total} bytes"                 )              # Validate GeoJSON before replacing the final file.             if target.suffix == ".geojson":                 with temp_target.open("r", encoding="utf-8") as f:                     data = json.load(f)                  if (                     data.get("type") != "FeatureCollection"                     or not isinstance(data.get("features"), list)                     or not data["features"]                 ):                     raise RuntimeError(                         f"{target.name} is not a valid non-empty GeoJSON FeatureCollection."                     )              temp_target.replace(target)             log(f"Downloaded {target.name}: {total:,} bytes")             return          except requests.HTTPError as exc:             status = exc.response.status_code if exc.response is not None else None              if status not in (429, 500, 502, 503, 504):                 raise              error = exc          except (requests.RequestException, RuntimeError, json.JSONDecodeError) as exc:             error = exc          finally:             if temp_target.exists():                 temp_target.unlink()          if attempt >= len(retry_delays):             raise RuntimeError(                 f"Could not download {target.name} after "                 f"{attempt + 1} attempts. Last error: {error}"             )          wait = retry_delays[attempt]         log(             f"Download attempt {attempt + 1} failed: {error}. "             f"Retrying in {wait} seconds..."         )         time.sleep(wait)     target.parent.mkdir(parents=True, exist_ok=True)      # Validate an existing cached GeoJSON before reusing it.     if target.exists() and target.stat().st_size > 100_000:         if target.suffix == ".geojson":             try:                 with target.open("r", encoding="utf-8") as f:                     cached = json.load(f)                 if cached.get("type") == "FeatureCollection":                     log(f"Using cached {target.name} ({target.stat().st_size:,} bytes)")                     return             except (json.JSONDecodeError, OSError):                 log(f"Cached {target.name} is invalid; downloading again.")         else:             log(f"Using cached {target.name} ({target.stat().st_size:,} bytes)")             return      log(f"Downloading {target.name} ...")      temp_target = target.with_name(target.name + ".part")     retry_delays = [5, 10, 20, 40, 60, 60, 60]      for attempt in range(len(retry_delays) + 1):         total = 0          try:             if temp_target.exists():                 temp_target.unlink()              with requests.get(                 url,                 stream=True,                 timeout=(30, 240),                 headers={                     "User-Agent": UA,                     "Accept": "application/geo+json, application/json, */*",                 },             ) as response:                  if response.status_code in (429, 500, 502, 503, 504):                     raise requests.HTTPError(                         f"Temporary server error: HTTP {response.status_code}",                         response=response,                     )                  response.raise_for_status()                  with temp_target.open("wb") as f:                     for block in response.iter_content(1024 * 1024):                         if block:                             f.write(block)                             total += len(block)              if total < 10_000:                 raise RuntimeError(                     f"{target.name} download too small: {total} bytes"                 )              # Validate GeoJSON before replacing the final file.             if target.suffix == ".geojson":                 with temp_target.open("r", encoding="utf-8") as f:                     data = json.load(f)                  if (                     data.get("type") != "FeatureCollection"                     or not isinstance(data.get("features"), list)                     or not data["features"]                 ):                     raise RuntimeError(                         f"{target.name} is not a valid non-empty GeoJSON FeatureCollection."                     )              temp_target.replace(target)             log(f"Downloaded {target.name}: {total:,} bytes")             return          except requests.HTTPError as exc:             status = exc.response.status_code if exc.response is not None else None              if status not in (429, 500, 502, 503, 504):                 raise              error = exc          except (requests.RequestException, RuntimeError, json.JSONDecodeError) as exc:             error = exc          finally:             if temp_target.exists():                 temp_target.unlink()          if attempt >= len(retry_delays):             raise RuntimeError(                 f"Could not download {target.name} after "                 f"{attempt + 1} attempts. Last error: {error}"             )          wait = retry_delays[attempt]         log(             f"Download attempt {attempt + 1} failed: {error}. "             f"Retrying in {wait} seconds..."         )         time.sleep(wait)     target.parent.mkdir(parents=True, exist_ok=True)      # Validate an existing cached GeoJSON before reusing it.     if target.exists() and target.stat().st_size > 100_000:         if target.suffix == ".geojson":             try:                 with target.open("r", encoding="utf-8") as f:                     cached = json.load(f)                 if cached.get("type") == "FeatureCollection":                     log(f"Using cached {target.name} ({target.stat().st_size:,} bytes)")                     return             except (json.JSONDecodeError, OSError):                 log(f"Cached {target.name} is invalid; downloading again.")         else:             log(f"Using cached {target.name} ({target.stat().st_size:,} bytes)")             return      log(f"Downloading {target.name} ...")      temp_target = target.with_name(target.name + ".part")     retry_delays = [5, 10, 20, 40, 60, 60, 60]      for attempt in range(len(retry_delays) + 1):         total = 0          try:             if temp_target.exists():                 temp_target.unlink()              with requests.get(                 url,                 stream=True,                 timeout=(30, 240),                 headers={                     "User-Agent": UA,                     "Accept": "application/geo+json, application/json, */*",                 },             ) as response:                  if response.status_code in (429, 500, 502, 503, 504):                     raise requests.HTTPError(                         f"Temporary server error: HTTP {response.status_code}",                         response=response,                     )                  response.raise_for_status()                  with temp_target.open("wb") as f:                     for block in response.iter_content(1024 * 1024):                         if block:                             f.write(block)                             total += len(block)              if total < 10_000:                 raise RuntimeError(                     f"{target.name} download too small: {total} bytes"                 )              # Validate GeoJSON before replacing the final file.             if target.suffix == ".geojson":                 with temp_target.open("r", encoding="utf-8") as f:                     data = json.load(f)                  if (                     data.get("type") != "FeatureCollection"                     or not isinstance(data.get("features"), list)                     or not data["features"]                 ):                     raise RuntimeError(                         f"{target.name} is not a valid non-empty GeoJSON FeatureCollection."                     )              temp_target.replace(target)             log(f"Downloaded {target.name}: {total:,} bytes")             return          except requests.HTTPError as exc:             status = exc.response.status_code if exc.response is not None else None              if status not in (429, 500, 502, 503, 504):                 raise              error = exc          except (requests.RequestException, RuntimeError, json.JSONDecodeError) as exc:             error = exc          finally:             if temp_target.exists():                 temp_target.unlink()          if attempt >= len(retry_delays):             raise RuntimeError(                 f"Could not download {target.name} after "                 f"{attempt + 1} attempts. Last error: {error}"             )          wait = retry_delays[attempt]         log(             f"Download attempt {attempt + 1} failed: {error}. "             f"Retrying in {wait} seconds..."         )         time.sleep(wait)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 100_000:
        log(f"Using cached {target.name} ({target.stat().st_size:,} bytes)")
        return
    log(f"Downloading {target.name} ...")
    with requests.get(url, stream=True, timeout=TIMEOUT, headers={"User-Agent": UA}) as r:
        r.raise_for_status()
        total = 0
        with target.open("wb") as f:
            for block in r.iter_content(1024 * 1024):
                if block:
                    f.write(block)
                    total += len(block)
    if total < 10_000:
        raise RuntimeError(f"{target.name} download looks too small ({total} bytes).")
    log(f"Downloaded {target.name}: {total:,} bytes")


def norm(s: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s).strip().lower())


def find_col(columns, patterns):
    for c in columns:
        n = norm(c)
        if any(re.search(p, n) for p in patterns):
            return c
    return None


def read_population(path: Path) -> dict[str, int]:
    """Read the ONS workbook without assuming a fixed sheet/header row."""
    xls = pd.ExcelFile(path, engine="openpyxl")
    selected = None
    for sheet in xls.sheet_names:
        preview = pd.read_excel(xls, sheet_name=sheet, header=None, nrows=35)
        for header in range(min(35, len(preview))):
            vals = [str(v) for v in preview.iloc[header].tolist()]
            code_col = next((v for v in vals if re.search(r"lsoa.*(code|cd)|lsoa21cd", norm(v))), None)
            if code_col:
                selected = (sheet, header)
                break
        if selected:
            break
    if not selected:
        raise RuntimeError(f"Could not find an LSOA code header in ONS workbook. Sheets: {xls.sheet_names}")

    sheet, header = selected
    df = pd.read_excel(xls, sheet_name=sheet, header=header)
    code_col = find_col(df.columns, [r"lsoa.*code", r"lsoa21cd", r"lsoacd"])
    if code_col is None:
        raise RuntimeError(f"Could not identify LSOA code column in sheet {sheet}: {list(df.columns)}")

    year_col = next((c for c in df.columns if "2024" in norm(c) or norm(c) in {"mid2024", "2024"}), None)
    total_col = next((c for c in df.columns if norm(c) in {
        "total", "allages", "totalpopulation", "persons", "allpersons", "population"
    }), None)
    sex_col = find_col(df.columns, [r"^sex$", r"sex"])
    age_col = find_col(df.columns, [r"^age$", r"agegroup", r"ageband"])

    if year_col is not None:
        work = df.copy()
        work["code"] = work[code_col].astype(str).str.strip()
        work = work[work["code"].str.startswith("E01")]

        # Prefer an explicit Persons / All ages row if ONS supplies one.
        if sex_col is not None:
            sex_values = work[sex_col].astype(str).str.lower().str.strip()
            persons = work[sex_values.isin({"persons", "all persons", "both sexes", "total"})]
            if len(persons):
                work = persons

        if age_col is not None:
            age_values = work[age_col].astype(str).str.lower().str.strip()
            all_ages = work[age_values.isin({"all ages", "all", "total", "all age groups"})]
            if len(all_ages):
                work = all_ages

        work["pop"] = pd.to_numeric(work[year_col], errors="coerce")
        work = work.dropna(subset=["pop"])
        # If no combined total row exists, mutually exclusive age/sex rows are summed.
        result = work.groupby("code")["pop"].sum().round().astype(int).to_dict()
    elif total_col is not None:
        values = pd.to_numeric(df[total_col], errors="coerce")
        work = pd.DataFrame({"code": df[code_col].astype(str).str.strip(), "pop": values})
        work = work[work["code"].str.startswith("E01")]
        work = work.dropna(subset=["pop"])
        result = work.groupby("code")["pop"].max().round().astype(int).to_dict()
    else:
        raise RuntimeError(
            "ONS workbook has an LSOA code but no recognisable mid-2024 or total population column. "
            f"Sheet={sheet}; columns={list(df.columns)}"
        )

    result = {k: v for k, v in result.items() if k.startswith("E01") and v >= 0}
    if len(result) < 30_000:
        raise RuntimeError(f"Only {len(result):,} England LSOAs found in population workbook; refusing partial output.")
    log(f"Population rows: {len(result):,}; total={sum(result.values()):,}")
    return result


def prop_code(props: dict) -> str | None:
    for key, value in props.items():
        nk = norm(key)
        if nk in {"lsoa21cd", "lsoa2021code", "lsoacd", "lsoacode"}:
            return str(value).strip()
    for key, value in props.items():
        if "lsoa" in norm(key) and ("cd" in norm(key) or "code" in norm(key)):
            return str(value).strip()
    return None


def read_feature_collection(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("type") != "FeatureCollection" or not isinstance(data.get("features"), list):
        raise RuntimeError(f"{path.name} is not a valid GeoJSON FeatureCollection.")
    return data["features"]


def read_clubs(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        clubs = list(csv.DictReader(f))
    if len(clubs) != 20:
        raise RuntimeError(f"Expected 20 clubs in clubs.csv; found {len(clubs)}.")
    for c in clubs:
        c["lat"] = float(c["lat"])
        c["lon"] = float(c["lon"])
    return clubs


def weighted_percentile(values, weights, percentile: float) -> float | None:
    pairs = sorted((float(v), float(w)) for v, w in zip(values, weights) if v is not None and w > 0)
    if not pairs:
        return None
    total = sum(w for _, w in pairs)
    threshold = total * percentile
    running = 0.0
    for value, weight in pairs:
        running += weight
        if running >= threshold:
            return value
    return pairs[-1][0]


def weighted_gini(values, weights) -> float | None:
    pairs = sorted((float(v), float(w)) for v, w in zip(values, weights) if v is not None and w > 0)
    if not pairs:
        return None
    total_w = sum(w for _, w in pairs)
    mean_sum = sum(v * w for v, w in pairs)
    if total_w <= 0 or mean_sum <= 0:
        return 0.0
    cumulative = 0.0
    numerator = 0.0
    for value, weight in pairs:
        numerator += weight * value * (2 * cumulative + weight - total_w)
        cumulative += weight
    return max(0.0, min(1.0, numerator / (total_w * mean_sum)))


def ors_matrix(api_key: str, origins: list[list[float]], destinations: list[list[float]]) -> tuple[list, list]:
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
        if response.status_code == 429 or response.status_code >= 500:
            wait = min(90, int(response.headers.get("Retry-After", 2 ** attempt)))
            log(f"ORS {response.status_code}; retrying in {wait}s")
            time.sleep(wait)
            continue
        if not response.ok:
            raise RuntimeError(f"OpenRouteService error {response.status_code}: {response.text[:800]}")
        data = response.json()
        if "durations" not in data or "distances" not in data:
            raise RuntimeError(f"Unexpected ORS response: {str(data)[:800]}")
        return data["durations"], data["distances"]
    raise RuntimeError("OpenRouteService retry limit reached. Check API quota and service status.")


def main() -> None:
    api_key = os.environ.get("ORS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing ORS_API_KEY environment variable. Add it as a GitHub Actions secret.")

    cache = ROOT / ".cache" / "fan-accessibility"
    pop_xlsx = cache / "lsoa_population_2024.xlsx"
    centroids_file = cache / "lsoa_population_weighted_centroids.geojson"
    boundaries_file = cache / "lsoa_boundaries_2021.geojson"
    download(POP_URL, pop_xlsx)
    download_arcgis_layer(CENTROIDS_URL, CENTROIDS_FILE)
    download(BOUNDARIES_URL, boundaries_file)
    population = read_population(pop_xlsx)
    centroid_features = read_feature_collection(centroids_file)
    boundary_features = read_feature_collection(boundaries_file)
    clubs = read_clubs(ROOT / "clubs.csv")

    # ONS centroid geometry is requested in EPSG:4326; filter to England LSOAs.
    origins = []
    for feature in centroid_features:
        code = prop_code(feature.get("properties") or {})
        geom = feature.get("geometry") or {}
        if not code or not code.startswith("E01") or code not in population:
            continue
        coords = geom.get("coordinates") or []
        if len(coords) < 2:
            continue
        lon, lat = float(coords[0]), float(coords[1])
        if not (-6.5 <= lon <= 2.2 and 49.5 <= lat <= 56.0):
            continue
        origins.append({"code": code, "lon": lon, "lat": lat, "population": population[code]})

    # De-duplicate by code, retaining the first valid centroid.
    dedup = {}
    for item in origins:
        dedup.setdefault(item["code"], item)
    origins = list(dedup.values())
    if len(origins) < 30_000:
        raise RuntimeError(f"Only {len(origins):,} England LSOA centroids matched population. Refusing partial output.")
    log(f"Matched origin points: {len(origins):,}")

    destinations = [[c["lon"], c["lat"]] for c in clubs]
    best_minutes = [None] * len(origins)
    best_km = [None] * len(origins)
    best_club = [None] * len(origins)

    calls = math.ceil(len(origins) / CHUNK_ORIGINS)
    if calls > 450:
        raise RuntimeError(f"Estimated {calls} matrix calls exceeds the safe daily quota budget.")
    log(f"Routing {len(origins):,} origins to {len(clubs)} stadiums in {calls} matrix calls.")
    for start in range(0, len(origins), CHUNK_ORIGINS):
        chunk = origins[start:start + CHUNK_ORIGINS]
        coords = [[p["lon"], p["lat"]] for p in chunk]
        durations, distances = ors_matrix(api_key, coords, destinations)
        for i, row in enumerate(durations):
            valid = [(j, value) for j, value in enumerate(row) if value is not None and math.isfinite(float(value))]
            if not valid:
                continue
            j, seconds = min(valid, key=lambda x: float(x[1]))
            distance = distances[i][j]
            index = start + i
            best_minutes[index] = float(seconds) / 60.0
            best_km[index] = float(distance) if distance is not None else None
            best_club[index] = j
        done = min(start + len(chunk), len(origins))
        log(f"Routed {done:,}/{len(origins):,} origins")
        if done < len(origins):
            time.sleep(REQUEST_GAP_SECONDS)

    # Keep only valid routed origins.
    rows = []
    for i, p in enumerate(origins):
        if best_minutes[i] is None or best_club[i] is None:
            continue
        j = best_club[i]
        rows.append({
            **p,
            "minutes": best_minutes[i],
            "distance_km": best_km[i],
            "club_code": clubs[j]["code"],
            "club_name": clubs[j]["name"],
        })
    if len(rows) < 0.95 * len(origins):
        raise RuntimeError(f"Only {len(rows):,}/{len(origins):,} origins routed. Refusing to publish incomplete coverage.")

    # Join travel attributes to official LSOA polygons, simplify only for web delivery.
    by_code = {r["code"]: r for r in rows}
    features_out = []
    for feature in boundary_features:
        props = feature.get("properties") or {}
        code = prop_code(props)
        if not code or not code.startswith("E01") or code not in by_code:
            continue
        row = by_code[code]
        minutes = row["minutes"]
        band = "0-30" if minutes <= 30 else "30-60" if minutes <= 60 else "60-90" if minutes <= 90 else "90+"
        geom = shape(feature["geometry"])
        geom = geom.simplify(0.00018, preserve_topology=True)
        features_out.append({
            "type": "Feature",
            "geometry": mapping(geom),
            "properties": {
                "lsoa": code,
                "population": int(row["population"]),
                "minutes": round(minutes, 1),
                "distance_km": round(row["distance_km"], 1) if row["distance_km"] is not None else None,
                "club_code": row["club_code"],
                "club_name": row["club_name"],
                "access_band": band,
            },
        })
    if len(features_out) < 0.95 * len(rows):
        raise RuntimeError(f"Only {len(features_out):,} routed LSOAs matched polygons. Refusing partial output.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    geojson = {"type": "FeatureCollection", "name": "Fan Accessibility & Equity", "features": features_out}
    geo_path = OUT_DIR / "fan_accessibility.geojson.gz"
    with gzip.open(geo_path, "wt", encoding="utf-8", compresslevel=8) as f:
        json.dump(geojson, f, separators=(",", ":"), ensure_ascii=False)

    weights = [r["population"] for r in rows]
    minutes = [r["minutes"] for r in rows]
    total_pop = int(sum(weights))
    coverage = {}
    for threshold in (30, 60, 90):
        covered = int(sum(r["population"] for r in rows if r["minutes"] <= threshold))
        coverage[str(threshold)] = {
            "population": covered,
            "share_pct": round(100 * covered / total_pop, 2) if total_pop else None,
        }

    club_summary = []
    for club in clubs:
        subset = [r for r in rows if r["club_code"] == club["code"]]
        w = [r["population"] for r in subset]
        m = [r["minutes"] for r in subset]
        assigned_pop = int(sum(w))
        club_summary.append({
            "code": club["code"],
            "name": club["name"],
            "assigned_population": assigned_pop,
            "lsoa_count": len(subset),
            "weighted_median_minutes": round(weighted_percentile(m, w, 0.5), 1) if subset else None,
            "weighted_p90_minutes": round(weighted_percentile(m, w, 0.9), 1) if subset else None,
            "within_30_pct": round(100 * sum(x for x, t in zip(w, m) if t <= 30) / assigned_pop, 2) if assigned_pop else None,
            "within_60_pct": round(100 * sum(x for x, t in zip(w, m) if t <= 60) / assigned_pop, 2) if assigned_pop else None,
            "within_90_pct": round(100 * sum(x for x, t in zip(w, m) if t <= 90) / assigned_pop, 2) if assigned_pop else None,
        })

    summary = {
        "title": "Fan Accessibility & Equity",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "population_reference": "ONS LSOA mid-2024 estimates (released 7 November 2025)",
        "geography_reference": "ONS LSOA 2021 population-weighted centroids and LSOA 2021 boundaries",
        "routing": "OpenRouteService driving-car matrix based on OpenStreetMap road network",
        "model": "Fastest modeled driving time; no live traffic, matchday congestion, parking, public transport, or actual fan travel behavior.",
        "origin_count": len(origins),
        "routed_lsoa_count": len(rows),
        "mapped_lsoa_count": len(features_out),
        "population_total": total_pop,
        "coverage_by_minutes": coverage,
        "weighted_median_minutes": round(weighted_percentile(minutes, weights, 0.5), 1),
        "weighted_p90_minutes": round(weighted_percentile(minutes, weights, 0.9), 1),
        "population_weighted_gini": round(weighted_gini(minutes, weights), 4),
        "club_catchments": sorted(club_summary, key=lambda x: x["assigned_population"], reverse=True),
        "sources": {
            "population": "https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationestimates/datasets/lowersuperoutputareamidyearpopulationestimates",
            "centroids": "https://www.data.gov.uk/dataset/e3e903a6-1864-4083-8837-017b6bdf8cc5/lower-layer-super-output-areas-december-2021-ew-population-weighted-centroids1",
            "boundaries": "https://www.data.gov.uk/dataset/04c65a08ecff4858bffc16e9ca9356f4/lower-layer-super-output-areas-december-2021-boundaries-ew-bsc-v4",
            "routing": "https://openrouteservice.org/",
            "road_network": "https://www.openstreetmap.org/copyright",
        },
        "licensing": "ONS geography contains ONS/Ordnance Survey rights; check ONS Geography Licence and attribution before redistribution. OpenStreetMap data is ODbL.",
    }
    (OUT_DIR / "fan_accessibility_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log(f"SUCCESS: {len(features_out):,} polygons; population={total_pop:,}; output={geo_path}")
    log("Summary: " + json.dumps({k: summary[k] for k in ["weighted_median_minutes", "weighted_p90_minutes", "population_weighted_gini", "coverage_by_minutes"]}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
