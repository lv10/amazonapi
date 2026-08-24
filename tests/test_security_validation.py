"""Security tests: Input validation, parameter bounds checking, and operation allowlisting."""

from __future__ import annotations

import pytest

from amazon.clients.creators import AmazonCreatorsAPI
from amazon.clients.paapi5 import AmazonPAAPI5
from amazon.exceptions import AmazonBadRequestError


def test_creators_input_validation(creators_credentials: dict[str, str]) -> None:
    client = AmazonCreatorsAPI(**creators_credentials)

    # Empty / whitespace / invalid item_ids
    with pytest.raises(AmazonBadRequestError, match="item_ids list cannot be empty"):
        client.get_items(item_ids=[])

    with pytest.raises(AmazonBadRequestError, match="item_ids list cannot be empty"):
        client.get_items(item_ids=["   ", ""])

    with pytest.raises(AmazonBadRequestError, match="maximum of 10 item_ids"):
        client.get_items(item_ids=[f"ASIN{i}" for i in range(11)])

    # Empty asin in get_variations
    with pytest.raises(AmazonBadRequestError, match="asin cannot be empty"):
        client.get_variations(asin="")

    with pytest.raises(AmazonBadRequestError, match="asin cannot be empty"):
        client.get_variations(asin="   ")

    # Invalid variations count / page
    with pytest.raises(AmazonBadRequestError, match="variation_count must be between 1 and 10"):
        client.get_variations(asin="B0041OSCBU", variation_count=0)

    with pytest.raises(AmazonBadRequestError, match="variation_page must be between 1 and 10"):
        client.get_variations(asin="B0041OSCBU", variation_page=11)

    # Search params validation
    with pytest.raises(AmazonBadRequestError, match="item_count must be between 1 and 10"):
        client.search_items(keywords="test", item_count=0)

    with pytest.raises(AmazonBadRequestError, match="item_page must be between 1 and 10"):
        client.search_items(keywords="test", item_page=15)

    with pytest.raises(AmazonBadRequestError, match="min_price cannot be negative"):
        client.search_items(keywords="test", min_price=-10)

    with pytest.raises(AmazonBadRequestError, match="max_price cannot be negative"):
        client.search_items(keywords="test", max_price=-5)

    with pytest.raises(AmazonBadRequestError, match="cannot be greater than max_price"):
        client.search_items(keywords="test", min_price=5000, max_price=1000)

    with pytest.raises(AmazonBadRequestError, match="min_reviews_rating must be between 1 and 5"):
        client.search_items(keywords="test", min_reviews_rating=6)

    with pytest.raises(AmazonBadRequestError, match="min_saving_percent must be between 1 and 100"):
        client.search_items(keywords="test", min_saving_percent=150)

    # Browse node IDs validation
    with pytest.raises(AmazonBadRequestError, match="browse_node_ids list cannot be empty"):
        client.get_browse_nodes(browse_node_ids=[])

    with pytest.raises(AmazonBadRequestError, match="maximum of 10 browse_node_ids"):
        client.get_browse_nodes(browse_node_ids=list(range(11)))

    # Endpoint injection protection
    with pytest.raises(AmazonBadRequestError, match="Invalid Creators API endpoint"):
        client._execute_request(endpoint="../../admin", payload={})

    client.close()


def test_paapi5_input_validation(paapi5_credentials: dict[str, str]) -> None:
    client = AmazonPAAPI5(**paapi5_credentials)

    # Empty / whitespace / invalid item_ids
    with pytest.raises(AmazonBadRequestError, match="item_ids list cannot be empty"):
        client.get_items(item_ids=[])

    with pytest.raises(AmazonBadRequestError, match="item_ids list cannot be empty"):
        client.get_items(item_ids=["", "  "])

    with pytest.raises(AmazonBadRequestError, match="maximum of 10 item_ids"):
        client.get_items(item_ids=[f"ASIN{i}" for i in range(11)])

    # Empty asin
    with pytest.raises(AmazonBadRequestError, match="asin cannot be empty"):
        client.get_variations(asin="   ")

    # Invalid variations count / page
    with pytest.raises(AmazonBadRequestError, match="variation_count must be between 1 and 10"):
        client.get_variations(asin="B0041OSCBU", variation_count=15)

    with pytest.raises(AmazonBadRequestError, match="variation_page must be between 1 and 10"):
        client.get_variations(asin="B0041OSCBU", variation_page=0)

    # Search params validation
    with pytest.raises(AmazonBadRequestError, match="item_count must be between 1 and 10"):
        client.search_items(keywords="test", item_count=20)

    with pytest.raises(AmazonBadRequestError, match="min_price cannot be negative"):
        client.search_items(keywords="test", min_price=-100)

    with pytest.raises(AmazonBadRequestError, match="cannot be greater than max_price"):
        client.search_items(keywords="test", min_price=2000, max_price=500)

    # Browse node IDs validation
    with pytest.raises(AmazonBadRequestError, match="browse_node_ids list cannot be empty"):
        client.get_browse_nodes(browse_node_ids=[])

    with pytest.raises(AmazonBadRequestError, match="maximum of 10 browse_node_ids"):
        client.get_browse_nodes(browse_node_ids=[str(i) for i in range(12)])

    # Operation injection protection
    with pytest.raises(AmazonBadRequestError, match="Invalid PA-API 5.0 operation"):
        client._execute_request(operation="ArbitraryOperation\r\nInjected-Header: 1", payload={})

    client.close()
