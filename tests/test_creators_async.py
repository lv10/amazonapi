"""Unit tests for Amazon Creators API (Asynchronous client)."""

from __future__ import annotations

import pytest
import respx

from amazon.clients.creators import CREATORS_API_BASE_URL, AsyncAmazonCreatorsAPI
from tests.conftest import (
    MOCK_GET_BROWSE_NODES_CREATORS_RESPONSE,
    MOCK_GET_ITEMS_CREATORS_RESPONSE,
    MOCK_GET_VARIATIONS_CREATORS_RESPONSE,
    MOCK_SEARCH_ITEMS_CREATORS_RESPONSE,
)


@respx.mock
@pytest.mark.asyncio
async def test_async_creators_get_items_success() -> None:
    route = respx.post(f"{CREATORS_API_BASE_URL}/getItems").respond(
        status_code=200,
        json=MOCK_GET_ITEMS_CREATORS_RESPONSE,
    )

    async with AsyncAmazonCreatorsAPI(credential_id="id", credential_secret="secret", marketplace="US") as api:
        res = await api.get_items(item_ids=["B0041OSCBU"])

        assert len(res.items) == 1
        item = res.item
        assert item is not None
        assert item.asin == "B0041OSCBU"
        assert item.title == "Kindle Paperwhite (16 GB)"

    assert route.call_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_async_creators_search_items_success() -> None:
    route = respx.post(f"{CREATORS_API_BASE_URL}/searchItems").respond(
        status_code=200,
        json=MOCK_SEARCH_ITEMS_CREATORS_RESPONSE,
    )

    async with AsyncAmazonCreatorsAPI(credential_id="id", credential_secret="secret", marketplace="DE") as api:
        res = await api.search_items(keywords="Python Book", item_count=5)

        assert len(res.items) == 2
        assert res.pagination is not None
        assert res.pagination.total_result_count == 42

    assert route.call_count == 1
    sent_request = route.calls[0].request
    assert sent_request.headers["x-marketplace"] == "www.amazon.de"


@respx.mock
@pytest.mark.asyncio
async def test_async_creators_get_variations_success() -> None:
    respx.post(f"{CREATORS_API_BASE_URL}/getVariations").respond(
        status_code=200,
        json=MOCK_GET_VARIATIONS_CREATORS_RESPONSE,
    )

    async with AsyncAmazonCreatorsAPI(credential_id="id", credential_secret="secret") as api:
        res = await api.get_variations(asin="B0041OSCBU")
        assert len(res.items) == 2


@respx.mock
@pytest.mark.asyncio
async def test_async_creators_get_browse_nodes_success() -> None:
    respx.post(f"{CREATORS_API_BASE_URL}/getBrowseNodes").respond(
        status_code=200,
        json=MOCK_GET_BROWSE_NODES_CREATORS_RESPONSE,
    )

    async with AsyncAmazonCreatorsAPI(credential_id="id", credential_secret="secret") as api:
        res = await api.get_browse_nodes(browse_node_ids=[17])
        assert len(res.browse_nodes) == 1
        assert res.browse_node.display_name == "Literature & Fiction"
