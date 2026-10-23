from __future__ import annotations

import json

import pytest

from deepvital.phase3.calibration_reporting import (
    render_calibration_svg,
    summarize_calibration,
)


def synthetic_predictions() -> tuple[list[int], list[float], list[float]]:
    labels = [0, 0, 1, 1, 1, 0]
    before_platt = [0.05, 0.20, 0.35, 0.65, 0.85, 0.95]
    after_platt = [0.10, 0.25, 0.55, 0.70, 0.80, 0.90]
    return labels, before_platt, after_platt


def test_every_window_is_in_exactly_one_bin() -> None:
    labels, raw, calibrated = synthetic_predictions()

    report = summarize_calibration(
        labels,
        raw,
        calibrated,
        bins=5,
    )

    for variant in report["variants"].values():
        assert sum(
            point["count"] for point in variant["points"]
        ) == len(labels)


def test_report_contains_both_probability_variants() -> None:
    labels, raw, calibrated = synthetic_predictions()

    report = summarize_calibration(labels, raw, calibrated)

    assert set(report["variants"]) == {
        "before_platt",
        "after_platt",
    }


def test_report_is_reproducible() -> None:
    labels, raw, calibrated = synthetic_predictions()

    first = summarize_calibration(labels, raw, calibrated)
    second = summarize_calibration(labels, raw, calibrated)

    assert first == second


def test_report_contains_no_patient_identifiers() -> None:
    labels, raw, calibrated = synthetic_predictions()

    report_text = json.dumps(
        summarize_calibration(labels, raw, calibrated)
    ).lower()

    for forbidden in (
        "subject_id",
        "hadm_id",
        "stay_id",
        "patient_id",
        "prediction_time",
    ):
        assert forbidden not in report_text


def test_misaligned_probabilities_are_rejected() -> None:
    with pytest.raises(ValueError, match="equal length"):
        summarize_calibration(
            [0, 1],
            [0.20],
            [0.20, 0.80],
        )


def test_invalid_probability_is_rejected() -> None:
    with pytest.raises(ValueError, match=r"in \[0, 1\]"):
        summarize_calibration(
            [0, 1],
            [0.20, 1.20],
            [0.20, 0.80],
        )


def test_svg_contains_curves_and_window_counts(tmp_path):
    report = summarize_calibration(
        labels=[0, 0, 1, 1],
        raw_probabilities=[0.1, 0.3, 0.7, 0.9],
        calibrated_probabilities=[0.2, 0.4, 0.6, 0.8],
        bins=4,
    )
    output_path = tmp_path / "calibration.svg"

    render_calibration_svg(report, output_path)

    svg = output_path.read_text(encoding="utf-8")
    assert svg.startswith("<svg")
    assert "Perfect calibration" in svg
    assert "Candidate before Platt" in svg
    assert "Candidate after Platt" in svg
    assert "Windows per probability interval" in svg
    assert "<rect" in svg
    assert 'class="histogram-y-tick"' in svg
    assert 'class="histogram-count"' in svg

def test_svg_is_reproducible(tmp_path):
    report = summarize_calibration(
        labels=[0, 0, 1, 1],
        raw_probabilities=[0.1, 0.3, 0.7, 0.9],
        calibrated_probabilities=[0.2, 0.4, 0.6, 0.8],
        bins=4,
    )
    first = tmp_path / "first.svg"
    second = tmp_path / "second.svg"

    render_calibration_svg(report, first)
    render_calibration_svg(report, second)

    assert first.read_bytes() == second.read_bytes()
