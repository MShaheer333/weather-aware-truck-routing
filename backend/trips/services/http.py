"""Shared HTTP session with retries, a User-Agent and a default timeout."""
from functools import lru_cache

import requests
from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@lru_cache(maxsize=1)
def session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=2,
        backoff_factor=0.4,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    adapter = HTTPAdapter(max_retries=retry, pool_maxsize=16)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.headers["User-Agent"] = settings.HTTP_USER_AGENT
    return s


def get_json(url: str, params: dict | None = None) -> dict | list:
    resp = session().get(url, params=params, timeout=settings.HTTP_TIMEOUT_SECONDS)
    resp.raise_for_status()
    return resp.json()
