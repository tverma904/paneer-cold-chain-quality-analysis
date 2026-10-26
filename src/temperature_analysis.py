"""Temperature-log cleaning and timestamp-aware cold-chain summaries."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

TEMPERATURE_COLUMNS = ("Time_Stamp", "Temperature")
OPTIONAL_COLUMNS = ("Counter", "RH", "Compressor", "Fridge_Open")


def clean_temperature_data(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Parse known fields while retaining invalid rows for data-quality review."""
    missing = set(TEMPERATURE_COLUMNS) - set(raw_df.columns)
    if missing:
        raise ValueError(f"Temperature file is missing columns: {sorted(missing)}")

    df = raw_df.copy()
    for column in OPTIONAL_COLUMNS:
        if column not in df.columns:
            df[column] = np.nan

    df["Time_Stamp"] = pd.to_datetime(
        df["Time_Stamp"], dayfirst=True, errors="coerce"
    )
    df["Temperature"] = pd.to_numeric(df["Temperature"], errors="coerce")
    df["RH"] = pd.to_numeric(df["RH"], errors="coerce")
    df["Temperature"] = df["Temperature"].where(np.isfinite(df["Temperature"]))
    df["RH"] = df["RH"].where(np.isfinite(df["RH"]))

    return df.sort_values("Time_Stamp", kind="stable", na_position="last").reset_index(
        drop=True
    )


def _state_value(value: Any) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip().casefold()
    if not text:
        return None
    if text in {"1", "1.0", "true", "yes", "on", "open"}:
        return "On" if text != "open" else "Open"
    if text in {"0", "0.0", "false", "no", "off", "closed"}:
        return "Off" if text != "closed" else "Closed"
    return str(value).strip()


def _timestamp_observations(df: pd.DataFrame) -> pd.DataFrame:
    valid = df.dropna(subset=["Time_Stamp", "Temperature"]).copy()
    if valid.empty:
        return pd.DataFrame(columns=["Time_Stamp", "Temperature", "RH"])

    aggregations: dict[str, Any] = {
        "Temperature": "mean",
        "RH": "mean",
    }
    for column in ("Compressor", "Fridge_Open"):
        if column in valid.columns:
            aggregations[column] = lambda values: (
                values.dropna().iloc[-1] if values.notna().any() else np.nan
            )
    return (
        valid.groupby("Time_Stamp", as_index=False, sort=True)
        .agg(aggregations)
        .sort_values("Time_Stamp")
        .reset_index(drop=True)
    )


def _crossing_time(
    first_time: pd.Timestamp,
    first_value: float,
    second_time: pd.Timestamp,
    second_value: float,
    threshold: float,
) -> pd.Timestamp:
    fraction = (threshold - first_value) / (second_value - first_value)
    return first_time + (second_time - first_time) * fraction


def _excursions(
    observations: pd.DataFrame,
    threshold: float,
    max_gap: pd.Timedelta,
) -> tuple[pd.DataFrame, float]:
    columns = [
        "Start",
        "End",
        "Duration_Minutes",
        "Recovery_Duration_Minutes",
        "Recovery_Estimable",
    ]
    if observations.empty:
        return pd.DataFrame(columns=columns), 0.0

    times = observations["Time_Stamp"].tolist()
    temperatures = observations["Temperature"].astype(float).tolist()
    above_indices = [i for i, value in enumerate(temperatures) if value > threshold]
    if not above_indices:
        return pd.DataFrame(columns=columns), 0.0

    groups: list[list[int]] = [[above_indices[0]]]
    for index in above_indices[1:]:
        previous = groups[-1][-1]
        if index == previous + 1 and times[index] - times[previous] <= max_gap:
            groups[-1].append(index)
        else:
            groups.append([index])

    records: list[dict[str, Any]] = []
    total_above_seconds = 0.0
    for group in groups:
        first, last = group[0], group[-1]
        start = times[first]
        end = times[last]
        if first > 0 and times[first] - times[first - 1] <= max_gap:
            start = _crossing_time(
                times[first - 1],
                temperatures[first - 1],
                times[first],
                temperatures[first],
                threshold,
            )
        if last + 1 < len(times) and times[last + 1] - times[last] <= max_gap:
            end = _crossing_time(
                times[last],
                temperatures[last],
                times[last + 1],
                temperatures[last + 1],
                threshold,
            )

        duration = max(0.0, (end - start).total_seconds())
        total_above_seconds += duration
        recovery_estimable = (
            last + 1 < len(times)
            and times[last + 1] - times[last] <= max_gap
            and temperatures[last + 1] <= threshold
        )
        recovery_seconds = (
            max(0.0, (end - times[first]).total_seconds())
            if recovery_estimable
            else np.nan
        )
        records.append(
            {
                "Start": start,
                "End": end,
                "Duration_Minutes": duration / 60,
                "Recovery_Duration_Minutes": recovery_seconds / 60,
                "Recovery_Estimable": recovery_estimable,
            }
        )

    return pd.DataFrame(records, columns=columns), total_above_seconds / 3600


