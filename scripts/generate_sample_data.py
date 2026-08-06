#!/usr/bin/env python3
"""Generate a deterministic, realistic DriveSense telemetry sample.

The generated drive is synthetic and contains deliberate operating scenarios
for exercising the MVP analyzer: idle periods, normal acceleration, highway
cruising, one aggressive acceleration, two hard-braking events, and a short
high-coolant-temperature interval.
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from pathlib import Path
from typing import Sequence


COLUMNS: tuple[str, ...] = (
    "timestamp_s",
    "engine_rpm",
    "vehicle_speed_kph",
    "throttle_position_pct",
    "coolant_temperature_c",
    "intake_air_temperature_c",
    "engine_load_pct",
)

SPEED_KEYFRAMES: tuple[tuple[int, float], ...] = (
    (0, 0.0),
    (20, 0.0),
    (35, 32.0),
    (55, 48.0),
    (70, 48.0),
    (78, 0.0),
    (92, 0.0),
    (115, 52.0),
    (124, 68.0),
    (129, 0.0),
    (142, 0.0),
    (165, 65.0),
    (205, 100.0),
    (290, 105.0),
    (320, 90.0),
    (345, 45.0),
    (355, 0.0),
    (372, 0.0),
    (405, 58.0),
    (426, 68.0),
    (430, 70.0),
    (438, 112.0),
    (460, 103.0),
    (485, 90.0),
    (505, 55.0),
    (512, 50.0),
    (516, 0.0),
    (532, 0.0),
    (555, 38.0),
    (575, 50.0),
    (590, 22.0),
    (600, 0.0),
)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def _interpolate_speed(timestamp_s: int) -> float:
    """Linearly interpolate the target speed at ``timestamp_s``."""
    for (start_t, start_speed), (end_t, end_speed) in zip(
        SPEED_KEYFRAMES,
        SPEED_KEYFRAMES[1:],
    ):
        if start_t <= timestamp_s <= end_t:
            span = end_t - start_t
            progress = 0.0 if span == 0 else (timestamp_s - start_t) / span
            return start_speed + ((end_speed - start_speed) * progress)
    return SPEED_KEYFRAMES[-1][1]


def _estimate_rpm(
    speed_kph: float,
    throttle_pct: float,
    timestamp_s: int,
    rng: random.Random,
) -> int:
    """Estimate plausible engine speed using simple virtual gear bands."""
    if speed_kph < 0.5:
        return round(_clamp(790.0 + rng.gauss(0.0, 18.0), 730.0, 860.0))

    if speed_kph < 18.0:
        rpm = 780.0 + (speed_kph * 115.0)
    elif speed_kph < 38.0:
        rpm = 720.0 + (speed_kph * 72.0)
    elif speed_kph < 65.0:
        rpm = 760.0 + (speed_kph * 50.0)
    elif speed_kph < 95.0:
        rpm = 820.0 + (speed_kph * 35.0)
    else:
        rpm = 850.0 + (speed_kph * 25.0)

    rpm += throttle_pct * 7.0
    rpm += rng.gauss(0.0, 45.0)

    if 430 <= timestamp_s <= 438:
        rpm = max(rpm, 4550.0 + ((timestamp_s - 430) * 155.0))

    return round(_clamp(rpm, 750.0, 6200.0))


def generate_rows(seed: int = 20260806) -> list[dict[str, int | float]]:
    """Return the canonical 601-row DriveSense sample trip."""
    rng = random.Random(seed)
    rows: list[dict[str, int | float]] = []
    previous_speed = 0.0
    speed_noise = 0.0

    for timestamp_s in range(601):
        target_speed = _interpolate_speed(timestamp_s)
        speed_noise = (speed_noise * 0.72) + rng.gauss(0.0, 0.34)
        speed_kph = 0.0 if target_speed < 0.5 else target_speed + speed_noise
        speed_kph = _clamp(speed_kph, 0.0, 130.0)
        acceleration_kph_s = speed_kph - previous_speed

        if speed_kph < 0.5:
            throttle_pct = 1.8 + rng.gauss(0.0, 0.35)
        elif acceleration_kph_s > 0.35:
            throttle_pct = (
                16.0
                + (acceleration_kph_s * 11.0)
                + (speed_kph * 0.055)
                + rng.gauss(0.0, 1.5)
            )
        elif acceleration_kph_s < -0.5:
            throttle_pct = 2.5 + rng.gauss(0.0, 0.65)
        else:
            throttle_pct = 10.0 + (speed_kph * 0.10) + rng.gauss(0.0, 1.4)

        if 430 <= timestamp_s <= 438:
            throttle_pct = 86.0 + ((timestamp_s - 430) * 0.9) + rng.gauss(0.0, 0.8)

        throttle_pct = _clamp(throttle_pct, 0.0, 100.0)
        engine_rpm = _estimate_rpm(
            speed_kph,
            throttle_pct,
            timestamp_s,
            rng,
        )

        engine_load_pct = (
            11.0
            + (throttle_pct * 0.72)
            + (max(acceleration_kph_s, 0.0) * 3.5)
            + rng.gauss(0.0, 1.4)
        )
        engine_load_pct = _clamp(engine_load_pct, 8.0, 98.0)

        warmup_temperature = 72.0 + (22.0 * (1.0 - math.exp(-timestamp_s / 115.0)))
        load_heat = max(engine_load_pct - 62.0, 0.0) * 0.035
        heat_soak = 11.8 * math.exp(-((timestamp_s - 468.0) / 31.0) ** 2)
        coolant_temperature_c = (
            warmup_temperature + load_heat + heat_soak + rng.gauss(0.0, 0.12)
        )

        intake_air_temperature_c = (
            27.0
            + (5.5 * math.exp(-timestamp_s / 100.0))
            + ((1.0 - min(speed_kph / 110.0, 1.0)) * 2.1)
            + (1.2 if speed_kph < 0.5 else 0.0)
            + rng.gauss(0.0, 0.18)
        )

        rows.append(
            {
                "timestamp_s": timestamp_s,
                "engine_rpm": engine_rpm,
                "vehicle_speed_kph": round(speed_kph, 1),
                "throttle_position_pct": round(throttle_pct, 1),
                "coolant_temperature_c": round(coolant_temperature_c, 1),
                "intake_air_temperature_c": round(intake_air_temperature_c, 1),
                "engine_load_pct": round(engine_load_pct, 1),
            }
        )
        previous_speed = speed_kph

    return rows


def write_csv(output_path: Path, seed: int) -> None:
    """Write the generated telemetry rows to ``output_path``."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=COLUMNS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(generate_rows(seed))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("sample_data/drive_log.csv"),
        help="Output CSV path (default: sample_data/drive_log.csv).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260806,
        help="Deterministic random seed (default: 20260806).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    write_csv(args.output, args.seed)
    print(f"Generated 601 telemetry rows at {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
