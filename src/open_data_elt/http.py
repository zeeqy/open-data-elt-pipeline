"""HTTP GET with per-host spacing and 429/5xx retries.

data.gov.my allows 4 requests per minute, so calls to it are spaced 15 s apart.
A 429 waits for Retry-After (or a backoff) and tries again.
"""

import time
from collections.abc import Callable
from urllib.parse import urlparse

import requests

MIN_INTERVAL = {"api.data.gov.my": 15.0, "api.bnm.gov.my": 1.0}
RETRY_STATUS = {429, 500, 502, 503, 504}

_last_call: dict[str, float] = {}


class FetchError(RuntimeError):
    pass


def get(
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: int = 60,
    max_tries: int = 5,
    sleep: Callable[[float], None] = time.sleep,
    session: requests.Session | None = None,
) -> requests.Response:
    host = urlparse(url).netloc
    http = session or requests
    for attempt in range(1, max_tries + 1):
        wait = MIN_INTERVAL.get(host, 0) - (time.monotonic() - _last_call.get(host, -1e9))
        if wait > 0:
            sleep(wait)
        _last_call[host] = time.monotonic()
        resp = http.get(url, params=params, headers=headers, timeout=timeout)
        if resp.status_code not in RETRY_STATUS:
            resp.raise_for_status()
            return resp
        if attempt == max_tries:
            break
        retry_after = resp.headers.get("Retry-After", "")
        sleep(float(retry_after) if retry_after.isdigit() else min(60.0, 5.0 * 2**attempt))
    raise FetchError(f"{url} still failing after {max_tries} tries (last {resp.status_code})")
