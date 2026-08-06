"""Load CSV telemetry into DriveSense's canonical tabular schema."""

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

SIGNAL_RANGES: dict[str, tuple[float | None, float | None]] = {
    "timestamp_s": (0.0, None),
    "engine_rpm": (0.0, 20_000.0),
    "vehicle_speed_kph": (0.0, 500.0),
    "throttle_position_pct": (0.0, 100.0),
    "coolant_temperature_c": (-40.0, 215.0),
    "intake_air_temperature_c": (-40.0, 215.0),
    "engine_load_pct": (0.0, 100.0),
}


class TelemetryValidationError(ValueError):
    """Raised when telemetry does not satisfy the DriveSense schema."""


def _csv_row_numbers(mask: pd.Series) -> str:
    """Return a concise list of one-based CSV row numbers selected by ``mask``."""
    row_numbers = [
        position + 2
        for position, is_invalid in enumerate(mask.to_numpy())
        if bool(is_invalid)
    ]
    displayed = ", ".join(str(row) for row in row_numbers[:5])
    if len(row_numbers) > 5:
        displayed += ", ..."
    return displayed


def _validate_ranges(telemetry: pd.DataFrame) -> None:
    """Reject values outside broad automotive and OBD-II signal limits."""
    for column, (minimum, maximum) in SIGNAL_RANGES.items():
        invalid = pd.Series(False, index=telemetry.index)
        if minimum is not None:
            invalid |= telemetry[column] < minimum
        if maximum is not None:
            invalid |= telemetry[column] > maximum

        if invalid.any():
            if maximum is None:
                expected = f">= {minimum:g}"
            elif minimum is None:
                expected = f"<= {maximum:g}"
            else:
                expected = f"between {minimum:g} and {maximum:g}"
            rows = _csv_row_numbers(invalid)
            raise TelemetryValidationError(
                f"Column '{column}' must be {expected}; invalid CSV rows: {rows}."
            )


def load_telemetry(csv_path: str | Path) -> pd.DataFrame:
    """Load and validate a telemetry CSV file.

    Returns a timestamp-sorted DataFrame containing only the canonical columns
    in ``REQUIRED_COLUMNS``. All returned columns use the ``float64`` dtype so
    downstream analysis receives a stable interface regardless of how values
    were represented in the source file.

    Raises:
        FileNotFoundError: If ``csv_path`` does not exist.
        TelemetryValidationError: If the CSV cannot be parsed or violates the
            canonical telemetry schema.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Telemetry CSV not found: {path}")
    if not path.is_file():
        raise TelemetryValidationError(f"Telemetry path is not a file: {path}")

    try:
        telemetry = pd.read_csv(path)
    except pd.errors.EmptyDataError as exc:
        raise TelemetryValidationError(
            "Telemetry CSV is empty or does not contain a header row."
        ) from exc
    except (pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise TelemetryValidationError(
            f"Telemetry CSV could not be parsed: {exc}"
        ) from exc

    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in telemetry.columns
    ]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise TelemetryValidationError(f"Missing required columns: {missing}.")
    if telemetry.empty:
        raise TelemetryValidationError("Telemetry CSV does not contain any data rows.")

    normalized = telemetry.loc[:, list(REQUIRED_COLUMNS)].copy()
    for column in REQUIRED_COLUMNS:
        numeric_values = pd.to_numeric(normalized[column], errors="coerce")
        invalid = numeric_values.isna() | numeric_values.isin(
            [float("inf"), float("-inf")]
        )
        if invalid.any():
            rows = _csv_row_numbers(invalid)
            raise TelemetryValidationError(
                f"Column '{column}' contains missing, non-numeric, or non-finite "
                f"values at CSV rows: {rows}."
            )
        normalized[column] = numeric_values.astype("float64")

    _validate_ranges(normalized)

    duplicate_timestamps = normalized["timestamp_s"].duplicated(keep=False)
    if duplicate_timestamps.any():
        rows = _csv_row_numbers(duplicate_timestamps)
        raise TelemetryValidationError(
            f"Column 'timestamp_s' contains duplicate values at CSV rows: {rows}."
        )

    return normalized.sort_values(
        "timestamp_s",
        kind="stable",
        ignore_index=True,
    )
