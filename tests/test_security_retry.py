"""Security tests: Retry backoff with jitter and Retry-After header parsing."""

from __future__ import annotations

import datetime

import httpx
import pytest
import respx

from amazon.clients.base import calculate_backoff, parse_retry_after
from amazon.clients.creators import AmazonCreatorsAPI
from amazon.clients.paapi5 import AmazonPAAPI5
from amazon.exceptions import AmazonThrottlingError
from tests.conftest import MOCK_GET_ITEMS_CREATORS_RESPONSE


def test_parse_retry_after() -> None:
    # Integer seconds
    resp_int = httpx.Response(429, headers={"Retry-After": "5"})
    assert parse_retry_after(resp_int, default=1.0) == 5.0

    # Missing header returns default
    resp_none = httpx.Response(429)
    assert parse_retry_after(resp_none, default=2.5) == 2.5

    # HTTP-date format in future
    future_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=10)
    http_date = future_time.strftime("%a, %d %b %Y %H:%M:%S GMT")
    resp_date = httpx.Response(429, headers={"Retry-After": http_date})
    delay = parse_retry_after(resp_date, default=1.0)
    assert 8.0 <= delay <= 12.0

    # Malformed header returns default
    resp_invalid = httpx.Response(429, headers={"Retry-After": "not-a-valid-date-or-number"})
    assert parse_retry_after(resp_invalid, default=3.0) == 3.0


def test_calculate_backoff_jitter() -> None:
    for attempt in range(1, 6):
        delay = calculate_backoff(retry_count=attempt, base_delay=1.0, max_delay=30.0)
        ceiling = min(30.0, 1.0 * (2 ** (attempt - 1)))
        assert 0.0 <= delay <= ceiling


@respx.mock
def test_creators_retry_on_503_and_recovery(creators_credentials: dict[str, str]) -> None:
    route = respx.post("https://creatorsapi.amazon/catalog/v1/getItems").mock(
        side_effect=[
            httpx.Response(503, text="Service Unavailable", headers={"Retry-After": "0"}),
            httpx.Response(200, json=MOCK_GET_ITEMS_CREATORS_RESPONSE),
        ]
    )

    client = AmazonCreatorsAPI(**creators_credentials, max_retries=2, retry_delay=0.01)
    res = client.get_items(item_ids="B0041OSCBU")
    assert res.item.asin == "B0041OSCBU"
    assert route.call_count == 2
    client.close()


@respx.mock
def test_paapi5_retry_on_429_exhaustion(paapi5_credentials: dict[str, str]) -> None:
    respx.post("https://webservices.amazon.com/paapi5/getitems").respond(
        status_code=429,
        text="Rate limit exceeded",
        headers={"Retry-After": "0"},
    )

    client = AmazonPAAPI5(**paapi5_credentials, max_retries=2, retry_delay=0.01)
    with pytest.raises(AmazonThrottlingError):
        client.get_items(item_ids="B0041OSCBU")
    client.close()
