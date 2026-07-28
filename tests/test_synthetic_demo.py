"""Public synthetic-demo tests that write only to pytest temporary directories."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

import pytest

from scripts.generate_synthetic_demo import FIELDNAMES, generate_dataset
from scripts.run_synthetic_demo import (
    INPUT_HOURS,
    LABEL_HORIZON_HOURS,
    assign_splits,
    build_windows,
    run_demo,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROTECTED_ARTIFACTS = (
    "reports/test_metrics.csv",
    "reports/validation_metrics.csv",
    "reports/model_comparison.csv",
    "reports/bootstrap_summary.json",
    "reports/thresholds.json",
    "models/baselines/model_selection.json",
    "reports/figures/calibration_curves.png",
    "reports/figures/decision_thresholds.png",
    "reports/figures/precision_recall_curves.png",
    "reports/figures/risk_distribution.png",
    "reports/figures/roc_curves.png",
)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_generation_is_reproducible_and_uses_fictitious_identifiers(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    generate_dataset(first, patients=12, hours=30, seed=17)
    generate_dataset(second, patients=12, hours=30, seed=17)
    assert first.read_bytes() == second.read_bytes()

    with first.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    subjects = {row["subject_id"] for row in rows}
    assert len(subjects) == 12
    assert all(re.fullmatch(r"SYNTH-P\d{4}", subject) for subject in subjects)
    assert set(rows[0]) == set(FIELDNAMES)
    assert not ({"name", "address", "phone", "email"} & set(rows[0]))


def test_windows_respect_input_and_label_horizons(tmp_path: Path) -> None:
    path = tmp_path / "raw.csv"
    rows = generate_dataset(path, patients=12, hours=30, seed=23)
    windows, feature_names = build_windows(rows)
    assert windows
    assert {row["input_hours"] for row in windows} == {INPUT_HOURS} == {12}
    assert {row["label_horizon_hours"] for row in windows} == {
        LABEL_HORIZON_HOURS
    } == {6}
    assert {row["label"] for row in windows} == {0, 1}
    assert all("future" not in name.lower() for name in feature_names)
    assert not ({"subject_id", "stay_id", "label", "split"} & set(feature_names))


def test_patient_splits_have_zero_overlap(tmp_path: Path) -> None:
    rows = generate_dataset(tmp_path / "raw.csv", patients=15, hours=30, seed=31)
    windows, _ = build_windows(rows)
    assignments = assign_splits(windows, seed=31)
    split_patients = {
        split: {patient for patient, assigned in assignments.items() if assigned == split}
        for split in ("train", "validation", "holdout")
    }
    assert all(split_patients.values())
    assert split_patients["train"].isdisjoint(split_patients["validation"])
    assert split_patients["train"].isdisjoint(split_patients["holdout"])
    assert split_patients["validation"].isdisjoint(split_patients["holdout"])


def test_demo_rejects_protected_project_paths(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="protected Phase 2"):
        run_demo(PROJECT_ROOT / "reports" / "synthetic_demo")
    with pytest.raises(ValueError, match="clinical data tree"):
        run_demo(
            tmp_path / "output",
            input_path=PROJECT_ROOT / "data/processed/modeling_windows.csv",
        )


def test_small_end_to_end_demo_writes_only_to_tmp_path(tmp_path: Path) -> None:
    before = {
        relative: _digest(PROJECT_ROOT / relative)
        for relative in PROTECTED_ARTIFACTS
    }
    output_dir = tmp_path / "synthetic_demo"
    summary = run_demo(output_dir, patients=12, hours=30, seed=20260726)
    expected = {
        "raw_vitals.csv",
        "hourly_vitals.csv",
        "windows.csv",
        "split_summary.json",
        "validation_metrics.json",
        "holdout_metrics.json",
        "demo_summary.json",
    }
    assert {path.name for path in output_dir.iterdir()} == expected
    assert summary["data_source"] == "fully_synthetic"
    assert summary["patient_overlap"] == 0
    assert summary["positive_windows"] > 0
    assert summary["negative_windows"] > 0
    assert summary["threshold_source"] == "synthetic_validation_only"
    persisted = json.loads((output_dir / "demo_summary.json").read_text())
    assert persisted == summary
    after = {
        relative: _digest(PROJECT_ROOT / relative)
        for relative in PROTECTED_ARTIFACTS
    }
    assert after == before
