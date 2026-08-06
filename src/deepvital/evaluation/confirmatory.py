"""Inference-only controls for a future confirmatory patient cohort."""

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from deepvital.reproducibility.fingerprints import fingerprint_file

from .metrics import evaluate_probabilities


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _development_patients(path: Path) -> set[str]:
    content = _read_json(path)
    assignments = content.get("patient_assignments", content.get("assignments", {}))
    if not isinstance(assignments, dict):
        raise TypeError("Development manifest has no patient assignment mapping")
    return {str(patient) for patient in assignments}


def evaluate_confirmatory(
    *,
    dataset: Path,
    dataset_role: str,
    protocol: Path,
    protocol_hash: str,
    cohort_fingerprint: str,
    frozen_model: Path,
    model_metadata: Path,
    development_manifest: Path,
    registry: Path,
    git_commit: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Evaluate one frozen model without training, selection, or threshold changes."""
    if dataset_role != "confirmatory-test":
        raise ValueError("dataset-role must be confirmatory-test")
    actual_protocol_hash = fingerprint_file(protocol)
    actual_cohort_hash = fingerprint_file(dataset)
    actual_model_hash = fingerprint_file(frozen_model)
    actual_model_metadata_hash = fingerprint_file(model_metadata)
    if actual_protocol_hash != protocol_hash:
        raise ValueError("Protocol hash does not match the frozen protocol")
    if actual_cohort_hash != cohort_fingerprint:
        raise ValueError("Cohort fingerprint does not match the supplied dataset")
    metadata = _read_json(model_metadata)
    if metadata.get("frozen") is not True:
        raise ValueError("Confirmatory evaluation requires frozen model metadata")
    threshold = metadata.get("threshold")
    features = metadata.get("feature_names")
    if not isinstance(threshold, (int, float)) or not isinstance(features, list):
        raise TypeError("Frozen threshold and feature names are required")

    with dataset.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {"subject_id", "label", *features}
    if not rows or not required <= set(rows[0]):
        raise ValueError("Confirmatory dataset does not match frozen model schema")
    confirmatory_patients = {row["subject_id"] for row in rows}
    overlap = confirmatory_patients & _development_patients(development_manifest)
    if overlap:
        raise ValueError("Confirmatory cohort contains development patients")

    signature = {
        "protocol_hash": actual_protocol_hash,
        "cohort_fingerprint": actual_cohort_hash,
        "model_hash": actual_model_hash,
        "model_metadata_hash": actual_model_metadata_hash,
        "threshold": float(threshold),
    }
    previous = _read_json(registry) if registry.exists() else None
    if previous is not None:
        previous_signature = {key: previous.get(key) for key in signature}
        if previous_signature != signature:
            raise ValueError("Consumed confirmatory test rejects changed frozen inputs")
        evaluation_kind = "technical_reproduction"
        reproduction_count = int(previous.get("technical_reproduction_count", 0)) + 1
        first_timestamp = previous["evaluation_timestamp"]
    else:
        evaluation_kind = "first_confirmatory_evaluation"
        reproduction_count = 0
        first_timestamp = datetime.now(timezone.utc).isoformat()

    import joblib

    model = joblib.load(frozen_model)
    matrix = [
        [float(row[name]) if row[name] != "" else math.nan for name in features]
        for row in rows
    ]
    labels = [int(row["label"]) for row in rows]
    scores = [float(value) for value in model.predict_proba(matrix)[:, 1]]
    report = {
        "evaluation_name": "confirmatory_test",
        "evaluation_role": "confirmatory_test",
        "evaluation_kind": evaluation_kind,
        "patients": len(confirmatory_patients),
        "windows": len(rows),
        "metrics": evaluate_probabilities(labels, scores, float(threshold)),
        **signature,
    }
    registry_value = {
        "confirmatory_test_consumed": True,
        "evaluation_timestamp": first_timestamp,
        "last_reproduction_timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit,
        "technical_reproduction_count": reproduction_count,
        **signature,
    }
    return report, registry_value
