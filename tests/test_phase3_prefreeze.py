from __future__ import annotations

import json
import math
import stat
from pathlib import Path

import pytest

from deepvital.features.windows import window_columns
from deepvital.models.clinical_baselines import predict_clinical_benchmarks
from deepvital.phase3.prefreeze import (
    BP_SOURCE_CODES,
    LOCKED_FEATURES,
    PHASE3_REGISTRATION_OUTPUT,
    PHASE3_RESULT_OUTPUTS,
    assert_phase3_prerun_ready,
    assert_registration_matches,
    assert_reserved_outputs_unused,
    build_private_fold_manifest,
    build_protocol_registration,
    derive_locked_features,
    feature_derivation_audit,
    fold_manifest_fingerprint,
    future_map_label_bounds,
    map_mean_6h_benchmark_score,
    raw_map_mean_6h,
    validate_private_fold_manifest,
    write_private_fold_manifest,
    write_registration_exclusively,
)
from deepvital.reproducibility.fingerprints import (
    fingerprint_configuration,
    fingerprint_file,
)

EXPECTED_FEATURES = (
    "map_mean_6h",
    "mean_arterial_pressure_current",
    "mean_arterial_pressure_rolling_slope",
    "heart_rate_current",
    "systolic_bp_current",
    "shock_index",
    "respiratory_rate_current",
    "oxygen_saturation_current",
    "mean_arterial_pressure_proportion_missing",
    "heart_rate_proportion_missing",
    "systolic_bp_proportion_missing",
    "respiratory_rate_proportion_missing",
    "oxygen_saturation_proportion_missing",
    "mean_arterial_pressure_h0_missing",
    "heart_rate_h0_missing",
    "systolic_bp_h0_missing",
    "respiratory_rate_h0_missing",
    "oxygen_saturation_h0_missing",
)


def synthetic_feature_row() -> dict[str, float | str | None]:
    row: dict[str, float | str | None] = {
        f"mean_arterial_pressure_hm{offset}_value": 60.0 + offset
        for offset in range(5, 0, -1)
    }
    row["mean_arterial_pressure_h0_value"] = 60.0
    for index, predictor in enumerate(LOCKED_FEATURES[1:13], start=1):
        row[predictor] = float(index)
    for predictor in LOCKED_FEATURES[13:]:
        row[predictor] = 0.0
    return row


def test_exact_locked_feature_whitelist_and_derivability_contract() -> None:
    assert LOCKED_FEATURES == EXPECTED_FEATURES
    audit = feature_derivation_audit()
    assert tuple(item.predictor for item in audit) == EXPECTED_FEATURES
    assert len(audit) == 18
    assert all(not item.requires_information_after_t for item in audit)
    assert all("t+" not in item.temporal_window for item in audit)
    canonical_columns = set(
        window_columns(
            [
                "heart_rate",
                "respiratory_rate",
                "systolic_bp",
                "diastolic_bp",
                "mean_arterial_pressure",
                "oxygen_saturation",
                "temperature",
                "oxygen_flow",
            ],
            input_hours=12,
        )
    )
    assert all(set(item.source_columns) <= canonical_columns for item in audit)


def test_locked_features_ignore_future_fields_and_enforce_binary_contract() -> None:
    row = synthetic_feature_row()
    baseline = derive_locked_features(row)
    row.update({"label": 1, "future_map_h1": 1.0, "future_map_h6": 999.0})
    assert derive_locked_features(row) == baseline
    assert tuple(baseline) == EXPECTED_FEATURES
    row["heart_rate_h0_missing"] = None
    with pytest.raises(ValueError, match="heart_rate_h0_missing"):
        derive_locked_features(row)


