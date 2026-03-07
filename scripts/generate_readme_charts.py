"""
Generate key charts for README.md — saves PNGs to assets/
Run from project root: python scripts/generate_readme_charts.py
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.colors as mcolors
import re
import warnings
from pathlib import Path

warnings.filterwarnings('ignore')
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 150
plt.rcParams['savefig.bbox'] = 'tight'

import seaborn as sns
sns.set_theme(style='whitegrid')

ENC      = 'latin-1'
DATA_DIR = Path('kc_assessor_data')
EDU_DIR  = Path('education_data')
ASSETS   = Path('assets')
ASSETS.mkdir(exist_ok=True)

fmt_dol = mticker.FuncFormatter(lambda x, _: f'${x:,.0f}')
fmt_k   = mticker.FuncFormatter(lambda x, _: f'${x/1_000:.0f}K')

print('Loading data...')

# ── KC Assessor ───────────────────────────────────────────────────────────────
rp  = pd.read_csv(DATA_DIR/'RealPropertySales/EXTR_RPSale.csv',   low_memory=False, encoding=ENC)
rb  = pd.read_csv(DATA_DIR/'ResidentialBuilding/EXTR_ResBldg.csv', low_memory=False, encoding=ENC)

def make_pin(df):
    return df['Major'].astype(str).str.zfill(6) + df['Minor'].astype(str).str.zfill(4)

rp['PIN'] = make_pin(rp)
rb['PIN'] = make_pin(rb)
rp['DocumentDate'] = pd.to_datetime(rp['DocumentDate'], errors='coerce')
rp['SaleYear']     = rp['DocumentDate'].dt.year

al = rp[
    (rp['SaleReason'] == 1) & (rp['SalePrice'] > 10_000) &
    (rp['PropertyClass'] == 8)
].copy()

rb_sfr = rb[
    (rb['NbrLivingUnits']==1) & (rb['SqFtTotLiving'].between(200,15_000)) &
    (rb['YrBuilt'].between(1870,2024))
].sort_values('BldgNbr').drop_duplicates('PIN', keep='first')

# ── OSPI ──────────────────────────────────────────────────────────────────────
ospi = pd.read_csv(EDU_DIR/'ospi_assessment_2324_king.csv', low_memory=False)
ospi_clean = ospi[ospi['dat'].isna() | (ospi['dat']=='None') | (ospi['dat']=='')].copy()
ospi_clean['pct_met'] = pd.to_numeric(
    ospi_clean['percent_consistent_grade_level_knowledge_and_above'].astype(str).str.rstrip('%'),
    errors='coerce')
school_scores = (
    ospi_clean
    .pivot_table(index=['districtname'], columns='testsubject', values='pct_met')
    .reset_index()
)
school_scores.columns.name = None
school_scores = school_scores.rename(columns={'Math':'pct_math','ELA':'pct_ela','Science':'pct_science'})
subj_cols = [c for c in ['pct_math','pct_ela','pct_science'] if c in school_scores.columns]
school_scores['pct_composite'] = school_scores[subj_cols].mean(axis=1)
district_scores = school_scores.set_index('districtname')

# PIN → district lookup
pin_district = pd.read_csv(EDU_DIR/'kc_pin_district_lookup.csv')[['PIN','NAME']].drop_duplicates('PIN')
pin_district.columns = ['PIN','gis_name']

def norm(name):
    if pd.isna(name): return name
    return re.sub(r'\s+School District.*', '', str(name), flags=re.IGNORECASE).strip().upper()

pin_district['_key'] = pin_district['gis_name'].apply(norm)
district_scores['_key'] = district_scores.index.map(norm)

# ─────────────────────────────────────────────────────────────────────────────
# Chart 1: Median SFR price trend 1990–2024
# ─────────────────────────────────────────────────────────────────────────────
print('Chart 1: Price trend...')
sfr_sales = al.merge(rb_sfr[['PIN']], on='PIN', how='inner')
yearly = (
    sfr_sales[sfr_sales['SaleYear'].between(1990, 2024)]
    .groupby('SaleYear')['SalePrice']
    .median()
)

fig, ax = plt.subplots(figsize=(10, 4.5))
ax.fill_between(yearly.index, yearly.values, alpha=0.15, color='steelblue')
ax.plot(yearly.index, yearly.values, color='steelblue', lw=2.5, marker='o', markersize=3)
ax.yaxis.set_major_formatter(fmt_k)
ax.set_title('King County Median SFR Sale Price (1990–2024)', fontsize=14, fontweight='bold')
ax.set_xlabel('Year')
ax.set_ylabel('Median Sale Price')
for yr, label in [(2012,'2012\nRecovery'), (2020,'2020\nCOVID run-up'), (2022,'2022\nPeak')]:
    if yr in yearly.index:
        ax.annotate(label, (yr, yearly[yr]),
                    textcoords='offset points', xytext=(0, 12),
                    ha='center', fontsize=8, color='steelblue',
                    arrowprops=dict(arrowstyle='->', color='steelblue', lw=1))
plt.tight_layout()
plt.savefig(ASSETS/'price_trend.png')
plt.close()
print('  Saved assets/price_trend.png')

# ─────────────────────────────────────────────────────────────────────────────
# Chart 2: School quality vs median price scatter
# ─────────────────────────────────────────────────────────────────────────────
print('Chart 2: School quality vs price...')
al_recent = al[al['SaleYear'].between(2015, 2024)].copy()
al_latest = al_recent.sort_values('DocumentDate').drop_duplicates('PIN', keep='last')
sales = al_latest.merge(rb_sfr[['PIN','SqFtTotLiving']], on='PIN', how='inner')
sales_d = sales.merge(pin_district, on='PIN', how='left')
sales_d['_key'] = sales_d['gis_name'].apply(norm)

housing_by_d = (
    sales_d.groupby('_key')
    .agg(median_price=('SalePrice','median'), n_sales=('SalePrice','count'))
    .reset_index()
)
ds_reset = district_scores[['_key','pct_composite']].reset_index()
combined = housing_by_d.merge(ds_reset, on='_key', how='inner').dropna()

fig, ax = plt.subplots(figsize=(10, 6))
sc = ax.scatter(
    combined['pct_composite'], combined['median_price'],
    s=combined['n_sales'] / combined['n_sales'].max() * 600,
    c=combined['median_price'], cmap='YlOrRd',
    alpha=0.85, edgecolors='white', lw=0.8
)
z = np.polyfit(combined['pct_composite'], combined['median_price'], 1)
xs = np.linspace(combined['pct_composite'].min(), combined['pct_composite'].max(), 100)
ax.plot(xs, np.poly1d(z)(xs), 'steelblue', ls='--', lw=1.8, alpha=0.8, label='Trend')

for _, row in combined.iterrows():
    label = str(row.get('districtname', row['_key'])).replace(' School District No. 1','').title()
    ax.annotate(label, (row['pct_composite'], row['median_price']),
                fontsize=7, textcoords='offset points', xytext=(4,3), alpha=0.85)

r = combined['pct_composite'].corr(combined['median_price'])
ax.text(0.97, 0.05, f'r = {r:.2f}', transform=ax.transAxes,
        ha='right', fontsize=13, color='steelblue', fontweight='bold')
ax.yaxis.set_major_formatter(fmt_dol)
ax.set_xlabel('OSPI Composite Pass Rate % (2023–24)', fontsize=11)
ax.set_ylabel('Median SFR Sale Price (2015–2024)', fontsize=11)
ax.set_title('School Quality vs. House Price by District\n(bubble size = transaction volume)',
             fontsize=13, fontweight='bold')
plt.colorbar(sc, ax=ax, label='Median Price')
plt.tight_layout()
plt.savefig(ASSETS/'school_price_scatter.png')
plt.close()
print('  Saved assets/school_price_scatter.png')

# ─────────────────────────────────────────────────────────────────────────────
# Chart 3: School quality premium (quartile bar chart)
# ─────────────────────────────────────────────────────────────────────────────
print('Chart 3: School quality premium...')
with_scores = sales_d.merge(ds_reset, on='_key', how='left')
with_scores['school_quartile'] = pd.qcut(
    with_scores['pct_composite'].fillna(with_scores['pct_composite'].median()),
    q=4, labels=['Q1\nBottom 25%','Q2','Q3','Q4\nTop 25%']
)
q_stats = with_scores.groupby('school_quartile', observed=True).agg(
    median_price=('SalePrice','median'), n=('SalePrice','count')
)
premium = (q_stats.loc['Q4\nTop 25%','median_price'] /
           q_stats.loc['Q1\nBottom 25%','median_price'] - 1) * 100

fig, ax = plt.subplots(figsize=(8, 5))
colors = ['#e74c3c','#e67e22','#2ecc71','#27ae60']
bars = ax.bar(q_stats.index, q_stats['median_price'], color=colors, width=0.6)
for bar, val in zip(bars, q_stats['median_price']):
    ax.text(bar.get_x()+bar.get_width()/2, val*1.015,
            f'${val/1e3:.0f}K', ha='center', fontsize=11, fontweight='bold')
ax.yaxis.set_major_formatter(fmt_dol)
ax.set_title(f'School Quality Premium: Top vs. Bottom Quartile = +{premium:.0f}%\n'
             f'(King County SFR, 2015–2024)', fontsize=12, fontweight='bold')
ax.set_ylabel('Median Sale Price')
ax.set_ylim(0, q_stats['median_price'].max() * 1.18)
plt.tight_layout()
plt.savefig(ASSETS/'school_premium.png')
plt.close()
print('  Saved assets/school_premium.png')

# ─────────────────────────────────────────────────────────────────────────────
# Chart 4: Crime quintile vs price (Seattle)
# ─────────────────────────────────────────────────────────────────────────────
print('Chart 4: Crime quintile...')
CRIME_DIR = Path('crime_data')
score_file = CRIME_DIR / 'seattle_sales_crime_score.csv'

if score_file.exists():
    crime_scores = pd.read_csv(score_file, dtype={'PIN': str})
    parcel_coords = pd.read_csv(EDU_DIR/'kc_parcel_coords.csv')[['PIN','LAT','LON']]
    seattle = (
        sales_d
        .merge(parcel_coords, on='PIN', how='left')
        .merge(crime_scores, on='PIN', how='inner')
    )
    seattle = seattle[
        seattle['LAT'].between(47.49, 47.74) &
        seattle['LON'].between(-122.46, -122.22)
    ].copy()
    seattle['ppsf'] = seattle['SalePrice'] / seattle['SqFtTotLiving'].replace(0, np.nan)
    seattle['safety_q'] = pd.qcut(
        seattle['crime_count_500m'], q=5,
        labels=['Q1\nSafest','Q2','Q3','Q4','Q5\nHighest\nCrime']
    )
    q_crime = seattle.groupby('safety_q', observed=True).agg(
        median_price=('SalePrice','median'),
        median_ppsf=('ppsf','median'),
        n=('SalePrice','count')
    )

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    safety_colors = ['#27ae60','#2ecc71','#f1c40f','#e67e22','#e74c3c']

    for ax, col, title, ylabel in [
        (axes[0], 'median_price', 'Median Sale Price', 'Median Sale Price'),
        (axes[1], 'median_ppsf',  'Median Price per SqFt', 'Median $/SqFt'),
    ]:
        bars = ax.bar(q_crime.index, q_crime[col], color=safety_colors, width=0.6)
        for bar, val in zip(bars, q_crime[col]):
            ax.text(bar.get_x()+bar.get_width()/2, val*1.015,
                    f'${val:,.0f}', ha='center', fontsize=9, fontweight='bold')
        ax.set_title(title, fontsize=12)
        ax.set_ylabel(ylabel)
        if col == 'median_price':
            ax.yaxis.set_major_formatter(fmt_dol)
        ax.tick_params(axis='x', labelsize=8)

    plt.suptitle('Seattle SFR: Safety Quintile vs. Price (2020–2024)',
                 fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig(ASSETS/'crime_quintile.png')
    plt.close()
    print('  Saved assets/crime_quintile.png')
else:
    print('  Skipped (crime score file not found)')

print('\nDone! All charts saved to assets/')
