"""Auditable, explicit unit normalization."""

from __future__ import annotations

from typing import Any


def normalize_unit(
    variable: str,
    value: float,
    original_unit: Any,
    ucum_code: Any,
    configuration: dict,
) -> tuple[float | None, str | None, str | None]:
    """Return normalized value, normalized unit, and conversion name."""
    variable_config = configuration.get(variable)
    if not isinstance(variable_config, dict):
        return None, None, None
    accepted = variable_config.get("accepted_units", {})
    candidates = [
        unit.strip()
        for unit in (original_unit, ucum_code)
        if isinstance(unit, str) and unit.strip()
    ]
    conversion = next((accepted[unit] for unit in candidates if unit in accepted), None)
    if conversion is None:
        return None, None, None
    if conversion == "identity":
        normalized = value
    elif conversion == "fahrenheit_to_celsius":
        normalized = (value - 32.0) * 5.0 / 9.0
    else:
        return None, None, None
    return normalized, str(variable_config["normalized_unit"]), conversion
