# Paneer Cold-Chain Quality Analysis

A Streamlit dashboard for exploring refrigerator temperature and humidity logs
alongside paneer microbial, sensory, and physicochemical measurements during
storage. The project supports reproducible data cleaning and descriptive and
paired statistical analysis; it does not determine food safety or shelf life.

## Problem statement

Refrigerator readings and product-quality results are often stored in separate
files and formats. This project brings the measurements into one interactive
view so users can inspect cold-chain patterns, storage-day trends, missing
values, and associations between paired quality measurements.

## Datasets

The application accepts:

- **Temperature log (CSV):** expected columns include `Counter`,
  `Time_Stamp`, `Temperature`, `RH`, `Compressor`, and `Fridge_Open`.
  Timestamps are parsed day-first. Temperature and RH are numeric; state
  columns retain their recorded representation.
- **Paneer quality workbook (Excel):** the original workbook has grouped
  headings and blank separator columns and is read without a header row. Its
  documented positional layout
  has at least 27 columns. The four microbial groups each have a raw CFU/mL
  value, a dilution value, and a derived log10 CFU/mL value: TPC at columns
  2–4, coliform at 5–7, yeast/mold at 8–10, and psychrophilic at 11–13.
  Sensory scores are at columns 15–18, pH at 20, moisture percentage at 21,
  and yield/fat fields at 23–26.

### Bundled demonstration data

The app loads the small, committed files in `data/sample/` by default:

- `temperature_demo.csv` — 289 synthetic readings at ten-minute intervals
  across 48 hours.
- `paneer_quality_demo.xlsx` — 70 synthetic replicate observations covering
  storage days 0–13, with five replicates per day and realistic missing
  measurements. Sensory values are absent for days 10–13 to demonstrate the
  observed-data handling and correlation sample limits.

These are **synthetic demonstration examples**, not the study's experimental
results. The notice and source labels in the app identify which dataset is
synthetic. The demo is self-contained and requires no secrets or private data.

The full `data/raw/` and processed data directories remain git-ignored. The
bundled `data/sample/` files are deliberately allowed in Git so Community Cloud
can load them. The app does not automatically load the private raw files.
You may keep your original full datasets in `data/raw/` for safekeeping, but
select them with the sidebar uploaders when you want to analyze them.

Optional sidebar uploads replace the sample independently for each dataset.
For example, uploading only a temperature CSV uses that CSV and continues to
use the synthetic workbook. Invalid uploads display an error and fall back to
the corresponding bundled demo if it is available. Uploads are held in memory
by Streamlit; the app does not save over local files or persist uploads.

If a local file is missing, empty, or malformed, the app reports a clear load
error and remains usable for uploading a valid replacement.

## Methodology and assumptions

### Temperature monitoring

- Dates are parsed with day-first interpretation. Invalid timestamps and
  nonnumeric temperature values are retained as missing for review and excluded
  from timestamped statistics.
- Duplicate timestamp readings count as individual valid readings in
  temperature and humidity summaries, but are averaged into one timestamp for
  duration estimation.
- The threshold (default 4 °C) is a configurable analytical reference, not a
  safety guarantee.
- Time above the threshold is estimated by linear interpolation across adjacent
  valid timestamp observations only when their gap is no longer than the
  configured maximum (default 30 minutes). Longer gaps are unknown and excluded.
- Excursion count represents observed above-threshold runs. Unobserved events
  inside long gaps cannot be identified. Longest duration and recovery duration
  are estimates under the same interpolation and gap assumptions.
- Door-opening counts describe observed closed/off-to-open/on transitions;
  state during long gaps is not inferred. Humidity, compressor, and door values
  are summarized as recorded.

### Paneer quality

- Workbook positions and row-2 heading labels are validated against the
  documented layout. A sheet with fewer than 27 columns or unexpected key
  headings is rejected with a schema error rather than silently mapped.
- Only rows with integer storage days 0–13 and integer replicate numbers 1–5
  are retained. This excludes Mean/SD summary rows and other headings.
- Measurements are converted to numeric values while preserving missing data;
  no missing value is replaced with zero.
- Column 4 is named `TPC_Log10` as documented. Other microbial fields are
  named using the workbook's CFU/mL, dilution, and log10 formula layout.
- The workbook derives each log measurement as
  `log10(CFU_per_mL / 10^(-dilution))`. A raw CFU value of zero makes that
  logarithm undefined, so the workbook formula result is missing while the
  corresponding raw zero count remains present. This missing log value is not
  an imputed zero and should be interpreted alongside the raw count.
- Daily summaries use the mean, sample standard deviation (ddof=1), and
  nonmissing sample count for each numeric measure.
