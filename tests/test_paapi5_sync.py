"""Unit tests for Amazon PA-API 5.0 (Synchronous client)."""

from __future__ import annotations

import json

import respx

from amazon.clients.paapi5 import AmazonPAAPI5
from tests.conftest import (
    MOCK_GET_BROWSE_NODES_CREATORS_RESPONSE,
    MOCK_GET_VARIATIONS_CREATORS_RESPONSE,
    MOCK_PAAPI5_GET_ITEMS_RESPONSE,
    MOCK_SEARCH_ITEMS_CREATORS_RESPONSE,
)


@respx.mock
def test_paapi5_get_items_success(paapi5_credentials: dict[str, str]) -> None:
    route = respx.post("https://webservices.amazon.com/paapi5/getitems").respond(
        status_code=200,
        json=MOCK_PAAPI5_GET_ITEMS_RESPONSE,
    )

    with AmazonPAAPI5(**paapi5_credentials) as api:
        res = api.get_items(item_ids=["B0041OSCBU"])

        assert len(res.items) == 1
        item = res.item
        assert item is not None
        assert item.asin == "B0041OSCBU"
        assert item.title == "Kindle Paperwhite (PA-API 5)"
        assert item.price.amount == 139.99

    assert route.call_count == 1
    sent_request = route.calls[0].request
    assert sent_request.headers["x-amz-target"] == "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.GetItems"
    assert "AWS4-HMAC-SHA256" in sent_request.headers["authorization"]

    sent_body = json.loads(sent_request.content.decode("utf-8"))
    assert sent_body["PartnerTag"] == "testpartner-20"
    assert sent_body["PartnerType"] == "Associates"
    assert sent_body["ItemIds"] == ["B0041OSCBU"]


@respx.mock
def test_paapi5_search_items_success(paapi5_credentials: dict[str, str]) -> None:
    route = respx.post("https://webservices.amazon.com/paapi5/searchitems").respond(
        status_code=200,
        json=MOCK_SEARCH_ITEMS_CREATORS_RESPONSE,
    )

    with AmazonPAAPI5(**paapi5_credentials) as api:
        res = api.search_items(keywords="Python", search_index="Books")
        assert len(res.items) == 2

    assert route.call_count == 1


@respx.mock
def test_paapi5_get_variations_success(paapi5_credentials: dict[str, str]) -> None:
    route = respx.post("https://webservices.amazon.com/paapi5/getvariations").respond(
        status_code=200,
        json=MOCK_GET_VARIATIONS_CREATORS_RESPONSE,
    )

    with AmazonPAAPI5(**paapi5_credentials) as api:
        res = api.get_variations(asin="B0041OSCBU")
        assert len(res.items) == 2

    assert route.call_count == 1


@respx.mock
def test_paapi5_get_browse_nodes_success(paapi5_credentials: dict[str, str]) -> None:
    route = respx.post("https://webservices.amazon.com/paapi5/getbrowsenodes").respond(
        status_code=200,
        json=MOCK_GET_BROWSE_NODES_CREATORS_RESPONSE,
    )

    with AmazonPAAPI5(**paapi5_credentials) as api:
        res = api.get_browse_nodes(browse_node_ids=["17"])
        assert len(res.browse_nodes) == 1

    assert route.call_count == 1
