#!/usr/bin/env python3
"""Evaluate a frozen model once on patients absent from all development data."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from deepvital.evaluation.confirmatory import evaluate_confirmatory


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument(
        "--dataset-role", choices=["confirmatory-test"], required=True
    )
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--protocol-hash", required=True)
    parser.add_argument("--cohort-fingerprint", required=True)
    parser.add_argument("--frozen-model", type=Path, required=True)
    parser.add_argument("--model-metadata", type=Path, required=True)
    parser.add_argument("--development-manifest", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip()
    report, registry = evaluate_confirmatory(
        dataset=args.dataset,
        dataset_role=args.dataset_role,
        protocol=args.protocol,
        protocol_hash=args.protocol_hash,
        cohort_fingerprint=args.cohort_fingerprint,
        frozen_model=args.frozen_model,
        model_metadata=args.model_metadata,
        development_manifest=args.development_manifest,
        registry=args.registry,
        git_commit=commit or "unavailable",
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.registry.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    args.registry.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"evaluation_kind": report["evaluation_kind"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
