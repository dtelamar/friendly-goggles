"""Command-line entry point for DriveSense."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence


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
        help="Directory for generated plots and reports (default: output).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the DriveSense command-line application."""
    parser = build_parser()
    parser.parse_args(argv)
    parser.error("Telemetry analysis is not implemented yet.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
