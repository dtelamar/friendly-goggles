"""Tests for deterministic telemetry plot generation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import pandas as pd

from data_loader import load_telemetry
from graphs import PLOT_FILENAMES, PlotGenerationError, generate_trip_plots


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PATH = REPOSITORY_ROOT / "sample_data" / "drive_log.csv"


class TripGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.telemetry = load_telemetry(SAMPLE_PATH)

    def _temporary_output(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        return temporary_directory, Path(temporary_directory.name) / "plots"

    def test_generates_five_readable_png_files(self) -> None:
        _, output_directory = self._temporary_output()

        output_paths = generate_trip_plots(self.telemetry, output_directory)

        self.assertEqual(
            [path.name for path in output_paths],
            list(PLOT_FILENAMES),
        )
        for path in output_paths:
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file())
                self.assertGreater(path.stat().st_size, 10_000)
                image = mpimg.imread(path)
                self.assertEqual(image.shape[:2], (780, 1500))
                self.assertIn(image.shape[2], (3, 4))

    def test_repeated_generation_overwrites_deterministic_paths(self) -> None:
        _, output_directory = self._temporary_output()
        first_paths = generate_trip_plots(self.telemetry, output_directory)
        first_sizes = [path.stat().st_size for path in first_paths]

        second_paths = generate_trip_plots(self.telemetry, output_directory)

        self.assertEqual(second_paths, first_paths)
        self.assertEqual(
            [path.stat().st_size for path in second_paths],
            first_sizes,
        )

    def test_sorts_without_modifying_input_and_closes_figures(self) -> None:
        _, output_directory = self._temporary_output()
        telemetry = self.telemetry.iloc[::-1].reset_index(drop=True)
        original = telemetry.copy(deep=True)

        generate_trip_plots(telemetry, output_directory)

        pd.testing.assert_frame_equal(telemetry, original)
        self.assertEqual(plt.get_fignums(), [])

    def test_rejects_empty_and_missing_column_inputs(self) -> None:
        _, output_directory = self._temporary_output()
        cases = {
            "empty": self.telemetry.iloc[0:0],
            "missing": self.telemetry.drop(columns="engine_rpm"),
        }

        for label, telemetry in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(PlotGenerationError):
                    generate_trip_plots(telemetry, output_directory)

    def test_rejects_output_directory_that_is_a_file(self) -> None:
        temporary_directory, _ = self._temporary_output()
        output_file = Path(temporary_directory.name) / "plots"
        output_file.write_text("not a directory", encoding="utf-8")

        with self.assertRaisesRegex(
            PlotGenerationError,
            "Could not create plot output directory",
        ):
            generate_trip_plots(self.telemetry, output_file)


if __name__ == "__main__":
    unittest.main()
