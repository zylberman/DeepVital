from __future__ import annotations

import math

import numpy as np
import pytest

import deepvital.phase3.posthoc_single_predictor as posthoc
from deepvital.phase3.prefreeze import (
    INNER_FOLDS,
    PHASE3_SEED,
    build_private_fold_manifest,
)


def synthetic_rows() -> tuple[list[dict[str, object]], dict]:
    """Create synthetic patient-grouped rows with both classes per patient."""
    patient_counts = {
        f"synthetic-{index:02d}": 2
        for index in range(15)
    }
    manifest = build_private_fold_manifest(patient_counts)

    rows: list[dict[str, object]] = []
    for patient_index, subject_id in enumerate(patient_counts):
        for label in (0, 1):
            baseline = 75.0 - 12.0 * label + 0.1 * patient_index
            row: dict[str, object] = {
                "subject_id": subject_id,
                "label": label,
                "mean_arterial_pressure_current": baseline + 0.5,
            }

            for offset, tag in enumerate(
                ("hm5", "hm4", "hm3", "hm2", "hm1", "h0")
            ):
                row[f"mean_arterial_pressure_{tag}_value"] = (
                    baseline + 0.1 * offset
                )

            rows.append(row)

    return rows, manifest


def test_allowed_predictors_are_exactly_the_requested_models() -> None:
    assert posthoc.ALLOWED_SINGLE_PREDICTORS == (
        "map_mean_6h",
        "mean_arterial_pressure_current",
    )


@pytest.mark.parametrize(
    "predictor",
    posthoc.ALLOWED_SINGLE_PREDICTORS,
)
def test_single_predictor_pipeline_matches_frozen_model_settings(
    predictor: str,
) -> None:
    pipeline = posthoc.build_single_predictor_candidate(
        predictor,
        c_value=0.1,
    )

    preprocessing = pipeline.named_steps["preprocessing"]
    candidate = pipeline.named_steps["candidate"]

    assert preprocessing.named_steps["median_imputer"].strategy == "median"
    assert preprocessing.named_steps["standard_scaler"] is not None
    assert candidate.C == 0.1
    assert candidate.penalty == "l2"
    assert candidate.solver == "lbfgs"
    assert candidate.class_weight == "balanced"
    assert candidate.max_iter == 1000
    assert candidate.random_state == PHASE3_SEED


@pytest.mark.parametrize(
    "predictor",
    posthoc.ALLOWED_SINGLE_PREDICTORS,
)
def test_nested_cv_produces_one_outer_prediction_per_window(
    predictor: str,
) -> None:
    rows, manifest = synthetic_rows()

    result = posthoc.run_single_predictor_nested_cv(
        rows,
        manifest,
        predictor,
    )
    summary = posthoc.summarize_single_predictor_oof(result)

    assert result.predictor == predictor
    assert len(result.labels) == len(rows)
    assert len(result.raw_probabilities) == len(rows)
    assert len(result.calibrated_probabilities) == len(rows)
    assert len(result.outer_folds) == len(rows)
    assert set(result.outer_folds) == {1, 2, 3, 4, 5}
    assert all(math.isfinite(value) for value in result.raw_probabilities)
    assert all(
        math.isfinite(value)
        for value in result.calibrated_probabilities
    )

    assert summary["evaluation_design"] == (
        "patient-grouped nested cross-validation internal validation"
    )
    assert summary["predictor"] == predictor
    assert len(summary["folds"]) == 5

    for fold in summary["folds"]:
        assert fold["patient_overlap"] == 0
        assert fold["outer_validation_patients"] == 3
        assert fold["outer_validation_windows"] == 6
        assert math.isfinite(fold["raw_auprc"])
        assert math.isfinite(fold["calibrated_auprc"])

    pooled = summary["pooled"]
    assert math.isfinite(pooled["raw_metrics"]["auprc"])
    assert math.isfinite(pooled["calibrated_metrics"]["auprc"])
    assert pooled["calibrated_minus_raw_auprc"] == pytest.approx(
        pooled["calibrated_metrics"]["auprc"]
        - pooled["raw_metrics"]["auprc"]
    )


def test_nested_cv_is_reproducible_with_fixed_manifest() -> None:
    rows, manifest = synthetic_rows()

    first = posthoc.run_single_predictor_nested_cv(
        rows,
        manifest,
        "map_mean_6h",
    )
    second = posthoc.run_single_predictor_nested_cv(
        rows,
        manifest,
        "map_mean_6h",
    )

    assert first.raw_probabilities == second.raw_probabilities
    assert (
        first.calibrated_probabilities
        == second.calibrated_probabilities
    )
    assert first.outer_folds == second.outer_folds
    assert first.fold_records == second.fold_records


def test_outer_validation_rows_are_never_used_for_model_fitting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows, manifest = synthetic_rows()
    fitted_value_sets: list[set[float]] = []

    class TrackingModel:
        def fit(
            self,
            x: np.ndarray,
            _y: np.ndarray,
        ) -> TrackingModel:
            values = np.asarray(x, dtype=float)[:, 0]
            fitted_value_sets.append(set(values.tolist()))
            return self

        def predict_proba(self, x: np.ndarray) -> np.ndarray:
            values = np.asarray(x, dtype=float)[:, 0]
            probabilities = 1.0 / (
                1.0 + np.exp((values - 70.0) / 5.0)
            )
            return np.column_stack(
                (1.0 - probabilities, probabilities)
            )

    monkeypatch.setattr(
        posthoc,
        "build_single_predictor_candidate",
        lambda _predictor, _c_value: TrackingModel(),
    )

    result = posthoc.run_single_predictor_nested_cv(
        rows,
        manifest,
        "map_mean_6h",
    )

    fits_per_outer_fold = (
        len(posthoc.C_GRID) * INNER_FOLDS + 1
    )
    assert len(fitted_value_sets) == 5 * fits_per_outer_fold

    matrix = posthoc.single_predictor_matrix(
        rows,
        "map_mean_6h",
    )
    assignments = manifest["patient_assignments"]

    for outer_fold in range(1, 6):
        validation_values = {
            matrix[index][0]
            for index, row in enumerate(rows)
            if int(
                assignments[str(row["subject_id"])]["outer_fold"]
            )
            == outer_fold
        }
        start = (outer_fold - 1) * fits_per_outer_fold
        stop = start + fits_per_outer_fold

        for training_values in fitted_value_sets[start:stop]:
            assert validation_values.isdisjoint(training_values)

    assert len(result.fold_records) == 5


def test_unsupported_predictor_is_rejected() -> None:
    rows, manifest = synthetic_rows()

    with pytest.raises(ValueError, match="Unsupported single predictor"):
        posthoc.run_single_predictor_nested_cv(
            rows,
            manifest,
            "heart_rate_current",
        )
