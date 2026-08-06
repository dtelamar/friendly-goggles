"""Plot generation for DriveSense telemetry reports."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def generate_trip_plots(
    telemetry: pd.DataFrame,
    output_directory: str | Path,
) -> list[Path]:
    """Generate the MVP telemetry plots and return their output paths."""
    raise NotImplementedError("Plot generation is not implemented yet.")
