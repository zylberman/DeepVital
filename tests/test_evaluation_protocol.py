"""Controls for cohort freezing, internal validation, and confirmatory evaluation."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import joblib
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from deepvital.evaluation.confirmatory import evaluate_confirmatory
from deepvital.evaluation.nested_cv import grouped_nested_cross_validation
from deepvital.reproducibility.fingerprints import (
    assert_public_metadata,
    fingerprint_configuration,
    fingerprint_file,
    fingerprint_records,
)


def _write_csv(path: Path, patients: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["subject_id", "label", "x"])
        writer.writeheader()
        for index, patient in enumerate(patients):
            writer.writerow({"subject_id": patient, "label": index % 2, "x": index})


def _confirmatory_files(tmp_path: Path) -> dict[str, Path | str]:
    dataset = tmp_path / "confirmatory.csv"
    _write_csv(dataset, ["NEW-A", "NEW-B", "NEW-C", "NEW-D"])
    protocol = tmp_path / "protocol.md"
    protocol.write_text("frozen protocol v1\n", encoding="utf-8")
    manifest = tmp_path / "development.json"
    manifest.write_text(
        json.dumps({"patient_assignments": {"DEV-A": "development"}}),
        encoding="utf-8",
    )
    model = LogisticRegression().fit([[0], [1], [2], [3]], [0, 1, 0, 1])
    model_path = tmp_path / "model.joblib"
    joblib.dump(model, model_path)
    metadata = tmp_path / "model.json"
    metadata.write_text(
        json.dumps({"frozen": True, "threshold": 0.5, "feature_names": ["x"]}),
        encoding="utf-8",
    )
    return {
        "dataset": dataset,
        "dataset_role": "confirmatory-test",
        "protocol": protocol,
        "protocol_hash": fingerprint_file(protocol),
        "cohort_fingerprint": fingerprint_file(dataset),
        "frozen_model": model_path,
        "model_metadata": metadata,
        "development_manifest": manifest,
        "registry": tmp_path / "registry.json",
        "git_commit": "synthetic-test",
    }


def test_fingerprints_are_deterministic_and_change_with_cohort() -> None:
    original = [{"subject_id": "SYNTH-A", "label": 0}]
    assert fingerprint_records(original) == fingerprint_records(reversed(original))
    assert fingerprint_records(original) != fingerprint_records(
        [*original, {"subject_id": "SYNTH-B", "label": 1}]
    )


def test_input_and_configuration_file_hashes_are_reproducible(tmp_path: Path) -> None:
    cohort = tmp_path / "cohort.csv"
    cohort.write_text("synthetic-row\n", encoding="utf-8")
    config = tmp_path / "config.json"
    config.write_text('{"window": 12}\n', encoding="utf-8")
    assert fingerprint_file(cohort) == fingerprint_file(cohort)
    assert fingerprint_configuration([config]) == fingerprint_configuration([config])
    original = fingerprint_file(cohort)
    cohort.write_text("synthetic-row-changed\n", encoding="utf-8")
    assert fingerprint_file(cohort) != original


def test_public_metadata_rejects_clinical_identifier_keys() -> None:
    assert_public_metadata({"patients": 10, "input_fingerprint": "sha256:test"})
    with pytest.raises(ValueError, match="forbidden key"):
        assert_public_metadata({"subject_id": "not-public"})


def test_nested_cv_is_patient_grouped_and_predicts_each_patient_once() -> None:
    x, y, subjects = [], [], []
    for patient in range(12):
        for window in range(2):
            x.append([patient + window / 10])
            y.append((patient + window) % 2)
            subjects.append(f"SYNTH-{patient:02d}")
    factories = {
        "logistic": lambda: Pipeline(
            [("scaler", StandardScaler()), ("model", LogisticRegression())]
        )
    }
    result = grouped_nested_cross_validation(
        x,
        y,
        subjects,
        factories,
        outer_folds=3,
        inner_folds=2,
        bootstrap_replicates=10,
    )
    assert result["evaluation_name"] == "internal_nested_cross_validation"
    assert result["evaluation_role"] == "internal_validation"
    assert result["each_patient_predicted_once"] is True
    assert result["resampling_unit"] == "patient"
    assert all(
        fold["threshold_source"] == "inner_cross_validation_only"
        for fold in result["folds"]
    )


def test_confirmatory_requires_frozen_model(tmp_path: Path) -> None:
    arguments = _confirmatory_files(tmp_path)
    Path(arguments["model_metadata"]).write_text(
        json.dumps({"frozen": False, "threshold": 0.5, "feature_names": ["x"]})
    )
    with pytest.raises(ValueError, match="frozen model"):
        evaluate_confirmatory(**arguments)


def test_confirmatory_rejects_development_patient_overlap(tmp_path: Path) -> None:
    arguments = _confirmatory_files(tmp_path)
    _write_csv(Path(arguments["dataset"]), ["DEV-A", "NEW-B"])
    arguments["cohort_fingerprint"] = fingerprint_file(Path(arguments["dataset"]))
    with pytest.raises(ValueError, match="development patients"):
        evaluate_confirmatory(**arguments)


def test_confirmatory_second_identical_run_is_reproduction(tmp_path: Path) -> None:
    arguments = _confirmatory_files(tmp_path)
    first, registry = evaluate_confirmatory(**arguments)
    Path(arguments["registry"]).write_text(json.dumps(registry), encoding="utf-8")
    second, updated = evaluate_confirmatory(**arguments)
    assert first["evaluation_kind"] == "first_confirmatory_evaluation"
    assert second["evaluation_kind"] == "technical_reproduction"
    assert updated["technical_reproduction_count"] == 1


def test_consumed_confirmatory_rejects_changed_configuration(tmp_path: Path) -> None:
    arguments = _confirmatory_files(tmp_path)
    _, registry = evaluate_confirmatory(**arguments)
    Path(arguments["registry"]).write_text(json.dumps(registry), encoding="utf-8")
    metadata = Path(arguments["model_metadata"])
    metadata.write_text(
        json.dumps({"frozen": True, "threshold": 0.4, "feature_names": ["x"]})
    )
    with pytest.raises(ValueError, match="changed frozen inputs"):
        evaluate_confirmatory(**arguments)


def test_protocol_and_cohort_hashes_are_verified(tmp_path: Path) -> None:
    arguments = _confirmatory_files(tmp_path)
    arguments["protocol_hash"] = "sha256:wrong"
    with pytest.raises(ValueError, match="Protocol hash"):
        evaluate_confirmatory(**arguments)


def test_training_code_has_no_confirmatory_dataset_dependency() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "scripts/train_baseline_models.py").read_text(encoding="utf-8")
    assert "evaluation.confirmatory" not in source
    assert 'load_split(dataset, "confirmatory' not in source
    source = (root / "src/deepvital/evaluation/confirmatory.py").read_text(
        encoding="utf-8"
    )
    assert "train_baseline_models" not in source
    assert ".fit(" not in source


def test_legacy_builder_requires_explicit_acknowledgement(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    command = [
        sys.executable,
        str(root / "scripts/build_phase_1b_dataset.py"),
        "--canonical-input",
        str(tmp_path / "input.csv"),
        "--hourly-output",
        str(tmp_path / "hourly.csv"),
        "--windows-output",
        str(tmp_path / "windows.csv"),
        "--quality-report",
        str(tmp_path / "quality.json"),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode != 0
    assert "deprecated" in result.stderr
