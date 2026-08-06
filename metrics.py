"""Driving-event detection and explainable scoring."""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd


METRIC_COLUMNS: tuple[str, ...] = (
    "timestamp_s",
    "engine_rpm",
    "vehicle_speed_kph",
    "throttle_position_pct",
    "coolant_temperature_c",
)

IDLE_SPEED_MAX_KPH = 0.5
IDLE_RPM_MIN = 600.0
IDLE_RPM_MAX = 900.0
AGGRESSIVE_THROTTLE_THRESHOLD_PCT = 80.0
AGGRESSIVE_RPM_THRESHOLD = 4500.0
HARD_BRAKING_THRESHOLD_MPS2 = -3.0
HIGH_COOLANT_THRESHOLD_C = 105.0

AGGRESSIVE_ACCELERATION_PENALTY = 8
HARD_BRAKING_PENALTY = 10
HIGH_COOLANT_PENALTY = 5
IDLE_ALLOWANCE_RATIO = 0.15
IDLE_PENALTY_INTERVAL_S = 30.0
IDLE_PENALTY_PER_INTERVAL = 2


class MetricsCalculationError(ValueError):
    """Raised when driving metrics cannot be calculated from telemetry."""


@dataclass(frozen=True)
class DrivingMetrics:
    """Behavioral metrics calculated for a single trip."""

    idle_time_s: float
    aggressive_acceleration_events: int
    hard_braking_events: int
    high_coolant_temperature_events: int
    driver_score: int
    classification: str


def _count_event_groups(flags: pd.Series) -> int:
    """Count contiguous true regions as distinct events."""
    event_starts = flags & ~flags.shift(fill_value=False)
    return int(event_starts.sum())


def _calculate_driver_score(
    *,
    drive_time_s: float,
    idle_time_s: float,
    aggressive_acceleration_events: int,
    hard_braking_events: int,
    high_coolant_temperature_events: int,
) -> int:
    """Calculate a clamped, explainable 0-100 driver score."""
    idle_allowance_s = drive_time_s * IDLE_ALLOWANCE_RATIO
    excessive_idle_s = max(idle_time_s - idle_allowance_s, 0.0)
    idle_penalty_intervals = math.ceil(
        excessive_idle_s / IDLE_PENALTY_INTERVAL_S
    )

    penalties = (
        aggressive_acceleration_events * AGGRESSIVE_ACCELERATION_PENALTY
        + hard_braking_events * HARD_BRAKING_PENALTY
        + high_coolant_temperature_events * HIGH_COOLANT_PENALTY
        + idle_penalty_intervals * IDLE_PENALTY_PER_INTERVAL
    )
    return max(0, min(100, 100 - penalties))


def _classify_driver(
    *,
    score: int,
    idle_ratio: float,
    average_throttle_pct: float,
    aggressive_acceleration_events: int,
    hard_braking_events: int,
) -> str:
    """Classify behavior using score, severe events, idle, and throttle."""
    severe_events = aggressive_acceleration_events + hard_braking_events
    if score < 75 or severe_events >= 3:
        return "Aggressive Driver"
    if (
        score >= 90
        and aggressive_acceleration_events == 0
        and hard_braking_events == 0
        and idle_ratio <= IDLE_ALLOWANCE_RATIO
        and average_throttle_pct <= 25.0
    ):
        return "Economical Driver"
    return "Smooth Driver"


def calculate_driving_metrics(telemetry: pd.DataFrame) -> DrivingMetrics:
    """Detect grouped driving events and calculate an explainable score.

    Calculations use elapsed timestamps rather than assuming a fixed sampling
    rate. The input is sorted internally without modifying the caller's
    DataFrame.

    Raises:
        MetricsCalculationError: If required signals are missing, the trip is
            empty, or timestamps are duplicated.
    """
    missing_columns = [
        column for column in METRIC_COLUMNS if column not in telemetry.columns
    ]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise MetricsCalculationError(
            f"Cannot calculate driving metrics; missing columns: {missing}."
        )
    if telemetry.empty:
        raise MetricsCalculationError(
            "Cannot calculate driving metrics for an empty telemetry trip."
        )

    ordered = telemetry.sort_values("timestamp_s", kind="stable").reset_index(
        drop=True
    )
    duplicate_timestamps = ordered["timestamp_s"].duplicated(keep=False)
    if duplicate_timestamps.any():
        raise MetricsCalculationError(
            "Cannot calculate driving metrics with duplicate timestamps."
        )

    timestamps = ordered["timestamp_s"]
    engine_rpm = ordered["engine_rpm"]
    vehicle_speed_kph = ordered["vehicle_speed_kph"]
    throttle_position_pct = ordered["throttle_position_pct"]
    coolant_temperature_c = ordered["coolant_temperature_c"]

    drive_time_s = float(timestamps.max() - timestamps.min())
    sample_intervals_s = (timestamps.shift(-1) - timestamps).fillna(0.0)
    idle_flags = (
        (vehicle_speed_kph <= IDLE_SPEED_MAX_KPH)
        & engine_rpm.between(IDLE_RPM_MIN, IDLE_RPM_MAX, inclusive="both")
    )
    idle_time_s = float(sample_intervals_s.where(idle_flags, 0.0).sum())

    aggressive_acceleration_flags = (
        (throttle_position_pct > AGGRESSIVE_THROTTLE_THRESHOLD_PCT)
        & (engine_rpm > AGGRESSIVE_RPM_THRESHOLD)
    )
    aggressive_acceleration_events = _count_event_groups(
        aggressive_acceleration_flags
    )

    elapsed_s = timestamps.diff()
    speed_change_mps = vehicle_speed_kph.diff() / 3.6
    acceleration_mps2 = speed_change_mps / elapsed_s
    hard_braking_flags = acceleration_mps2 <= HARD_BRAKING_THRESHOLD_MPS2
    hard_braking_events = _count_event_groups(hard_braking_flags)

    high_coolant_flags = coolant_temperature_c >= HIGH_COOLANT_THRESHOLD_C
    high_coolant_temperature_events = _count_event_groups(high_coolant_flags)

    driver_score = _calculate_driver_score(
        drive_time_s=drive_time_s,
        idle_time_s=idle_time_s,
        aggressive_acceleration_events=aggressive_acceleration_events,
        hard_braking_events=hard_braking_events,
        high_coolant_temperature_events=high_coolant_temperature_events,
    )
    idle_ratio = idle_time_s / drive_time_s if drive_time_s > 0.0 else 0.0
    classification = _classify_driver(
        score=driver_score,
        idle_ratio=idle_ratio,
        average_throttle_pct=float(throttle_position_pct.mean()),
        aggressive_acceleration_events=aggressive_acceleration_events,
        hard_braking_events=hard_braking_events,
    )

    return DrivingMetrics(
        idle_time_s=idle_time_s,
        aggressive_acceleration_events=aggressive_acceleration_events,
        hard_braking_events=hard_braking_events,
        high_coolant_temperature_events=high_coolant_temperature_events,
        driver_score=driver_score,
        classification=classification,
    )
