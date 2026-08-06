"""Tests for CSV telemetry loading and schema validation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from data_loader import REQUIRED_COLUMNS, TelemetryValidationError, load_telemetry


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PATH = REPOSITORY_ROOT / "sample_data" / "drive_log.csv"

VALID_ROW = {
    "timestamp_s": 0,
    "engine_rpm": 800,
    "vehicle_speed_kph": 0,
    "throttle_position_pct": 2,
    "coolant_temperature_c": 90,
    "intake_air_temperature_c": 30,
    "engine_load_pct": 12,
}


class DataLoaderTests(unittest.TestCase):
    def _write_csv(self, contents: str) -> Path:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        path = Path(temporary_directory.name) / "telemetry.csv"
        path.write_text(contents, encoding="utf-8")
        return path

    def _csv_from_rows(
        self,
        rows: list[dict[str, object]],
        columns: tuple[str, ...] = REQUIRED_COLUMNS,
    ) -> Path:
        dataframe = pd.DataFrame(rows, columns=columns)
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        path = Path(temporary_directory.name) / "telemetry.csv"
        dataframe.to_csv(path, index=False, lineterminator="\n")
        return path

    def test_loads_canonical_sample(self) -> None:
        telemetry = load_telemetry(SAMPLE_PATH)

        self.assertEqual(telemetry.shape, (601, 7))
        self.assertEqual(tuple(telemetry.columns), REQUIRED_COLUMNS)
        self.assertTrue(telemetry["timestamp_s"].is_monotonic_increasing)
        self.assertTrue(
            all(dtype == "float64" for dtype in telemetry.dtypes.astype(str))
        )

    def test_sorts_rows_and_discards_unknown_columns(self) -> None:
        later_row = VALID_ROW | {"timestamp_s": 2, "optional_pid": 99}
        earlier_row = VALID_ROW | {"timestamp_s": 1, "optional_pid": 42}
        path = self._csv_from_rows(
            [later_row, earlier_row],
            REQUIRED_COLUMNS + ("optional_pid",),
        )

        telemetry = load_telemetry(path)

        self.assertEqual(telemetry["timestamp_s"].tolist(), [1.0, 2.0])
        self.assertEqual(tuple(telemetry.columns), REQUIRED_COLUMNS)

    def test_rejects_missing_required_columns(self) -> None:
        columns = tuple(
            column for column in REQUIRED_COLUMNS if column != "engine_load_pct"
        )
        path = self._csv_from_rows([VALID_ROW], columns)

        with self.assertRaisesRegex(
            TelemetryValidationError,
            "Missing required columns: engine_load_pct",
        ):
            load_telemetry(path)

    def test_rejects_empty_file_and_header_only_csv(self) -> None:
        cases = {
            "empty file": self._write_csv(""),
            "header only": self._write_csv(",".join(REQUIRED_COLUMNS) + "\n"),
        }

        for label, path in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(TelemetryValidationError):
                    load_telemetry(path)

    def test_rejects_invalid_numeric_values_with_row_number(self) -> None:
        invalid_values = {
            "non-numeric": "unknown",
            "missing": "",
            "non-finite": "inf",
        }

        for label, value in invalid_values.items():
            with self.subTest(label=label):
                path = self._csv_from_rows(
                    [VALID_ROW, VALID_ROW | {"timestamp_s": 1, "engine_rpm": value}]
                )
                with self.assertRaisesRegex(
                    TelemetryValidationError,
                    "Column 'engine_rpm'.*CSV rows: 3",
                ):
                    load_telemetry(path)

    def test_rejects_values_outside_signal_range(self) -> None:
        invalid_values = {
            "timestamp_s": -1,
            "vehicle_speed_kph": -0.1,
            "throttle_position_pct": 100.1,
            "coolant_temperature_c": 216,
            "engine_load_pct": -1,
        }

        for column, value in invalid_values.items():
            with self.subTest(column=column):
                path = self._csv_from_rows([VALID_ROW | {column: value}])
                with self.assertRaisesRegex(TelemetryValidationError, column):
                    load_telemetry(path)

    def test_rejects_duplicate_timestamps(self) -> None:
        path = self._csv_from_rows([VALID_ROW, VALID_ROW])

        with self.assertRaisesRegex(
            TelemetryValidationError,
            "duplicate values at CSV rows: 2, 3",
        ):
            load_telemetry(path)

    def test_missing_path_raises_file_not_found(self) -> None:
        missing_path = Path("does-not-exist.csv")

        with self.assertRaisesRegex(FileNotFoundError, str(missing_path)):
            load_telemetry(missing_path)


if __name__ == "__main__":
    unittest.main()
