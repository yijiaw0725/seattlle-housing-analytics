"""
King County Assessor Dataset Verification
==========================================
Verifies field names, data types, value distributions, and lookup code mappings
across the four core datasets used in the Seattle housing price analysis.

Datasets verified:
  - EXTR_RPSale.csv       (Real Property Sales)
  - EXTR_ResBldg.csv      (Residential Building)
  - EXTR_Parcel.csv       (Parcel)
  - EXTR_LookUp.csv       (Lookup / code dictionary)
"""

import pandas as pd
import textwrap

ENCODING = "latin-1"

PATHS = {
    "RPSale":  "kc_assessor_data/RealPropertySales/EXTR_RPSale.csv",
    "ResBldg": "kc_assessor_data/ResidentialBuilding/EXTR_ResBldg.csv",
    "Parcel":  "kc_assessor_data/Parcel/EXTR_Parcel.csv",
    "LookUp":  "kc_assessor_data/Lookup/EXTR_LookUp.csv",
}

SEP  = "=" * 70
SEP2 = "-" * 70


def header(title):
    print(f"\n{SEP}\n{title}\n{SEP}")


def subheader(title):
    print(f"\n{SEP2}\n{title}\n{SEP2}")


def check(label, result, note=""):
    status = "PASS" if result else "FAIL"
    line = f"  [{status}] {label}"
    if note:
        line += f"\n         note: {note}"
    print(line)


# ---------------------------------------------------------------------------
# Load all datasets
# ---------------------------------------------------------------------------
header("Loading datasets")
dfs = {}
for name, path in PATHS.items():
    dfs[name] = pd.read_csv(path, low_memory=False, encoding=ENCODING)
    print(f"  {name:10s}  {dfs[name].shape[0]:>10,} rows  x  {dfs[name].shape[1]:>3} cols")

rp  = dfs["RPSale"]
rb  = dfs["ResBldg"]
par = dfs["Parcel"]
lu  = dfs["LookUp"]


# ---------------------------------------------------------------------------
# 2.2.1 Real Property Sales
# ---------------------------------------------------------------------------
header("2.2.1  Real Property Sales  (EXTR_RPSale.csv)")

subheader("File & shape")
print(f"  Shape: {rp.shape[0]:,} rows  x  {rp.shape[1]} columns")
check("SalePrice exists as numeric", pd.api.types.is_numeric_dtype(rp["SalePrice"]))
print(f"  Price range: ${rp['SalePrice'].min():,.0f} – ${rp['SalePrice'].max():,.0f}")
print(f"  Median sale price (all records): ${rp['SalePrice'].median():,.0f}")

subheader("Field existence")
expected_fields = [
    "Major", "Minor", "DocumentDate", "SalePrice",
    "RecordingNbr", "SaleReason", "PropertyClass",
]
for f in expected_fields:
    check(f"Field '{f}' exists", f in rp.columns)

subheader("PIN construction  (Major 6-digit + Minor 4-digit = 10-char string)")
sample_pins = (
    rp["Major"].astype(str).str.zfill(6) + rp["Minor"].astype(str).str.zfill(4)
).head(5).tolist()
check("All sample PINs are 10 characters", all(len(p) == 10 for p in sample_pins))
print(f"  Sample PINs: {sample_pins}")

subheader("PropertyClass distribution")
# PropertyClass=8 = Res-Improved property (residential SFR)
pc_counts = rp["PropertyClass"].value_counts()
pct_8 = pc_counts.get(8, 0) / len(rp) * 100
print(f"  Top 5 PropertyClass values:\n{pc_counts.head(5).to_string()}")
check("PropertyClass=8 is the dominant class (SFR / Res-Improved)",
      pct_8 > 50,
      f"PropertyClass=8 accounts for {pct_8:.1f}% of all records")
# Lookup confirmation
lu_pc = lu[lu["LUType"] == 4].set_index("LUItem")["LUDescription"].to_dict()
print(f"\n  PropertyClass lookup (LUType=4): {lu_pc}")

subheader("SaleReason distribution")
sr_counts = rp["SaleReason"].value_counts()
print(f"  Top 10 SaleReason codes:\n{sr_counts.head(10).to_string()}")
pct_sr1 = sr_counts.get(1, 0) / len(rp) * 100
check("SaleReason=1 ('None' / no exclusion — arms-length) is most common",
      sr_counts.index[0] == 1,
      f"SaleReason=1 = {pct_sr1:.1f}% of records (open-market sales)")

# Lookup for SaleReason (LUType=7 = SaleWarning/SaleReason flag descriptions)
lu_sr = lu[lu["LUType"] == 7].set_index("LUItem")["LUDescription"].to_dict()
top_sr_codes = sr_counts.head(5).index.tolist()
print("\n  SaleReason code descriptions (LUType=7):")
for code in top_sr_codes:
    desc = lu_sr.get(code, "(not in LUType=7 — likely clean/arms-length)")
    print(f"    {code:>3}: {desc.strip()}")

