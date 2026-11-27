"""Place search via Nominatim (OpenStreetMap). Results are cached to respect its usage policy."""
from __future__ import annotations

from dataclasses import dataclass

import requests
from django.conf import settings
from django.core.cache import cache

from ..exceptions import UpstreamError
from . import http


@dataclass(frozen=True)
class Place:
    label: str
    lat: float
    lon: float


def search(query: str, limit: int = 5) -> list[Place]:
    query = " ".join(query.split())
    if len(query) < 3:
        return []
    key = f"geocode:{query.lower()}:{limit}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    params = {"q": query, "format": "jsonv2", "limit": limit, "addressdetails": 0}
    if settings.NOMINATIM_COUNTRY_CODES:
        params["countrycodes"] = settings.NOMINATIM_COUNTRY_CODES
    try:
        data = http.get_json(f"{settings.NOMINATIM_BASE_URL}/search", params)
    except requests.RequestException as exc:
        raise UpstreamError("Geocoding service is unavailable. Please try again.") from exc

    places = [Place(label=item["display_name"], lat=float(item["lat"]), lon=float(item["lon"])) for item in data]
    cache.set(key, places, 60 * 60 * 24)
    return places
