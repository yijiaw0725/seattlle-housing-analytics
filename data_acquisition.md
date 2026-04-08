# Data Acquisition
### King County Housing Price Analysis

This document describes how all datasets were obtained — what was collected, where it came from, how it was downloaded, and what filters were applied before analysis.

---

## Section 1 — Data Sources

### 1.1 King County Assessor — Core Housing Data

**Source:** King County Assessor's Office Data Download Portal
(`info.kingcounty.gov/assessor/datadownload`)

**Access method:** The portal requires users to check a "terms of use" checkbox before download links appear on the page. Rather than doing this manually each time, the download script ([`scripts/download_kc_assessor_data.py`](scripts/download_kc_assessor_data.py)) automates this step: it submits the checkbox form in code, then downloads each zip file in small chunks — so large files (hundreds of MB) transfer reliably without loading everything into memory at once.

**Coverage:** Full historical records — no date filter is applied at download time, because the portal only offers complete bulk exports with no API for partial queries. Time filtering is applied during analysis (see below).

**Files downloaded:**

The four target files are declared explicitly in the download script:

```python
# scripts/download_kc_assessor_data.py

DOWNLOAD_DIR = "./kc_assessor_data"

TARGET_FILES = [
    "real property sales",
    "residential building",
    "parcel",
    "lookup",
]
```

| File | Contents | Raw rows | Raw columns |
|------|----------|----------|-------------|
| `EXTR_RPSale.csv` | Every recorded property sale — price, date, sale type, instrument, warnings | 2,415,964 | 24 |
| `EXTR_ResBldg.csv` | Residential building attributes — living area, year built, grade, condition, bedrooms, baths | 532,072 | 50 |
| `EXTR_Parcel.csv` | Parcel-level attributes — land use, 10 separate view columns, waterfront location and bank | 627,512 | 81 |
| `EXTR_LookUp.csv` | Code dictionary — maps numeric codes in the other three files to human-readable labels | 1,224 | 3 |

> **Note:** All four files use `latin-1` encoding (not UTF-8). The join key across tables is `PIN`, a 10-character parcel identifier constructed as `Major` (6 digits) + `Minor` (4 digits).

**Filters applied during analysis:**

To isolate genuine open-market single-family residential transactions, the following filters are applied before any modeling or EDA:

| Filter | Value | What it keeps |
|--------|-------|---------------|
| `SaleReason` | = 1 | Voluntary open-market sales only — excludes foreclosures, government acquisitions, and trust transfers where price is not set by the market |
| `SalePrice` | > \$10,000 | Transactions with a real price — excludes symbolic transfers (e.g. $1 deed between family members) that do not reflect market value |
| `PropertyClass` | = 8 | Residential properties with a building on the land — excludes vacant lots, commercial, and industrial parcels |
| `SaleYear` | 2015 – 2024 | A consistent 10-year window aligned with the crime dataset; avoids structural market shifts from the 2008 financial crisis |
| `NbrLivingUnits` | = 1 | Single-family homes only — excludes duplexes and apartment buildings, which follow different pricing dynamics |
| `SqFtTotLiving` | 200 – 15,000 sq ft | Homes of plausible size — removes likely data entry errors at both extremes |
| `YrBuilt` | 1870 – 2024 | Homes with a valid build year — removes records where the year is missing or defaulted to zero |

After filtering, **271,923 sales** remain as the analysis-ready dataset.

---

### 1.2 Seattle Police Department — Crime Incidents

**Source:** City of Seattle Open Data Portal — SPD Crime Data 2008–Present
(`data.seattle.gov`, dataset ID `tazs-3rd5`)

**Access method:** Socrata JSON API, paginated (the API returns data in batches of 1,000 rows at a time; the script loops through all batches automatically). Filters are applied at the query level so only relevant records are downloaded: incidents from 2015 onward with a valid GPS location.

**Coverage:** **2015 – 2024** (10 years), chosen to align with the KC Assessor analysis window so that crime scores and housing sales share the same time frame.

