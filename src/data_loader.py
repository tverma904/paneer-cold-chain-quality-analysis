"""Load uploaded datasets or bundled synthetic demonstration data."""

from pathlib import Path
from typing import BinaryIO

import pandas as pd

from src.temperature_analysis import clean_temperature_data

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DATA_DIR = PROJECT_ROOT / "data" / "sample"
TEMPERATURE_SAMPLE_NAME = "temperature_demo.csv"
QUALITY_SAMPLE_NAME = "paneer_quality_demo.xlsx"


def _sample_file_path(filename: str) -> Path:
    path = SAMPLE_DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Bundled demonstration dataset is missing: {path}. "
            "Restore the sample file or upload a replacement."
        )
    if not path.is_file():
        raise ValueError(
            f"Expected the demonstration dataset at {path}, but the path is not a file."
        )
    if path.stat().st_size == 0:
        raise ValueError(f"Bundled demonstration dataset is empty: {path}")
    return path


def _validate_upload(uploaded_file: BinaryIO, dataset_name: str) -> None:
    if hasattr(uploaded_file, "getvalue") and not uploaded_file.getvalue():
        raise ValueError(f"The uploaded {dataset_name} file is empty.")
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)


def load_temperature_data(uploaded_file: BinaryIO | None = None) -> pd.DataFrame:
    """Load and clean an uploaded temperature log or the bundled sample."""
    if uploaded_file is not None:
        source = "uploaded"
        _validate_upload(uploaded_file, "temperature CSV")
        input_file = uploaded_file
    else:
        source = "bundled demonstration"
        input_file = _sample_file_path(TEMPERATURE_SAMPLE_NAME)
    try:
        raw_df = pd.read_csv(input_file)
    except Exception as error:
        raise ValueError(
            f"Could not read the {source} temperature CSV: {error}"
        ) from error

    return clean_temperature_data(raw_df)


def load_quality_data(uploaded_file: BinaryIO | None = None) -> pd.DataFrame:
    """Load uploaded workbook cells or the bundled sample without headers."""
    if uploaded_file is not None:
        source = "uploaded"
        _validate_upload(uploaded_file, "quality workbook")
        input_file = uploaded_file
    else:
        source = "bundled demonstration"
        input_file = _sample_file_path(QUALITY_SAMPLE_NAME)
    try:
        return pd.read_excel(input_file, header=None)
    except Exception as error:
        raise ValueError(
            f"Could not read the {source} quality workbook: {error}"
        ) from error
