#!/usr/bin/env python3
"""Build hourly ICU data, 12-hour windows, and future hypotension labels."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from deepvital.cohort.dataset import build_phase_1b_dataset  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical-input", required=True, type=Path)
    parser.add_argument("--hourly-output", required=True, type=Path)
    parser.add_argument("--windows-output", required=True, type=Path)
    parser.add_argument("--quality-report", required=True, type=Path)
    parser.add_argument(
        "--config", type=Path, default=PROJECT_ROOT / "configs/cohort.yaml"
    )
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    report = build_phase_1b_dataset(
        args.canonical_input,
        args.hourly_output,
        args.windows_output,
        args.quality_report,
        config,
    )
    counts = report["counts"]
    print(
        f"Phase 1B complete: {counts.get('hourly_rows', 0)} hourly rows, "
        f"{counts.get('windows_created', 0)} windows, "
        f"{counts.get('positive_windows', 0)} positive labels."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
