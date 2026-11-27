"""Weather risk classification: threshold table + load rules from the assessment brief.

Boundary convention (documented because the brief's ranges overlap at their edges):
  * A value exactly on a band edge falls in the *higher* (safer-side-of-caution) band,
    e.g. wind 35.0 mph is High, rain 0.25 in/hr is High.
  * The only exception is the brief's explicit "No Travel" cut-offs for rain and snow, which are
    written as strict ">" (> 1.00 in/hr, > 3.0 in/hr), so exactly 1.00 / 3.0 stays Severe.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..domain import RiskAssessment, RiskLevel, WeatherSample


@dataclass(frozen=True)
class Thresholds:
    """Lower bounds of Moderate, High, Severe and No Travel."""

    moderate: float
    high: float
    severe: float
    no_travel: float
    no_travel_strict: bool = False  # True -> No Travel only when value > no_travel (not >=)

    def classify(self, value: float) -> RiskLevel:
        if value > self.no_travel if self.no_travel_strict else value >= self.no_travel:
            return RiskLevel.NO_TRAVEL
        if value >= self.severe:
            return RiskLevel.SEVERE
        if value >= self.high:
            return RiskLevel.HIGH
        if value >= self.moderate:
            return RiskLevel.MODERATE
        return RiskLevel.LOW


WIND = Thresholds(25, 35, 45, 55)
RAIN = Thresholds(0.10, 0.25, 0.50, 1.00, no_travel_strict=True)
SNOW = Thresholds(0.5, 1.0, 2.0, 3.0, no_travel_strict=True)

# Load rules (pounds)
HEAVY_WIND_NO_TRAVEL_LB = 30_000  # 45-54 mph and load above this -> No Travel
HEAVY_WIND_SEVERE_LB = 40_000  # 35-44 mph and load above this -> Severe


def classify_wind(wind_mph: float, load_lb: float) -> tuple[RiskLevel, str | None]:
    """Wind level including the load-dependent rules. Returns (level, note-if-load-rule-applied)."""
    base = WIND.classify(wind_mph)
    if 45 <= wind_mph < 55 and load_lb > HEAVY_WIND_NO_TRAVEL_LB:
        return RiskLevel.NO_TRAVEL, f"{wind_mph:.0f} mph wind with a load over {HEAVY_WIND_NO_TRAVEL_LB:,} lb is No Travel"
    if 35 <= wind_mph < 45 and load_lb > HEAVY_WIND_SEVERE_LB:
        return RiskLevel.SEVERE, f"{wind_mph:.0f} mph wind with a load over {HEAVY_WIND_SEVERE_LB:,} lb is Severe"
    return base, None


def assess(sample: WeatherSample, load_lb: float) -> RiskAssessment:
    wind_level, note = classify_wind(sample.wind_mph, load_lb)
    rain_level = RAIN.classify(sample.rain_in_hr)
    snow_level = SNOW.classify(sample.snow_in_hr)
    level = max(wind_level, rain_level, snow_level)
    # Only report the load rule if it is what actually drives the final level.
    load_rule = note if note and wind_level == level and WIND.classify(sample.wind_mph) < level else None
    return RiskAssessment(level, wind_level, rain_level, snow_level, load_rule)
