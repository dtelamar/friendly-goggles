"""Trip-level automotive telemetry analysis."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class TripSummary:
    """Engineering summary values calculated for a single trip."""

    drive_time_s: float
    average_rpm: float
    maximum_rpm: float
    average_speed_kph: float
    maximum_speed_kph: float
    average_coolant_temperature_c: float
    maximum_coolant_temperature_c: float
    average_intake_air_temperature_c: float


def summarize_trip(telemetry: pd.DataFrame) -> TripSummary:
    """Calculate trip and engine summary statistics."""
    raise NotImplementedError("Trip analysis is not implemented yet.")