def analyze_temperature(
    df: pd.DataFrame,
    threshold: float = 4.0,
    max_gap: str | pd.Timedelta = "30min",
) -> dict[str, Any]:
    """Summarize observations and estimate above-threshold time.

    Intervals are estimated only between distinct, valid timestamps no farther
    apart than ``max_gap``. Threshold crossings are linearly interpolated;
    gaps beyond the limit are unknown and are not counted. Excursion counts
    are observed runs, so unobserved events inside long gaps cannot be inferred.
    """
    if threshold is None or not np.isfinite(float(threshold)):
        raise ValueError("threshold must be a finite number")
    gap_limit = pd.Timedelta(max_gap)
    if gap_limit <= pd.Timedelta(0):
        raise ValueError("max_gap must be greater than zero")

    cleaned = clean_temperature_data(df)
    valid_readings = cleaned.dropna(subset=["Time_Stamp", "Temperature"])
    observations = _timestamp_observations(cleaned)
    valid_count = len(valid_readings)
    temperatures = valid_readings["Temperature"]
    above_count = int((temperatures > threshold).sum())
    excursions, above_hours = _excursions(observations, float(threshold), gap_limit)

    if len(observations) > 1:
        gaps = observations["Time_Stamp"].diff().dropna()
        gap_count = int((gaps > gap_limit).sum())
        largest_gap_minutes = gaps.max().total_seconds() / 60
    else:
        gap_count = 0
        largest_gap_minutes = np.nan

    humidity = valid_readings["RH"].dropna()
    state_summaries: dict[str, dict[str, int]] = {}
    for column in ("Fridge_Open", "Compressor"):
        if column not in valid_readings:
            state_summaries[column] = {}
            continue
        states = valid_readings[column].map(_state_value)
        state_summaries[column] = {
            str(state): int(count)
            for state, count in states.value_counts(dropna=True).items()
        }

    door_states = observations.get(
        "Fridge_Open", pd.Series(dtype=object)
    ).map(_state_value)
    door_open_values = {"Open", "On"}
    opening_count = 0
    if len(observations) > 1 and "Fridge_Open" in observations:
        gap_mask = observations["Time_Stamp"].diff().gt(gap_limit)
        previous_state: str | None = None
        for index, current in enumerate(door_states):
            if index and gap_mask.iloc[index]:
                previous_state = None
            if (
                previous_state is not None
                and current in door_open_values
                and previous_state not in door_open_values
            ):
                opening_count += 1
            previous_state = current

    recovery = excursions.loc[
        excursions["Recovery_Estimable"], "Recovery_Duration_Minutes"
    ]
    return {
        "valid_readings": valid_count,
        "mean_temperature": float(temperatures.mean()) if valid_count else np.nan,
        "minimum_temperature": float(temperatures.min()) if valid_count else np.nan,
        "maximum_temperature": float(temperatures.max()) if valid_count else np.nan,
        "median_temperature": float(temperatures.median()) if valid_count else np.nan,
        "readings_above_threshold": above_count,
        "percent_readings_above_threshold": (
            above_count / valid_count * 100 if valid_count else np.nan
        ),
        "estimated_time_above_threshold_hours": above_hours,
        "excursion_count": len(excursions),
        "longest_excursion_minutes": (
            float(excursions["Duration_Minutes"].max()) if not excursions.empty else 0.0
        ),
        "mean_recovery_duration_minutes": (
            float(recovery.mean()) if not recovery.empty else np.nan
        ),
        "estimable_recovery_count": len(recovery),
        "excursions": excursions,
        "humidity_valid_readings": int(humidity.count()),
        "mean_humidity": float(humidity.mean()) if not humidity.empty else np.nan,
        "minimum_humidity": float(humidity.min()) if not humidity.empty else np.nan,
        "maximum_humidity": float(humidity.max()) if not humidity.empty else np.nan,
        "door_opening_count": opening_count,
        "state_counts": state_summaries,
        "timestamp_gap_count": gap_count,
        "largest_timestamp_gap_minutes": largest_gap_minutes,
        "maximum_estimation_gap_minutes": gap_limit.total_seconds() / 60,
        "observations": observations,
    }
