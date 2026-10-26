"""Cleaning, summaries, and paired statistical analysis for paneer workbook data."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

QUALITY_COLUMN_MAP = {
    0: "Day",
    1: "Replicate",
    2: "TPC_CFU",
    3: "TPC_Dilution",
    4: "TPC_Log10",
    5: "Coliform_CFU",
    6: "Coliform_Dilution",
    7: "Coliform_Log10",
    8: "Yeast_Mold_CFU",
    9: "Yeast_Mold_Dilution",
    10: "Yeast_Mold_Log10",
    11: "Psychrophilic_CFU",
    12: "Psychrophilic_Dilution",
    13: "Psychrophilic_Log10",
    15: "Colour_Appearance",
    16: "Body_Texture",
    17: "Flavour",
    18: "Overall_Acceptability",
    20: "pH",
    21: "Moisture_Percent",
    23: "Milk",
    24: "Paneer",
    25: "Yield_Percent",
    26: "Fat_Percent",
}
QUALITY_COLUMNS = tuple(QUALITY_COLUMN_MAP.values())
QUALITY_HEADER_LABELS = {
    0: ("day",),
    1: ("repl", "replicate"),
    4: ("total plate count",),
    7: ("coliform count",),
    10: ("yeast and mold", "yeast mold"),
    13: ("psychrophilic count", "pyschrophilic count"),
    15: ("colour and appearance", "color and appearance"),
    16: ("body and texture",),
    17: ("flavour", "flavor"),
    18: ("overall acceptability",),
    20: ("ph",),
    21: ("moisture",),
    25: ("yield",),
    26: ("fat",),
}


def _normalize_header(value: Any) -> str:
    return "".join(character for character in str(value).casefold() if character.isalnum())


def clean_quality_data(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Map the workbook's documented positions and retain replicate rows only."""
    if raw_df is None or raw_df.shape[1] <= max(QUALITY_COLUMN_MAP):
        found = 0 if raw_df is None else raw_df.shape[1]
        raise ValueError(
            "Quality workbook does not match the expected positional layout: "
            f"expected at least {max(QUALITY_COLUMN_MAP) + 1} columns, found {found}."
        )
    if raw_df.shape[0] < 2:
        raise ValueError(
            "Quality workbook is missing the expected column-heading row at row 2."
        )

    mismatches = []
    for column, expected_labels in QUALITY_HEADER_LABELS.items():
        actual = _normalize_header(raw_df.iat[1, column])
        if not any(
            _normalize_header(expected) in actual for expected in expected_labels
        ):
            mismatches.append(
                f"column {column} expected one of {expected_labels}, found "
                f"'{raw_df.iat[1, column]}'"
            )
    if mismatches:
        raise ValueError(
            "Quality workbook headings do not match the expected positional layout: "
            + "; ".join(mismatches)
        )

    df = raw_df.copy()
    df["Source_Row"] = np.arange(1, len(df) + 1)
    df = df.rename(columns=QUALITY_COLUMN_MAP)
    df = df.loc[:, ["Source_Row", *QUALITY_COLUMNS]]

    df["Day"] = pd.to_numeric(df["Day"], errors="coerce")
    df["Replicate"] = pd.to_numeric(df["Replicate"], errors="coerce")
    valid_day = df["Day"].between(0, 13) & df["Day"].mod(1).eq(0)
    valid_replicate = (
        df["Replicate"].between(1, 5) & df["Replicate"].mod(1).eq(0)
    )
    df = df.loc[valid_day & valid_replicate].copy()

    for column in QUALITY_COLUMNS:
        if column not in {"Day", "Replicate"}:
            df[column] = pd.to_numeric(df[column], errors="coerce")
            df[column] = df[column].where(np.isfinite(df[column]))

    return df.sort_values(["Day", "Replicate"], kind="stable").reset_index(drop=True)


