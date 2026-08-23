"""Unit tests for unified AmazonAPI and AsyncAmazonAPI facades."""

from __future__ import annotations

import pytest
import respx

from amazon.clients.unified import AmazonAPI, AsyncAmazonAPI
from amazon.exceptions import AmazonConfigurationError
from tests.conftest import (
    MOCK_GET_BROWSE_NODES_CREATORS_RESPONSE,
    MOCK_GET_ITEMS_CREATORS_RESPONSE,
    MOCK_GET_VARIATIONS_CREATORS_RESPONSE,
    MOCK_SEARCH_ITEMS_CREATORS_RESPONSE,
)


def test_unified_sync_creators_initialization() -> None:
    api = AmazonAPI(credential_id="test-id", credential_secret="test-secret", marketplace="US")
    assert api._is_creators is True
    api.close()


def test_unified_sync_paapi_initialization() -> None:
    api = AmazonAPI(
        access_key="AKIA123",
        secret_key="secret123",
        associate_tag="tag-20",
        marketplace="US",
    )
    assert api._is_creators is False
    api.close()


def test_unified_sync_legacy_args_initialization() -> None:
    api = AmazonAPI(
        aws_access_key="AKIA123",
        secret_key="secret123",
        associate_tag="tag-20",
        host="us",
    )
    assert api._is_creators is False
    api.close()


def test_unified_sync_invalid_args_raises() -> None:
    with pytest.raises(AmazonConfigurationError):
        AmazonAPI()


def test_unified_async_invalid_args_raises() -> None:
    with pytest.raises(AmazonConfigurationError):
        AsyncAmazonAPI()


def test_unified_async_paapi_initialization() -> None:
    api = AsyncAmazonAPI(
        access_key="AKIA123",
        secret_key="secret123",
        associate_tag="tag-20",
    )
    assert api._is_creators is False


@respx.mock
def test_unified_sync_item_lookup_legacy_alias() -> None:
    respx.post("https://creatorsapi.amazon/catalog/v1/getItems").respond(
        status_code=200,
        json=MOCK_GET_ITEMS_CREATORS_RESPONSE,
    )

    api = AmazonAPI(credential_id="test-id", credential_secret="test-secret")
    res = api.item_lookup(ItemId="B0041OSCBU")
    assert res.item.asin == "B0041OSCBU"
    api.close()


def test_unified_sync_item_lookup_missing_id_raises() -> None:
    api = AmazonAPI(credential_id="test-id", credential_secret="test-secret")
    with pytest.raises(AmazonConfigurationError):
        api.item_lookup()
    api.close()


def test_unified_sync_node_browse_missing_id_raises() -> None:
    api = AmazonAPI(credential_id="test-id", credential_secret="test-secret")
    with pytest.raises(AmazonConfigurationError):
        api.node_browse_lookup()
    api.close()


@respx.mock
def test_unified_sync_item_search_legacy_alias() -> None:
    respx.post("https://creatorsapi.amazon/catalog/v1/searchItems").respond(
        status_code=200,
        json=MOCK_SEARCH_ITEMS_CREATORS_RESPONSE,
    )

    api = AmazonAPI(credential_id="test-id", credential_secret="test-secret")
    res = api.item_search(Keywords="Kindle")
    assert len(res.items) == 2
    api.close()


@respx.mock
def test_unified_sync_get_variations() -> None:
    respx.post("https://creatorsapi.amazon/catalog/v1/getVariations").respond(
        status_code=200,
        json=MOCK_GET_VARIATIONS_CREATORS_RESPONSE,
    )

    api = AmazonAPI(credential_id="test-id", credential_secret="test-secret")
    res = api.get_variations(asin="B0041OSCBU")
    assert len(res.items) == 2
    api.close()


@respx.mock
def test_unified_sync_node_browse_lookup_legacy_alias() -> None:
    respx.post("https://creatorsapi.amazon/catalog/v1/getBrowseNodes").respond(
        status_code=200,
        json=MOCK_GET_BROWSE_NODES_CREATORS_RESPONSE,
    )

    api = AmazonAPI(credential_id="test-id", credential_secret="test-secret")
    res = api.node_browse_lookup(browse_node_id=17)
    assert res.browse_node.id == "17"
    api.close()


@respx.mock
@pytest.mark.asyncio
async def test_unified_async_operations() -> None:
    respx.post("https://creatorsapi.amazon/catalog/v1/getItems").respond(
        status_code=200,
        json=MOCK_GET_ITEMS_CREATORS_RESPONSE,
    )
    respx.post("https://creatorsapi.amazon/catalog/v1/searchItems").respond(
        status_code=200,
        json=MOCK_SEARCH_ITEMS_CREATORS_RESPONSE,
    )
    respx.post("https://creatorsapi.amazon/catalog/v1/getVariations").respond(
        status_code=200,
        json=MOCK_GET_VARIATIONS_CREATORS_RESPONSE,
    )
    respx.post("https://creatorsapi.amazon/catalog/v1/getBrowseNodes").respond(
        status_code=200,
        json=MOCK_GET_BROWSE_NODES_CREATORS_RESPONSE,
    )

    async with AsyncAmazonAPI(credential_id="test-id", credential_secret="test-secret") as api:
        res1 = await api.get_items(item_ids="B0041OSCBU")
        assert res1.item.asin == "B0041OSCBU"

        res2 = await api.search_items(keywords="Python")
        assert len(res2.items) == 2

        res3 = await api.get_variations(asin="B0041OSCBU")
        assert len(res3.items) == 2

        res4 = await api.get_browse_nodes(browse_node_ids=[17])
        assert res4.browse_node.id == "17"
