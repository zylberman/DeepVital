"""Aggregate-only calibration reporting for Phase 3 OOF predictions."""

from __future__ import annotations

import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from deepvital.evaluation.calibration import (
    calibration_curve,
    calibration_intercept_slope,
)


def summarize_calibration(
    labels: Sequence[int],
    raw_probabilities: Sequence[float],
    calibrated_probabilities: Sequence[float],
    *,
    bins: int = 10,
) -> dict[str, Any]:
    """Summarize raw and Platt-calibrated OOF probabilities without identifiers."""
    if bins < 2:
        raise ValueError("At least two calibration bins are required")

    if not (
        len(labels)
        == len(raw_probabilities)
        == len(calibrated_probabilities)
    ):
        raise ValueError("Labels and probability vectors must have equal length")

    if not labels:
        raise ValueError("Calibration reporting requires at least one prediction")

    normalized_labels = [int(value) for value in labels]
    if set(normalized_labels) != {0, 1}:
        raise ValueError("Calibration reporting requires both binary outcome classes")

    variants: dict[str, dict[str, Any]] = {}

    for name, probabilities in (
        ("before_platt", raw_probabilities),
        ("after_platt", calibrated_probabilities),
    ):
        values = [float(value) for value in probabilities]

        if any(
            not math.isfinite(value) or not 0.0 <= value <= 1.0
            for value in values
        ):
            raise ValueError("All predicted probabilities must be finite and in [0, 1]")

        points = []
        for point in calibration_curve(
            normalized_labels,
            values,
            bins=bins,
        ):
            bin_index = int(point["bin"])
            points.append(
                {
                    "bin": bin_index,
                    "lower_bound": bin_index / bins,
                    "upper_bound": (bin_index + 1) / bins,
                    "count": int(point["count"]),
                    "mean_predicted": float(point["mean_predicted"]),
                    "observed_proportion": float(point["observed"]),
                }
            )

        if sum(point["count"] for point in points) != len(normalized_labels):
            raise AssertionError("Calibration-bin counts do not include every window")

        intercept, slope = calibration_intercept_slope(
            normalized_labels,
            values,
        )

        variants[name] = {
            "calibration_intercept": float(intercept),
            "calibration_slope": float(slope),
            "points": points,
        }

    return {
        "analysis_role": (
            "reviewer-requested post-hoc calibration reporting"
        ),
        "validation_description": (
            "patient-grouped nested cross-validation internal validation"
        ),
        "binning": {
            "method": "ten fixed-width probability intervals",
            "number_of_bins": bins,
            "interval_rule": (
                "[lower, upper), except the final interval includes 1.0"
            ),
        },
        "number_of_windows": len(normalized_labels),
        "number_of_positive_windows": sum(normalized_labels),
        "variants": variants,
    }
