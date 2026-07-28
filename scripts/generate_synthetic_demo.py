#!/usr/bin/env python3
"""Generate fictitious hourly vital signs for the public DeepVital demo."""

from __future__ import annotations

import argparse
import csv
import math
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

WARNING = (
    "Synthetic data are intended only for software demonstration and do not "
    "represent a clinically valid population."
)

VITAL_COLUMNS = (
    "heart_rate",
    "respiratory_rate",
    "systolic_bp",
    "diastolic_bp",
    "mean_arterial_pressure",
    "oxygen_saturation",
    "temperature",
    "oxygen_flow",
)

FIELDNAMES = (
    "subject_id",
    "stay_id",
    "charttime",
    *VITAL_COLUMNS,
)

PLAUSIBLE_RANGES = {
    "heart_rate": (30.0, 220.0),
    "respiratory_rate": (6.0, 50.0),
    "systolic_bp": (50.0, 250.0),
    "diastolic_bp": (25.0, 150.0),
    "mean_arterial_pressure": (30.0, 180.0),
    "oxygen_saturation": (70.0, 100.0),
    "temperature": (30.0, 43.0),
    "oxygen_flow": (0.0, 15.0),
}


def _rounded(value: float) -> str:
    return f"{value:.2f}"


def _validate_row(row: dict[str, str]) -> None:
    for variable, (lower, upper) in PLAUSIBLE_RANGES.items():
        value = row[variable]
        if value and not lower <= float(value) <= upper:
            raise ValueError(f"Synthetic {variable} is outside the configured range")


def generate_rows(
    patients: int,
    hours: int,
    seed: int,
    missing_rate: float = 0.08,
) -> list[dict[str, str]]:
    """Return deterministic artificial observations with positive and negative cases."""
    if patients < 10:
        raise ValueError("At least 10 patients are required for the three demo splits")
    if hours < 24:
        raise ValueError("At least 24 hours are required for 12-hour windows and labels")
    if not 0 <= missing_rate < 0.5:
        raise ValueError("missing_rate must be in [0, 0.5)")

    rng = random.Random(seed)
    start = datetime(2026, 1, 1, tzinfo=UTC)
    rows: list[dict[str, str]] = []
    onset = max(14, min(hours - 7, (2 * hours) // 3))

    for patient_index in range(patients):
        subject_id = f"SYNTH-P{patient_index + 1:04d}"
        stay_id = f"SYNTH-STAY-{patient_index + 1:04d}"
        has_low_map_episode = patient_index % 2 == 0
        patient_hr = rng.uniform(65, 95)
        patient_map = rng.uniform(72, 88)

        for hour in range(hours):
            circadian = math.sin(2 * math.pi * hour / 24)
            map_value = patient_map + 2.0 * circadian + rng.gauss(0, 2.0)
            if has_low_map_episode and onset <= hour <= onset + 2:
                map_value = rng.uniform(54, 62)

            diastolic = max(35.0, map_value - rng.uniform(8, 15))
            systolic = min(220.0, map_value + rng.uniform(28, 45))
            row = {
                "subject_id": subject_id,
                "stay_id": stay_id,
                "charttime": (start + timedelta(hours=hour)).isoformat(),
                "heart_rate": _rounded(patient_hr + 4 * circadian + rng.gauss(0, 4)),
                "respiratory_rate": _rounded(16 + rng.gauss(0, 2)),
                "systolic_bp": _rounded(systolic),
                "diastolic_bp": _rounded(diastolic),
                "mean_arterial_pressure": _rounded(map_value),
                "oxygen_saturation": _rounded(
                    min(100.0, max(82.0, 96 + rng.gauss(0, 1.5)))
                ),
                "temperature": _rounded(36.8 + 0.2 * circadian + rng.gauss(0, 0.15)),
                "oxygen_flow": _rounded(
                    0.0 if rng.random() < 0.75 else rng.uniform(1, 5)
                ),
            }

            for variable in VITAL_COLUMNS:
                preserve_label_block = (
                    variable == "mean_arterial_pressure"
                    and has_low_map_episode
                    and onset - 1 <= hour <= onset + 5
                )
                if not preserve_label_block and rng.random() < missing_rate:
                    row[variable] = ""

            _validate_row(row)
            rows.append(row)
    return rows


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    """Write synthetic observations, creating only the requested output directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def generate_dataset(
    output: Path,
    patients: int = 30,
    hours: int = 48,
    seed: int = 20260726,
    missing_rate: float = 0.08,
) -> list[dict[str, str]]:
    """Generate and persist the deterministic public demonstration dataset."""
    rows = generate_rows(patients, hours, seed, missing_rate)
    write_rows(output, rows)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--patients", type=int, default=30)
    parser.add_argument("--hours", type=int, default=48)
    parser.add_argument("--seed", type=int, default=20260726)
    parser.add_argument("--missing-rate", type=float, default=0.08)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/synthetic_demo/raw_vitals.csv"),
    )
    args = parser.parse_args()
    rows = generate_dataset(
        args.output,
        patients=args.patients,
        hours=args.hours,
        seed=args.seed,
        missing_rate=args.missing_rate,
    )
    print(WARNING)
    print(
        f"Wrote {len(rows)} artificial hourly rows for {args.patients} "
        f"fictitious patients to {args.output}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
