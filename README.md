# Paneer Cold-Chain Quality Analysis

An interactive Streamlit dashboard for exploring refrigerator conditions and
paneer quality measurements across storage time. It brings temperature and
humidity logs together with microbial, sensory, and physicochemical data, while
making missing observations and analytical limitations visible.

**Live dashboard:** [Open Paneer Cold-Chain Quality Analysis on Streamlit](https://paneer-cold-chain-quality-analysis-5ajwnvdfcpqusuusurmvnd.streamlit.app/)

> The dashboard is an exploratory analysis tool, not a food-safety assessment
> or a validated shelf-life determination. Bundled results are synthetic
> demonstrations, not experimental findings.

## Project overview

Cold-chain temperature records and product-quality measurements are often
collected separately. Reviewing them together can help identify patterns in
storage conditions, product measurements, missing data, and paired
observations over time.

This project provides a reproducible workflow for loading and cleaning those
files, summarizing measurements by storage day, exploring temperature
excursions, and comparing paired microbial and sensory observations. The
default deployment uses small synthetic sample datasets, and users can
optionally load their own compatible files.

## Dashboard features

The dashboard has five sections:

1. **Overview** — active dataset status and source labels, cold-chain KPIs,
   latest available quality indicators, and data-quality diagnostics.
2. **Cold-Chain Monitoring** — interactive temperature and humidity charts,
   a configurable temperature reference threshold, excursion estimates,
   timestamp-gap warnings, and door/compressor state summaries.
3. **Paneer Quality** — microbial trends in log10 CFU/mL or raw CFU/mL, with
   replicate points, daily means, sample-standard-deviation error bars, and
   valid counts; sensory trends; pH and moisture trends; and replicate-level or
   daily-summary tables.
4. **Statistical Analysis** — paired TPC versus overall-acceptability
   scatterplot, Pearson and Spearman correlations, paired sample counts and
   p-values, and a separate descriptive association adjusted for linear
   storage day.
5. **Data Explorer** — filtered, cleaned quality observations, missing-value
   summaries, cleaned-data downloads, and daily-summary downloads.

## Methodology

### Temperature excursions

Temperature timestamps are parsed day-first and observations are sorted.
Duplicate timestamps are retained as readings for descriptive summaries but
averaged to one timestamp for duration estimation. Threshold time is estimated
by linearly interpolating between valid adjacent observations only when their
gap is no longer than the user-configured maximum gap (30 minutes by default).
Longer gaps are treated as unknown. Excursion counts describe observed runs;
events inside long gaps cannot be inferred.

The default 4.0 °C threshold is a **configurable analytical reference**, not a
food-safety guarantee. A reading above it does not by itself establish unsafe
food or equipment failure.

### Paneer quality measurements

The workbook is read without assuming a single-row header. The cleaning
function validates the expected positional layout and key headings, maps the
documented measurement columns, and keeps only integer storage days 0–13 and
replicates 1–5. This excludes summary rows such as Mean and SD. Missing values
remain missing; they are not filled with zero.

Daily summaries report each variable's mean, sample standard deviation, and
nonmissing observation count. Microbial charts can show the workbook-provided
log10 CFU/mL values or raw CFU/mL values. Zero raw counts remain available in
raw-count views; their logarithm is undefined and remains missing. Charts show
observed replicates and do not bridge missing days.

### Exploratory and statistical analysis

Daily trend descriptions compare the first and last days with valid observed
values and report the contributing counts. They are descriptive and do not
extrapolate to unmeasured days.

Pearson and Spearman correlations use complete TPC-log and
overall-acceptability pairs from the active dataset. The supplementary
storage-day-adjusted coefficient is calculated by separately fitting ordinary
least-squares linear models for TPC and acceptability against storage day, then
correlating their residuals. The adjusted coefficient is descriptive only; no
adjusted p-value is reported because replicate clustering is not modeled.
Neither pooled nor adjusted association establishes causation.

## Findings and interpretation

### Bundled synthetic demonstration results

The following values are calculated from the bundled synthetic samples to
demonstrate the dashboard. **They are not results from the original
experiment.**

- The temperature sample contains 289 readings across approximately 48 hours.
  At the default 4.0 °C analytical reference, 29 readings (10.0%) are above
  the threshold; five observed excursions are counted, with about 5.18 hours
  estimated above the reference under the configured gap and interpolation
  method.
- The synthetic quality workbook contains 70 replicate rows: five per day
  across days 0–13. It has 50 paired TPC/acceptability observations on days
  0–9; acceptability is missing on days 10–13.
- Across the 50 pairs, pooled Pearson r is approximately −0.966 and Spearman
  ρ is approximately −0.964. The descriptive linear storage-day-adjusted
  residual correlation is approximately +0.085. No adjusted p-value is
  reported. Pooled p-values are shown by the app but do not account for
  replicate clustering.
- In the synthetic workbook, daily mean TPC increases from approximately
  2.34 log10 CFU/mL on day 0 to 5.09 on day 9, while mean overall
  acceptability declines from approximately 8.88 to 4.92 over those observed
  days.

These values are recalculated from the bundled files and are included only to
illustrate functionality. The original experimental datasets are not included
in the repository, so this README makes no claims about their measured
findings. Upload an authorized, compatible experimental dataset to explore its
results. Correlation does not establish causation.

## Technology stack

The application uses:

- **Python** for data loading, cleaning, and analysis.
- **Streamlit** for the interactive dashboard and file uploads.
- **Pandas** and **NumPy** for tabular processing and numerical calculations.
- **SciPy** for Pearson and Spearman statistics.
- **Plotly Express** and **Plotly Graph Objects** for interactive charts.
- **OpenPyXL** for Excel workbook support.

Dependencies and minimum versions are listed in [requirements.txt](requirements.txt).

## Repository structure

```text
.
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── .streamlit/
│   └── config.toml
├── assets/
│   └── images/
│       ├── cold-storage.jpg
│       ├── digital-thermometer.jpg
│       ├── microbiology-lab.jpg
│       └── paneer.jpg
├── data/
│   ├── sample/
│   │   ├── paneer_quality_demo.xlsx
│   │   └── temperature_demo.csv
│   └── raw/                 # local-only; ignored by Git
├── src/
│   ├── data_loader.py
│   ├── quality_analysis.py
│   └── temperature_analysis.py
└── tests/
    └── test_analysis.py
```

The full experimental files are excluded by the `data/raw/` Git ignore rule.
Only the small synthetic demonstration datasets in `data/sample/` are intended
to be tracked. Do not add private data or secrets to the repository.

## Installation and local run

Use Python 3.10 or newer. From the repository root, create and activate a
virtual environment in Windows PowerShell, then install the requirements:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Start the dashboard from the same project directory:

```powershell
streamlit run app.py
```

Streamlit prints a local URL in the terminal when the app is ready.

## Using bundled samples and uploads

The bundled synthetic CSV and Excel workbook load automatically on startup.
The sidebar identifies the active source for each dataset separately and
provides optional upload controls:

- Temperature log: CSV with `Time_Stamp` and `Temperature`; optional fields
  include `Counter`, `RH`, `Compressor`, and `Fridge_Open`.
- Paneer quality workbook: Excel file with the documented positional layout
  and expected row-2 headings.

An upload replaces the bundled sample for that dataset only. For example,
uploading a temperature CSV while leaving the workbook uploader empty uses the
uploaded temperature data and bundled synthetic quality data. Invalid uploads
show an error and fall back to the corresponding bundled sample when it can be
loaded. Uploaded files are processed in memory and are not written over the
bundled samples or local raw datasets.

## Data sources and image credits

The committed `data/sample/` files are explicitly synthetic examples for
exploring the dashboard. Original experimental data may be held locally in
`data/raw/`, but those files are ignored by Git and are not bundled with this
project. Use only data you are authorized to analyze.

The locally stored photos are illustrative stock imagery, not photographs of
the study's actual samples, equipment, or laboratory. Cropping or resizing is
noted below:

- **Overview — cold room:** [Cold Room After Installation](https://commons.wikimedia.org/wiki/File:Cold_Room_After_Installation.jpg)
  by Mesadbal, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
  Cropped and resized.
- **Paneer Quality — paneer:** [Panir Paneer Indian cheese fresh](https://commons.wikimedia.org/wiki/File:Panir_Paneer_Indian_cheese_fresh.jpg)
  by Sonja Pauen (Stanhopea), [CC BY 2.0 Germany](https://creativecommons.org/licenses/by/2.0/de/deed.en).
  Cropped and resized.
- **Cold-Chain Monitoring — thermometer:** [Digital Thermometer TES-1302](https://commons.wikimedia.org/wiki/File:Digital_Thermometer_TES-1302.jpg)
  by Andy116, [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
  Cropped and resized.
- **Statistical Analysis — microbiology:** [National Lab Week 130410-F-TT327-015](https://commons.wikimedia.org/wiki/File:National_Lab_Week_130410-F-TT327-015.jpg),
  U.S. Air Force photograph by Airman 1st Class Jason Couillard; public domain
  in the United States. Resized.

## Screenshots

No screenshots are included in this README. To add genuine screenshots, run the
app locally with the bundled sample data, capture the rendered Overview or a
dashboard section in your browser, save the image under a tracked path such as
`docs/screenshots/`, and then embed it using a repository-relative Markdown
path. Do not present stock imagery as a screenshot of the application.

## Testing and verification

Run the unit tests from the project root:

```powershell
python -m unittest discover -s tests -v
```

Optional local checks:

```powershell
python -m compileall -q app.py src tests
python -m pip check
git diff --check
```

The test suite uses deterministic synthetic fixtures and the bundled sample
files; it does not require the original experimental datasets.

## Limitations and future improvements

- Temperature exposure estimates depend on timestamp quality and the configured
  maximum gap. Conditions inside longer gaps are unknown, and interpolation is
  only an estimate.
- Microbial, sensory, and physicochemical measurements depend on the
  workbook's positional mapping and documented units. Confirm these with the
  study protocol before interpreting uploaded workbooks.
- Pooled correlation p-values do not account for replicates clustered within
  storage days. The adjusted residual coefficient is descriptive and does not
  remove all confounding. Replicate identity is not documented as tracking the
  same physical sample over time.
- Missing observations limit conclusions; they are not evidence of zero
  measurements. Sensory values are not interpolated.
- Neither a temperature reference nor the measured quality indicators alone
  establish food safety or a validated shelf life. Use appropriate validated
  methods and applicable food-safety procedures for operational decisions.

Future work could add study-protocol documentation, validated experimental
unit and repeated-measure handling when those details are available, and
additional checks for uploaded workbook schemas. Any inferential extensions
should be based on the actual study design rather than assumptions about
replicate independence.