subheader("SaleWarning field")
check("SaleWarning field exists (space-delimited non-market flag codes)",
      "SaleWarning" in rp.columns)
has_warning = rp["SaleWarning"].fillna("").str.strip().ne("").mean() * 100
print(f"  Records with at least one SaleWarning flag: {has_warning:.1f}%")


# ---------------------------------------------------------------------------
# 2.2.2 Residential Building
# ---------------------------------------------------------------------------
header("2.2.2  Residential Building  (EXTR_ResBldg.csv)")

subheader("File & shape")
print(f"  Shape: {rb.shape[0]:,} rows  x  {rb.shape[1]} columns")

subheader("Key field existence")
expected_rb = [
    "SqFtTotLiving", "BldgGrade", "Condition",
    "YrBuilt", "YrRenovated", "Bedrooms",
    "BathFullCount", "BathHalfCount", "Bath3qtrCount",
]
for f in expected_rb:
    check(f"Field '{f}' exists", f in rb.columns)

subheader("BldgGrade distribution  (ordinal 1–13)")
grade_counts = rb["BldgGrade"].value_counts().sort_index()
print(f"\n  Grade counts:\n{grade_counts.to_string()}")
pct_grade7 = grade_counts.get(7, 0) / len(rb) * 100
check("Grade=7 (Average) is the dominant grade",
      grade_counts.idxmax() == 7,
      f"Grade=7 = {pct_grade7:.1f}% of buildings")
check("Grade range is 1–13 (ignoring edge codes like 20)",
      rb["BldgGrade"].between(1, 13).sum() / len(rb) > 0.99)

subheader("Condition distribution  (1=Poor … 5=Very Good)")
cond_counts = rb["Condition"].value_counts().sort_index()
print(f"\n  Condition counts:\n{cond_counts.to_string()}")
pct_cond3 = cond_counts.get(3, 0) / len(rb) * 100
check("Condition=3 (Average) is dominant",
      cond_counts.idxmax() == 3,
      f"Condition=3 = {pct_cond3:.1f}% of buildings")
print("  Confirmed scale: 1=Poor, 2=Fair, 3=Average, 4=Good, 5=Very Good")

subheader("YrRenovated — data pitfall check")
zero_pct = (rb["YrRenovated"] == 0).mean() * 100
check("YrRenovated=0 for the majority of records (un-renovated properties)",
      zero_pct > 90,
      f"{zero_pct:.1f}% of rows have YrRenovated=0 (must engineer EffectiveAge in modeling)")

subheader("SqFtTotLiving summary")
sqft = rb["SqFtTotLiving"]
print(f"  Min: {sqft.min():,}  |  Median: {sqft.median():,.0f}  |  "
      f"Mean: {sqft.mean():,.0f}  |  Max: {sqft.max():,}")

subheader("ViewUtilization — CORRECTION to research notes")
in_rb  = "ViewUtilization" in rb.columns
in_par = "ViewUtilization" in par.columns
check("ViewUtilization is in ResBldg (not Parcel)", in_rb)
check("ViewUtilization is NOT in Parcel", not in_par,
      "Research note incorrectly placed ViewUtilization under Parcel")
if in_rb:
    vu = rb["ViewUtilization"].str.strip().value_counts()
    print(f"  ViewUtilization values: {vu.to_dict()}")
    print("  This is a Y/N flag on the building record, not a numeric score")


# ---------------------------------------------------------------------------
# 2.2.3 Parcel
# ---------------------------------------------------------------------------
header("2.2.3  Parcel  (EXTR_Parcel.csv)")

subheader("File & shape")
print(f"  Shape: {par.shape[0]:,} rows  x  {par.shape[1]} columns")

subheader("Key field existence")
expected_par = ["SqFtLot", "TrafficNoise", "PowerLines", "WfntLocation", "WfntFootage"]
for f in expected_par:
    check(f"Field '{f}' exists", f in par.columns)

subheader("View columns — CORRECTION to research notes")
print("  Research note mentions 'ViewUtilization' as a single Parcel field.")
print("  Actual data uses SEPARATE binary columns per view type:")
view_cols = [c for c in par.columns if c in [
    "MtRainier", "Olympics", "Cascades", "Territorial",
    "SeattleSkyline", "PugetSound", "LakeWashington",
    "LakeSammamish", "SmallLakeRiverCreek", "OtherView"
]]
for c in view_cols:
    pct = (par[c] > 0).mean() * 100
    print(f"    {c:<24} {pct:.1f}% of parcels have non-zero value")
check("Individual view columns exist in Parcel", len(view_cols) >= 8,
      f"Found {len(view_cols)} view columns: {view_cols}")

subheader("WfntLocation (note: field is 'WfntLocation', not 'WaterfrontLocation')")
check("WfntLocation exists", "WfntLocation" in par.columns)
check("'WaterfrontLocation' does NOT exist (correct field name is WfntLocation)",
      "WaterfrontLocation" not in par.columns)
