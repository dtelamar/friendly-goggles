"""Tests for driving-event detection, scoring, and classification."""

from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from data_loader import load_telemetry
from metrics import (
    DrivingMetrics,
    MetricsCalculationError,
    calculate_driving_metrics,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PATH = REPOSITORY_ROOT / "sample_data" / "drive_log.csv"


def _telemetry(
    *,
    timestamps: list[float],
    rpm: list[float] | None = None,
    speed: list[float] | None = None,
    throttle: list[float] | None = None,
    coolant: list[float] | None = None,
) -> pd.DataFrame:
    row_count = len(timestamps)
    return pd.DataFrame(
        {
            "timestamp_s": timestamps,
            "engine_rpm": rpm or [2000.0] * row_count,
            "vehicle_speed_kph": speed or [40.0] * row_count,
            "throttle_position_pct": throttle or [20.0] * row_count,
            "coolant_temperature_c": coolant or [90.0] * row_count,
        }
    )


class DrivingMetricsTests(unittest.TestCase):
    def test_groups_contiguous_samples_into_single_events(self) -> None:
        telemetry = _telemetry(
            timestamps=[0, 1, 2, 3, 4, 5, 6],
            rpm=[800, 4600, 4700, 2000, 2000, 800, 800],
            speed=[0, 20, 25, 30, 30, 0, 0],
            throttle=[2, 85, 90, 20, 20, 2, 2],
            coolant=[90, 90, 90, 105, 106, 90, 90],
        )

        metrics = calculate_driving_metrics(telemetry)

        self.assertEqual(
            metrics,
            DrivingMetrics(
                idle_time_s=2.0,
                aggressive_acceleration_events=1,
                hard_braking_events=1,
                high_coolant_temperature_events=1,
                driver_score=75,
                classification="Smooth Driver",
            ),
        )

    def test_idle_duration_uses_irregular_sample_intervals(self) -> None:
        telemetry = _telemetry(
            timestamps=[0, 2, 5, 8],
            rpm=[800, 850, 2000, 2000],
            speed=[0, 0, 10, 10],
            throttle=[2, 2, 20, 20],
        )

        metrics = calculate_driving_metrics(telemetry)

        self.assertEqual(metrics.idle_time_s, 5.0)
        self.assertEqual(metrics.driver_score, 98)
        self.assertEqual(metrics.classification, "Smooth Driver")

    def test_hard_braking_uses_elapsed_time_and_metric_units(self) -> None:
        telemetry = _telemetry(
            timestamps=[0, 1, 3],
            speed=[36, 36, 0],
        )

        metrics = calculate_driving_metrics(telemetry)

        self.assertEqual(metrics.hard_braking_events, 1)

    def test_event_thresholds_use_documented_boundaries(self) -> None:
        telemetry = _telemetry(
            timestamps=[0, 1, 2],
            rpm=[4500, 4500.1, 2000],
            throttle=[80, 80.1, 20],
            coolant=[104.9, 105, 105.1],
        )

        metrics = calculate_driving_metrics(telemetry)

        self.assertEqual(metrics.aggressive_acceleration_events, 1)
        self.assertEqual(metrics.high_coolant_temperature_events, 1)

    def test_classifies_low_load_trip_as_economical(self) -> None:
        telemetry = _telemetry(
            timestamps=[0, 10, 20],
            speed=[30, 32, 31],
            throttle=[12, 14, 13],
        )

        metrics = calculate_driving_metrics(telemetry)

        self.assertEqual(metrics.driver_score, 100)
        self.assertEqual(metrics.classification, "Economical Driver")

    def test_canonical_sample_detects_deliberate_scenarios(self) -> None:
        metrics = calculate_driving_metrics(load_telemetry(SAMPLE_PATH))

        self.assertEqual(metrics.aggressive_acceleration_events, 1)
        self.assertEqual(metrics.hard_braking_events, 2)
        self.assertEqual(metrics.high_coolant_temperature_events, 1)
        self.assertEqual(metrics.driver_score, 67)
        self.assertEqual(metrics.classification, "Aggressive Driver")

    def test_sorts_input_without_modifying_caller_dataframe(self) -> None:
        telemetry = _telemetry(timestamps=[2, 0, 1])
        original = telemetry.copy(deep=True)

        calculate_driving_metrics(telemetry)

        pd.testing.assert_frame_equal(telemetry, original)

    def test_rejects_empty_missing_and_duplicate_timestamp_inputs(self) -> None:
        valid = _telemetry(timestamps=[0, 1])
        cases = {
            "empty": valid.iloc[0:0],
            "missing": valid.drop(columns="engine_rpm"),
            "duplicate": _telemetry(timestamps=[0, 0]),
        }

        for label, telemetry in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(MetricsCalculationError):
                    calculate_driving_metrics(telemetry)


if __name__ == "__main__":
    unittest.main()
