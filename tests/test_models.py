"""Unit tests for models and response deserialization."""

from __future__ import annotations

from amazon.models.browse_nodes import BrowseNodesResult
from amazon.models.common import Price
from amazon.models.items import GetItemsResult, GetVariationsResult, SearchResult
from tests.conftest import (
    MOCK_GET_BROWSE_NODES_CREATORS_RESPONSE,
    MOCK_GET_ITEMS_CREATORS_RESPONSE,
    MOCK_GET_VARIATIONS_CREATORS_RESPONSE,
    MOCK_SEARCH_ITEMS_CREATORS_RESPONSE,
)


def test_price_deserialization() -> None:
    p = Price.from_dict({"Amount": 19.99, "Currency": "USD", "DisplayAmount": "$19.99"})
    assert p is not None
    assert p.amount == 19.99
    assert p.currency == "USD"
    assert p.display_amount == "$19.99"

    assert Price.from_dict(None) is None
    assert Price.from_dict({}) is None


def test_get_items_model_properties() -> None:
    res = GetItemsResult.from_dict(MOCK_GET_ITEMS_CREATORS_RESPONSE)
    assert not res.has_errors
    assert res.to_dict() == MOCK_GET_ITEMS_CREATORS_RESPONSE
    assert len(res.items) == 1

    item = res.item
    assert item is not None
    assert item.asin == "B0041OSCBU"
    assert item.title == "Kindle Paperwhite (16 GB)"
    assert item.image_url == "https://m.media-amazon.com/images/I/image_lg.jpg"
    assert item.price is not None
    assert item.price.amount == 139.99
    assert item.item_info.brand == "Amazon"
    assert item.item_info.manufacturer == "Amazon"
    assert item.item_info.product_group == "Digital Device"
    assert len(item.item_info.features) == 3
    assert item.offers.listings[0].is_prime is True
    assert item.offers.listings[0].merchant_name == "Amazon.com"


def test_search_result_model_properties() -> None:
    res = SearchResult.from_dict(MOCK_SEARCH_ITEMS_CREATORS_RESPONSE)
    assert len(res.items) == 2
    assert res.pagination.total_result_count == 42
    assert res.pagination.total_pages == 5
    assert res.pagination.search_url.startswith("https://www.amazon.com/s")
    assert res.item.asin == "B0041OSCBU"


def test_variations_result_model_properties() -> None:
    res = GetVariationsResult.from_dict(MOCK_GET_VARIATIONS_CREATORS_RESPONSE)
    assert len(res.items) == 2
    assert res.variation_summary.page_count == 1
    assert res.variation_summary.variation_count == 2
    assert res.variation_summary.lowest_price.amount == 129.99
    assert res.variation_summary.highest_price.amount == 169.99


def test_browse_nodes_result_model_properties() -> None:
    res = BrowseNodesResult.from_dict(MOCK_GET_BROWSE_NODES_CREATORS_RESPONSE)
    assert len(res.browse_nodes) == 1
    node = res.browse_node
    assert node.id == "17"
    assert node.display_name == "Literature & Fiction"
    assert node.is_root is False
    assert node.ancestor.id == "283155"
    assert node.ancestor.display_name == "Books"
    assert len(node.children) == 2
    assert node.children[0].id == "10129"
