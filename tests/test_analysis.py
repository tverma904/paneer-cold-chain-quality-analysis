import unittest
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.data_loader import load_quality_data, load_temperature_data
from src.quality_analysis import (
    clean_quality_data,
    daily_quality_summary,
    format_p_value,
    missing_value_summary,
    paired_correlations,
    quality_data_diagnostics,
)
from src.temperature_analysis import analyze_temperature, clean_temperature_data

QUALITY_HEADERS = [
    "Day",
    "Repl",
    "cfu/ml",
    "dil",
    "Total plate count (TPC)",
    "cfu/ml",
    "dil",
    "Coliform count",
    "cfu/ml",
    "dil",
    "Yeast and mold",
    "cfu/ml",
    "dil",
    "Pyschrophilic count",
    np.nan,
    "Colour and Appearance",
    "Body and Texture",
    "Flavour",
    "Overall Acceptability",
    np.nan,
    "pH",
    "Moisture %",
    np.nan,
    "Milk",
    "Paneer",
    "Yield (%)",
    "Fat %",
]


def _quality_rows():
    rows = [[np.nan] * 27, QUALITY_HEADERS]
    for day in range(14):
        for replicate in range(1, 6):
            row = [np.nan] * 27
            row[0] = day
            row[1] = replicate
            row[2] = 20 + day + replicate
            row[3] = 1
            row[4] = day + replicate / 10
            row[5] = day + replicate
            row[6] = 1
            row[7] = day + replicate / 10
            row[8] = day + replicate + 1
            row[9] = 1
            row[10] = day + replicate / 10
            row[11] = day + replicate + 2
            row[12] = 1
            row[13] = day + replicate / 10
            row[15] = 5 + replicate
            row[16] = 6 + replicate
            row[17] = 7 + replicate
            row[18] = 8 + replicate
            row[20] = 6.2 + day / 100
            row[21] = 52 + day
            rows.append(row)
    return rows


def _quality_workbook_bytes(tpc_value):
    row = [np.nan] * 27
    row[0] = 0
    row[1] = 1
    row[4] = tpc_value
    row[26] = 5
    workbook = BytesIO()
    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        pd.DataFrame([row]).to_excel(writer, header=False, index=False)
    workbook.seek(0)
    return workbook.getvalue()


class DataLoaderTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.raw_directory = Path(self.temporary_directory.name)
        self.data_loader_patch = patch(
            "src.data_loader.SAMPLE_DATA_DIR", self.raw_directory
        )
        self.data_loader_patch.start()
        self.addCleanup(self.data_loader_patch.stop)

    def write_sample_datasets(self, temperature=2.5, tpc=1.25):
        pd.DataFrame(
            {
                "Time_Stamp": ["02-01-2024 00:00"],
                "Temperature": [temperature],
            }
        ).to_csv(self.raw_directory / "temperature_demo.csv", index=False)
        (self.raw_directory / "paneer_quality_demo.xlsx").write_bytes(
            _quality_workbook_bytes(tpc)
        )

    def test_loads_bundled_datasets_when_no_upload_is_provided(self):
        self.write_sample_datasets()

        temperature = load_temperature_data()
        quality = load_quality_data()

        self.assertEqual(temperature.loc[0, "Temperature"], 2.5)
        self.assertEqual(temperature.loc[0, "Time_Stamp"], pd.Timestamp("2024-01-02"))
        self.assertEqual(quality.iloc[0, 4], 1.25)

    def test_uploaded_datasets_take_precedence_over_sample_files(self):
        self.write_sample_datasets(temperature=2.5, tpc=1.25)
        temperature_upload = BytesIO(
            b"Time_Stamp,Temperature\n03-01-2024 00:00,8.5\n"
        )
        quality_upload = BytesIO(_quality_workbook_bytes(3.75))

        temperature = load_temperature_data(temperature_upload)
        quality = load_quality_data(quality_upload)

        self.assertEqual(temperature.loc[0, "Temperature"], 8.5)
        self.assertEqual(temperature.loc[0, "Time_Stamp"], pd.Timestamp("2024-01-03"))
        self.assertEqual(quality.iloc[0, 4], 3.75)

    def test_temperature_upload_overrides_only_temperature_sample(self):
        self.write_sample_datasets(temperature=2.5, tpc=1.25)
        uploaded = BytesIO(b"Time_Stamp,Temperature\n03-01-2024 00:00,8.5\n")

        temperature = load_temperature_data(uploaded)
        quality = load_quality_data()

        self.assertEqual(temperature.loc[0, "Temperature"], 8.5)
        self.assertEqual(quality.iloc[0, 4], 1.25)

    def test_quality_upload_overrides_only_quality_sample(self):
        self.write_sample_datasets(temperature=2.5, tpc=1.25)
        uploaded = BytesIO(_quality_workbook_bytes(3.75))

        temperature = load_temperature_data()
        quality = load_quality_data(uploaded)

        self.assertEqual(temperature.loc[0, "Temperature"], 2.5)
        self.assertEqual(quality.iloc[0, 4], 3.75)

    def test_missing_and_empty_sample_files_are_reported(self):
        with self.assertRaisesRegex(FileNotFoundError, "demonstration dataset is missing"):
            load_temperature_data()
        with self.assertRaisesRegex(FileNotFoundError, "demonstration dataset is missing"):
            load_quality_data()

        (self.raw_directory / "temperature_demo.csv").write_bytes(b"")
        with self.assertRaisesRegex(ValueError, "demonstration dataset is empty"):
            load_temperature_data()

        (self.raw_directory / "paneer_quality_demo.xlsx").write_bytes(b"")
        with self.assertRaisesRegex(ValueError, "demonstration dataset is empty"):
            load_quality_data()

    def test_empty_upload_is_reported(self):
        with self.assertRaisesRegex(ValueError, "uploaded temperature CSV file is empty"):
            load_temperature_data(BytesIO(b""))
        with self.assertRaisesRegex(ValueError, "uploaded quality workbook file is empty"):
            load_quality_data(BytesIO(b""))

    def test_default_sample_files_have_usable_expected_schemas(self):
        from src.data_loader import (
            PROJECT_ROOT,
            QUALITY_SAMPLE_NAME,
            TEMPERATURE_SAMPLE_NAME,
        )

        temperature_path = PROJECT_ROOT / "data" / "sample" / TEMPERATURE_SAMPLE_NAME
        quality_path = PROJECT_ROOT / "data" / "sample" / QUALITY_SAMPLE_NAME
        self.assertEqual(temperature_path.parent, PROJECT_ROOT / "data" / "sample")
        self.assertTrue(temperature_path.is_file())
        self.assertTrue(quality_path.is_file())
        raw_temperature = pd.read_csv(temperature_path)
        raw_quality = pd.read_excel(quality_path, header=None)
        self.assertEqual(
            set(raw_temperature.columns),
            {"Counter", "Time_Stamp", "Temperature", "RH", "Compressor", "Fridge_Open"},
        )
        cleaned_temperature = clean_temperature_data(raw_temperature)
        cleaned_quality = clean_quality_data(raw_quality)
        with patch("src.data_loader.SAMPLE_DATA_DIR", temperature_path.parent):
            loaded_temperature = load_temperature_data()
            loaded_quality = load_quality_data()
        self.assertGreaterEqual(len(cleaned_temperature), 100)
        self.assertTrue(cleaned_temperature["Time_Stamp"].notna().all())
        self.assertGreater(
            analyze_temperature(cleaned_temperature)["excursion_count"], 0
        )
        self.assertEqual(len(cleaned_quality), 70)
        self.assertEqual(cleaned_quality["Day"].nunique(), 14)
        self.assertEqual(cleaned_quality.groupby("Day").Replicate.nunique().min(), 5)
        self.assertEqual(
            int(cleaned_quality["Overall_Acceptability"].notna().sum()), 50
        )
        for column in [
            "TPC_Log10",
            "Coliform_Log10",
            "Yeast_Mold_Log10",
            "Psychrophilic_Log10",
            "pH",
            "Moisture_Percent",
        ]:
            self.assertTrue(cleaned_quality[column].notna().any(), column)
        self.assertEqual(len(loaded_temperature), len(cleaned_temperature))
        self.assertEqual(len(loaded_quality), len(raw_quality))

    def test_malformed_uploads_raise_clear_read_errors(self):
        malformed_temperature = BytesIO(b"not_a_temperature_column\n1\n")
        with self.assertRaisesRegex(
            ValueError, "Temperature file is missing columns"
        ):
            load_temperature_data(malformed_temperature)

        malformed_quality = BytesIO(b"not an Excel workbook")
        with self.assertRaisesRegex(
            ValueError, "Could not read the uploaded quality workbook"
        ):
            load_quality_data(malformed_quality)


