# Spatial Competitive Burden Index (SCBI)

## What this measures
SCBI is an exploratory, relative comparison of estimated spatial travel burden across the 20 clubs in the supplied 2026/27 Atlas dataset. It is not a measure of club quality, competitive fairness, or causal impact on match results.

## Baseline formula
`SCBI = 0.35D + 0.25L + 0.25S + 0.15T`

Each component is converted to a 0–100 mid-percentile rank across the 20 clubs (ties receive the average rank).

| Component | Weight | Definition |
|---|---:|---|
| D — Total away distance | 35% | Sum of 19 straight-line stadium-to-stadium distances, calculated with the Atlas stadium coordinates. |
| L — Long-trip exposure | 25% | Mean trip severity across 19 away trips: <200 km = 0; 200–299 = 25; 300–399 = 60; ≥400 = 100. |
| S — Consecutive away rounds | 25% | Count of adjacent gameweek pairs where the club is away in both rounds. This does not infer elapsed rest hours. |
| T — Driving-time burden | 15% | Sum of OSRM driving durations from the supplied 20×20 `travel.json` matrix. |

## Baseline results
- Clubs: 20; away fixtures analysed: 380 (19 per club).
- Highest SCBI: Newcastle (93.4).
- Lowest SCBI: Coventry City (5.3).
- Mean SCBI: 50.0.
- Clubs within two ranking places across all three sensitivity scenarios: 14 of 20.

| Rank | Club | SCBI | Away km | Long-trip score | Consecutive away pairs | Driving hours | D | L | S | T |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | Newcastle | 93.4 | 5529 | 40.8 | 3 | 78.4 | 100.0 | 100.0 | 73.7 | 100.0 |
| 2 | Sunderland | 89.5 | 5398 | 38.7 | 3 | 77.4 | 94.7 | 94.7 | 73.7 | 94.7 |
| 3 | Brighton | 82.9 | 4310 | 33.4 | 3 | 64.7 | 84.2 | 89.5 | 73.7 | 84.2 |
| 4 | Ipswich Town | 77.6 | 4044 | 20.5 | 3 | 61.5 | 78.9 | 78.9 | 73.7 | 78.9 |
| 5 | Bournemouth | 71.1 | 4743 | 32.1 | 2 | 70.5 | 89.5 | 84.2 | 21.1 | 89.5 |
| 6 | Everton | 70.9 | 3889 | 17.4 | 3 | 59.8 | 73.7 | 65.8 | 73.7 | 68.4 |
| 7 | Liverpool | 68.3 | 3856 | 17.4 | 3 | 57.8 | 68.4 | 65.8 | 73.7 | 63.2 |
| 8 | Hull City | 62.8 | 3813 | 15.5 | 3 | 59.9 | 63.2 | 44.7 | 73.7 | 73.7 |
| 9 | Fulham | 48.7 | 3258 | 16.3 | 3 | 50.1 | 31.6 | 57.9 | 73.7 | 31.6 |
| 10 | Crystal Palace | 47.1 | 3410 | 18.4 | 2 | 55.5 | 42.1 | 73.7 | 21.1 | 57.9 |
| 11 | Leeds | 43.0 | 3607 | 15.5 | 2 | 51.9 | 57.9 | 44.7 | 21.1 | 42.1 |
| 12 | Chelsea | 42.8 | 3259 | 14.2 | 3 | 50.3 | 36.8 | 23.7 | 73.7 | 36.8 |
| 13 | Man United | 42.0 | 3444 | 15.5 | 2 | 53.3 | 52.6 | 44.7 | 21.1 | 47.4 |
| 14 | Man City | 40.9 | 3422 | 15.5 | 2 | 55.1 | 47.4 | 44.7 | 21.1 | 52.6 |
| 15 | Arsenal | 35.7 | 3231 | 14.2 | 3 | 50.0 | 21.1 | 23.7 | 73.7 | 26.3 |
| 16 | Aston Villa | 24.9 | 3035 | 5.3 | 3 | 44.9 | 10.5 | 7.9 | 73.7 | 5.3 |
| 17 | Brentford | 22.8 | 3236 | 14.2 | 2 | 48.6 | 26.3 | 23.7 | 21.1 | 15.8 |
| 18 | Tottenham | 19.9 | 3225 | 14.2 | 2 | 49.7 | 15.8 | 23.7 | 21.1 | 21.1 |
| 19 | Nott'm Forest | 10.7 | 2953 | 5.3 | 2 | 46.0 | 5.3 | 7.9 | 21.1 | 10.5 |
| 20 | Coventry City | 5.3 | 2914 | 3.9 | 2 | 43.7 | 0.0 | 0.0 | 21.1 | 0.0 |

## Weight sensitivity
The page recalculates club ranks under three alternative weight profiles:

| Scenario | D | L | S | T |
|---|---:|---:|---:|---:|
| Baseline | 35% | 25% | 25% | 15% |
| Distance-led | 50% | 20% | 20% | 10% |
| Schedule-led | 25% | 20% | 40% | 15% |
| Time-led | 25% | 20% | 20% | 35% |

| Club | Baseline rank | Distance-led | Schedule-led | Time-led | Rank range |
|---|---:|---:|---:|---:|---:|
| Newcastle | 1 | 1 | 1 | 1 | 0 |
| Sunderland | 2 | 2 | 2 | 2 | 0 |
| Brighton | 3 | 3 | 3 | 3 | 0 |
| Ipswich Town | 4 | 4 | 4 | 4 | 0 |
| Bournemouth | 5 | 5 | 8 | 5 | 3 |
| Everton | 6 | 6 | 5 | 6 | 1 |
| Liverpool | 7 | 7 | 6 | 7 | 1 |
| Hull City | 8 | 8 | 7 | 8 | 1 |
| Fulham | 9 | 11 | 9 | 10 | 2 |
| Crystal Palace | 10 | 10 | 12 | 9 | 3 |
| Leeds | 11 | 9 | 13 | 13 | 4 |
| Chelsea | 12 | 14 | 10 | 14 | 4 |
| Man United | 13 | 12 | 14 | 12 | 2 |
| Man City | 14 | 13 | 15 | 11 | 4 |
| Arsenal | 15 | 15 | 11 | 15 | 4 |
| Aston Villa | 16 | 17 | 16 | 17 | 1 |
| Brentford | 17 | 16 | 17 | 16 | 1 |
| Tottenham | 18 | 18 | 18 | 18 | 0 |
| Nott'm Forest | 19 | 19 | 19 | 19 | 0 |
| Coventry City | 20 | 20 | 20 | 20 | 0 |

## Data provenance and limitations
- `atlas.json` generated: 2026-11-25; source: Fantasy Premier League feed.
- `travel.json` generated: 2026-11-25; source: OSRM driving (https://router.project-osrm.org).
- The road matrix is OSRM car routing between stadium coordinates. It is not live traffic, rail, coach, or door-to-door fan travel.
- Stadium coordinates are approximate. Straight-line distance is not road mileage.
- The Atlas README notes 12 fixtures in gameweeks 36 and 37 were completed by elimination. Because S uses gameweek sequence only, it avoids treating inferred calendar dates as confirmed recovery intervals.
- Hour-based recovery-gap calculations are excluded until all relevant fixture dates and kick-off times are confirmed.
- The SCBI currently runs in browser JavaScript from `atlas.json` and `travel.json`. It is not yet a server-side or PostGIS calculation.
- The percentile transformation makes scores relative to this 20-club sample; a score is not an absolute physical burden scale and can change if the club set or data changes.
