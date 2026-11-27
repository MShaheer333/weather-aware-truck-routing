"""Route ranking.

Order of preference from the brief: fewest Severe miles, then fewest High miles, then lowest average
risk, then shortest travel time. We put *No Travel* miles ahead of all of them: a stretch where
travel is prohibited is strictly worse than a Severe one, so a route crossing one can never beat a
route that does not just because it has fewer Severe miles.

Miles are compared at 0.1 mi resolution, average risk at 0.01 and time at 1 minute so that float
noise or trivially small differences do not decide the winner ahead of the next criterion.
"""
from __future__ import annotations

from ..domain import AnalyzedRoute, RiskLevel

CRITERIA = ("No Travel miles", "Severe miles", "High miles", "average risk", "travel time")


def criteria_values(a: AnalyzedRoute) -> tuple[float, float, float, float, float]:
    m = a.metrics.miles_by_level
    return (
        round(m.get(RiskLevel.NO_TRAVEL, 0.0), 1),
        round(m.get(RiskLevel.SEVERE, 0.0), 1),
        round(m.get(RiskLevel.HIGH, 0.0), 1),
        round(a.metrics.avg_risk, 2),
        round(a.route.duration_seconds / 60),
    )


def rank_routes(routes: list[AnalyzedRoute]) -> list[AnalyzedRoute]:
    """Return routes best-first and set `.rank` (1 = recommended)."""
    ordered = sorted(routes, key=criteria_values)
    for position, item in enumerate(ordered, start=1):
        item.rank = position
    return ordered


def explain(best: AnalyzedRoute, others: list[AnalyzedRoute], name) -> str:
    """One-sentence reason the best route won, citing the first criterion that separated it."""
    if not others:
        return f"{name(best)} is the only drivable option found."
    runner_up = others[0]
    b, r = criteria_values(best), criteria_values(runner_up)
    for i, label in enumerate(CRITERIA):
        if b[i] == r[i]:
            continue
        if label == "travel time":
            return (
                f"{name(best)} has the same weather risk as {name(runner_up)} but is faster "
                f"({_hm(best.route.duration_seconds)} vs {_hm(runner_up.route.duration_seconds)})."
            )
        if label == "average risk":
            return (
                f"{name(best)} has the lowest average risk ({b[i]:.2f} vs {r[i]:.2f} on {name(runner_up)}) "
                "with equal Severe and High mileage."
            )
        return f"{name(best)} has the fewest {label} ({b[i]:.1f} vs {r[i]:.1f} on {name(runner_up)})."
    return f"{name(best)} is as safe as the alternatives and the fastest."


def _hm(seconds: float) -> str:
    minutes = round(seconds / 60)
    return f"{minutes // 60}h {minutes % 60:02d}m"
