"""Technical pre-freeze contracts for the prespecified Phase 3 analysis."""

from __future__ import annotations

import json
import math
import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, TextIO

from deepvital.reproducibility.fingerprints import (
    assert_public_metadata,
    fingerprint_configuration,
    fingerprint_file,
    sha256_bytes,
)

PHASE3_SEED = 20260726
OUTER_FOLDS = 5
INNER_FOLDS = 3

LOCKED_FEATURES = (
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

RESERVED_PHASE3_OUTPUTS = (
    Path("reports/phase3_protocol_registration.json"),
    Path("reports/phase3_incremental_value.json"),
    Path("reports/phase3_model_comparison.csv"),
    Path("reports/phase3_paired_comparisons.csv"),
    Path("reports/phase3_sensitivity_analysis.json"),
    Path("reports/phase3_protocol_deviations.json"),
)
PHASE3_REGISTRATION_OUTPUT = RESERVED_PHASE3_OUTPUTS[0]
PHASE3_RESULT_OUTPUTS = RESERVED_PHASE3_OUTPUTS[1:]
REGISTRATION_MATCH_FIELDS = (
    "frozen_protocol_sha256",
    "frozen_protocol_git_commit",
    "canonical_cohort_fingerprint",
    "fold_manifest_fingerprint",
    "configuration_fingerprint",
    "source_commit",
    "outcome_input_fingerprints",
)
OUTCOME_INPUT_NAMES = (
    "canonical_modeling_windows",
    "future_map_sensitivity",
    "bp_invasive_preferred",
    "bp_non_invasive_only",
)

BP_SOURCE_CODES = {
    "invasive_systolic_bp": ("220050", "225309"),
    "invasive_mean_arterial_pressure": ("220052", "225312"),
    "non_invasive_systolic_bp": ("220179",),
    "non_invasive_mean_arterial_pressure": ("220181",),
}

_MAP_6H_COLUMNS = tuple(
    f"mean_arterial_pressure_{tag}_value"
    for tag in ("hm5", "hm4", "hm3", "hm2", "hm1", "h0")
)
_CURRENT_FEATURES = (
    "mean_arterial_pressure_current",
    "heart_rate_current",
    "systolic_bp_current",
    "shock_index",
    "respiratory_rate_current",
    "oxygen_saturation_current",
)
_MISSINGNESS_VARIABLES = (
    "mean_arterial_pressure",
    "heart_rate",
    "systolic_bp",
    "respiratory_rate",
    "oxygen_saturation",
)


@dataclass(frozen=True)
class FeatureDerivation:
    """Auditable derivation contract for one locked predictor."""

    predictor: str
    source_columns: tuple[str, ...]
    temporal_window: str
    transformation: str
    missingness_behavior: str
    requires_information_after_t: bool = False


def feature_derivation_audit() -> tuple[FeatureDerivation, ...]:
    """Return the complete, ordered derivation contract for all locked features."""
    specifications = [
        FeatureDerivation(
            "map_mean_6h",
            _MAP_6H_COLUMNS,
            "t-5 through t (inclusive)",
            "Arithmetic mean of all finite calculable *_value columns",
            "Ignore absent/non-finite values; unavailable if none are finite",
        ),
        FeatureDerivation(
            "mean_arterial_pressure_current",
            ("mean_arterial_pressure_current",),
            "t",
            "Identity",
            "Continuous missing value remains unavailable for fold-local imputation",
        ),
        FeatureDerivation(
            "mean_arterial_pressure_rolling_slope",
            ("mean_arterial_pressure_rolling_slope",),
            "t-11 through t (inclusive)",
            "Existing least-squares slope over calculable hourly *_value entries",
            "Unavailable with fewer than two calculable hourly values",
        ),
    ]
    for predictor in _CURRENT_FEATURES[1:]:
        specifications.append(
            FeatureDerivation(
                predictor,
                (predictor,),
                "t",
                "Identity (shock_index is existing heart_rate/systolic_bp ratio)",
                "Continuous missing value remains unavailable for fold-local imputation",
            )
        )
    for variable in _MISSINGNESS_VARIABLES:
        predictor = f"{variable}_proportion_missing"
        specifications.append(
            FeatureDerivation(
                predictor,
                (predictor,),
                "t-11 through t (inclusive)",
                "Existing 1 - observed_count / 12 summary",
                "Structurally present continuous proportion; absence is unavailable",
            )
        )
    for variable in _MISSINGNESS_VARIABLES:
        predictor = f"{variable}_h0_missing"
        specifications.append(
            FeatureDerivation(
                predictor,
                (predictor,),
                "t",
                "Identity; must be exactly 0 or 1",
                "Unexpected absence or non-binary value is a data-contract failure",
            )
        )
    by_name = {item.predictor: item for item in specifications}
    return tuple(by_name[name] for name in LOCKED_FEATURES)


def _finite_number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def raw_map_mean_6h(row: Mapping[str, Any]) -> float | None:
    """Reproduce the raw mean underlying the existing map_mean_6h benchmark."""
    values = [
        value
        for column in _MAP_6H_COLUMNS
        if (value := _finite_number(row.get(column, ""))) is not None
    ]
    return mean(values) if values else None


def map_mean_6h_benchmark_score(
    row: Mapping[str, Any], center: float = 65.0, scale: float = 10.0
) -> float:
    """Apply the current benchmark's neutral rule and stable sigmoid mapping."""
    value = raw_map_mean_6h(row)
    if value is None:
        return 0.5
    argument = (center - value) / scale
    if argument >= 0:
        return 1.0 / (1.0 + math.exp(-min(argument, 700.0)))
    exp_value = math.exp(max(argument, -700.0))
    return exp_value / (1.0 + exp_value)


def derive_locked_features(row: Mapping[str, Any]) -> dict[str, float | None]:
    """Derive exactly the locked inputs without fitting or reading future fields."""
    output: dict[str, float | None] = {"map_mean_6h": raw_map_mean_6h(row)}
    for predictor in LOCKED_FEATURES[1:13]:
        output[predictor] = _finite_number(row.get(predictor, ""))
    for predictor in LOCKED_FEATURES[13:]:
        value = _finite_number(row.get(predictor, ""))
        if value not in (0.0, 1.0):
            raise ValueError(f"Binary missingness feature violates contract: {predictor}")
        output[predictor] = value
    return output


def bounded_future_map_label(
    future_map: Sequence[float | None],
    *,
    threshold: float,
    consecutive_hours: int,
    missing_as_low: bool,
) -> int:
    """Label one prespecified incomplete-future-MAP bound."""
    if consecutive_hours < 1:
        raise ValueError("consecutive_hours must be at least one")
    run = 0
    for raw_value in future_map:
        value = _finite_number(raw_value)
        is_low = missing_as_low if value is None else value < threshold
        run = run + 1 if is_low else 0
        if run >= consecutive_hours:
            return 1
    return 0


def future_map_label_bounds(
    future_map: Sequence[float | None],
    *,
    threshold: float,
    consecutive_hours: int,
) -> tuple[int, int]:
    """Return missing-as-not-low then missing-as-low labels together."""
    return (
        bounded_future_map_label(
            future_map,
            threshold=threshold,
            consecutive_hours=consecutive_hours,
            missing_as_low=False,
        ),
        bounded_future_map_label(
            future_map,
            threshold=threshold,
            consecutive_hours=consecutive_hours,
            missing_as_low=True,
        ),
    )


def _assignment_order(
    patient_window_counts: Mapping[str, int], seed: int, namespace: str
) -> list[str]:
    def key(patient: str) -> tuple[int, str, str]:
        digest = sha256_bytes(f"{seed}|{namespace}|{patient}".encode())
        return (-patient_window_counts[patient], digest, patient)

    return sorted(patient_window_counts, key=key)


def _balanced_assignments(
    patient_window_counts: Mapping[str, int], folds: int, seed: int, namespace: str
) -> dict[str, int]:
    if folds < 2 or len(patient_window_counts) < folds:
        raise ValueError("Fold assignment requires at least one patient per fold")
    window_load = [0] * folds
    patient_load = [0] * folds
    assignments: dict[str, int] = {}
    for patient in _assignment_order(patient_window_counts, seed, namespace):
        fold_index = min(
            range(folds), key=lambda index: (window_load[index], patient_load[index], index)
        )
        assignments[patient] = fold_index + 1
        window_load[fold_index] += patient_window_counts[patient]
        patient_load[fold_index] += 1
    return assignments


def build_private_fold_manifest(
    patient_window_counts: Mapping[str, int],
    *,
    outer_folds: int = OUTER_FOLDS,
    inner_folds: int = INNER_FOLDS,
    seed: int = PHASE3_SEED,
) -> dict[str, Any]:
    """Create deterministic outcome-blind patient assignments for private storage."""
    counts = {str(patient): int(count) for patient, count in patient_window_counts.items()}
    if not counts or any(not patient or count < 1 for patient, count in counts.items()):
        raise ValueError("Patient IDs and positive window counts are required")
    outer = _balanced_assignments(counts, outer_folds, seed, "outer")
    inner_by_outer: dict[int, dict[str, int]] = {}
    for outer_fold in range(1, outer_folds + 1):
        training_counts = {
            patient: count
            for patient, count in counts.items()
            if outer[patient] != outer_fold
        }
        inner_by_outer[outer_fold] = _balanced_assignments(
            training_counts, inner_folds, seed, f"inner-outer-{outer_fold}"
        )
    assignments = {
        patient: {
            "outer_fold": outer[patient],
            "inner_validation_fold_by_outer_training_fold": {
                str(outer_fold): inner_by_outer[outer_fold][patient]
                for outer_fold in range(1, outer_folds + 1)
                if outer[patient] != outer_fold
            },
        }
        for patient in sorted(counts)
    }
    manifest = {
        "manifest_version": "deepvital-phase3-folds-v1",
        "seed": seed,
        "outer_folds": outer_folds,
        "inner_folds": inner_folds,
        "patient_window_counts": dict(sorted(counts.items())),
        "patient_assignments": assignments,
    }
    validate_private_fold_manifest(manifest)
    return manifest


def validate_private_fold_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Validate assignments and return identifier-free public accounting."""
    assignments = manifest["patient_assignments"]
    counts = manifest["patient_window_counts"]
    if set(assignments) != set(counts):
        raise ValueError("Manifest patient accounting differs from window counts")
    outer_folds = int(manifest["outer_folds"])
    inner_folds = int(manifest["inner_folds"])
    public_outer: dict[str, dict[str, int]] = {}
    for outer_fold in range(1, outer_folds + 1):
        validation = {
            patient
            for patient, value in assignments.items()
            if int(value["outer_fold"]) == outer_fold
        }
        training = set(assignments) - validation
        if training & validation:
            raise ValueError("Patient overlap detected in outer fold")
        if not validation:
            raise ValueError("Empty outer validation fold")
        for patient in training:
            inner = assignments[patient][
                "inner_validation_fold_by_outer_training_fold"
            ]
            value = int(inner[str(outer_fold)])
            if value not in range(1, inner_folds + 1):
                raise ValueError("Invalid inner validation fold")
        public_outer[str(outer_fold)] = {
            "training_patients": len(training),
            "validation_patients": len(validation),
            "training_windows": sum(int(counts[item]) for item in training),
            "validation_windows": sum(int(counts[item]) for item in validation),
            "patient_overlap": 0,
        }
    public = {
        "manifest_version": manifest["manifest_version"],
        "seed": int(manifest["seed"]),
        "outer_folds": outer_folds,
        "inner_folds": inner_folds,
        "number_of_patients": len(assignments),
        "number_of_windows": sum(int(value) for value in counts.values()),
        "outer_fold_accounting": public_outer,
        "all_patients_have_one_outer_fold": True,
        "zero_patient_overlap": True,
    }
    assert_public_metadata(public)
    return public


def fold_manifest_fingerprint(manifest: Mapping[str, Any]) -> str:
    """Fingerprint canonical private manifest bytes without exposing identifiers."""
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return sha256_bytes(encoded)


def write_private_fold_manifest(
    path: Path, manifest: Mapping[str, Any], *, private_root: Path
) -> None:
    """Exclusively write an identifier-bearing manifest under a private root."""
    resolved_path = path.resolve()
    resolved_root = private_root.resolve()
    if resolved_path == resolved_root or resolved_root not in resolved_path.parents:
        raise ValueError("Private manifest must be written below private_root")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")


def assert_reserved_outputs_unused(repository_root: Path) -> None:
    """Abort if any Phase 3 result exists; preregistration is allowed to exist."""
    occupied = [path for path in PHASE3_RESULT_OUTPUTS if (repository_root / path).exists()]
    if occupied:
        labels = ", ".join(str(path) for path in occupied)
        raise FileExistsError(f"Phase 3 result outputs already exist: {labels}")


def assert_registration_matches(
    registration_path: Path, expected_registration: Mapping[str, Any]
) -> dict[str, Any]:
    """Require an existing preregistration to match every frozen analysis input."""
    if not registration_path.is_file():
        raise FileNotFoundError(
            f"Phase 3 protocol registration is required: {registration_path}"
        )
    with registration_path.open(encoding="utf-8") as handle:
        existing = json.load(handle)
    assert_public_metadata(existing)
    mismatches = [
        field
        for field in REGISTRATION_MATCH_FIELDS
        if existing.get(field) != expected_registration.get(field)
    ]
    if mismatches:
        raise ValueError(
            "Phase 3 registration mismatch for: " + ", ".join(mismatches)
        )
    return existing


def validate_registered_source_state(
    *, registered_source_commit: str, current_head: str, working_tree_dirty: bool
) -> None:
    """Reject code that differs from the clean implementation commit registered."""
    if current_head != registered_source_commit:
        raise RuntimeError(
            "Git HEAD does not match registered Phase 3 source_commit"
        )
    if working_tree_dirty:
        raise RuntimeError("Phase 3 formal execution requires a clean Git working tree")


def capture_git_source_state(repository_root: Path) -> tuple[str, bool]:
    """Capture HEAD and tracked/untracked status without touching analysis inputs."""
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return head, bool(status.strip())


def assert_registered_source_state(
    repository_root: Path, registration: Mapping[str, Any]
) -> str:
    """Mechanically enforce registered HEAD and a clean tree before data access."""
    current_head, dirty = capture_git_source_state(repository_root)
    validate_registered_source_state(
        registered_source_commit=str(registration.get("source_commit", "")),
        current_head=current_head,
        working_tree_dirty=dirty,
    )
    return current_head


def fingerprint_outcome_inputs(paths: Mapping[str, Path]) -> dict[str, str]:
    """Fingerprint the four exact private development inputs without exposing rows."""
    if set(paths) != set(OUTCOME_INPUT_NAMES):
        raise ValueError(
            "Outcome input paths must be exactly: " + ", ".join(OUTCOME_INPUT_NAMES)
        )
    return {name: fingerprint_file(paths[name]) for name in OUTCOME_INPUT_NAMES}


def assert_phase3_prerun_ready(
    repository_root: Path, expected_registration: Mapping[str, Any]
) -> dict[str, Any]:
    """Enforce a matching preregistration and unused result paths before a run."""
    assert_reserved_outputs_unused(repository_root)
    return assert_registration_matches(
        repository_root / PHASE3_REGISTRATION_OUTPUT, expected_registration
    )


def open_output_exclusively(path: Path) -> TextIO:
    """Open one output only when absent, preventing silent artifact replacement."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.open("x", encoding="utf-8")


def build_protocol_registration(
    *,
    protocol_path: Path,
    frozen_protocol_git_commit: str,
    canonical_cohort_fingerprint: str,
    private_fold_manifest: Mapping[str, Any],
    source_commit: str,
    configuration_paths: Sequence[Path],
    execution_timestamp: str,
    outcome_input_paths: Mapping[str, Path] | None = None,
) -> dict[str, Any]:
    """Build separate public registration metadata without changing the protocol."""
    datetime.fromisoformat(execution_timestamp.replace("Z", "+00:00"))
    registration = {
        "registration_version": "deepvital-phase3-registration-v1",
        "frozen_protocol_sha256": fingerprint_file(protocol_path),
        "frozen_protocol_git_commit": frozen_protocol_git_commit,
        "canonical_cohort_fingerprint": canonical_cohort_fingerprint,
        "fold_manifest_fingerprint": fold_manifest_fingerprint(private_fold_manifest),
        "source_commit": source_commit,
        "configuration_fingerprint": fingerprint_configuration(configuration_paths),
        "outcome_input_fingerprints": (
            fingerprint_outcome_inputs(outcome_input_paths)
            if outcome_input_paths is not None
            else None
        ),
        "execution_timestamp": execution_timestamp,
    }
    assert_public_metadata(registration)
    return registration


def write_registration_exclusively(path: Path, registration: Mapping[str, Any]) -> None:
    """Write public registration once and reject identifier-bearing metadata."""
    assert_public_metadata(registration)
    with open_output_exclusively(path) as handle:
        json.dump(registration, handle, indent=2, sort_keys=True)
        handle.write("\n")


def audit_as_public_records() -> list[dict[str, Any]]:
    """Represent feature contracts as identifier-free machine-readable records."""
    records = [asdict(item) for item in feature_derivation_audit()]
    for record in records:
        assert_public_metadata(record)
    return records
