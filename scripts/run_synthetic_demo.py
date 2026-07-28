#!/usr/bin/env python3
"""Run an isolated end-to-end DeepVital demonstration on synthetic data."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from deepvital.evaluation.metrics import evaluate_probabilities, select_thresholds
from scripts.generate_synthetic_demo import (
    VITAL_COLUMNS,
    WARNING,
    generate_dataset,
)

INPUT_HOURS = 12
LABEL_HORIZON_HOURS = 6
MAP_THRESHOLD = 65.0
CONSECUTIVE_LOW_MAP_HOURS = 2
SPLITS = ("train", "validation", "holdout")


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _validate_demo_paths(output_dir: Path, input_path: Path | None) -> None:
    protected = (
        PROJECT_ROOT / "reports",
        PROJECT_ROOT / "models/baselines",
        PROJECT_ROOT / "data/processed",
    )
    if any(_is_within(output_dir, parent) for parent in protected):
        raise ValueError("Synthetic demo output must not use a protected Phase 2 path")
    if input_path is not None and _is_within(input_path, PROJECT_ROOT / "data"):
        raise ValueError("Synthetic demo input must not read from the clinical data tree")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"subject_id", "stay_id", "charttime", *VITAL_COLUMNS}
    if not rows or not required <= set(rows[0]):
        raise ValueError("Synthetic input does not match the expected schema")
    return rows


def _number(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def hourly_representation(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Validate one artificial row per patient/hour and return chronological rows."""
    ordered = sorted(
        rows,
        key=lambda row: (
            row["subject_id"],
            row["stay_id"],
            datetime.fromisoformat(row["charttime"]),
        ),
    )
    keys = [(row["subject_id"], row["stay_id"], row["charttime"]) for row in ordered]
    if len(keys) != len(set(keys)):
        raise ValueError("Synthetic input contains duplicate patient-hour rows")
    return ordered


def _future_label(future_maps: list[float]) -> int:
    run = 0
    for value in future_maps:
        run = run + 1 if value < MAP_THRESHOLD else 0
        if run >= CONSECUTIVE_LOW_MAP_HOURS:
            return 1
    return 0


def _summaries(history: list[dict[str, str]]) -> dict[str, float]:
    features: dict[str, float] = {}
    for variable in VITAL_COLUMNS:
        values = [_number(row[variable]) for row in history]
        observed = [value for value in values if math.isfinite(value)]
        features[f"{variable}_current"] = values[-1]
        features[f"{variable}_mean_12h"] = (
            mean(observed) if observed else math.nan
        )
        features[f"{variable}_min_12h"] = min(observed) if observed else math.nan
        features[f"{variable}_max_12h"] = max(observed) if observed else math.nan
        features[f"{variable}_missing_fraction"] = 1 - len(observed) / INPUT_HOURS
        features[f"{variable}_slope_12h"] = (
            (observed[-1] - observed[0]) / max(len(observed) - 1, 1)
            if len(observed) >= 2
            else math.nan
        )
    return features


def build_windows(rows: list[dict[str, str]]) -> tuple[list[dict], list[str]]:
    """Create 12-hour predictors and labels from the following six observed MAP hours."""
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in hourly_representation(rows):
        grouped[(row["subject_id"], row["stay_id"])].append(row)

    windows: list[dict] = []
    feature_names: list[str] = []
    for (subject_id, stay_id), stay_rows in sorted(grouped.items()):
        for index in range(INPUT_HOURS - 1, len(stay_rows) - LABEL_HORIZON_HOURS):
            history = stay_rows[index - INPUT_HOURS + 1 : index + 1]
            future = stay_rows[index + 1 : index + 1 + LABEL_HORIZON_HOURS]
            future_maps = [_number(row["mean_arterial_pressure"]) for row in future]
            if not all(math.isfinite(value) for value in future_maps):
                continue
            features = _summaries(history)
            feature_names = list(features)
            windows.append(
                {
                    "subject_id": subject_id,
                    "stay_id": stay_id,
                    "window_start": history[0]["charttime"],
                    "prediction_time": history[-1]["charttime"],
                    "input_hours": INPUT_HOURS,
                    "label_horizon_hours": LABEL_HORIZON_HOURS,
                    **features,
                    "label": _future_label(future_maps),
                }
            )
    if not windows:
        raise ValueError("Synthetic data produced no complete modeling windows")
    return windows, feature_names


def assign_splits(windows: list[dict], seed: int) -> dict[str, str]:
    """Stratify fictitious patients by whether any of their windows is positive."""
    patient_positive: dict[str, bool] = defaultdict(bool)
    for row in windows:
        patient_positive[row["subject_id"]] |= bool(row["label"])

    groups = {
        positive: sorted(
            patient
            for patient, has_event in patient_positive.items()
            if has_event is positive
        )
        for positive in (False, True)
    }
    assignments: dict[str, str] = {}
    rng = random.Random(seed)
    for patients in groups.values():
        rng.shuffle(patients)
        count = len(patients)
        train_end = max(1, round(0.6 * count))
        validation_end = min(count - 1, train_end + max(1, round(0.2 * count)))
        for index, patient in enumerate(patients):
            split = (
                "train"
                if index < train_end
                else "validation"
                if index < validation_end
                else "holdout"
            )
            assignments[patient] = split
    if set(assignments.values()) != set(SPLITS):
        raise ValueError("Synthetic cohort is too small to populate all three splits")
    return assignments


