# Seattle Housing Analytics

Exploratory analysis of King County residential real estate — combining public assessor records, school quality data, and GIS boundaries to understand what drives housing prices.

---

## Notebooks

| Notebook | Description |
|----------|-------------|
| [`kc_housing_eda.ipynb`](kc_housing_eda.ipynb) | Full EDA across all four KC Assessor datasets: price trends, structural features, parcel attributes, waterfront premiums, and feature engineering |
| [`kc_schools_housing.ipynb`](kc_schools_housing.ipynb) | School quality analysis: OSPI pass rates, GIS spatial join (parcel → school district), and school quality premium quantification |

---

## Data Sources

### 1. KC Assessor (local, gitignored — run download script)

[King County Department of Assessments — Data Download Portal](https://info.kingcounty.gov/assessor/datadownload/default.aspx)

| Dataset | File | Rows | Description |
|---------|------|------|-------------|
| Real Property Sales | `EXTR_RPSale.csv` | 2.4M | All historical ownership transfers |
| Residential Building | `EXTR_ResBldg.csv` | 532K | Physical attributes of residential structures |
| Parcel | `EXTR_Parcel.csv` | 627K | Land characteristics, views, waterfront, zoning |
| Lookup | `EXTR_LookUp.csv` | 1.2K | Code dictionary for all categorical fields |

### 2. Education Data (committed — `education_data/`)

| File | Source | Description |
|------|--------|-------------|
| `ospi_assessment_2324_king.csv` | [WA OSPI via Socrata API](https://data.wa.gov/education/Report-Card-Assessment-Data-2023-24-School-Year/x73g-mrqp) | King County school-level Math/ELA/Science pass rates (2023–24) |
| `kc_school_districts.geojson` | [KC GIS MapServer layer 416](https://gisdata.kingcounty.gov/arcgis/rest/services/OpenDataPortal/district___base/MapServer/416) | School district boundary polygons |
| `kc_parcel_coords.csv` | [KC GIS address point layer 642](https://gisdata.kingcounty.gov/arcgis/rest/services/OpenDataPortal/admin__address_point/MapServer/642) | 669K parcel lat/lon coordinates (PIN → LAT/LON) |
| `kc_pin_district_lookup.csv` | Derived (spatial join) | PIN → school district lookup table |

---

## Project Structure

```
seattlle-housing-analytics/
├── kc_housing_eda.ipynb              # KC Assessor EDA (price trends, features, premiums)
├── kc_schools_housing.ipynb          # School quality + housing price analysis
├── education_data/
│   ├── ospi_assessment_2324_king.csv # OSPI school pass rates
│   ├── kc_school_districts.geojson   # School district boundaries (GIS)
│   ├── kc_parcel_coords.csv          # Parcel lat/lon from KC GIS
│   └── kc_pin_district_lookup.csv    # PIN → district spatial join result
├── scripts/
│   ├── download_kc_assessor_data.py  # Downloads KC Assessor zip files
│   └── dataset_verification.py       # Validates field names & distributions
└── README.md
```

---

## Quickstart

```bash
# 1. Create and activate virtual environment
uv venv
source .venv/bin/activate

# 2. Install dependencies
uv pip install pandas numpy matplotlib seaborn jupyter geopandas requests

# 3. Download KC Assessor data
python scripts/download_kc_assessor_data.py

# 4. Verify data integrity
python scripts/dataset_verification.py

# 5. Launch notebooks
jupyter notebook
```

> Education data (`education_data/`) is already committed — no separate download needed.

---

## Key Findings

### Housing EDA (`kc_housing_eda.ipynb`)
- **Arms-length filter**: `SaleReason=1` + `PropertyClass=8` + `SalePrice > $10K` keeps 881K clean SFR records
- **Price trend**: Median SFR price rose from ~$150K (1990) to ~$900K (2022); sharp run-ups in 2012–2018 and 2020–2022
- **Top predictors**: Living area and BldgGrade have the strongest price correlations (r > 0.55)
- **Waterfront premium**: ~2.2% of parcels; waterfront SFR prices ~150%+ above non-waterfront
- **Key data pitfall**: `YrRenovated=0` for 94.9% of records — requires `EffectiveAge` engineering

### School Quality Analysis (`kc_schools_housing.ipynb`)
- **District–price correlation**: r = 0.77 between OSPI composite pass rate and median district house price
- **School quality premium**: Top-quartile school district homes sell for **+98.6%** over bottom-quartile ($1.02M vs $511K median, SFR 2015–2024)
- **GIS pipeline**: 669K parcel coordinates → point-in-polygon → 100% district assignment, 99.5% OSPI match rate

---

## Key Field Corrections (verified against actual CSVs)

| Research Note | Actual Data |
|---------------|-------------|
| `ViewUtilization` in Parcel | It is in **ResBldg** (Y/N flag); Parcel has 10 separate view columns |
| Field `WaterfrontLocation` | Actual field name is **`WfntLocation`** |
| `SaleReason=1` = arms-length | Confirmed — 59% of all records |
