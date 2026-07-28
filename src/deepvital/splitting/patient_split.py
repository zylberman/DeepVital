"""Keep every correlated window from a patient in one deterministic split.

A window-level split would evaluate on observations closely related to windows
already seen during training.
"""

from __future__ import annotations

import random
from typing import Any


def assign_patient_splits(
    subject_ids: set[str], proportions: dict[str, float], seed: int
) -> dict[str, str]:
    if set(proportions) != {"train", "validation", "test"}:
        raise ValueError("Expected train, validation, and test proportions")
    if abs(sum(proportions.values()) - 1.0) > 1e-9:
        raise ValueError("Split proportions must sum to one")
    patients = sorted(subject_ids)
    random.Random(seed).shuffle(patients)
    train_end = round(len(patients) * proportions["train"])
    validation_end = train_end + round(len(patients) * proportions["validation"])
    assignments = {}
    for index, subject_id in enumerate(patients):
        if index < train_end:
            split = "train"
        elif index < validation_end:
            split = "validation"
        else:
            split = "test"
        assignments[subject_id] = split
    return assignments


def assert_patient_disjoint(rows: list[dict[str, Any]]) -> None:
    seen: dict[str, str] = {}
    for row in rows:
        subject_id = row["subject_id"]
        split = row["split"]
        previous = seen.setdefault(subject_id, split)
        if previous != split:
            raise ValueError("Patient overlap detected across splits")


def aggregate_split_summary(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for split in ("train", "validation", "test"):
        selected = [row for row in rows if row["split"] == split]
        patients = {row["subject_id"] for row in selected}
        admissions = {row["hadm_id"] for row in selected}
        stays = {row["stay_id"] for row in selected}
        positives = sum(int(row["label"]) for row in selected)
        output[split] = {
            "patients": len(patients),
            "hospital_admissions": len(admissions),
            "icu_stays": len(stays),
            "windows": len(selected),
            "positive_windows": positives,
            "negative_windows": len(selected) - positives,
            "event_prevalence": positives / len(selected) if selected else None,
        }
    return output