def _matrix(
    windows: list[dict],
    feature_names: list[str],
    split: str,
) -> tuple[list[list[float]], list[int]]:
    selected = [row for row in windows if row["split"] == split]
    return (
        [[float(row[name]) for name in feature_names] for row in selected],
        [int(row["label"]) for row in selected],
    )


def _json_metric(y: list[int], p: list[float], threshold: float) -> dict:
    result = evaluate_probabilities(y, p, threshold)
    return {
        key: (None if isinstance(value, float) and math.isnan(value) else value)
        for key, value in result.items()
    }


def fit_and_evaluate(
    windows: list[dict],
    feature_names: list[str],
    seed: int,
) -> tuple[dict, dict, dict]:
    """Select between two demo models on validation and score synthetic holdout once."""
    from sklearn.dummy import DummyClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    x_train, y_train = _matrix(windows, feature_names, "train")
    x_validation, y_validation = _matrix(windows, feature_names, "validation")
    x_holdout, y_holdout = _matrix(windows, feature_names, "holdout")
    models = {
        "dummy_prevalence": DummyClassifier(strategy="prior"),
        "logistic_regression": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=1000,
                        random_state=seed,
                    ),
                ),
            ]
        ),
    }

    validation: dict[str, dict] = {}
    fitted = {}
    for name, model in models.items():
        model.fit(x_train, y_train)
        probabilities = model.predict_proba(x_validation)[:, 1].tolist()
        threshold = select_thresholds(y_validation, probabilities)["youden"]
        validation[name] = _json_metric(y_validation, probabilities, threshold)
        fitted[name] = model

    selected_model = min(
        validation,
        key=lambda name: (
            -float(validation[name]["auprc"]),
            float(validation[name]["brier_score"]),
            name,
        ),
    )
    locked_threshold = float(validation[selected_model]["threshold"])
    holdout_probabilities = fitted[selected_model].predict_proba(x_holdout)[:, 1].tolist()
    holdout = _json_metric(y_holdout, holdout_probabilities, locked_threshold)
    selection = {
        "selected_model": selected_model,
        "selection_partition": "synthetic_validation",
        "selection_rule": "highest validation AUPRC, then lowest Brier score, then name",
        "threshold_source": "synthetic_validation_only",
        "locked_threshold": locked_threshold,
    }
    return validation, holdout, selection


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_demo(
    output_dir: Path,
    patients: int = 30,
    hours: int = 48,
    seed: int = 20260726,
    input_path: Path | None = None,
) -> dict:
    """Run the synthetic workflow without reading or writing Phase 2 artifacts."""
    _validate_demo_paths(output_dir, input_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "raw_vitals.csv"
    if input_path is None:
        rows = generate_dataset(raw_path, patients=patients, hours=hours, seed=seed)
    else:
        rows = read_rows(input_path)
        _write_csv(raw_path, rows, list(rows[0]))

    hourly = hourly_representation(rows)
    _write_csv(output_dir / "hourly_vitals.csv", hourly, list(hourly[0]))
    windows, feature_names = build_windows(hourly)
    assignments = assign_splits(windows, seed)
    for row in windows:
        row["split"] = assignments[row["subject_id"]]
    _write_csv(output_dir / "windows.csv", windows, list(windows[0]))

    split_summary = {
        split: {
            "patients": len(
                {row["subject_id"] for row in windows if row["split"] == split}
            ),
            "windows": sum(row["split"] == split for row in windows),
            "positive_windows": sum(
                row["split"] == split and row["label"] == 1 for row in windows
            ),
        }
        for split in SPLITS
    }
    validation, holdout, selection = fit_and_evaluate(windows, feature_names, seed)
    summary = {
        "warning": WARNING,
        "data_source": "fully_synthetic",
        "seed": seed,
        "patients": len(assignments),
        "windows": len(windows),
        "positive_windows": sum(row["label"] for row in windows),
        "negative_windows": sum(not row["label"] for row in windows),
        "input_window_hours": INPUT_HOURS,
        "label_horizon_hours": LABEL_HORIZON_HOURS,
        "patient_overlap": 0,
        **selection,
    }
    _write_json(output_dir / "split_summary.json", split_summary)
    _write_json(output_dir / "validation_metrics.json", validation)
    _write_json(output_dir / "holdout_metrics.json", holdout)
    _write_json(output_dir / "demo_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/synthetic_demo"),
    )
    parser.add_argument("--input", type=Path)
    parser.add_argument("--patients", type=int, default=30)
    parser.add_argument("--hours", type=int, default=48)
    parser.add_argument("--seed", type=int, default=20260726)
    args = parser.parse_args()
    summary = run_demo(
        args.output_dir,
        patients=args.patients,
        hours=args.hours,
        seed=args.seed,
        input_path=args.input,
    )
    print(WARNING)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