def render_calibration_svg(
    report: dict[str, Any],
    output_path: Path,
) -> None:
    """Render calibration curves and window counts as an SVG figure."""
    width = 1000
    height = 940
    left = 110
    top = 120
    plot_size = 620
    histogram_top = 790
    histogram_height = 90

    variants = report["variants"]
    required = {"before_platt", "after_platt"}
    if set(variants) != required:
        raise ValueError("Calibration report must contain both variants.")

    number_of_bins = int(report["binning"]["number_of_bins"])
    if number_of_bins < 2:
        raise ValueError("At least two calibration bins are required.")

    colors = {
        "before_platt": "#D55E00",
        "after_platt": "#0072B2",
    }
    labels = {
        "before_platt": "Candidate before Platt",
        "after_platt": "Candidate after Platt",
    }

    def x_position(value: float) -> float:
        return left + plot_size * value

    def y_position(value: float) -> float:
        return top + plot_size * (1.0 - value)

    parts = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">'
        ),
        '<rect width="100%" height="100%" fill="white"/>',
        (
            '<text x="500" y="42" text-anchor="middle" '
            'font-family="Arial" font-size="24" font-weight="bold">'
            "Post-hoc calibration of outer-fold predictions"
            "</text>"
        ),
        (
            '<text x="500" y="72" text-anchor="middle" '
            'font-family="Arial" font-size="15">'
            f'{report["number_of_windows"]} prediction windows; '
            f'{report["number_of_positive_windows"]} positive windows'
            "</text>"
        ),
    ]

    for tick in range(6):
        value = tick / 5
        x = x_position(value)
        y = y_position(value)

        parts.append(
            f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" '
            f'y2="{top + plot_size}" stroke="#DDDDDD"/>'
        )
        parts.append(
            f'<line x1="{left}" y1="{y:.1f}" '
            f'x2="{left + plot_size}" y2="{y:.1f}" '
            'stroke="#DDDDDD"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{top + plot_size + 25}" '
            'text-anchor="middle" font-family="Arial" font-size="12">'
            f"{value:.1f}</text>"
        )
        parts.append(
            f'<text x="{left - 18}" y="{y + 4:.1f}" '
            'text-anchor="end" font-family="Arial" font-size="12">'
            f"{value:.1f}</text>"
        )

    parts.extend(
        [
            (
                f'<line x1="{left}" y1="{top + plot_size}" '
                f'x2="{left + plot_size}" y2="{top}" '
                'stroke="#555555" stroke-width="2" '
                'stroke-dasharray="7,7"/>'
            ),
            (
                f'<text x="{left + plot_size / 2}" '
                f'y="{top + plot_size + 58}" text-anchor="middle" '
                'font-family="Arial" font-size="15">'
                "Mean predicted probability"
                "</text>"
            ),
            (
                f'<text x="30" y="{top + plot_size / 2}" '
                'text-anchor="middle" font-family="Arial" font-size="15" '
                f'transform="rotate(-90 30 {top + plot_size / 2})">'
                "Observed proportion"
                "</text>"
            ),
        ]
    )

    for variant_name in ("before_platt", "after_platt"):
        points = variants[variant_name]["points"]
        coordinates = " ".join(
            (
                f'{x_position(float(point["mean_predicted"])):.1f},'
                f'{y_position(float(point["observed_proportion"])):.1f}'
            )
            for point in points
        )

        if coordinates:
            parts.append(
                f'<polyline points="{coordinates}" fill="none" '
                f'stroke="{colors[variant_name]}" stroke-width="3"/>'
            )

        for point in points:
            x = x_position(float(point["mean_predicted"]))
            y = y_position(float(point["observed_proportion"]))
            parts.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" '
                f'fill="{colors[variant_name]}"/>'
            )

    legend_x = 765
    legend_y = 150
    parts.extend(
        [
            (
                f'<line x1="{legend_x}" y1="{legend_y}" '
                f'x2="{legend_x + 38}" y2="{legend_y}" '
                'stroke="#555555" stroke-width="2" '
                'stroke-dasharray="7,7"/>'
            ),
            (
                f'<text x="{legend_x + 48}" y="{legend_y + 5}" '
                'font-family="Arial" font-size="13">'
                "Perfect calibration"
                "</text>"
            ),
        ]
    )

    for index, variant_name in enumerate(("before_platt", "after_platt"), 1):
        y = legend_y + 34 * index
        parts.extend(
            [
                (
                    f'<line x1="{legend_x}" y1="{y}" '
                    f'x2="{legend_x + 38}" y2="{y}" '
                    f'stroke="{colors[variant_name]}" stroke-width="3"/>'
                ),
                (
                    f'<circle cx="{legend_x + 19}" cy="{y}" r="4" '
                    f'fill="{colors[variant_name]}"/>'
                ),
                (
                    f'<text x="{legend_x + 48}" y="{y + 5}" '
                    'font-family="Arial" font-size="13">'
                    f"{labels[variant_name]}</text>"
                ),
            ]
        )

    all_counts = [
        int(point["count"])
        for variant in variants.values()
        for point in variant["points"]
    ]
    maximum_count = max(all_counts, default=1)
    
    for fraction in (0.0, 0.5, 1.0):
        tick_count = round(maximum_count * fraction)
        tick_y = (
            histogram_top
            + histogram_height * (1.0 - fraction)
        )

        parts.append(
            f'<line x1="{left - 5}" y1="{tick_y:.1f}" '
            f'x2="{left + plot_size}" y2="{tick_y:.1f}" '
            'stroke="#E6E6E6" stroke-width="1"/>'
        )
        parts.append(
            f'<text class="histogram-y-tick" '
            f'x="{left - 10}" y="{tick_y + 4:.1f}" '
            'text-anchor="end" font-family="Arial" '
            f'font-size="10">{tick_count:,}</text>'
        )

    slot_width = plot_size / number_of_bins
    bar_width = slot_width * 0.32

    parts.append(
        f'<line x1="{left}" y1="{histogram_top + histogram_height}" '
        f'x2="{left + plot_size}" '
        f'y2="{histogram_top + histogram_height}" '
        'stroke="#333333" stroke-width="1.5"/>'
    )
    parts.append(
        f'<text x="30" y="{histogram_top + histogram_height / 2}" '
        'text-anchor="middle" font-family="Arial" font-size="14" '
        f'transform="rotate(-90 30 '
        f'{histogram_top + histogram_height / 2})">'
        "Window count"
        "</text>"
    )
    parts.append(
        f'<text x="{left}" y="{histogram_top - 14}" '
        'font-family="Arial" font-size="15" font-weight="bold">'
        "Windows per probability interval"
        "</text>"
    )
    
    count_by_variant = {
        name: {
            int(point["bin"]): int(point["count"])
            for point in variants[name]["points"]
        }
        for name in required
    }

    for bin_number in range(number_of_bins):
        center = left + slot_width * (bin_number + 0.5)

        for offset, variant_name in enumerate(
            ("before_platt", "after_platt")
        ):
            count = count_by_variant[variant_name].get(bin_number, 0)
            bar_height = histogram_height * count / maximum_count
            x = center - bar_width + offset * bar_width
            y = histogram_top + histogram_height - bar_height

            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" '
                f'width="{bar_width:.1f}" height="{bar_height:.1f}" '
                f'fill="{colors[variant_name]}" opacity="0.82"/>'
            )
            label_y = max(y - 4, histogram_top + 9)
            parts.append(
                f'<text class="histogram-count" '
                f'x="{x + bar_width / 2:.1f}" '
                f'y="{label_y:.1f}" '
                'text-anchor="middle" font-family="Arial" '
                f'font-size="8">{count:,}</text>'
            )

        lower = bin_number / number_of_bins
        parts.append(
            f'<text x="{center:.1f}" '
            f'y="{histogram_top + histogram_height + 20}" '
            'text-anchor="middle" font-family="Arial" font-size="10">'
            f"{lower:.1f}</text>"
        )

    parts.extend(
        [
            (
                '<text x="500" y="925" text-anchor="middle" '
                'font-family="Arial" font-size="12" fill="#555555">'
                "Fixed-width probability intervals; aggregate internal "
                "out-of-fold results."
                "</text>"
            ),
            "</svg>",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(parts), encoding="utf-8")
