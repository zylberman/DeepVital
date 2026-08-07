"""Deterministic fingerprints for private inputs and aggregate public metadata."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

FORBIDDEN_PUBLIC_KEYS = {
    "subject_id",
    "hadm_id",
    "stay_id",
    "patient_id",
    "prediction_time",
    "window_id",
    "patient_assignments",
}
FORBIDDEN_PUBLIC_FRAGMENTS = ("Patient/", "Encounter/")


def sha256_bytes(value: bytes) -> str:
    """Return a prefixed SHA-256 digest without exposing the hashed content."""
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def fingerprint_file(path: Path) -> str:
    """Hash a file by streaming bytes; private values never enter the result."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def fingerprint_configuration(paths: Iterable[Path]) -> str:
    """Hash normalized path labels and configuration bytes deterministically."""
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.name):
        digest.update(path.name.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def fingerprint_records(records: Iterable[Mapping[str, Any]]) -> str:
    """Hash sorted canonical JSON records for synthetic tests and registries."""
    encoded = [
        json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
        for record in records
    ]
    return sha256_bytes("\n".join(sorted(encoded)).encode())


def assert_public_metadata(metadata: Mapping[str, Any]) -> None:
    """Reject identifier-bearing keys anywhere in public metadata."""
    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key).lower() in FORBIDDEN_PUBLIC_KEYS:
                    raise ValueError(f"Public metadata contains forbidden key: {key}")
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, str) and any(
            fragment in value for fragment in FORBIDDEN_PUBLIC_FRAGMENTS
        ):
            raise ValueError("Public metadata contains a clinical reference")

    visit(metadata)