class TemperatureAnalysisTests(unittest.TestCase):
    def test_cleaning_parses_dates_coerces_values_and_sorts(self):
        raw = pd.DataFrame(
            {
                "Time_Stamp": ["02-01-2024 00:10", "invalid", "02-01-2024 00:00"],
                "Temperature": ["5.2", "bad", "3.1"],
                "RH": ["60", "bad", "55"],
                "Fridge_Open": ["0", "1", "0"],
            }
        )

        cleaned = clean_temperature_data(raw)

        self.assertEqual(cleaned["Time_Stamp"].iloc[0], pd.Timestamp("2024-01-02"))
        self.assertTrue(pd.isna(cleaned["Time_Stamp"].iloc[-1]))
        self.assertTrue(pd.isna(cleaned["Temperature"].iloc[-1]))
        self.assertTrue(cleaned["Compressor"].isna().all())

    def test_excursion_duration_uses_interpolated_crossings(self):
        raw = pd.DataFrame(
            {
                "Time_Stamp": pd.date_range("2024-01-01", periods=4, freq="10min"),
                "Temperature": [3.0, 5.0, 7.0, 3.0],
            }
        )

        result = analyze_temperature(raw, threshold=4, max_gap="15min")

        self.assertEqual(result["valid_readings"], 4)
        self.assertEqual(result["excursion_count"], 1)
        self.assertAlmostEqual(
            result["estimated_time_above_threshold_hours"] * 60, 22.5
        )
        self.assertAlmostEqual(result["longest_excursion_minutes"], 22.5)
        self.assertEqual(result["estimable_recovery_count"], 1)
        self.assertAlmostEqual(result["mean_recovery_duration_minutes"], 17.5)

    def test_irregular_and_long_timestamp_gaps_are_not_counted(self):
        raw = pd.DataFrame(
            {
                "Time_Stamp": [
                    "01-01-2024 00:20",
                    "01-01-2024 00:00",
                    "01-01-2024 02:00",
                ],
                "Temperature": [6.0, 5.0, 5.0],
            }
        )

        result = analyze_temperature(raw, threshold=4, max_gap="30min")

        self.assertEqual(result["excursion_count"], 2)
        self.assertAlmostEqual(
            result["estimated_time_above_threshold_hours"] * 60, 20
        )
        self.assertEqual(result["timestamp_gap_count"], 1)
        self.assertAlmostEqual(result["largest_timestamp_gap_minutes"], 100)

    def test_duplicate_timestamps_count_as_readings_but_not_duration_intervals(self):
        raw = pd.DataFrame(
            {
                "Time_Stamp": [
                    "01-01-2024 00:10",
                    "01-01-2024 00:00",
                    "01-01-2024 00:00",
                ],
                "Temperature": [5.0, 4.0, 2.0],
            }
        )

        result = analyze_temperature(raw, threshold=4, max_gap="15min")

        self.assertEqual(result["valid_readings"], 3)
        self.assertEqual(result["excursion_count"], 1)
        self.assertAlmostEqual(result["estimated_time_above_threshold_hours"] * 60, 5)

    def test_empty_and_invalid_temperature_rows_return_empty_statistics(self):
        raw = pd.DataFrame(
            {"Time_Stamp": ["bad"], "Temperature": ["not-a-number"]}
        )

        result = analyze_temperature(raw)

        self.assertEqual(result["valid_readings"], 0)
        self.assertTrue(np.isnan(result["mean_temperature"]))
        self.assertEqual(result["excursion_count"], 0)

    def test_non_finite_measurements_are_treated_as_missing(self):
        raw = pd.DataFrame(
            {
                "Time_Stamp": ["01-01-2024 00:00"],
                "Temperature": [np.inf],
                "RH": [-np.inf],
            }
        )

        cleaned = clean_temperature_data(raw)

        self.assertTrue(pd.isna(cleaned.loc[0, "Temperature"]))
        self.assertTrue(pd.isna(cleaned.loc[0, "RH"]))


