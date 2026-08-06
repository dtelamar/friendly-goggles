"""Telemetry data-source loading and validation contracts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS: tuple[str, ...] = (
    "timestamp_s",
    "engine_rpm",
    "vehicle_speed_kph",
    "throttle_position_pct",
    "coolant_temperature_c",
    "intake_air_temperature_c",
    "engine_load_pct",
)


class TelemetryValidationError(ValueError):
    """Raised when telemetry does not satisfy the DriveSense schema."""


def load_telemetry(csv_path: str | Path) -> pd.DataFrame:
    """Load and validate a telemetry CSV file.

    The implementation will return a timestamp-sorted DataFrame containing the
    canonical columns listed in ``REQUIRED_COLUMNS``.
    """
    raise NotImplementedError("CSV telemetry loading is not implemented yet.")
