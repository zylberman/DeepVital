"""Future-only sustained-hypotension label."""

from __future__ import annotations


def sustained_hypotension_label(
    future_map: list[float | None],
    threshold: float = 65.0,
    consecutive_hours: int = 2,
    require_complete: bool = True,
) -> int | None:
    """Label consecutive low MAP using future hours only.

    Returns None when the primary complete-horizon requirement is not met.
    """
    if require_complete and any(value is None for value in future_map):
        return None
    run = 0
    for value in future_map:
        if value is not None and value < threshold:
            run += 1
            if run >= consecutive_hours:
                return 1
        else:
            run = 0
    return 0
