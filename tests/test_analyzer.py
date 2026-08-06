"""Tests for trip-level telemetry summary calculations."""

from __future__ import annotations

import math
import unittest
from dataclasses import fields
from pathlib import Path

import pandas as pd

from analyzer import TelemetryAnalysisError, TripSummary, summarize_trip
from data_loader import load_telemetry


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PATH = REPOSITORY_ROOT / "sample_data" / "drive_log.csv"


class TripAnalyzerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.telemetry = pd.DataFrame(
            {
                "timestamp_s": [5.0, 7.0, 10.0],
                "engine_rpm": [800.0, 1200.0, 2000.0],
                "vehicle_speed_kph": [0.0, 20.0, 40.0],
                "throttle_position_pct": [2.0, 22.0, 42.0],
                "coolant_temperature_c": [80.0, 90.0, 100.0],
                "intake_air_temperature_c": [30.0, 31.0, 32.0],
            }
        )

    def test_calculates_expected_summary(self) -> None:
        summary = summarize_trip(self.telemetry)

        self.assertEqual(
            summary,
            TripSummary(
                drive_time_s=5.0,
                average_rpm=4000.0 / 3.0,
                minimum_rpm=800.0,
                maximum_rpm=2000.0,
                average_speed_kph=20.0,
                maximum_speed_kph=40.0,
                average_throttle_position_pct=22.0,
                average_coolant_temperature_c=90.0,
                maximum_coolant_temperature_c=100.0,
                average_intake_air_temperature_c=31.0,
            ),
        )

    def test_duration_uses_timestamp_range_for_unsorted_rows(self) -> None:
        unsorted = self.telemetry.iloc[[2, 0, 1]].reset_index(drop=True)

        summary = summarize_trip(unsorted)

        self.assertEqual(summary.drive_time_s, 5.0)

    def test_single_sample_trip_has_zero_duration(self) -> None:
        summary = summarize_trip(self.telemetry.iloc[[0]])

        self.assertEqual(summary.drive_time_s, 0.0)

    def test_rejects_empty_trip(self) -> None:
        empty_trip = self.telemetry.iloc[0:0]

        with self.assertRaisesRegex(
            TelemetryAnalysisError,
            "Cannot summarize an empty telemetry trip",
        ):
            summarize_trip(empty_trip)

    def test_reports_all_missing_summary_columns(self) -> None:
        incomplete = self.telemetry.drop(
            columns=["engine_rpm", "coolant_temperature_c"]
        )

        with self.assertRaisesRegex(
            TelemetryAnalysisError,
            "missing columns: engine_rpm, coolant_temperature_c",
        ):
            summarize_trip(incomplete)

    def test_canonical_sample_produces_finite_summary_values(self) -> None:
        summary = summarize_trip(load_telemetry(SAMPLE_PATH))

        self.assertEqual(summary.drive_time_s, 600.0)
        self.assertEqual(summary.minimum_rpm, 748.0)
        self.assertEqual(summary.maximum_rpm, 5790.0)
        self.assertAlmostEqual(summary.maximum_speed_kph, 112.3)
        for field in fields(summary):
            self.assertTrue(
                math.isfinite(getattr(summary, field.name)),
                msg=f"{field.name} should contain a finite statistic",
            )


if __name__ == "__main__":
    unittest.main()
