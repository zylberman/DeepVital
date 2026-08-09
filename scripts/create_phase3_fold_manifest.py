"""Create the private Phase 3 fold manifest without reading outcomes."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from deepvital.phase3.prefreeze import (
    build_private_fold_manifest,
    fold_manifest_fingerprint,
    validate_private_fold_manifest,
    write_private_fold_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--windows", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/phase3/fold_manifest.json"),
    )
    parser.add_argument(
        "--private-root", type=Path, default=Path("data/processed")
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    counts: Counter[str] = Counter()
    with args.windows.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "subject_id" not in reader.fieldnames:
            raise ValueError("Window input must contain subject_id")
        for row in reader:
            counts[row["subject_id"]] += 1
    manifest = build_private_fold_manifest(counts)
    write_private_fold_manifest(args.output, manifest, private_root=args.private_root)
    public = validate_private_fold_manifest(manifest)
    print(
        json.dumps(
            {
                "fold_manifest_fingerprint": fold_manifest_fingerprint(manifest),
                "public_accounting": public,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
