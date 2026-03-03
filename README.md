# Seattle Housing Analytics

Exploratory analysis of King County residential real estate using public assessor data.

## Data Source

[King County Department of Assessments — Data Download Portal](https://info.kingcounty.gov/assessor/datadownload/default.aspx)

Four datasets are used:

| Dataset | File | Description |
|---------|------|-------------|
| Real Property Sales | `EXTR_RPSale.csv` | All historical ownership transfers (2.4M records) |
| Residential Building | `EXTR_ResBldg.csv` | Physical attributes of residential structures |
| Parcel | `EXTR_Parcel.csv` | Land characteristics, views, waterfront, zoning |
| Lookup | `EXTR_LookUp.csv` | Code dictionary for all categorical fields |

> Raw data files are not committed to this repo (too large). Run the download script to fetch them locally.

## Project Structure

```
seattlle-housing-analytics/
├── scripts/
│   ├── download_kc_assessor_data.py   # Downloads zip files from KC portal
│   └── dataset_verification.py        # Validates field names & distributions
├── notebooks/
│   └── kc_housing_eda.ipynb           # Full EDA across all four datasets
├── data/                              # Local data directory (gitignored)
└── README.md
```

## Quickstart

```bash
# 1. Create and activate virtual environment
uv venv
source .venv/bin/activate

# 2. Install dependencies
uv pip install pandas numpy matplotlib seaborn jupyter

# 3. Download data
python scripts/download_kc_assessor_data.py

# 4. Verify data integrity
python scripts/dataset_verification.py

# 5. Launch EDA notebook
jupyter notebook notebooks/kc_housing_eda.ipynb
```

## EDA Highlights

- **Arms-length filter**: `SaleReason=1` + `PropertyClass=8` + `SalePrice > $10K`
- **Price trend**: Median SFR price rose sharply 2012–2018, surged again 2020–2022
- **Top predictors**: Living area, BldgGrade, EffectiveAge, waterfront location
- **Waterfront premium**: ~2.2% of parcels carry a significant price premium
- **Key data pitfall**: `YrRenovated=0` for 94.9% of records — requires `EffectiveAge` engineering

## Key Field Corrections (verified against actual CSVs)

| Research Note | Actual Data |
|---------------|-------------|
| `ViewUtilization` in Parcel | It is in **ResBldg** (Y/N flag); Parcel has 10 separate view columns |
| Field `WaterfrontLocation` | Actual field name is **`WfntLocation`** |
| `SaleReason=1` = arms-length | Confirmed — 59% of all records, no exclusion flag |
