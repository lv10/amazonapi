"""Unit tests for Amazon Creators API (Synchronous client)."""

from __future__ import annotations

import json

import pytest
import respx

from amazon.clients.creators import CREATORS_API_BASE_URL, AmazonCreatorsAPI
from amazon.exceptions import AmazonBadRequestError
from tests.conftest import (
    MOCK_GET_BROWSE_NODES_CREATORS_RESPONSE,
    MOCK_GET_ITEMS_CREATORS_RESPONSE,
    MOCK_GET_VARIATIONS_CREATORS_RESPONSE,
    MOCK_SEARCH_ITEMS_CREATORS_RESPONSE,
)


@respx.mock
def test_creators_get_items_success() -> None:
    route = respx.post(f"{CREATORS_API_BASE_URL}/getItems").respond(
        status_code=200,
        json=MOCK_GET_ITEMS_CREATORS_RESPONSE,
    )

    with AmazonCreatorsAPI(credential_id="id", credential_secret="secret", marketplace="US") as api:
        res = api.get_items(item_ids=["B0041OSCBU"])

        assert res.has_errors is False
        assert len(res.items) == 1
        item = res.item
        assert item is not None
        assert item.asin == "B0041OSCBU"
        assert item.title == "Kindle Paperwhite (16 GB)"
        assert item.price is not None
        assert item.price.amount == 139.99
        assert item.price.currency == "USD"
        assert item.image_url == "https://m.media-amazon.com/images/I/image_lg.jpg"

    assert route.call_count == 1
    sent_request = route.calls[0].request
    assert sent_request.headers["x-marketplace"] == "www.amazon.com"
    assert sent_request.headers["Authorization"] == "Bearer mock-access-token-123456"

    sent_body = json.loads(sent_request.content.decode("utf-8"))
    assert sent_body["itemIds"] == ["B0041OSCBU"]


@respx.mock
def test_creators_get_items_raw_mode() -> None:
    respx.post(f"{CREATORS_API_BASE_URL}/getItems").respond(
        status_code=200,
        json=MOCK_GET_ITEMS_CREATORS_RESPONSE,
    )

    api = AmazonCreatorsAPI(credential_id="id", credential_secret="secret")
    raw_data = api.get_items(item_ids="B0041OSCBU", raw=True)
    assert isinstance(raw_data, dict)
    assert "itemsResult" in raw_data
    api.close()


def test_creators_get_items_validation_errors() -> None:
    api = AmazonCreatorsAPI(credential_id="id", credential_secret="secret")

    with pytest.raises(AmazonBadRequestError):
        api.get_items(item_ids=[])

    with pytest.raises(AmazonBadRequestError):
        api.get_items(item_ids=[f"B00000000{i}" for i in range(11)])

    api.close()


@respx.mock
def test_creators_search_items_success() -> None:
    route = respx.post(f"{CREATORS_API_BASE_URL}/searchItems").respond(
        status_code=200,
        json=MOCK_SEARCH_ITEMS_CREATORS_RESPONSE,
    )

    with AmazonCreatorsAPI(credential_id="id", credential_secret="secret", marketplace="UK") as api:
        res = api.search_items(
            keywords="Kindle",
            brand="Amazon",
            search_index="Electronics",
            item_count=5,
            min_price=1000,
            max_price=5000,
            sort_by="Price:LowToHigh",
        )

        assert len(res.items) == 2
        assert res.pagination is not None
        assert res.pagination.total_result_count == 42
        assert res.pagination.total_pages == 5

    assert route.call_count == 1
    sent_request = route.calls[0].request
    assert sent_request.headers["x-marketplace"] == "www.amazon.co.uk"
    sent_body = json.loads(sent_request.content.decode("utf-8"))
    assert sent_body["keywords"] == "Kindle"
    assert sent_body["brand"] == "Amazon"
    assert sent_body["searchIndex"] == "Electronics"
    assert sent_body["itemCount"] == 5
    assert sent_body["minPrice"] == 1000
    assert sent_body["maxPrice"] == 5000
    assert sent_body["sortBy"] == "Price:LowToHigh"


@respx.mock
def test_creators_get_variations_success() -> None:
    route = respx.post(f"{CREATORS_API_BASE_URL}/getVariations").respond(
        status_code=200,
        json=MOCK_GET_VARIATIONS_CREATORS_RESPONSE,
    )

    with AmazonCreatorsAPI(credential_id="id", credential_secret="secret") as api:
        res = api.get_variations(asin="B0041OSCBU", variation_count=5)

        assert len(res.items) == 2
        assert res.items[0].asin == "B0041OSCBU_V1"
        assert res.items[0].item_info.color == "Black"
        assert res.items[0].item_info.size == "16GB"
        assert res.variation_summary is not None
        assert res.variation_summary.variation_count == 2
        assert res.variation_summary.lowest_price.amount == 129.99
        assert res.variation_summary.highest_price.amount == 169.99

    assert route.call_count == 1


def test_creators_get_variations_empty_asin() -> None:
    api = AmazonCreatorsAPI(credential_id="id", credential_secret="secret")
    with pytest.raises(AmazonBadRequestError):
        api.get_variations(asin="")
    api.close()


@respx.mock
def test_creators_get_browse_nodes_success() -> None:
    route = respx.post(f"{CREATORS_API_BASE_URL}/getBrowseNodes").respond(
        status_code=200,
        json=MOCK_GET_BROWSE_NODES_CREATORS_RESPONSE,
    )

    with AmazonCreatorsAPI(credential_id="id", credential_secret="secret") as api:
        res = api.get_browse_nodes(browse_node_ids=[17])

        assert len(res.browse_nodes) == 1
        node = res.browse_node
        assert node is not None
        assert node.id == "17"
        assert node.display_name == "Literature & Fiction"
        assert node.ancestor is not None
        assert node.ancestor.id == "283155"
        assert node.ancestor.display_name == "Books"
        assert len(node.children) == 2
        assert node.children[0].display_name == "Contemporary"

    assert route.call_count == 1