**Geographic scope:** SPD data covers **Seattle city limits only**, which is a subset of the broader King County area used in Section 1.1. King County has dozens of independent police departments — each city operates its own, with different data formats and varying levels of public availability. For simplicity, this study uses SPD data only. As a result, the crime-adjusted pricing model is limited to properties within Seattle; suburbs such as Bellevue, Redmond, and Kirkland are excluded from crime-related analysis.

**File produced:**

The date range and coordinate requirement are applied directly in the download query:

```python
# kc_crime_housing.ipynb

BASE_URL     = 'https://data.seattle.gov/resource/tazs-3rd5.json'
where_clause = (
    "offense_date >= '2015-01-01' "
    "AND offense_date < '2025-01-01' "
    "AND latitude != 'REDACTED'"
)
```

| File | Records | Notes |
|------|---------|-------|
| `crime_data/spd_crime_2015_2024.csv` | 733,596 | ~85% of all SPD records carry a mappable GPS location; the remaining ~15% have the coordinate field withheld for privacy reasons and are excluded |

---

### 1.3 Washington OSPI — School Quality

**Source:** Washington Office of Superintendent of Public Instruction (OSPI) Report Card
(`data.wa.gov`, dataset ID `x73g-mrqp`)

**Access method:** Socrata JSON API, paginated. The following filters are applied at query time:

| Filter | Value | Note |
|--------|-------|------|
| `countyname` | King | King County only |
| `organizationlevel` | School | The dataset contains results aggregated at multiple levels — statewide, district, and individual school. This filter selects individual school records, since school-level scores are what gets attached to housing data |
| `studentgroup` | All Students | Results are also broken down by race, income, and other subgroups. "All Students" is the overall figure with no demographic split, avoiding double-counting |
| `gradelevel` | All Grades | Same logic — selects the school-wide total rather than individual grade breakdowns |
| Test type | SBAC, WCAS | The two main Washington State standardized assessments. SBAC covers Math and ELA (grades 3–8 and 11); WCAS covers Science (grades 5, 8, and 11). The AIM assessment — designed for students with significant cognitive disabilities and scored on a different scale — is excluded to keep scores comparable across schools |

**Coverage:** **2023 – 2024 school year.** The goal of the school analysis in this study is to quantify how school quality affects property prices — not to track how school performance changes over time. A single recent snapshot is sufficient for this purpose. The 2023–24 year is the most recent complete year available at the time of analysis.

**Scope:** The dataset covers K–12 public schools across King County — 269 elementary schools, 74 middle schools, and 62 high schools. Washington State tests students in Math and ELA (grades 3–8 and 11) and Science (grades 5, 8, and 11). Each record is one school's pass rate for one subject — the share of that school's students who scored at or above the state's grade-level benchmark.

**File produced:**

| File | Contents |
|------|----------|
| `education_data/ospi_assessment_2324_king.csv` | Per-school pass rates for Math, ELA, and Science across King County public schools (K–12) |

**Metric used in analysis:** The data is processed in two steps. First, each school's three subject pass rates are averaged into one composite score. Then all schools within the same district are averaged together into a single district-level score, which is what gets joined to housing sales.

```python
# kc_schools_housing.ipynb

# Step 1 — school-level composite
school_scores['pct_composite'] = school_scores[['pct_math', 'pct_ela', 'pct_science']].mean(axis=1)

# Step 2 — district-level aggregate
district_scores = school_scores.groupby('districtname')['pct_composite'].mean()
```

So the final score attached to each property is the average pass rate across all schools — elementary, middle, and high — in that school district.

**Limitations.** For simplicity, this metric has some constraints: pass rate does not distinguish between barely passing and excelling; a single year may not represent a school's typical performance; and the district average combines all school levels despite elementary schools being most relevant to most buyers. That said, pass rate is the most standardized and consistently available measure across all King County schools, making it a practical baseline for comparing districts and quantifying the price premium associated with school quality.

---

### 1.4 King County GIS — Spatial Reference Data

