"""Unit tests for error handling, retries, and exceptions mapping."""

from __future__ import annotations

import httpx
import pytest
import respx

from amazon.clients.creators import AmazonCreatorsAPI, AsyncAmazonCreatorsAPI
from amazon.exceptions import (
    AmazonAPIError,
    AmazonAuthenticationError,
    AmazonBadRequestError,
    AmazonNotFoundError,
    AmazonServerError,
    AmazonThrottlingError,
)
from tests.conftest import MOCK_GET_ITEMS_CREATORS_RESPONSE


@respx.mock
def test_handle_400_bad_request() -> None:
    respx.post("https://creatorsapi.amazon/catalog/v1/getItems").respond(
        status_code=400,
        json={
            "errors": [
                {"code": "InvalidParameterValue", "message": "The value [INVALID] for ItemId is invalid."}
            ]
        },
    )

    api = AmazonCreatorsAPI(credential_id="id", credential_secret="secret", max_retries=0)
    with pytest.raises(AmazonBadRequestError) as exc_info:
        api.get_items(item_ids="INVALID")

    assert exc_info.value.status_code == 400
    assert "The value [INVALID] for ItemId is invalid" in str(exc_info.value)
    api.close()


@respx.mock
def test_handle_403_access_denied() -> None:
    respx.post("https://creatorsapi.amazon/catalog/v1/getItems").respond(
        status_code=403,
        json={
            "errors": [
                {"code": "AccessDeniedException", "message": "Access is denied for this partner tag."}
            ]
        },
    )

    api = AmazonCreatorsAPI(credential_id="id", credential_secret="secret", max_retries=0)
    with pytest.raises(AmazonAuthenticationError) as exc_info:
        api.get_items(item_ids="B0041OSCBU")

    assert exc_info.value.status_code == 403
    api.close()


@respx.mock
def test_handle_429_throttling() -> None:
    respx.post("https://creatorsapi.amazon/catalog/v1/getItems").respond(
        status_code=429,
        json={
            "errors": [
                {"code": "RequestThrottled", "message": "You are submitting requests too quickly."}
            ]
        },
    )

    api = AmazonCreatorsAPI(credential_id="id", credential_secret="secret", max_retries=1, retry_delay=0.01)
    with pytest.raises(AmazonThrottlingError) as exc_info:
        api.get_items(item_ids="B0041OSCBU")

    assert exc_info.value.status_code == 429
    api.close()


@respx.mock
def test_handle_404_not_found() -> None:
    respx.post("https://creatorsapi.amazon/catalog/v1/getItems").respond(
        status_code=404,
        json={
            "errors": [
                {"code": "NoExactMatches", "message": "No exact matches were found for your request."}
            ]
        },
    )

    api = AmazonCreatorsAPI(credential_id="id", credential_secret="secret", max_retries=0)
    with pytest.raises(AmazonNotFoundError) as exc_info:
        api.get_items(item_ids="B0041OSCBU")

    assert exc_info.value.status_code == 404
    api.close()


@respx.mock
def test_handle_500_server_error() -> None:
    respx.post("https://creatorsapi.amazon/catalog/v1/getItems").respond(
        status_code=500,
        text="Internal Server Error",
    )

    api = AmazonCreatorsAPI(credential_id="id", credential_secret="secret", max_retries=0)
    with pytest.raises(AmazonServerError) as exc_info:
        api.get_items(item_ids="B0041OSCBU")

    assert exc_info.value.status_code == 500
    api.close()


@respx.mock
def test_retry_on_429_eventually_succeeds_sync() -> None:
    route = respx.post("https://creatorsapi.amazon/catalog/v1/getItems")
    route.side_effect = [
        httpx.Response(429, json={"errors": [{"code": "RequestThrottled", "message": "Slow down"}]}),
        httpx.Response(200, json=MOCK_GET_ITEMS_CREATORS_RESPONSE),
    ]

    with AmazonCreatorsAPI(credential_id="id", credential_secret="secret", max_retries=2, retry_delay=0.01) as api:
        res = api.get_items(item_ids=["B0041OSCBU"])
        assert len(res.items) == 1
        assert route.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_retry_on_429_eventually_succeeds_async() -> None:
    route = respx.post("https://creatorsapi.amazon/catalog/v1/getItems")
    route.side_effect = [
        httpx.Response(429, json={"errors": [{"code": "RequestThrottled", "message": "Slow down"}]}),
        httpx.Response(200, json=MOCK_GET_ITEMS_CREATORS_RESPONSE),
    ]

    async with AsyncAmazonCreatorsAPI(credential_id="id", credential_secret="secret", max_retries=2, retry_delay=0.01) as api:
        res = await api.get_items(item_ids=["B0041OSCBU"])
        assert len(res.items) == 1
        assert route.call_count == 2


@respx.mock
def test_retry_on_401_clears_cache_and_succeeds() -> None:
    route = respx.post("https://creatorsapi.amazon/catalog/v1/getItems")
    route.side_effect = [
        httpx.Response(401, json={"errors": [{"code": "InvalidToken", "message": "Token expired"}]}),
        httpx.Response(200, json=MOCK_GET_ITEMS_CREATORS_RESPONSE),
    ]

    with AmazonCreatorsAPI(credential_id="id", credential_secret="secret", max_retries=2, retry_delay=0.01) as api:
        res = api.get_items(item_ids=["B0041OSCBU"])
        assert len(res.items) == 1
        assert route.call_count == 2


def test_exception_repr() -> None:
    exc = AmazonAPIError("test message", status_code=400, error_code="InvalidParameter")
    assert "AmazonAPIError(message='test message', status_code=400, error_code='InvalidParameter')" in repr(exc)
