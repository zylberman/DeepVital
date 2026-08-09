"""Aggregate-safe provenance for a future formal Phase 3 execution."""

from __future__ import annotations

import importlib.metadata
import platform
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from deepvital.reproducibility.fingerprints import fingerprint_configuration


def environment_metadata(packages: Sequence[str] = ("numpy", "scikit-learn", "scipy")) -> dict[str, Any]:
    """Return interpreter and selected dependency versions without local paths."""
    versions = {}
    for package in packages:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform_system": platform.system(),
        "dependency_versions": versions,
    }


def build_execution_provenance(
    *,
    registration: Mapping[str, Any],
    implementation_source_commit: str,
    configuration_paths: Sequence[Path],
    execution_timestamp: str | None = None,
) -> dict[str, Any]:
    """Build the frozen provenance block for future aggregate outputs."""
    timestamp = execution_timestamp or datetime.now(UTC).isoformat()
    return {
        "frozen_protocol_git_commit": registration["frozen_protocol_git_commit"],
        "frozen_protocol_sha256": registration["frozen_protocol_sha256"],
        "implementation_source_commit": implementation_source_commit,
        "canonical_cohort_fingerprint": registration["canonical_cohort_fingerprint"],
        "fold_manifest_fingerprint": registration["fold_manifest_fingerprint"],
        "configuration_fingerprint": fingerprint_configuration(configuration_paths),
        "execution_timestamp": timestamp,
        "environment": environment_metadata(),
        "python_executable_basename": Path(sys.executable).name,
    }