To attach a school district label to each property, two pieces of information are needed: the geographic boundaries of each school district, and the coordinates of each parcel. KC Assessor's `EXTR_Parcel.csv` does not include latitude or longitude, so both must be sourced separately from the King County GIS portal (`gisdata.kingcounty.gov`) via ArcGIS REST API.

```python
# kc_schools_housing.ipynb

# School district boundaries — single request, returns GeoJSON polygons
GEO_URL = (
    'https://gisdata.kingcounty.gov/arcgis/rest/services/OpenDataPortal/'
    'district___base/MapServer/416/query?where=1%3D1&outFields=*&f=geojson'
)

# Parcel coordinates — paginated (~669K records, 1,000 per request)
COORDS_URL = (
    'https://gisdata.kingcounty.gov/arcgis/rest/services/'
    'OpenDataPortal/admin__address_point/MapServer/642/query'
)
```

With both datasets in hand, each parcel's coordinates are matched against the district boundary polygons to determine which school district it falls in — producing a simple PIN → school district lookup table used throughout the analysis.

**Files produced:**

| File | Contents |
|------|----------|
| `education_data/kc_school_districts.geojson` | School district boundary polygons for all of King County |
| `education_data/kc_parcel_coords.csv` | Latitude and longitude for each parcel PIN |
| `education_data/kc_pin_district_lookup.csv` | Final lookup: PIN → school district name |

---

### 1.5 Data Source Summary

| Category | Source | Time Range | Records (analysis-ready) | Access |
|----------|--------|------------|--------------------------|--------|
| Housing transactions | KC Assessor — RPSale | 2015 – 2024 | 271,923 SFR sales | Bulk zip download |
| Building attributes | KC Assessor — ResBldg | Full history | 516,765 SFR buildings | Bulk zip download |
| Parcel attributes | KC Assessor — Parcel | Current snapshot | 627,512 parcels | Bulk zip download |
| Code dictionary | KC Assessor — LookUp | Current snapshot | 1,224 codes | Bulk zip download |
| Crime incidents | SPD via Socrata API | 2015 – 2024 | 733,596 incidents | API (filtered at query) |
| School test scores | WA OSPI via Socrata API | 2023 – 2024 | King County public schools (K–12) | API (filtered at query) |
| School district boundaries | KC GIS ArcGIS REST | Current snapshot | 20 districts | ArcGIS REST API |
| Parcel coordinates | KC GIS ArcGIS REST | Current snapshot | 669,420 parcels | ArcGIS REST API |

---

## Section 2 — Acquisition Methodology

This section documents the technical approach used to retrieve each dataset, explains why a particular method was necessary, and highlights the key code responsible for each step.

---

### 2.1 Method A — Form-Based Web Scraping (KC Assessor)

**Why this approach is required**

The King County Assessor portal does not expose an API. Downloads are gated behind an ASP.NET disclaimer form — a user must check a checkbox before zip file links appear. There is no direct URL to the files without first submitting that form. A plain `requests.get()` on the zip URL fails with a redirect to the disclaimer page.

The solution is to simulate the browser interaction programmatically:

```python
# scripts/download_kc_assessor_data.py

def get_download_links(session):
    # Step 1: GET the page — extract all hidden ASP.NET fields (__VIEWSTATE, etc.)
    resp = session.get(BASE_URL)
    soup = BeautifulSoup(resp.text, "html.parser")
    form_data = {inp["name"]: inp.get("value", "")
                 for inp in soup.find_all("input") if inp.get("name")}

    # Step 2: Check the disclaimer checkbox, then POST
    form_data["kingcounty_gov$cphContent$CheckBox1"] = "on"
    resp2 = session.post(BASE_URL, data=form_data)

    # Step 3: Parse the unlocked page for .zip links
    soup2 = BeautifulSoup(resp2.text, "html.parser")
    links = {a.get_text(strip=True).lower(): a["href"]
             for a in soup2.find_all("a", href=True)
             if ".zip" in a["href"].lower()}
    return links
```

