"""Driving-event detection and explainable scoring."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DrivingMetrics:
    """Behavioral metrics calculated for a single trip."""

    idle_time_s: float
    aggressive_acceleration_events: int
    hard_braking_events: int
    high_coolant_temperature_events: int
    driver_score: int
    classification: str


def calculate_driving_metrics(telemetry: pd.DataFrame) -> DrivingMetrics:
    """Detect driving events and calculate an explainable driver score."""
    raise NotImplementedError("Driving metrics are not implemented yet.")
