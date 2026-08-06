"""Regression tests for the canonical synthetic telemetry sample."""

from __future__ import annotations

import csv
import unittest
from pathlib import Path

from scripts.generate_sample_data import COLUMNS, generate_rows


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PATH = REPOSITORY_ROOT / "sample_data" / "drive_log.csv"


def _read_sample() -> list[dict[str, int | float]]:
    with SAMPLE_PATH.open(encoding="utf-8", newline="") as sample_file:
        reader = csv.DictReader(sample_file)
        rows: list[dict[str, int | float]] = []
        for row in reader:
            rows.append(
                {
                    "timestamp_s": int(row["timestamp_s"]),
                    "engine_rpm": int(row["engine_rpm"]),
                    "vehicle_speed_kph": float(row["vehicle_speed_kph"]),
                    "throttle_position_pct": float(row["throttle_position_pct"]),
                    "coolant_temperature_c": float(row["coolant_temperature_c"]),
                    "intake_air_temperature_c": float(
                        row["intake_air_temperature_c"]
                    ),
                    "engine_load_pct": float(row["engine_load_pct"]),
                }
            )
        if reader.fieldnames != list(COLUMNS):
            raise AssertionError(f"Unexpected CSV columns: {reader.fieldnames}")
        return rows


def _count_event_groups(flags: list[bool]) -> int:
    return sum(
        flag and (index == 0 or not flags[index - 1])
        for index, flag in enumerate(flags)
    )


class SampleDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = _read_sample()

    def test_committed_csv_matches_generator(self) -> None:
        self.assertEqual(self.rows, generate_rows())

    def test_trip_shape_and_cadence(self) -> None:
        self.assertEqual(len(self.rows), 601)
        self.assertEqual(
            [row["timestamp_s"] for row in self.rows],
            list(range(601)),
        )

    def test_signal_ranges_are_plausible(self) -> None:
        for row in self.rows:
            self.assertGreaterEqual(row["engine_rpm"], 700)
            self.assertLessEqual(row["engine_rpm"], 6500)
            self.assertGreaterEqual(row["vehicle_speed_kph"], 0.0)
            self.assertLessEqual(row["vehicle_speed_kph"], 130.0)
            self.assertGreaterEqual(row["throttle_position_pct"], 0.0)
            self.assertLessEqual(row["throttle_position_pct"], 100.0)
            self.assertGreaterEqual(row["engine_load_pct"], 0.0)
            self.assertLessEqual(row["engine_load_pct"], 100.0)
            self.assertGreaterEqual(row["coolant_temperature_c"], 65.0)
            self.assertLessEqual(row["coolant_temperature_c"], 115.0)
            self.assertGreaterEqual(row["intake_air_temperature_c"], 15.0)
            self.assertLessEqual(row["intake_air_temperature_c"], 60.0)

    def test_deliberate_scenarios_are_detectable(self) -> None:
        aggressive_flags = [
            row["throttle_position_pct"] > 80.0 and row["engine_rpm"] > 4500
            for row in self.rows
        ]

        acceleration_mps2 = [0.0]
        for previous, current in zip(self.rows, self.rows[1:]):
            delta_time_s = current["timestamp_s"] - previous["timestamp_s"]
            delta_speed_mps = (
                current["vehicle_speed_kph"] - previous["vehicle_speed_kph"]
            ) / 3.6
            acceleration_mps2.append(delta_speed_mps / delta_time_s)
        hard_braking_flags = [value <= -3.0 for value in acceleration_mps2]

        hot_coolant_flags = [
            row["coolant_temperature_c"] >= 105.0 for row in self.rows
        ]

        self.assertEqual(_count_event_groups(aggressive_flags), 1)
        self.assertEqual(_count_event_groups(hard_braking_flags), 2)
        self.assertEqual(_count_event_groups(hot_coolant_flags), 1)
        self.assertGreaterEqual(
            sum(row["vehicle_speed_kph"] == 0.0 for row in self.rows),
            70,
        )


if __name__ == "__main__":
    unittest.main()
