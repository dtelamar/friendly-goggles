"""Tests for the end-to-end DriveSense command-line workflow."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest

from analyzer import TripSummary
from graphs import PLOT_FILENAMES
from main import _format_duration, format_trip_report, main
from metrics import DrivingMetrics


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PATH = REPOSITORY_ROOT / "sample_data" / "drive_log.csv"


class CommandLineTests(unittest.TestCase):
    def test_formats_short_and_hour_long_durations(self) -> None:
        cases = {
            0.0: "0m 00s",
            85.0: "1m 25s",
            600.0: "10m 00s",
            3661.0: "1h 01m 01s",
        }

        for seconds, expected in cases.items():
            with self.subTest(seconds=seconds):
                self.assertEqual(_format_duration(seconds), expected)

    def test_formats_trip_report(self) -> None:
        summary = TripSummary(
            drive_time_s=600.0,
            average_rpm=2964.94,
            minimum_rpm=748.0,
            maximum_rpm=5790.0,
            average_speed_kph=54.54,
            maximum_speed_kph=112.3,
            average_throttle_position_pct=19.75,
            average_coolant_temperature_c=90.86,
            maximum_coolant_temperature_c=105.6,
            average_intake_air_temperature_c=29.15,
        )
        metrics = DrivingMetrics(
            idle_time_s=85.0,
            aggressive_acceleration_events=1,
            hard_braking_events=2,
            high_coolant_temperature_events=1,
            driver_score=67,
            classification="Aggressive Driver",
        )

        report = format_trip_report(
            source_path=Path("trip.csv"),
            summary=summary,
            metrics=metrics,
            plot_paths=[Path("output/rpm_vs_time.png")],
        )

        expected_lines = (
            "DriveSense Trip Report",
            "Source: trip.csv",
            "Drive time: 10m 00s",
            "Average RPM: 2,964.9",
            "Maximum speed: 112.3 km/h",
            "Idle time: 1m 25s",
            "Driver score: 67/100",
            "Classification: Aggressive Driver",
            "- output/rpm_vs_time.png",
        )
        for line in expected_lines:
            with self.subTest(line=line):
                self.assertIn(line, report)

    def test_runs_complete_sample_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_directory = Path(temporary_directory) / "plots"
            stdout = StringIO()
            stderr = StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(
                    [
                        str(SAMPLE_PATH),
                        "--output-dir",
                        str(output_directory),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertIn("Drive time: 10m 00s", stdout.getvalue())
            self.assertIn("Driver score: 67/100", stdout.getvalue())
            self.assertIn(
                "Classification: Aggressive Driver",
                stdout.getvalue(),
            )
            self.assertEqual(
                sorted(path.name for path in output_directory.iterdir()),
                sorted(PLOT_FILENAMES),
            )

    def test_returns_error_for_missing_input_file(self) -> None:
        stderr = StringIO()

        with redirect_stderr(stderr):
            exit_code = main(["missing-drive.csv"])

        self.assertEqual(exit_code, 1)
        self.assertIn("DriveSense error: Telemetry CSV not found", stderr.getvalue())

    def test_returns_error_for_invalid_csv(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            invalid_csv = Path(temporary_directory) / "invalid.csv"
            invalid_csv.write_text("timestamp_s,engine_rpm\n0,800\n", encoding="utf-8")
            stderr = StringIO()

            with redirect_stderr(stderr):
                exit_code = main([str(invalid_csv)])

        self.assertEqual(exit_code, 1)
        self.assertIn("DriveSense error: Missing required columns", stderr.getvalue())

    def test_returns_error_when_output_directory_is_a_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_file = Path(temporary_directory) / "plots"
            output_file.write_text("not a directory", encoding="utf-8")
            stderr = StringIO()

            with redirect_stderr(stderr):
                exit_code = main(
                    [
                        str(SAMPLE_PATH),
                        "--output-dir",
                        str(output_file),
                    ]
                )

        self.assertEqual(exit_code, 1)
        self.assertIn(
            "DriveSense error: Could not create plot output directory",
            stderr.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()
