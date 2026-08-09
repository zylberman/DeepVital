from __future__ import annotations

import copy
import csv
import json
import math
from pathlib import Path

import pytest

from deepvital.evaluation.bootstrap import paired_patient_bootstrap
from deepvital.phase3.generation import (
    VARIABLES,
    build_phase3_sensitivity_windows,
    filter_bp_source_rows,
)
from deepvital.phase3.implementation import (
    ADVANCEMENT_MARGIN,
    APPROVED_MODEL_NAME,
    BINARY_FEATURES,
    C_GRID,
    CONTINUOUS_FEATURES,
    advancement_decision,
    build_locked_candidate,
    load_frozen_manifest,
    run_frozen_nested_cv,
    validate_frozen_config,
)
from deepvital.phase3.prefreeze import (
    LOCKED_FEATURES,
    build_private_fold_manifest,
    fingerprint_outcome_inputs,
    fold_manifest_fingerprint,
    validate_registered_source_state,
)
from deepvital.phase3.provenance import build_execution_provenance
from deepvital.phase3.sensitivities import (
    aggregate_bp_source_hour,
    benchmark_missingness_indices,
    evaluation_weights,
    frozen_sensitivity_definitions,
    incomplete_future_map_sensitivity,
    missingness_charting_report,
    outcome_sensitivity_grid,
)

ROOT = Path(__file__).parents[1]


def frozen_config() -> dict:
    return json.loads((ROOT / "configs/phase3_frozen.json").read_text())


def synthetic_rows() -> tuple[list[dict[str, object]], dict]:
    patient_counts = {f"synthetic-{index:02d}": 2 for index in range(15)}
    manifest = build_private_fold_manifest(patient_counts)
    rows: list[dict[str, object]] = []
    for patient_index, patient in enumerate(patient_counts):
        for label in (0, 1):
            baseline = 75.0 - label * 12.0 + patient_index * 0.1
            row: dict[str, object] = {
                "subject_id": patient,
                "window_id": f"synthetic-window-{patient_index}-{label}",
                "label": label,
            }
            for offset, tag in enumerate(("hm5", "hm4", "hm3", "hm2", "hm1", "h0")):
                row[f"mean_arterial_pressure_{tag}_value"] = baseline + offset * 0.1
            for feature_index, name in enumerate(LOCKED_FEATURES[1:13]):
                row[name] = baseline + feature_index * 0.01
            for feature_index, name in enumerate(LOCKED_FEATURES[13:]):
                row[name] = float((patient_index + label + feature_index) % 2)
            rows.append(row)
    return rows, manifest


def test_frozen_configuration_and_model_space_are_closed() -> None:
    config = frozen_config()
    validate_frozen_config(config)
    assert C_GRID == (0.1, 1.0)
    assert APPROVED_MODEL_NAME == "l2_logistic_regression"
    assert ADVANCEMENT_MARGIN == 0.02
    assert CONTINUOUS_FEATURES + BINARY_FEATURES == LOCKED_FEATURES
    for c_value in C_GRID:
        pipeline = build_locked_candidate(c_value)
        candidate = pipeline.named_steps["candidate"]
        assert candidate.penalty == "l2"
        assert candidate.solver == "lbfgs"
        assert candidate.class_weight == "balanced"
        assert candidate.max_iter == 1000
        assert candidate.C == c_value
        assert set(pipeline.named_steps) == {"preprocessing", "candidate"}
    with pytest.raises(ValueError, match="closed values"):
        build_locked_candidate(10.0)
    changed = copy.deepcopy(config)
    changed["candidate"]["C_values"].append(10.0)
    with pytest.raises(ValueError, match="candidate"):
        validate_frozen_config(changed)


@pytest.mark.parametrize(
    ("section", "field", "changed_value"),
    [
        ("validation", "primary_metric", "auroc"),
        ("validation", "bootstrap_replicates", 999),
        ("validation", "advancement_margin", 0.01),
        ("calibration", "method", "isotonic"),
        ("thresholds", "primary", "fixed_0.5"),
        ("sensitivities", "map_thresholds", [65.0]),
    ],
)
def test_frozen_configuration_rejects_every_scientific_switch(
    section: str, field: str, changed_value: object
) -> None:
    config = frozen_config()
    config[section][field] = changed_value
    with pytest.raises(ValueError, match=section):
        validate_frozen_config(config)


def test_preprocessing_is_fitted_only_when_candidate_fit_is_called() -> None:
    model = build_locked_candidate(0.1)
    preprocessing = model.named_steps["preprocessing"]
    assert not hasattr(preprocessing, "transformers_")
    x = [[math.nan] * 13 + [0, 1, 0, 1, 0], [2.0] * 13 + [1, 0, 1, 0, 1]]
    model.fit(x, [0, 1])
    imputer = model.named_steps["preprocessing"].named_transformers_[
        "continuous"
    ].named_steps["median_imputer"]
    assert list(imputer.statistics_) == [2.0] * 13


