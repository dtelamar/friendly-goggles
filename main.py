"""Command-line entry point for DriveSense."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

from analyzer import TelemetryAnalysisError, TripSummary, summarize_trip
from data_loader import TelemetryValidationError, load_telemetry
from graphs import PlotGenerationError, generate_trip_plots
from metrics import DrivingMetrics, MetricsCalculationError, calculate_driving_metrics


def build_parser() -> argparse.ArgumentParser:
    """Build the DriveSense command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Analyze an automotive telemetry CSV log."
    )
    parser.add_argument(
        "telemetry_csv",
        type=Path,
        help="Path to a telemetry CSV file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory for generated plots (default: output).",
    )
    return parser


def _format_duration(seconds: float) -> str:
    """Format an elapsed duration as a compact, human-readable value."""
    total_seconds = max(0, round(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, remaining_seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {remaining_seconds:02d}s"
    return f"{minutes}m {remaining_seconds:02d}s"


def format_trip_report(
    *,
    source_path: Path,
    summary: TripSummary,
    metrics: DrivingMetrics,
    plot_paths: Sequence[Path],
) -> str:
    """Build the deterministic command-line report for one analyzed trip."""
    plot_lines = "\n".join(f"- {path}" for path in plot_paths)
    return "\n".join(
        (
            "DriveSense Trip Report",
            "======================",
            f"Source: {source_path}",
            "",
            "Trip Summary",
            "------------",
            f"Drive time: {_format_duration(summary.drive_time_s)}",
            f"Average RPM: {summary.average_rpm:,.1f}",
            f"Minimum RPM: {summary.minimum_rpm:,.0f}",
            f"Maximum RPM: {summary.maximum_rpm:,.0f}",
            f"Average speed: {summary.average_speed_kph:.1f} km/h",
            f"Maximum speed: {summary.maximum_speed_kph:.1f} km/h",
            (
                "Average throttle: "
                f"{summary.average_throttle_position_pct:.1f}%"
            ),
            (
                "Average coolant: "
                f"{summary.average_coolant_temperature_c:.1f} °C"
            ),
            f"Peak coolant: {summary.maximum_coolant_temperature_c:.1f} °C",
            (
                "Average intake air: "
                f"{summary.average_intake_air_temperature_c:.1f} °C"
            ),
            "",
            "Driving Behavior",
            "----------------",
            f"Idle time: {_format_duration(metrics.idle_time_s)}",
            (
                "Aggressive acceleration events: "
                f"{metrics.aggressive_acceleration_events}"
            ),
            f"Hard braking events: {metrics.hard_braking_events}",
            (
                "High coolant events: "
                f"{metrics.high_coolant_temperature_events}"
            ),
            f"Driver score: {metrics.driver_score}/100",
            f"Classification: {metrics.classification}",
            "",
            "Generated Plots",
            "---------------",
            plot_lines,
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the DriveSense command-line application."""
    parser = build_parser()
    arguments = parser.parse_args(argv)

    try:
        telemetry = load_telemetry(arguments.telemetry_csv)
        summary = summarize_trip(telemetry)
        metrics = calculate_driving_metrics(telemetry)
        plot_paths = generate_trip_plots(telemetry, arguments.output_dir)
    except (
        OSError,
        TelemetryValidationError,
        TelemetryAnalysisError,
        MetricsCalculationError,
        PlotGenerationError,
    ) as exc:
        print(f"DriveSense error: {exc}", file=sys.stderr)
        return 1

    print(
        format_trip_report(
            source_path=arguments.telemetry_csv,
            summary=summary,
            metrics=metrics,
            plot_paths=plot_paths,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
