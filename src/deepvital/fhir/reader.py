"""Streaming readers for gzip-compressed FHIR NDJSON."""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any


def stream_fhir_resources(
    path: Path,
) -> Iterator[tuple[dict[str, Any] | None, str | None]]:
    """Yield one resource at a time and a non-sensitive error category.

    Malformed content is never included in the returned error string.
    """
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                resource = json.loads(line)
            except (json.JSONDecodeError, UnicodeDecodeError):
                yield None, "malformed_json"
                continue
            if not isinstance(resource, dict):
                yield None, "non_object_json"
                continue
            yield resource, None
