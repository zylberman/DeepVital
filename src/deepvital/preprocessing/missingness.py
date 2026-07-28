"""Validation helpers for explicit, leakage-safe missingness configuration."""

from __future__ import annotations


def validate_missingness_config(config: dict, variables: list[str]) -> None:
    if config.get("backward_fill") is not False:
        raise ValueError("Backward filling must remain disabled")
    if config.get("interpolation") is not False:
        raise ValueError("Future-dependent interpolation must remain disabled")
    limits = config.get("forward_fill_max_hours", {})
    if set(limits) != set(variables):
        raise ValueError("Every variable must have exactly one forward-fill limit")
    if any(not isinstance(value, int) or value < 0 for value in limits.values()):
        raise ValueError("Forward-fill limits must be non-negative integer hours")
