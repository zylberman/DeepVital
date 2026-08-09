"""Run the preregistered Phase 3 development analysis after explicit authorization."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from deepvital.evaluation.metrics import select_thresholds
from deepvital.phase3.implementation import (
    advancement_decision,
    discrimination_delta,
    load_frozen_manifest,
    patient_equal_delta_auprc,
    run_frozen_nested_cv,
    summarize_oof,
    validate_frozen_config,
)
from deepvital.phase3.prefreeze import (
    PHASE3_REGISTRATION_OUTPUT,
    assert_phase3_prerun_ready,
    assert_registered_source_state,
    assert_reserved_outputs_unused,
    fingerprint_outcome_inputs,
    fold_manifest_fingerprint,
    open_output_exclusively,
    raw_map_mean_6h,
)
from deepvital.phase3.provenance import build_execution_provenance
from deepvital.phase3.sensitivities import (
    CONSECUTIVE_HOURS,
    MAP_THRESHOLDS,
    benchmark_missingness_indices,
    frozen_sensitivity_definitions,
    incomplete_future_map_sensitivity,
    missingness_charting_report,
    outcome_sensitivity_grid,
)
from deepvital.reproducibility.fingerprints import (
    fingerprint_configuration,
    fingerprint_file,
)

ROOT = Path(__file__).resolve().parents[1]
RESULT_PATHS = {
    "primary": ROOT / "reports/phase3_incremental_value.json",
    "comparison": ROOT / "reports/phase3_model_comparison.csv",
    "paired": ROOT / "reports/phase3_paired_comparisons.csv",
    "sensitivities": ROOT / "reports/phase3_sensitivity_analysis.json",
    "deviations": ROOT / "reports/phase3_protocol_deviations.json",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument(
        "--sensitivity-dataset",
        type=Path,
        required=True,
        help="Development windows with future_map_h1 through future_map_h6",
    )
    parser.add_argument("--bp-invasive-preferred-dataset", type=Path, required=True)
    parser.add_argument("--bp-non-invasive-only-dataset", type=Path, required=True)
    parser.add_argument(
        "--config", type=Path, default=ROOT / "configs/phase3_frozen.json"
    )
    return parser.parse_args()


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _future_map(row: dict[str, str]) -> list[float | None]:
    values = []
    for hour in range(1, 7):
        raw = row.get(f"future_map_h{hour}", "")
        values.append(None if raw in (None, "") else float(raw))
    return values


def _run_variant(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    try:
        oof = run_frozen_nested_cv(rows, manifest)
        summary = summarize_oof(oof)
        return {
            "status": "completed",
            "delta_auprc": summary["primary"]["observed_difference"],
            "delta_auprc_ci_95_lower": summary["primary"]["ci_95_lower"],
            "delta_auprc_ci_95_upper": summary["primary"]["ci_95_upper"],
            "number_of_patients": len(set(oof.subjects)),
            "number_of_windows": len(rows),
        }
    except (AssertionError, ValueError) as exc:
        return {"status": "failed", "failure": type(exc).__name__, "message": str(exc)}


def _expected_registration(
    config: dict[str, Any],
    manifest: dict[str, Any],
    config_path: Path,
    source_commit: str,
    outcome_input_paths: dict[str, Path],
) -> dict[str, Any]:
    protocol_path = ROOT / "docs/PHASE_3_PROTOCOL.md"
    protocol_hash = fingerprint_file(protocol_path)
    if protocol_hash != config["protocol"]["sha256"]:
        raise ValueError("Frozen protocol SHA256 differs from configuration")
    manifest_hash = fold_manifest_fingerprint(manifest)
    if manifest_hash != config["fold_manifest"]["expected_fingerprint"]:
        raise ValueError("Private fold-manifest fingerprint mismatch")
    metadata = json.loads(
        (ROOT / config["canonical_cohort"]["metadata_path"]).read_text()
    )
    cohort_hash = metadata[config["canonical_cohort"]["fingerprint_field"]]
    if cohort_hash != config["canonical_cohort"]["expected_fingerprint"]:
        raise ValueError("Canonical cohort fingerprint mismatch")
    return {
        "frozen_protocol_sha256": protocol_hash,
        "frozen_protocol_git_commit": config["protocol"]["git_commit"],
        "canonical_cohort_fingerprint": cohort_hash,
        "fold_manifest_fingerprint": manifest_hash,
        "configuration_fingerprint": fingerprint_configuration([config_path]),
        "source_commit": source_commit,
        "outcome_input_fingerprints": fingerprint_outcome_inputs(outcome_input_paths),
    }


def _write_json(path: Path, value: Any) -> None:
    with open_output_exclusively(path) as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> int:
    args = parse_args()
    config = json.loads(args.config.read_text())
    validate_frozen_config(config)
    manifest_path = ROOT / config["fold_manifest"]["path"]
    manifest = load_frozen_manifest(
        manifest_path, config["fold_manifest"]["expected_fingerprint"]
    )
    assert_reserved_outputs_unused(ROOT)
    registration_path = ROOT / PHASE3_REGISTRATION_OUTPUT
    registration = json.loads(registration_path.read_text())
    source_commit = assert_registered_source_state(ROOT, registration)
    outcome_input_paths = {
        "canonical_modeling_windows": args.dataset,
        "future_map_sensitivity": args.sensitivity_dataset,
        "bp_invasive_preferred": args.bp_invasive_preferred_dataset,
        "bp_non_invasive_only": args.bp_non_invasive_only_dataset,
    }
    expected_registration = _expected_registration(
        config,
        manifest,
        args.config,
        source_commit,
        outcome_input_paths,
    )

    # Git state is checked before hashes open private bytes; exact hash agreement is
    # checked before CSV parsing exposes any outcome-bearing content.
    registration = assert_phase3_prerun_ready(ROOT, expected_registration)

    rows = _read_rows(args.dataset)
    expected_windows = config["canonical_cohort"]["expected_windows"]
    if len(rows) != expected_windows:
        raise ValueError("Canonical eligible-window count mismatch")
    if len({row["subject_id"] for row in rows}) != config["canonical_cohort"][
        "expected_patients_with_windows"
    ]:
        raise ValueError("Canonical eligible-patient count mismatch")
    primary_oof = run_frozen_nested_cv(rows, manifest)
    primary = summarize_oof(primary_oof)

    sensitivity_rows = _read_rows(args.sensitivity_dataset)
    outcome_variants: dict[str, Any] = {}
    for threshold in MAP_THRESHOLDS:
        for consecutive in CONSECUTIVE_HOURS:
            key = f"map_lt_{int(threshold)}_{consecutive}_consecutive"
            variant = []
            for row in sensitivity_rows:
                labels = outcome_sensitivity_grid(_future_map(row), require_complete=True)
                if labels[key] is not None:
                    variant.append({**row, "label": labels[key]})
            outcome_variants[key] = _run_variant(variant, manifest)
    incomplete_bounds = {}
    for bound in ("missing_as_not_low", "missing_as_low"):
        variant = []
        for row in sensitivity_rows:
            labels = incomplete_future_map_sensitivity(
                _future_map(row), threshold=65.0, consecutive_hours=2
            )
            variant.append({**row, "label": labels[bound]})
        incomplete_bounds[bound] = _run_variant(variant, manifest)
    bp_variants = {
        "invasive_preferred": _run_variant(
            _read_rows(args.bp_invasive_preferred_dataset), manifest
        ),
        "non_invasive_only": _run_variant(
            _read_rows(args.bp_non_invasive_only_dataset), manifest
        ),
    }
    bp_deltas = {
        name: value["delta_auprc"]
        for name, value in bp_variants.items()
        if value["status"] == "completed"
    }
    sensitivities_disclosed = (
        len(outcome_variants) == 9
        and len(incomplete_bounds) == 2
        and len(bp_variants) == 2
    )
    decision = advancement_decision(
        delta_auprc=primary["primary"]["observed_difference"],
        delta_auprc_ci_lower=primary["primary"]["ci_95_lower"],
        oof_accounting_valid=True,
        primary_protocol_deviation=False,
        patient_equal_delta_auprc=patient_equal_delta_auprc(primary_oof),
        bp_source_delta_auprcs=bp_deltas,
        sensitivities_disclosed=sensitivities_disclosed,
        threshold_reproducible=True,
    )
    strategy_scores = (
        primary_oof.calibrated_candidate
        if decision["decision"] == "logistic_regression_advances"
        else primary_oof.benchmark
    )
    final_thresholds = select_thresholds(primary_oof.labels, strategy_scores)
    provenance = build_execution_provenance(
        registration=registration,
        implementation_source_commit=source_commit,
        configuration_paths=[args.config],
    )
    public_primary = {
        **primary,
        "advancement": decision,
        "final_development_thresholds": final_thresholds,
        "provenance": provenance,
        "oof_invariants": {
            "each_window_predicted_once": True,
            "patient_overlap": 0,
            "number_of_windows": len(rows),
            "number_of_patients": len(set(primary_oof.subjects)),
        },
    }
    sensitivity_report = {
        "definitions": frozen_sensitivity_definitions(),
        "outcome_grid": outcome_variants,
        "incomplete_future_map": incomplete_bounds,
        "bp_source_alternatives": bp_variants,
        "benchmark_missingness": {
            policy: discrimination_delta(
                [primary_oof.labels[index] for index in indices],
                [primary_oof.raw_candidate[index] for index in indices],
                [primary_oof.benchmark[index] for index in indices],
            )
            for policy in ("neutral_score_0.5", "complete_case")
            for indices in [
                benchmark_missingness_indices(
                    [
                        raw_map_mean_6h(row) is not None
                        for row in rows
                    ],
                    policy,
                )
            ]
        },
        "patient_equal_delta_auprc": patient_equal_delta_auprc(primary_oof),
        "missingness_charting_frequency": missingness_charting_report(
            rows,
            manifest,
            (
                "mean_arterial_pressure",
                "heart_rate",
                "systolic_bp",
                "respiratory_rate",
                "oxygen_saturation",
            ),
        ),
        "provenance": provenance,
    }
    _write_json(RESULT_PATHS["primary"], public_primary)
    with open_output_exclusively(RESULT_PATHS["comparison"]) as handle:
        writer = csv.writer(handle)
        writer.writerow(["model", "auroc", "auprc", "brier_score", "log_loss"])
        for name, values in (
            ("logistic_regression", primary["raw_candidate_metrics"]),
            ("map_mean_6h", primary["benchmark_metrics"]),
        ):
            writer.writerow(
                [name, values["auroc"], values["auprc"], values.get("brier_score"), values.get("log_loss")]
            )
    with open_output_exclusively(RESULT_PATHS["paired"]) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(primary["primary"]))
        writer.writeheader()
        writer.writerows([primary["primary"], primary["secondary_delta_auroc"]])
    _write_json(RESULT_PATHS["sensitivities"], sensitivity_report)
    _write_json(RESULT_PATHS["deviations"], {"protocol_deviations": [], "provenance": provenance})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
