"""Shared private-data helpers for Phase 2 commands."""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def phase_1b_gate() -> dict:
    """Reconcile private dataset, manifest, and aggregate Phase 1B reports."""
    dataset = ROOT / "data/processed/modeling_windows.csv"
    manifest_path = ROOT / "data/processed/split_manifest.json"
    quality = read_json(ROOT / "reports/phase_1b_quality.json")
    summary = read_json(ROOT / "reports/split_summary.json")
    manifest = read_json(manifest_path)
    assignments = manifest.get("patient_assignments", manifest.get("assignments", manifest))
    seen: dict[str, str] = {}
    counts = Counter()
    positives = Counter()
    with dataset.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"subject_id", "hadm_id", "stay_id", "prediction_time", "split", "label"}
        assert required <= set(reader.fieldnames or [])
        assert not any("future" in name.lower() for name in reader.fieldnames or [])
        for row in reader:
            subject, split = row["subject_id"], row["split"]
            assert split in {"train", "validation", "test"}
            assert subject not in seen or seen[subject] == split
            seen[subject] = split
            assigned = assignments.get(subject)
            if isinstance(assigned, dict):
                assigned = assigned.get("split")
            assert assigned == split
            counts[split] += 1
            positives[split] += int(row["label"])
    report_splits = summary.get("splits", summary)
    for split in counts:
        assert counts[split] == report_splits[split].get("window_count", report_splits[split].get("windows"))
        assert positives[split] == report_splits[split].get("positive_window_count", report_splits[split].get("positive_windows"))
    q = quality.get("windowing", quality.get("counts", quality))
    candidate = q.get("candidate_windows", quality.get("candidate_windows"))
    created = q.get("windows_created", quality.get("windows_created"))
    excluded = q.get("windows_excluded_incomplete_future_map", quality.get("windows_excluded_incomplete_future_map"))
    assert candidate == created + excluded
    return {
        "status": "passed",
        "assigned_patients": len(assignments),
        "patients_with_windows": len(seen),
        "windows": sum(counts.values()),
        "split_window_counts": dict(counts),
        "zero_patient_overlap": True,
        "manifest_matches_dataset": True,
        "candidate_accounting": True,
        "temporal_contract": "predictors through t; outcome t+1 through t+6",
    }


def write_metrics(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def patient_window_distribution(rows: list[dict[str, str]], split: str) -> list[dict]:
    counts = Counter(row["subject_id"] for row in rows)
    values = sorted(counts.values())
    quantile = lambda p: values[round((len(values) - 1) * p)]
    return [
        {"split": split, "statistic": name, "value": value}
        for name, value in (
            ("patient_count", len(values)),
            ("minimum", min(values)),
            ("p25", quantile(0.25)),
            ("median", quantile(0.5)),
            ("p75", quantile(0.75)),
            ("maximum", max(values)),
        )
    ]