def test_frozen_manifest_is_consumed_and_changed_fingerprint_rejected(
    tmp_path: Path,
) -> None:
    _, manifest = synthetic_rows()
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    expected = fold_manifest_fingerprint(manifest)
    assert load_frozen_manifest(path, expected) == manifest
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        load_frozen_manifest(path, "sha256:" + "0" * 64)


def test_registered_source_commit_and_clean_tree_are_mandatory() -> None:
    validate_registered_source_state(
        registered_source_commit="a" * 40,
        current_head="a" * 40,
        working_tree_dirty=False,
    )
    with pytest.raises(RuntimeError, match="HEAD"):
        validate_registered_source_state(
            registered_source_commit="a" * 40,
            current_head="b" * 40,
            working_tree_dirty=False,
        )
    with pytest.raises(RuntimeError, match="clean Git working tree"):
        validate_registered_source_state(
            registered_source_commit="a" * 40,
            current_head="a" * 40,
            working_tree_dirty=True,
        )


def test_all_four_outcome_inputs_are_fingerprinted_and_changes_fail(
    tmp_path: Path,
) -> None:
    names = (
        "canonical_modeling_windows",
        "future_map_sensitivity",
        "bp_invasive_preferred",
        "bp_non_invasive_only",
    )
    paths = {}
    for index, name in enumerate(names):
        path = tmp_path / f"{name}.csv"
        path.write_text(f"synthetic-{index}\n")
        paths[name] = path
    before = fingerprint_outcome_inputs(paths)
    assert tuple(before) == names
    paths["future_map_sensitivity"].write_text("changed\n")
    after = fingerprint_outcome_inputs(paths)
    assert after["future_map_sensitivity"] != before["future_map_sensitivity"]
    assert all(after[name] == before[name] for name in names if name != "future_map_sensitivity")


def test_nested_cv_has_one_oof_prediction_no_overlap_and_training_scopes() -> None:
    rows, manifest = synthetic_rows()
    result = run_frozen_nested_cv(rows, manifest)
    assert len(result.raw_candidate) == len(rows)
    assert len(result.calibrated_candidate) == len(rows)
    assert len(result.benchmark) == len(rows)
    assert all(math.isfinite(value) for value in result.raw_candidate)
    assert {record["selected_C"] for record in result.fold_records} <= set(C_GRID)
    assert len(result.fold_records) == 5
    assert all(record["patient_overlap"] == 0 for record in result.fold_records)
    assert all(
        record["calibration_training_scope"] == "outer_training_inner_oof_only"
        for record in result.fold_records
    )
    assert all(
        set(record["inner_mean_auprc_by_C"]) == {"0.1", "1.0"}
        for record in result.fold_records
    )
    assert all(
        record["candidate_threshold"]["youden"] is not None
        and record["benchmark_threshold"]["youden"] is not None
        for record in result.fold_records
    )


def test_paired_bootstrap_uses_patient_clusters_and_identical_pairs() -> None:
    subjects = ["a", "a", "b", "b", "c", "c"]
    labels = [0, 1, 0, 1, 0, 1]
    predictions = {
        "candidate": [0.1, 0.9, 0.2, 0.8, 0.3, 0.7],
        "benchmark": [0.2, 0.8, 0.3, 0.7, 0.4, 0.6],
    }
    first = paired_patient_bootstrap(
        subjects, labels, predictions, "benchmark", {"candidate"}, 25, 20260726
    )
    second = paired_patient_bootstrap(
        subjects, labels, predictions, "benchmark", {"candidate"}, 25, 20260726
    )
    assert first == second
    assert {row["metric"] for row in first} == {"delta_auprc", "delta_auroc"}
    assert all(row["difference_definition"] == "comparison_minus_reference" for row in first)


def test_advancement_exposes_every_frozen_criterion() -> None:
    passed = advancement_decision(
        delta_auprc=0.02,
        delta_auprc_ci_lower=0.001,
        oof_accounting_valid=True,
        primary_protocol_deviation=False,
        patient_equal_delta_auprc=-0.02,
        bp_source_delta_auprcs={"invasive_preferred": -0.02, "non_invasive_only": 0.0},
        sensitivities_disclosed=True,
        threshold_reproducible=True,
    )
    assert passed["decision"] == "logistic_regression_advances"
    assert all(item["status"] == "PASS" for item in passed["primary_criteria"].values())
    failed = advancement_decision(
        delta_auprc=0.019999,
        delta_auprc_ci_lower=0.001,
        oof_accounting_valid=True,
        primary_protocol_deviation=False,
        patient_equal_delta_auprc=0.0,
        bp_source_delta_auprcs={"invasive_preferred": 0.0, "non_invasive_only": 0.0},
        sensitivities_disclosed=True,
        threshold_reproducible=True,
    )
    assert failed["primary_criteria"]["delta_auprc_at_least_0.02"]["status"] == "FAIL"