- Microbial charts can display either raw CFU/mL counts or workbook-derived
  log10 CFU/mL values. They show individual observed replicates, daily means,
  sample-SD error bars where estimable, and valid counts in hover details.
  Missing days remain gaps; a single valid observation has an undefined sample
  SD. Zero counts remain available in raw-count views and have missing,
  mathematically undefined log values.
- Correlations use only rows with both TPC and overall acceptability present.
  Pearson and Spearman coefficients and p-values are reported with the paired
  sample count. The pooled analysis does not model replicates clustered within
  storage day or separate shared storage-day trends from replicate-level
  association; its p-values should therefore be interpreted cautiously.
  Storage days without sensory observations are excluded entirely. A
  correlation does not establish causation.
- A supplementary descriptive analysis separately regresses TPC and
  acceptability on linear storage day and correlates the resulting residuals.
  It requires at least four complete pairs across four days and does not report
  a row-independent p-value because replicate clustering is not modeled. The
  residual comparison does not remove all confounding, establish causation, or
  identify whether replicates represent repeated measurements of the same
  physical units; that structure is not documented.
- Missing sensory values are not interpolated; charts leave unobserved days
  blank.

## Installation

Python 3.10 or newer is recommended.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run locally

From the project root:

```powershell
streamlit run app.py
```

On startup, the bundled samples load automatically. Use the sidebar to
optionally replace either sample with your own CSV or Excel workbook.

## Dashboard features

1. **Overview:** dataset load status, computed cold-chain indicators, latest
   available quality indicators, and expected-observation diagnostics.
2. **Cold-Chain Monitoring:** interactive temperature and humidity charts,
   threshold and estimation-gap controls, excursion summaries, gap warnings,
   and door/compressor state counts.
3. **Paneer Quality:** daily microbial trends, sensory trends, pH and moisture,
   plus replicate-level and daily-summary tables.
4. **Statistical Analysis:** paired TPC/overall-acceptability scatter plot,
   Pearson and Spearman statistics, p-values, and interpretation limitations.
5. **Data Explorer:** filtered quality observations, missingness summary, and
   CSV downloads for cleaned datasets and daily summaries.

## Tests

The analysis tests use synthetic data and do not require the private datasets:

```powershell
python -m unittest discover -s tests -v
```

## Deploy on Streamlit Community Cloud

1. Push the application code, `requirements.txt`, `README.md`, `.streamlit/`,
   and the small `data/sample/` demonstration files to a GitHub repository.
   Keep private raw data and secrets out of the repository.
2. In Streamlit Community Cloud, create an app from that repository and select
   `app.py` as the entry point.
3. Deploy. The app opens with synthetic samples; users can optionally replace
   either dataset using the sidebar uploaders.
4. Do not place private datasets in the repository or configure secrets for
   the sample-data demo.

## Limitations and responsible interpretation

Results depend on timestamp quality, measurement completeness, the workbook's
documented positional layout, and the units/transformations used when
measurements were recorded. Time-between-reading estimates do not reveal
conditions inside unknown gaps, and recorded microbial or sensory measures
alone do not establish safety, causation, or shelf life. Confirm data
definitions with the study protocol and use applicable validated food-safety
procedures for decisions.

## Illustrative image credits

The dashboard uses locally stored, resized image derivatives in
`assets/images/`. They are illustrative stock photographs only; none depict
the study's samples, equipment, laboratory, or measured results. Crops and
resizing are noted below.

- **Overview — cold room:** [Cold Room After Installation](https://commons.wikimedia.org/wiki/File:Cold_Room_After_Installation.jpg)
  by Mesadbal, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
  Cropped and resized for the dashboard.
- **Paneer Quality — paneer:** [Panir Paneer Indian cheese fresh](https://commons.wikimedia.org/wiki/File:Panir_Paneer_Indian_cheese_fresh.jpg)
  by Sonja Pauen (Stanhopea), [CC BY 2.0 Germany](https://creativecommons.org/licenses/by/2.0/de/deed.en).
  Cropped and resized for the dashboard.
- **Cold-Chain Monitoring — thermometer:** [Digital Thermometer TES-1302](https://commons.wikimedia.org/wiki/File:Digital_Thermometer_TES-1302.jpg)
  by Andy116, [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
  Cropped and resized for the dashboard.
- **Statistical Analysis — microbiology:** [National Lab Week 130410-F-TT327-015](https://commons.wikimedia.org/wiki/File:National_Lab_Week_130410-F-TT327-015.jpg),
  U.S. Air Force photograph by Airman 1st Class Jason Couillard; public domain
  in the United States. Resized for the dashboard.

Image captions in the app identify the photos as illustrative and distinguish
them from the active dataset and its results.
