"""Plot generation for DriveSense telemetry reports."""

from __future__ import annotations

from pathlib import Path
from typing import Final

import matplotlib
import pandas as pd

matplotlib.use("Agg")

from matplotlib import pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.ticker import StrMethodFormatter  # noqa: E402


PLOT_COLUMNS: tuple[str, ...] = (
    "timestamp_s",
    "engine_rpm",
    "vehicle_speed_kph",
    "throttle_position_pct",
    "coolant_temperature_c",
)

PLOT_FILENAMES: tuple[str, ...] = (
    "rpm_vs_time.png",
    "speed_vs_time.png",
    "throttle_vs_time.png",
    "coolant_vs_time.png",
    "throttle_vs_rpm.png",
)

FIGURE_SIZE: Final[tuple[float, float]] = (10.0, 5.2)
PLOT_DPI: Final[int] = 150
HIGH_COOLANT_THRESHOLD_C: Final[float] = 105.0
PRIMARY_COLOR: Final[str] = "#2457A6"
THROTTLE_COLOR: Final[str] = "#7A4EAB"
COOLANT_COLOR: Final[str] = "#D26A35"


class PlotGenerationError(ValueError):
    """Raised when telemetry plots cannot be generated."""


def _style_axes(ax: Axes) -> None:
    """Apply the shared, restrained DriveSense plot styling."""
    ax.grid(True, color="#D7DEE8", linewidth=0.8, alpha=0.65)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(colors="#344054")
    ax.title.set_color("#172B4D")
    ax.xaxis.label.set_color("#344054")
    ax.yaxis.label.set_color("#344054")


def _save_figure(fig: Figure, output_path: Path) -> None:
    """Save and close one figure, translating filesystem failures."""
    try:
        fig.savefig(
            output_path,
            dpi=PLOT_DPI,
            facecolor="white",
        )
    except OSError as exc:
        raise PlotGenerationError(f"Could not save plot: {output_path}") from exc
    finally:
        plt.close(fig)


def _save_time_series_plot(
    *,
    elapsed_minutes: pd.Series,
    values: pd.Series,
    title: str,
    y_label: str,
    color: str,
    output_path: Path,
    threshold: float | None = None,
    threshold_label: str | None = None,
) -> None:
    """Create and save one telemetry time-series plot."""
    with plt.style.context("seaborn-v0_8-whitegrid"):
        fig, ax = plt.subplots(figsize=FIGURE_SIZE)
        ax.plot(
            elapsed_minutes,
            values,
            color=color,
            linewidth=1.8,
        )
        if threshold is not None:
            ax.axhline(
                threshold,
                color="#B42318",
                linestyle="--",
                linewidth=1.4,
                label=threshold_label,
            )
            ax.legend(frameon=False, loc="best")
        ax.set_title(title, fontsize=15, fontweight="semibold", pad=12)
        ax.set_xlabel("Elapsed time (min)")
        ax.set_ylabel(y_label)
        ax.margins(x=0.01)
        _style_axes(ax)
        fig.tight_layout()
        _save_figure(fig, output_path)


def _save_throttle_rpm_plot(
    telemetry: pd.DataFrame,
    output_path: Path,
) -> None:
    """Create a throttle-versus-RPM scatter colored by vehicle speed."""
    with plt.style.context("seaborn-v0_8-whitegrid"):
        fig, ax = plt.subplots(figsize=FIGURE_SIZE)
        scatter = ax.scatter(
            telemetry["engine_rpm"],
            telemetry["throttle_position_pct"],
            c=telemetry["vehicle_speed_kph"],
            cmap="viridis",
            s=26,
            alpha=0.72,
            linewidths=0,
        )
        colorbar = fig.colorbar(scatter, ax=ax, pad=0.02)
        colorbar.set_label("Vehicle speed (km/h)")
        ax.set_title(
            "Throttle position vs engine speed",
            fontsize=15,
            fontweight="semibold",
            pad=12,
        )
        ax.set_xlabel("Engine speed (RPM)")
        ax.set_ylabel("Throttle position (%)")
        ax.xaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
        _style_axes(ax)
        fig.tight_layout()
        _save_figure(fig, output_path)


def generate_trip_plots(
    telemetry: pd.DataFrame,
    output_directory: str | Path,
) -> list[Path]:
    """Generate the five MVP telemetry plots and return their output paths.

    The function sorts a copy of the input by timestamp, creates the output
    directory when necessary, and overwrites existing plots with the same
    deterministic filenames.

    Raises:
        PlotGenerationError: If required columns or rows are missing, the
            output directory cannot be created, or a plot cannot be saved.
    """
    missing_columns = [
        column for column in PLOT_COLUMNS if column not in telemetry.columns
    ]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise PlotGenerationError(
            f"Cannot generate telemetry plots; missing columns: {missing}."
        )
    if telemetry.empty:
        raise PlotGenerationError("Cannot generate plots for an empty trip.")

    output_path = Path(output_directory)
    try:
        output_path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise PlotGenerationError(
            f"Could not create plot output directory: {output_path}"
        ) from exc

    ordered = telemetry.sort_values("timestamp_s", kind="stable").reset_index(
        drop=True
    )
    elapsed_minutes = (
        ordered["timestamp_s"] - ordered["timestamp_s"].min()
    ) / 60.0
    output_paths = [output_path / filename for filename in PLOT_FILENAMES]

    _save_time_series_plot(
        elapsed_minutes=elapsed_minutes,
        values=ordered["engine_rpm"],
        title="Engine speed over time",
        y_label="Engine speed (RPM)",
        color=PRIMARY_COLOR,
        output_path=output_paths[0],
    )
    _save_time_series_plot(
        elapsed_minutes=elapsed_minutes,
        values=ordered["vehicle_speed_kph"],
        title="Vehicle speed over time",
        y_label="Vehicle speed (km/h)",
        color=PRIMARY_COLOR,
        output_path=output_paths[1],
    )
    _save_time_series_plot(
        elapsed_minutes=elapsed_minutes,
        values=ordered["throttle_position_pct"],
        title="Throttle position over time",
        y_label="Throttle position (%)",
        color=THROTTLE_COLOR,
        output_path=output_paths[2],
    )
    _save_time_series_plot(
        elapsed_minutes=elapsed_minutes,
        values=ordered["coolant_temperature_c"],
        title="Coolant temperature over time",
        y_label="Coolant temperature (°C)",
        color=COOLANT_COLOR,
        output_path=output_paths[3],
        threshold=HIGH_COOLANT_THRESHOLD_C,
        threshold_label="High coolant threshold (105 °C)",
    )
    _save_throttle_rpm_plot(ordered, output_paths[4])

    return output_paths