class QualityAnalysisTests(unittest.TestCase):
    def test_microbial_raw_counts_dilutions_and_log_values_are_mapped(self):
        raw = pd.DataFrame(_quality_rows()[:3])
        raw.loc[2, 5] = 0
        raw.loc[2, 6] = 0
        raw.loc[2, 7] = np.nan

        cleaned = clean_quality_data(raw)
        row = cleaned.iloc[0]

        self.assertEqual(row["TPC_CFU"], 21)
        self.assertEqual(row["TPC_Dilution"], 1)
        self.assertEqual(row["TPC_Log10"], 0.1)
        self.assertEqual(row["Coliform_CFU"], 0)
        self.assertEqual(row["Coliform_Dilution"], 0)
        self.assertTrue(pd.isna(row["Coliform_Log10"]))
        self.assertEqual(row["Yeast_Mold_CFU"], 2)
        self.assertEqual(row["Yeast_Mold_Dilution"], 1)
        self.assertEqual(row["Yeast_Mold_Log10"], 0.1)
        self.assertEqual(row["Psychrophilic_CFU"], 3)
        self.assertEqual(row["Psychrophilic_Dilution"], 1)
        self.assertEqual(row["Psychrophilic_Log10"], 0.1)

    def test_cleaning_excludes_mean_and_sd_summary_rows(self):
        raw_rows = _quality_rows()
        for label in ("Mean", "SD"):
            summary = [np.nan] * 27
            summary[0] = label
            summary[1] = label
            summary[4] = 999
            raw_rows.append(summary)

        cleaned = clean_quality_data(pd.DataFrame(raw_rows))

        self.assertEqual(len(cleaned), 70)
        self.assertEqual(cleaned["Day"].nunique(), 14)
        self.assertEqual(cleaned["Replicate"].nunique(), 5)
        self.assertNotIn(999, cleaned["TPC_Log10"].tolist())
        self.assertEqual(quality_data_diagnostics(cleaned), [])

    def test_quality_diagnostics_report_duplicate_and_missing_replicates(self):
        raw = pd.DataFrame(_quality_rows())
        raw = raw.drop(index=[2, 3]).reset_index(drop=True)
        duplicate = raw.iloc[[2]].copy()
        raw = pd.concat([raw, duplicate], ignore_index=True)

        messages = quality_data_diagnostics(clean_quality_data(raw))

        self.assertTrue(any("duplicate Day/Replicate" in message for message in messages))
        self.assertTrue(any("Expected 70" in message for message in messages))
        self.assertTrue(any("expected Day/Replicate pair" in message for message in messages))

    def test_missing_measurements_remain_missing_and_are_reported(self):
        raw = pd.DataFrame(_quality_rows())
        raw.loc[2, 18] = np.inf

        cleaned = clean_quality_data(raw)
        missing = missing_value_summary(cleaned).set_index("Variable")

        self.assertTrue(pd.isna(cleaned.loc[0, "Overall_Acceptability"]))
        self.assertEqual(missing.loc["Overall_Acceptability", "Missing_Count"], 1)
        self.assertAlmostEqual(
            missing.loc["Overall_Acceptability", "Missing_Percent"], 100 / 70
        )

    def test_daily_summary_uses_sample_sd_and_nonmissing_counts(self):
        raw = pd.DataFrame(_quality_rows())
        raw.iloc[2, 4] = np.nan
        cleaned = clean_quality_data(raw)

        day_zero = daily_quality_summary(cleaned).set_index("Day").loc[0]

        self.assertEqual(day_zero["TPC_Log10_N"], 4)
        self.assertAlmostEqual(day_zero["TPC_Log10_Mean"], 0.35)
        self.assertAlmostEqual(
            day_zero["TPC_Log10_SD"], np.std([0.2, 0.3, 0.4, 0.5], ddof=1)
        )

    def test_correlations_use_only_paired_observations(self):
        data = pd.DataFrame(
            {
                "TPC_Log10": [1, 2, 3, np.nan, 5],
                "Overall_Acceptability": [5, 4, 3, 2, np.nan],
            }
        )

        result = paired_correlations(data)

        self.assertEqual(result["n"], 3)
        self.assertAlmostEqual(result["pearson_r"], -1)
        self.assertAlmostEqual(result["spearman_r"], -1)
        self.assertEqual(format_p_value(0.0001), "<0.001")
        self.assertEqual(format_p_value(0.05), "0.050")

    def test_incorrect_workbook_width_is_reported(self):
        with self.assertRaisesRegex(ValueError, "expected at least 27 columns"):
            clean_quality_data(pd.DataFrame([[0, 1, 2]]))

    def test_incorrect_workbook_headers_are_reported(self):
        raw = pd.DataFrame(_quality_rows())
        raw.iloc[1, 7] = "Yield (%)"

        with self.assertRaisesRegex(
            ValueError, "headings do not match.*column 7 expected one of"
        ):
            clean_quality_data(raw)


if __name__ == "__main__":
    unittest.main()