@pytest.mark.parametrize(
    "values",
    [
        [60, 61, 62, 63, 64, 65],
        [None, "", "nan", 63, 64, 65],
        [None, "", "nan", "inf", "bad", None],
    ],
)
def test_map_mean_6h_is_exactly_the_existing_benchmark(values: list[object]) -> None:
    tags = ("hm5", "hm4", "hm3", "hm2", "hm1", "h0")
    row = {
        f"mean_arterial_pressure_{tag}_value": value
        for tag, value in zip(tags, values, strict=True)
    }
    existing = predict_clinical_benchmarks(
        row,
        training_prevalence=0.2,
        config={"risk_center_map": 65.0, "risk_scale_map": 10.0},
    )["map_mean_6h"]
    assert map_mean_6h_benchmark_score(row) == existing
    finite = [float(value) for value in values if _is_finite(value)]
    expected_raw = sum(finite) / len(finite) if finite else None
    assert raw_map_mean_6h(row) == expected_raw


def _is_finite(value: object) -> bool:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def test_prespecified_missing_future_map_bounds() -> None:
    assert future_map_label_bounds(
        [64.0, None, 70.0, 70.0, 70.0, 70.0],
        threshold=65.0,
        consecutive_hours=2,
    ) == (0, 1)
    assert future_map_label_bounds(
        [None, None, None, None, None, None],
        threshold=65.0,
        consecutive_hours=2,
    ) == (0, 1)
    assert future_map_label_bounds(
        [65.0, 65.0, 64.0, 64.0, 70.0, 70.0],
        threshold=65.0,
        consecutive_hours=2,
    ) == (1, 1)


def patient_counts() -> dict[str, int]:
    return {f"patient-{index}": index + 1 for index in range(12)}


def test_deterministic_patient_folds_have_zero_overlap() -> None:
    first = build_private_fold_manifest(patient_counts())
    second = build_private_fold_manifest(dict(reversed(list(patient_counts().items()))))
    assert first == second
    assert fold_manifest_fingerprint(first) == fold_manifest_fingerprint(second)
    public = validate_private_fold_manifest(first)
    assert public["outer_folds"] == 5
    assert public["inner_folds"] == 3
    assert public["zero_patient_overlap"] is True
    assert public["all_patients_have_one_outer_fold"] is True
    assignments = first["patient_assignments"]
    assert len(assignments) == len(patient_counts())
    for patient, assignment in assignments.items():
        outer = assignment["outer_fold"]
        assert outer in range(1, 6)
        assert str(outer) not in assignment["inner_validation_fold_by_outer_training_fold"]
        assert len(assignment["inner_validation_fold_by_outer_training_fold"]) == 4
        validation = {
            name for name, value in assignments.items() if value["outer_fold"] == outer
        }
        assert patient in validation
        assert not (validation & (set(assignments) - validation))


def test_private_manifest_exposes_only_public_fingerprint(tmp_path: Path) -> None:
    manifest = build_private_fold_manifest(patient_counts())
    private_root = tmp_path / "private"
    path = private_root / "phase3" / "fold_manifest.json"
    write_private_fold_manifest(path, manifest, private_root=private_root)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert "patient-1" in path.read_text()
    public = {
        "fold_manifest_fingerprint": fold_manifest_fingerprint(manifest),
        "accounting": validate_private_fold_manifest(manifest),
    }
    public_text = json.dumps(public)
    assert "patient-1" not in public_text
    assert "patient_assignments" not in public_text
    with pytest.raises(FileExistsError):
        write_private_fold_manifest(path, manifest, private_root=private_root)


def test_reserved_outputs_and_exclusive_write_protect_existing_files(
    tmp_path: Path,
) -> None:
    assert_reserved_outputs_unused(tmp_path)
    registration = tmp_path / PHASE3_REGISTRATION_OUTPUT
    registration.parent.mkdir(parents=True)
    registration.write_text("{}")
    assert_reserved_outputs_unused(tmp_path)
    occupied = tmp_path / PHASE3_RESULT_OUTPUTS[0]
    occupied.parent.mkdir(parents=True, exist_ok=True)
    occupied.write_text("prior artifact")
    with pytest.raises(FileExistsError, match="phase3_incremental_value"):
        assert_reserved_outputs_unused(tmp_path)