def daily_quality_summary(cleaned_df: pd.DataFrame) -> pd.DataFrame:
    """Return per-day means, sample SDs, and nonmissing sample counts."""
    measurement_columns = [
        column
        for column in cleaned_df.select_dtypes(include="number").columns
        if column not in {"Day", "Replicate", "Source_Row"}
    ]
    if cleaned_df.empty or not measurement_columns:
        return pd.DataFrame(columns=["Day"])

    grouped = cleaned_df.groupby("Day")[measurement_columns].agg(
        ["mean", "std", "count"]
    )
    statistic_labels = {"mean": "Mean", "std": "SD", "count": "N"}
    grouped.columns = [
        f"{column}_{statistic_labels[statistic]}"
        for column, statistic in grouped.columns
    ]
    return grouped.reset_index()


def missing_value_summary(cleaned_df: pd.DataFrame) -> pd.DataFrame:
    """Report missing counts and percentages without imputing values."""
    columns = [
        column
        for column in cleaned_df.columns
        if column not in {"Source_Row", "Day", "Replicate"}
    ]
    row_count = len(cleaned_df)
    return pd.DataFrame(
        {
            "Variable": columns,
            "Missing_Count": [int(cleaned_df[column].isna().sum()) for column in columns],
            "Missing_Percent": [
                float(cleaned_df[column].isna().mean() * 100) if row_count else np.nan
                for column in columns
            ],
        }
    )


def quality_data_diagnostics(cleaned_df: pd.DataFrame) -> list[str]:
    """Describe expected-experiment discrepancies without discarding valid data."""
    messages: list[str] = []
    observed_pairs = cleaned_df[["Day", "Replicate"]]
    duplicate_count = int(observed_pairs.duplicated().sum())
    if duplicate_count:
        messages.append(
            f"{duplicate_count} duplicate Day/Replicate combination(s) were found."
        )

    expected_pairs = {(day, replicate) for day in range(14) for replicate in range(1, 6)}
    actual_pairs = set(map(tuple, observed_pairs.itertuples(index=False, name=None)))
    if len(cleaned_df) != 70:
        messages.append(
            f"Expected 70 replicate observations (14 days × 5 replicates); "
            f"found {len(cleaned_df)}."
        )
    missing_pairs = expected_pairs - actual_pairs
    if missing_pairs:
        messages.append(
            f"{len(missing_pairs)} expected Day/Replicate pair(s) are absent."
        )
    return messages


def paired_correlations(
    cleaned_df: pd.DataFrame,
    x_column: str = "TPC_Log10",
    y_column: str = "Overall_Acceptability",
) -> dict[str, Any]:
    """Compute Pearson and Spearman correlations from complete pairs only."""
    missing_columns = {x_column, y_column} - set(cleaned_df.columns)
    if missing_columns:
        raise ValueError(f"Quality data is missing columns: {sorted(missing_columns)}")

    paired = cleaned_df[[x_column, y_column]].apply(
        pd.to_numeric, errors="coerce"
    ).dropna()
    paired = paired.loc[np.isfinite(paired).all(axis=1)]
    count = len(paired)
    result: dict[str, Any] = {
        "n": count,
        "x_column": x_column,
        "y_column": y_column,
        "pearson_r": np.nan,
        "pearson_p": np.nan,
        "spearman_r": np.nan,
        "spearman_p": np.nan,
    }
    if count < 2:
        return result

    x = paired[x_column].to_numpy(dtype=float)
    y = paired[y_column].to_numpy(dtype=float)
    if np.ptp(x) > 0 and np.ptp(y) > 0:
        pearson = stats.pearsonr(x, y)
        spearman = stats.spearmanr(x, y)
        result.update(
            pearson_r=float(pearson.statistic),
            pearson_p=float(pearson.pvalue),
            spearman_r=float(spearman.statistic),
            spearman_p=float(spearman.pvalue),
        )
    return result


def format_p_value(p_value: float | None) -> str:
    """Format p-values consistently for dashboard output."""
    if p_value is None or not np.isfinite(p_value):
        return "Not estimable"
    if p_value < 0.001:
        return "<0.001"
    return f"{p_value:.3f}"
