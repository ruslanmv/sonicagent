"""Small sample statistics for endpoint timings."""

from __future__ import annotations


def percentile(values: list[float], percent: float) -> float | None:
    """Linear percentile. ``percent`` is 0–100. Empty input returns None."""
    if not values:
        return None
    if percent < 0 or percent > 100:
        raise ValueError("percent must be between 0 and 100")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * (percent / 100)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = rank - low
    return ordered[low] * (1 - weight) + ordered[high] * weight


def summarize(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"n": 0, "min": None, "p50": None, "p95": None, "p99": None, "max": None}
    summary: dict[str, float | int | None] = {
        "n": len(values),
        "min": min(values),
        "p50": percentile(values, 50),
        "p95": percentile(values, 95),
        "max": max(values),
    }
    summary["p99"] = percentile(values, 99) if len(values) >= 20 else None
    return summary
