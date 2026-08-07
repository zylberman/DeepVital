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
from scripts.build_canonical_cohort import (
    build_metadata,
    capture_source_state,
    require_clean_worktree,
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
    with pytest.raises(ValueError, match="clinical reference"):
        assert_public_metadata({"source": "Patient/not-public"})


def test_source_state_is_captured_before_outputs_and_remains_source_provenance(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.email", "synthetic@example.invalid"],
        cwd=repository,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Synthetic Test"],
        cwd=repository,
        check=True,
    )
    (repository / "source.txt").write_text("source\n", encoding="utf-8")
    subprocess.run(["git", "add", "source.txt"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "source"], cwd=repository, check=True)
    state = capture_source_state(repository)
    expected_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert state == {
        "source_code_commit": expected_commit,
        "working_tree_dirty_before_run": False,
    }
    (repository / "generated.json").write_text("{}\n", encoding="utf-8")
    assert state["working_tree_dirty_before_run"] is False

    canonical = tmp_path / "canonical.csv"
    windows = tmp_path / "windows.csv"
    canonical.write_text("private synthetic input\n", encoding="utf-8")
    windows.write_text("private synthetic output\n", encoding="utf-8")
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    (report_dir / "hourly_quality.json").write_text(
        json.dumps(
            {"entities": {"patients": 2, "hospital_admissions": 2, "icu_stays": 2}}
        )
    )
    (report_dir / "label_distribution.json").write_text(
        json.dumps({"total": 2, "positive": 1, "event_prevalence": 0.5})
    )
    (report_dir / "split_summary.json").write_text(json.dumps({"seed": 7}))
    config = tmp_path / "config.json"
    config.write_text("{}\n", encoding="utf-8")
    metadata = build_metadata(
        canonical,
        windows,
        report_dir,
        [config],
        "2026-01-01T00:00:00+00:00",
        state,
    )
    assert metadata["source_code_commit"] == expected_commit
    assert "git_commit" not in metadata
    require_clean_worktree(state)
    with pytest.raises(RuntimeError, match="clean working tree"):
        require_clean_worktree(
            {
                "source_code_commit": expected_commit,
                "working_tree_dirty_before_run": True,
            }
        )


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
    benchmarks = {
        "constant_prevalence": lambda train, valid: (
            [sum(y[int(index)] for index in train) / len(train)] * len(valid),
            [True] * len(valid),
        ),
        "synthetic_score": lambda train, valid: (
            [float(x[int(index)][0]) / 12 for index in valid],
            [int(index) % 2 == 0 for index in valid],
        ),
    }
    benchmark_metadata = {
        "constant_prevalence": {"prediction_output_type": "probability"},
        "synthetic_score": {"prediction_output_type": "ranking_score"},
    }
    result = grouped_nested_cross_validation(
        x,
        y,
        subjects,
        factories,
        benchmarks,
        benchmark_metadata,
        outer_folds=3,
        inner_folds=2,
        bootstrap_replicates=10,
    )
    assert result["evaluation_name"] == "internal_nested_cross_validation"
    assert result["evaluation_role"] == "internal_validation"
    assert result["each_patient_assigned_to_one_outer_fold"] is True
    assert result["each_window_predicted_once_out_of_fold"] is True
    assert result["patient_overlap_between_outer_folds"] == 0
    assert result["oof_prediction_count"] == len(y)
    assert result["resampling_unit"] == "patient"
    assert all(
        fold["threshold_source"] == "inner_cross_validation_only"
        for fold in result["folds"]
    )
    assert {
        row["model"] for row in result["development_model_comparison"]
    } == {"constant_prevalence", "nested_ml_strategy", "synthetic_score"}
    assert all(
        row["threshold_policy"] == "fold_specific_inner_cv"
        for row in result["development_model_comparison"]
    )
    assert result["final_threshold_status"] == "not_frozen"
    score_row = next(
        row
        for row in result["development_model_comparison"]
        if row["model"] == "synthetic_score"
    )
    assert score_row["brier_score"] is None
    assert score_row["log_loss"] is None
    assert "brier_score" not in score_row["bootstrap_ci"]
    assert score_row["availability_analysis"]["uncalculable_windows"] > 0
    paired = result["paired_patient_bootstrap_vs_nested_ml"]
    assert paired
    assert all(row["reference_model"] == "nested_ml_strategy" for row in paired)
    assert all(row["number_of_valid_bootstraps"] == 10 for row in paired)
    score_metrics = {
        row["metric"]
        for row in paired
        if row["comparison_model"] == "synthetic_score"
    }
    assert score_metrics == {"delta_auroc", "delta_auprc"}


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
