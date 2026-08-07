#!/usr/bin/env python3
"""Build the administrative-bound canonical Phase 1B cohort and public metadata."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from deepvital.cohort.hourly_dataset import build_hourly_dataset
from deepvital.reproducibility.fingerprints import (
    assert_public_metadata,
    fingerprint_configuration,
    fingerprint_file,
)
from deepvital.windows.builder import build_modeling_dataset


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def capture_source_state(root: Path = ROOT) -> dict[str, str | bool]:
    """Capture source provenance before the cohort command writes any output."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    commit = result.stdout.strip() if result.returncode == 0 else "unavailable"
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "source_code_commit": commit,
        "working_tree_dirty_before_run": status.returncode != 0
        or bool(status.stdout.strip()),
    }


def require_clean_worktree(source_state: dict[str, str | bool]) -> None:
    """Abort strict publication builds before any output when source is dirty."""
    if source_state["working_tree_dirty_before_run"]:
        raise RuntimeError(
            "Strict canonical generation requires a clean working tree before run"
        )


def build_metadata(
    canonical_input: Path,
    windows_output: Path,
    report_dir: Path,
    config_paths: list[Path],
    generation_timestamp: str,
    source_state: dict[str, str | bool],
) -> dict:
    """Create aggregate-only metadata for an already completed canonical build."""
    hourly = _read(report_dir / "hourly_quality.json")
    labels = _read(report_dir / "label_distribution.json")
    splits = _read(report_dir / "split_summary.json")
    metadata = {
        "dataset_name": "deepvital_mimic_fhir_demo_canonical",
        "dataset_version": "phase1b-canonical-v1",
        "cohort_definition_version": "administrative-icu-bounds-v1",
        "evaluation_role": "development",
        "confirmatory_test": False,
        **source_state,
        "configuration_hash": fingerprint_configuration(config_paths),
        "input_fingerprint": fingerprint_file(canonical_input),
        "output_fingerprint": fingerprint_file(windows_output),
        "generation_timestamp": generation_timestamp,
        "number_of_patients": hourly["entities"]["patients"],
        "number_of_admissions": hourly["entities"]["hospital_admissions"],
        "number_of_icu_stays": hourly["entities"]["icu_stays"],
        "number_of_windows": labels["total"],
        "number_of_positive_windows": labels["positive"],
        "prevalence": labels["event_prevalence"],
        "split_seed": splits["seed"],
        "confirmatory_test_status": "confirmatory_test_pending",
    }
    assert_public_metadata(metadata)
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical-input", type=Path, required=True)
    parser.add_argument("--fhir-dir", type=Path, required=True)
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "data/processed/canonical_v1"
    )
    parser.add_argument(
        "--report-dir", type=Path, default=ROOT / "reports/canonical_v1"
    )
    parser.add_argument(
        "--metadata-output",
        type=Path,
        default=ROOT / "reports/canonical_cohort_metadata.json",
    )
    parser.add_argument(
        "--require-clean-worktree",
        action="store_true",
        help="Abort before writing outputs unless the source worktree is clean.",
    )
    args = parser.parse_args()
    source_state = capture_source_state()
    if args.require_clean_worktree:
        require_clean_worktree(source_state)
    generation_timestamp = datetime.now(timezone.utc).isoformat()
    config_paths = [
        ROOT / "configs/hourly_aggregation.yaml",
        ROOT / "configs/missingness.yaml",
        ROOT / "configs/windowing.yaml",
        ROOT / "configs/labeling.yaml",
        ROOT / "configs/splitting.yaml",
    ]
    aggregation, missingness, windowing, labeling, splitting = map(_read, config_paths)
    hourly_output = args.output_dir / "hourly_vitals.csv"
    windows_output = args.output_dir / "modeling_windows.csv"
    build_hourly_dataset(
        args.canonical_input,
        args.fhir_dir,
        hourly_output,
        args.report_dir / "hourly_quality.json",
        aggregation,
        missingness,
    )
    build_modeling_dataset(
        hourly_output,
        windows_output,
        args.output_dir / "split_manifest.json",
        args.report_dir,
        aggregation["variables"],
        missingness,
        windowing,
        labeling,
        splitting,
    )
    metadata = build_metadata(
        args.canonical_input,
        windows_output,
        args.report_dir,
        config_paths,
        generation_timestamp,
        source_state,
    )
    args.metadata_output.parent.mkdir(parents=True, exist_ok=True)
    args.metadata_output.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(metadata, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
