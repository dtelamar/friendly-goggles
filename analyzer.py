"""Trip-level automotive telemetry analysis."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


SUMMARY_COLUMNS: tuple[str, ...] = (
    "timestamp_s",
    "engine_rpm",
    "vehicle_speed_kph",
    "throttle_position_pct",
    "coolant_temperature_c",
    "intake_air_temperature_c",
)


class TelemetryAnalysisError(ValueError):
    """Raised when a trip cannot be summarized from the supplied telemetry."""


@dataclass(frozen=True)
class TripSummary:
    """Engineering summary values calculated for a single trip."""

    drive_time_s: float
    average_rpm: float
    minimum_rpm: float
    maximum_rpm: float
    average_speed_kph: float
    maximum_speed_kph: float
    average_throttle_position_pct: float
    average_coolant_temperature_c: float
    maximum_coolant_temperature_c: float
    average_intake_air_temperature_c: float


def summarize_trip(telemetry: pd.DataFrame) -> TripSummary:
    """Calculate trip and engine summary statistics.

    ``telemetry`` is expected to follow the normalized DataFrame contract
    produced by :func:`data_loader.load_telemetry`. The timestamp range is used
    for duration, making the calculation independent of sample frequency.

    Raises:
        TelemetryAnalysisError: If the DataFrame is empty or does not contain
            every signal required for the summary.
    """
    missing_columns = [
        column for column in SUMMARY_COLUMNS if column not in telemetry.columns
    ]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise TelemetryAnalysisError(
            f"Cannot summarize telemetry; missing columns: {missing}."
        )
    if telemetry.empty:
        raise TelemetryAnalysisError("Cannot summarize an empty telemetry trip.")

    timestamps = telemetry["timestamp_s"]
    engine_rpm = telemetry["engine_rpm"]
    vehicle_speed = telemetry["vehicle_speed_kph"]
    throttle_position = telemetry["throttle_position_pct"]
    coolant_temperature = telemetry["coolant_temperature_c"]
    intake_air_temperature = telemetry["intake_air_temperature_c"]

    return TripSummary(
        drive_time_s=float(timestamps.max() - timestamps.min()),
        average_rpm=float(engine_rpm.mean()),
        minimum_rpm=float(engine_rpm.min()),
        maximum_rpm=float(engine_rpm.max()),
        average_speed_kph=float(vehicle_speed.mean()),
        maximum_speed_kph=float(vehicle_speed.max()),
        average_throttle_position_pct=float(throttle_position.mean()),
        average_coolant_temperature_c=float(coolant_temperature.mean()),
        maximum_coolant_temperature_c=float(coolant_temperature.max()),
        average_intake_air_temperature_c=float(intake_air_temperature.mean()),
    )
