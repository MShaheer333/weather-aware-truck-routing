"""Hourly forecasts from Open-Meteo (keyless) and interpolation to an arbitrary timestamp."""
from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import requests
from django.conf import settings
from django.core.cache import cache

from ..domain import WeatherSample
from ..exceptions import UpstreamError
from . import http
from .geo import LatLon

CHUNK_SIZE = 50  # locations per request (keeps URLs short)
CACHE_SECONDS = 20 * 60
HOURLY_VARS = "wind_speed_10m,rain,showers,snowfall"


@dataclass
class ForecastSeries:
    """Hourly values starting at `start` (UTC)."""

    start: datetime
    wind_mph: list[float]
    rain_in_hr: list[float]  # rain + showers: liquid precipitation in the preceding hour
    snow_in_hr: list[float]  # snowfall (inches of snow) in the preceding hour

    @property
    def end(self) -> datetime:
        return self.start + timedelta(hours=len(self.wind_mph) - 1)

    def at(self, when: datetime) -> WeatherSample:
        """Linear interpolation between the two surrounding hours (clamped at the series ends)."""
        last = len(self.wind_mph) - 1
        hours = min(max((when - self.start).total_seconds() / 3600, 0.0), last)
        lo = math.floor(hours)
        hi = min(lo + 1, last)
        frac = hours - lo

        def lerp(series: list[float]) -> float:
            return series[lo] + (series[hi] - series[lo]) * frac

        return WeatherSample(lerp(self.wind_mph), lerp(self.rain_in_hr), lerp(self.snow_in_hr))


def grid_key(point: LatLon) -> LatLon:
    """Snap to ~0.7 mi so neighbouring points share one forecast (the weather model grid is coarser)."""
    return (round(point[0], 2), round(point[1], 2))


def fetch_forecasts(points: list[LatLon], start_date: date, end_date: date) -> dict[LatLon, ForecastSeries]:
    """Forecast series for each snapped, de-duplicated point. Look results up with `grid_key`."""
    keys = list(dict.fromkeys(grid_key(p) for p in points))
    result: dict[LatLon, ForecastSeries] = {}
    missing: list[LatLon] = []
    for key in keys:
        cached = cache.get(_cache_key(key, start_date, end_date))
        if cached is not None:
            result[key] = cached
        else:
            missing.append(key)

    chunks = [missing[i : i + CHUNK_SIZE] for i in range(0, len(missing), CHUNK_SIZE)]
    if chunks:
        with ThreadPoolExecutor(max_workers=8) as pool:
            responses = pool.map(lambda c: _request(c, start_date, end_date), chunks)
            for chunk, series_list in zip(chunks, responses):
                for key, series in zip(chunk, series_list):
                    cache.set(_cache_key(key, start_date, end_date), series, CACHE_SECONDS)
                    result[key] = series
    return result


def _cache_key(key: LatLon, start_date: date, end_date: date) -> str:
    return f"wx:{key[0]}:{key[1]}:{start_date}:{end_date}"


def _request(chunk: list[LatLon], start_date: date, end_date: date) -> list[ForecastSeries]:
    params = {
        "latitude": ",".join(str(p[0]) for p in chunk),
        "longitude": ",".join(str(p[1]) for p in chunk),
        "hourly": HOURLY_VARS,
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "GMT",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
    try:
        data = http.get_json(f"{settings.OPEN_METEO_BASE_URL}/v1/forecast", params)
    except requests.RequestException as exc:
        raise UpstreamError("Weather service is unavailable. Please try again.") from exc
    payload = data if isinstance(data, list) else [data]
    if len(payload) != len(chunk):
        raise UpstreamError("Weather service returned an unexpected response.")
    return [_parse(item) for item in payload]


def _parse(item: dict) -> ForecastSeries:
    hourly = item["hourly"]
    start = datetime.fromisoformat(hourly["time"][0]).replace(tzinfo=timezone.utc)
    return ForecastSeries(
        start=start,
        wind_mph=_clean(hourly["wind_speed_10m"]),
        rain_in_hr=[a + b for a, b in zip(_clean(hourly["rain"]), _clean(hourly["showers"]))],
        snow_in_hr=_clean(hourly["snowfall"]),
    )


def _clean(values: list[float | None]) -> list[float]:
    """Replace gaps (null) with the previous value (or 0 at the start)."""
    out: list[float] = []
    for v in values:
        out.append(float(v) if v is not None else (out[-1] if out else 0.0))
    return out