def test_protocol_registration_generates_separate_fingerprints(tmp_path: Path) -> None:
    protocol = tmp_path / "protocol.md"
    protocol.write_text("frozen protocol\n")
    configuration = tmp_path / "config.json"
    configuration.write_text('{"seed":20260726}\n')
    manifest = build_private_fold_manifest(patient_counts())
    registration = build_protocol_registration(
        protocol_path=protocol,
        frozen_protocol_git_commit="a" * 40,
        canonical_cohort_fingerprint="sha256:" + "b" * 64,
        private_fold_manifest=manifest,
        source_commit="c" * 40,
        configuration_paths=[configuration],
        execution_timestamp="2026-08-08T12:00:00+00:00",
    )
    assert registration["frozen_protocol_sha256"] == fingerprint_file(protocol)
    assert registration["configuration_fingerprint"] == fingerprint_configuration(
        [configuration]
    )
    assert registration["fold_manifest_fingerprint"] == fold_manifest_fingerprint(
        manifest
    )
    assert "patient_assignments" not in json.dumps(registration)
    output = tmp_path / "registration.json"
    write_registration_exclusively(output, registration)
    with pytest.raises(FileExistsError):
        write_registration_exclusively(output, registration)


def test_prerun_accepts_exact_registration_and_rejects_mismatch(tmp_path: Path) -> None:
    protocol = tmp_path / "protocol.md"
    protocol.write_text("frozen protocol\n")
    configuration = tmp_path / "config.json"
    configuration.write_text('{"seed":20260726}\n')
    manifest = build_private_fold_manifest(patient_counts())
    expected = build_protocol_registration(
        protocol_path=protocol,
        frozen_protocol_git_commit="a" * 40,
        canonical_cohort_fingerprint="sha256:" + "b" * 64,
        private_fold_manifest=manifest,
        source_commit="c" * 40,
        configuration_paths=[configuration],
        execution_timestamp="2026-08-08T12:00:00+00:00",
    )
    registration_path = tmp_path / PHASE3_REGISTRATION_OUTPUT
    write_registration_exclusively(registration_path, expected)
    assert assert_phase3_prerun_ready(tmp_path, expected) == expected

    mismatch = dict(expected)
    mismatch["configuration_fingerprint"] = "sha256:" + "d" * 64
    with pytest.raises(ValueError, match="configuration_fingerprint"):
        assert_phase3_prerun_ready(tmp_path, mismatch)

    result_path = tmp_path / PHASE3_RESULT_OUTPUTS[-1]
    result_path.write_text("existing result")
    with pytest.raises(FileExistsError, match="phase3_protocol_deviations"):
        assert_phase3_prerun_ready(tmp_path, expected)


def test_prerun_requires_registration(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="registration is required"):
        assert_registration_matches(
            tmp_path / PHASE3_REGISTRATION_OUTPUT,
            {
                field: "expected"
                for field in (
                    "frozen_protocol_sha256",
                    "frozen_protocol_git_commit",
                    "canonical_cohort_fingerprint",
                    "fold_manifest_fingerprint",
                    "configuration_fingerprint",
                )
            },
        )


def test_bp_source_codes_match_versioned_mapping() -> None:
    expected = {
        "invasive_systolic_bp": ("220050", "225309"),
        "invasive_mean_arterial_pressure": ("220052", "225312"),
        "non_invasive_systolic_bp": ("220179",),
        "non_invasive_mean_arterial_pressure": ("220181",),
    }
    assert BP_SOURCE_CODES == expected
    mapping_path = Path(__file__).parents[1] / "configs/fhir_vital_signs.yaml"
    mapping = json.loads(mapping_path.read_text())["mappings"]
    assert all(code in mapping for codes in expected.values() for code in codes)