def test_all_frozen_sensitivity_definitions() -> None:
    definitions = frozen_sensitivity_definitions()
    assert len(definitions["outcome_grid"]) == 9
    grid = outcome_sensitivity_grid([59, 59, 66, 66, 66, 66])
    assert grid["map_lt_60_2_consecutive"] == 1
    assert grid["map_lt_60_3_consecutive"] == 0
    assert incomplete_future_map_sensitivity(
        [64, None, 70, 70, 70, 70], threshold=65, consecutive_hours=2
    ) == {"missing_as_not_low": 0, "missing_as_low": 1}
    measurements = [
        {"code": "220050", "value": 90},
        {"code": "220179", "value": 110},
    ]
    assert aggregate_bp_source_hour(
        measurements, alternative="invasive_preferred", variable="systolic_bp"
    ) == 90
    assert aggregate_bp_source_hour(
        measurements, alternative="non_invasive_only", variable="systolic_bp"
    ) == 110
    assert benchmark_missingness_indices([True, False], "neutral_score_0.5") == [0, 1]
    assert benchmark_missingness_indices([True, False], "complete_case") == [0]
    assert evaluation_weights(["a", "a", "b"], "window_weighted") == [1, 1, 1]
    assert evaluation_weights(["a", "a", "b"], "patient_equal") == [0.5, 0.5, 1.0]
    rows, manifest = synthetic_rows()
    charting = missingness_charting_report(
        rows,
        manifest,
        ("mean_arterial_pressure",),
    )
    assert len(charting["by_outer_fold_and_outcome"]) == 10
    assert charting["unavailable_map_mean_6h_windows"] == 0
    assert charting["windows_per_patient"] == {
        "minimum": 2,
        "mean": 2,
        "maximum": 2,
    }


def test_bp_source_filtering_is_deterministic_and_not_analyst_selectable() -> None:
    base = {
        "subject_id": "synthetic",
        "hadm_id": "admission",
        "stay_id": "stay",
        "observation_time": "2026-01-01T00:10:00Z",
        "normalized_variable": "systolic_bp",
        "numeric_value": "100",
    }
    rows = [
        {**base, "observation_code": "220050"},
        {**base, "observation_code": "220179", "numeric_value": "110"},
    ]
    first = filter_bp_source_rows(rows, "invasive_preferred")
    second = filter_bp_source_rows(list(reversed(rows)), "invasive_preferred")
    assert first == second
    assert [row["observation_code"] for row in first] == ["220050"]
    non_invasive = filter_bp_source_rows(rows, "non_invasive_only")
    assert [row["observation_code"] for row in non_invasive] == ["220179"]
    with pytest.raises(ValueError, match="Unapproved"):
        filter_bp_source_rows(rows, "analyst_choice")


def test_future_map_input_generation_is_deterministic(tmp_path: Path) -> None:
    from deepvital.preprocessing.hourly import hourly_columns

    hourly = tmp_path / "hourly.csv"
    fields = hourly_columns(list(VARIABLES))
    with hourly.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for hour in range(18):
            row: dict[str, object] = {
                "subject_id": "synthetic",
                "hadm_id": "admission",
                "stay_id": "stay",
                "hour": f"2026-01-01T{hour:02d}:00:00Z",
            }
            for variable in VARIABLES:
                value = 70.0 + hour
                row[f"{variable}_observed_value"] = value
                row[f"{variable}_observed"] = 1
                row[f"{variable}_measurement_count"] = 1
                row[f"{variable}_value"] = value
                row[f"{variable}_missing"] = 0
                row[f"{variable}_hours_since"] = 0
                row[f"{variable}_forward_filled"] = 0
            writer.writerow(row)
    first = tmp_path / "future-one.csv"
    second = tmp_path / "future-two.csv"
    for output in (first, second):
        build_phase3_sensitivity_windows(
            hourly,
            output,
            include_incomplete_future_map=True,
            config_root=ROOT / "configs",
        )
    assert first.read_bytes() == second.read_bytes()
    with first.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert [rows[0][f"future_map_h{hour}"] for hour in range(1, 7)] == [
        "82.0",
        "83.0",
        "84.0",
        "85.0",
        "86.0",
        "87.0",
    ]


def test_provenance_contains_frozen_and_environment_metadata(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text("{}")
    registration = {
        "frozen_protocol_git_commit": "a" * 40,
        "frozen_protocol_sha256": "sha256:" + "b" * 64,
        "canonical_cohort_fingerprint": "sha256:" + "c" * 64,
        "fold_manifest_fingerprint": "sha256:" + "d" * 64,
    }
    provenance = build_execution_provenance(
        registration=registration,
        implementation_source_commit="e" * 40,
        configuration_paths=[config],
        execution_timestamp="2026-08-08T12:00:00+00:00",
    )
    assert provenance["implementation_source_commit"] == "e" * 40
    assert provenance["execution_timestamp"] == "2026-08-08T12:00:00+00:00"
    assert provenance["configuration_fingerprint"].startswith("sha256:")
    assert "python_version" in provenance["environment"]