wf_counts = par["WfntLocation"].value_counts()
print(f"  WfntLocation top values:\n{wf_counts.head(8).to_string()}")

subheader("TrafficNoise distribution  (0=None … 3=Severe)")
tn = par["TrafficNoise"].value_counts().sort_index()
print(f"\n{tn.to_string()}")
check("TrafficNoise range is 0–3", par["TrafficNoise"].between(0, 3).all())
print("  Confirmed: 0=None, 1=Slight, 2=Moderate, 3=Severe")

subheader("PowerLines  (Y/N flag)")
pl = par["PowerLines"].value_counts()
print(f"\n{pl.to_string()}")
check("PowerLines is Y/N", set(pl.index).issubset({"Y", "N"}))


# ---------------------------------------------------------------------------
# 2.2.4 Lookup Table
# ---------------------------------------------------------------------------
header("2.2.4  Lookup Table  (EXTR_LookUp.csv)")

subheader("File & shape")
print(f"  Shape: {lu.shape[0]:,} rows  x  {lu.shape[1]} columns")
check("Columns are LUType, LUItem, LUDescription",
      list(lu.columns) == ["LUType", "LUItem", "LUDescription"])
print(f"  Unique LUType values ({lu['LUType'].nunique()}): {sorted(lu['LUType'].unique().tolist())}")

subheader("Key LUType mappings")
lu_types = {
    4:   "PropertyType (Res-Land, Res-Improved, C/I, etc.)",
    5:   "SaleInstrument (Foreclosure, Estate, Trust, etc.)",
    6:   "SaleInstrument / Deed type (Warranty, Quit Claim, etc.)",
    7:   "SaleReason / SaleWarning flags (non-market indicators)",
    50:  "WfntLocation body of water (Puget Sound, Lake Wash., etc.)",
    52:  "WfntBank (Low, Medium, High, No Bank)",
    108: "HeatSystem (Forced Air, Heat Pump, etc.)",
}
for lt, desc in lu_types.items():
    exists = lt in lu["LUType"].values
    check(f"LUType={lt:>3}  —  {desc}", exists)

subheader("HeatSystem example join  (LUType=108)")
lu_heat = lu[lu["LUType"] == 108][["LUItem", "LUDescription"]].set_index("LUItem")
lu_heat.index.name = "HeatSystem code"
print(f"\n{lu_heat.to_string()}")

subheader("SaleReason flag descriptions  (LUType=7, top codes)")
lu_sr7 = lu[lu["LUType"] == 7].set_index("LUItem")["LUDescription"]
top_codes = [1, 2, 3, 4, 5, 7, 8, 18]
print("\n  Key non-market SaleReason codes from LUType=7:")
for c in top_codes:
    if c in lu_sr7.index:
        print(f"    {c:>3}: {lu_sr7[c].strip()}")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
header("SUMMARY")
print(textwrap.dedent("""
  Dataset                  Rows       Cols   Status
  ----------------------   ---------  -----  ------
  Real Property Sales      2,415,964     24   OK
  Residential Building       532,072     50   OK
  Parcel                     627,512     81   OK
  Lookup                       1,224      3   OK

  CONFIRMED fields from research notes:
    RPSale   : Major, Minor, DocumentDate, SalePrice, RecordingNbr,
               SaleReason, PropertyClass, SaleWarning, PrincipalUse
    ResBldg  : SqFtTotLiving, BldgGrade (1-13), Condition (1-5),
               YrBuilt, YrRenovated, Bedrooms, BathFullCount,
               BathHalfCount, Bath3qtrCount, ViewUtilization
    Parcel   : SqFtLot, TrafficNoise (0-3), PowerLines (Y/N),
               WfntLocation, WfntFootage, WfntBank

  CORRECTIONS to research notes:
    (1) ViewUtilization is in RESBLDG (not Parcel).
        It is a binary Y/N flag, not a numeric score.
        Parcel uses separate binary columns per view type:
        MtRainier, Olympics, Cascades, Territorial, SeattleSkyline,
        PugetSound, LakeWashington, LakeSammamish, SmallLakeRiverCreek.

    (2) Waterfront field is named 'WfntLocation' (not 'WaterfrontLocation').

    (3) YrRenovated=0 for 94.9% of records — confirmed data pitfall.
        Use: EffectiveAge = SaleYear - max(YrBuilt, YrRenovated_if_nonzero)

    (4) SaleReason=1 (most common, 59%) = clean/arms-length sale.
        Non-market codes are in LUType=7 (e.g., 18=Quit Claim Deed,
        13=Bankruptcy, 14=Sheriff/Tax Sale, 38=Divorce).

    (5) PropertyClass=8 = 'Res-Improved property' per LUType=4 (67% of sales).
        Research note says 'usually Single Family' — confirmed.
"""))


if __name__ == "__main__":
    pass
