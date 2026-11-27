"""Plain data types shared by the services (no Django, no I/O)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum

from .services.geo import LatLon


class RiskLevel(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self) -> str:
        return self.name.replace("_", " ").title()


@dataclass(frozen=True)
class WeatherSample:
    wind_mph: float
    rain_in_hr: float
    snow_in_hr: float


@dataclass(frozen=True)
class RiskAssessment:
    level: RiskLevel
    wind_level: RiskLevel
    rain_level: RiskLevel
    snow_level: RiskLevel
    load_rule: str | None = None  # human readable note when a load rule changed the outcome


@dataclass
class Route:
    index: int
    coordinates: list[LatLon]
    cum_miles: list[float]  # aligned with coordinates
    cum_seconds: list[float]  # aligned with coordinates (truck-adjusted)
    summary: str = ""

    @property
    def distance_miles(self) -> float:
        return self.cum_miles[-1]

    @property
    def duration_seconds(self) -> float:
        return self.cum_seconds[-1]


@dataclass
class Checkpoint:
    mile: float
    lat: float
    lon: float
    eta: datetime
    weather: WeatherSample
    risk: RiskAssessment
    owned_miles: float = 0.0


@dataclass
class RouteMetrics:
    miles_by_level: dict[RiskLevel, float] = field(default_factory=dict)
    avg_risk: float = 0.0
    max_level: RiskLevel = RiskLevel.LOW


@dataclass
class AnalyzedRoute:
    route: Route
    checkpoints: list[Checkpoint]
    metrics: RouteMetrics
    rank: int = 0
