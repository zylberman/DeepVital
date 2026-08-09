"""Register a frozen Phase 3 protocol separately from the protocol file."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from deepvital.phase3.prefreeze import (
    assert_reserved_outputs_unused,
    build_protocol_registration,
    write_registration_exclusively,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=Path("docs/PHASE_3_PROTOCOL.md"))
    parser.add_argument("--protocol-git-commit", required=True)
    parser.add_argument("--canonical-cohort-fingerprint", required=True)
    parser.add_argument("--private-fold-manifest", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--configuration", type=Path, action="append", required=True)
    parser.add_argument("--canonical-modeling-windows", type=Path, required=True)
    parser.add_argument("--future-map-sensitivity-input", type=Path, required=True)
    parser.add_argument("--bp-invasive-preferred-input", type=Path, required=True)
    parser.add_argument("--bp-non-invasive-only-input", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/phase3_protocol_registration.json"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repository_root = Path.cwd()
    assert_reserved_outputs_unused(repository_root)
    with args.private_fold_manifest.open(encoding="utf-8") as handle:
        private_manifest = json.load(handle)
    registration = build_protocol_registration(
        protocol_path=args.protocol,
        frozen_protocol_git_commit=args.protocol_git_commit,
        canonical_cohort_fingerprint=args.canonical_cohort_fingerprint,
        private_fold_manifest=private_manifest,
        source_commit=args.source_commit,
        configuration_paths=args.configuration,
        execution_timestamp=datetime.now(UTC).isoformat(),
        outcome_input_paths={
            "canonical_modeling_windows": args.canonical_modeling_windows,
            "future_map_sensitivity": args.future_map_sensitivity_input,
            "bp_invasive_preferred": args.bp_invasive_preferred_input,
            "bp_non_invasive_only": args.bp_non_invasive_only_input,
        },
    )
    write_registration_exclusively(args.output, registration)
    print(json.dumps(registration, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