Files are then stream-downloaded in 64 KB chunks with live progress output (`download_file()` in the same script). The four target files are matched by partial link text (`"real property sales"`, `"residential building"`, `"parcel"`, `"lookup"`), making the script robust to minor wording changes on the portal page.

**Key trade-off:** Because the portal only offers complete bulk exports, **all historical records are downloaded** regardless of the analysis window. The 2015–2024 time filter is applied later in each notebook when loading the CSV, rather than at download time.

---

### 2.2 Method B — Paginated Socrata JSON API (Crime & School Data)

**Why this approach is preferred**

Both the SPD crime dataset and the OSPI school assessment dataset are hosted on Socrata-powered open data portals (`data.seattle.gov` and `data.wa.gov`). Socrata exposes a standard REST API that supports server-side filtering via a SQL-like `$where` clause, and returns JSON with a `$limit`/`$offset` pagination mechanism (maximum 1,000 rows per request).

Filtering at the query level avoids downloading millions of irrelevant rows — for crime data, this means excluding pre-2015 records and incidents with redacted GPS coordinates before any data leaves the server.

```python
# kc_crime_housing.ipynb — SPD crime download loop

BASE_URL     = 'https://data.seattle.gov/resource/tazs-3rd5.json'
where_clause = (
    "offense_date >= '2015-01-01' "
    "AND offense_date < '2025-01-01' "
    "AND latitude != 'REDACTED'"
)

all_records, offset = [], 0
while True:
    batch = requests.get(BASE_URL, params={
        '$where':  where_clause,
        '$limit':  1000,
        '$offset': offset,
    }).json()
    if not batch:
        break
    all_records.extend(batch)
    offset += 1000
```

The same pattern is used for OSPI school data (`data.wa.gov`, dataset ID `x73g-mrqp`), with additional filters for `countyname = King`, `organizationlevel = School`, and `studentgroup = All Students`.

**Cache-first pattern:** Both notebooks check whether the output CSV already exists before initiating the download loop. This prevents redundant multi-hour downloads on subsequent runs:

```python
if CRIME_FILE.exists():
    crime = pd.read_csv(CRIME_FILE, low_memory=False)
else:
    # ... run the paginated download loop
```

---

### 2.3 Method C — ArcGIS REST API (King County GIS Layers)

**Why this approach is required**

`EXTR_Parcel.csv` from the KC Assessor contains no latitude or longitude columns. To spatially join parcel records to school district boundaries, two geographic reference layers must be retrieved from the King County GIS MapServer.

Both layers are accessed through the ArcGIS Feature Service query endpoint, which returns GeoJSON directly:

```python
# kc_schools_housing.ipynb — school district boundary download

GEO_URL = (
    'https://gisdata.kingcounty.gov/arcgis/rest/services/OpenDataPortal/'
    'district___base/MapServer/416/query'
    '?where=1%3D1&outFields=*&f=geojson'
)
# Layer 416 = school district polygons (schdst_area)
# Layer 642 = address point layer — provides PIN → (lat, lon) mapping
```

The parcel centroid layer (~669,000 records) also requires pagination, fetched in batches of 1,000 using the ArcGIS `resultOffset` parameter. The resulting `kc_parcel_coords.csv` is then used in a point-in-polygon spatial join (via `geopandas`) to assign each parcel to its school district, producing the `kc_pin_district_lookup.csv` join table.

---

### 2.4 Acquisition Method Comparison

| Method | Data acquired | Filter at download? | Approx. download time |
|--------|--------------|--------------------|-----------------------|
| Form scraping + stream download | KC Assessor (4 zip files) | No — full history only | 5 – 10 min |
| Socrata JSON API (paginated) | SPD crime incidents | Yes — 2015–2024, valid coords | ~15 min |
| Socrata JSON API (paginated) | OSPI school scores | Yes — King County, school level | < 1 min |
| ArcGIS REST API | School district GeoJSON | No — complete layer | < 1 min |
| ArcGIS REST API (paginated) | Parcel centroids | No — complete layer | ~7 min |
