"""Unit tests for Amazon PA-API 5.0 (Asynchronous client)."""

from __future__ import annotations

import pytest
import respx

from amazon.clients.paapi5 import AsyncAmazonPAAPI5
from tests.conftest import (
    MOCK_GET_BROWSE_NODES_CREATORS_RESPONSE,
    MOCK_GET_VARIATIONS_CREATORS_RESPONSE,
    MOCK_PAAPI5_GET_ITEMS_RESPONSE,
    MOCK_SEARCH_ITEMS_CREATORS_RESPONSE,
)


@respx.mock
@pytest.mark.asyncio
async def test_async_paapi5_get_items_success(paapi5_credentials: dict[str, str]) -> None:
    respx.post("https://webservices.amazon.com/paapi5/getitems").respond(
        status_code=200,
        json=MOCK_PAAPI5_GET_ITEMS_RESPONSE,
    )

    async with AsyncAmazonPAAPI5(**paapi5_credentials) as api:
        res = await api.get_items(item_ids=["B0041OSCBU"])
        assert len(res.items) == 1
        assert res.item.asin == "B0041OSCBU"


@respx.mock
@pytest.mark.asyncio
async def test_async_paapi5_search_items_success(paapi5_credentials: dict[str, str]) -> None:
    respx.post("https://webservices.amazon.com/paapi5/searchitems").respond(
        status_code=200,
        json=MOCK_SEARCH_ITEMS_CREATORS_RESPONSE,
    )

    async with AsyncAmazonPAAPI5(**paapi5_credentials) as api:
        res = await api.search_items(keywords="Python")
        assert len(res.items) == 2


@respx.mock
@pytest.mark.asyncio
async def test_async_paapi5_get_variations_success(paapi5_credentials: dict[str, str]) -> None:
    respx.post("https://webservices.amazon.com/paapi5/getvariations").respond(
        status_code=200,
        json=MOCK_GET_VARIATIONS_CREATORS_RESPONSE,
    )

    async with AsyncAmazonPAAPI5(**paapi5_credentials) as api:
        res = await api.get_variations(asin="B0041OSCBU")
        assert len(res.items) == 2


@respx.mock
@pytest.mark.asyncio
async def test_async_paapi5_get_browse_nodes_success(paapi5_credentials: dict[str, str]) -> None:
    respx.post("https://webservices.amazon.com/paapi5/getbrowsenodes").respond(
        status_code=200,
        json=MOCK_GET_BROWSE_NODES_CREATORS_RESPONSE,
    )

    async with AsyncAmazonPAAPI5(**paapi5_credentials) as api:
        res = await api.get_browse_nodes(browse_node_ids=["17"])
        assert len(res.browse_nodes) == 1
