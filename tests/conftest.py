"""Pytest fixtures and mock response payloads for Amazon API tests."""

from __future__ import annotations

import pytest
import respx

MOCK_OAUTH_TOKEN_RESPONSE = {
    "access_token": "mock-access-token-123456",
    "token_type": "bearer",
    "expires_in": 3600,
    "scope": "creatorsapi::default",
}

MOCK_GET_ITEMS_CREATORS_RESPONSE = {
    "itemsResult": {
        "items": [
            {
                "asin": "B0041OSCBU",
                "detailPageUrl": "https://www.amazon.com/dp/B0041OSCBU?tag=test-tag-20",
                "itemInfo": {
                    "title": {
                        "displayValue": "Kindle Paperwhite (16 GB)",
                        "label": "Title",
                        "locale": "en_US",
                    },
                    "byLineInfo": {
                        "brand": {"displayValue": "Amazon"},
                        "manufacturer": {"displayValue": "Amazon"},
                    },
                    "classifications": {
                        "productGroup": {"displayValue": "Digital Device"}
                    },
                    "features": {
                        "displayValues": ["6.8-inch display", "Adjustable warm light", "Up to 10 weeks battery"]
                    },
                },
                "images": {
                    "primary": {
                        "small": {"url": "https://m.media-amazon.com/images/I/image_small.jpg", "height": 75, "width": 75},
                        "medium": {"url": "https://m.media-amazon.com/images/I/image_med.jpg", "height": 160, "width": 160},
                        "large": {"url": "https://m.media-amazon.com/images/I/image_lg.jpg", "height": 500, "width": 500},
                    }
                },
                "offers": {
                    "listings": [
                        {
                            "id": "offer-listing-1",
                            "price": {
                                "amount": 139.99,
                                "currency": "USD",
                                "displayAmount": "$139.99",
                            },
                            "savingBasis": {
                                "amount": 149.99,
                                "currency": "USD",
                                "displayAmount": "$149.99",
                            },
                            "availability": {"type": "NOW", "message": "In Stock"},
                            "condition": {"value": "New"},
                            "deliveryInfo": {"isPrimeEligible": True},
                            "merchantInfo": {"id": "ATVPDKIKX0DER", "name": "Amazon.com"},
                        }
                    ],
                    "summaries": [
                        {
                            "lowestPrice": {
                                "amount": 139.99,
                                "currency": "USD",
                                "displayAmount": "$139.99",
                            }
                        }
                    ],
                },
            }
        ]
    }
}

MOCK_SEARCH_ITEMS_CREATORS_RESPONSE = {
    "searchResult": {
        "items": [
            {
                "asin": "B0041OSCBU",
                "detailPageUrl": "https://www.amazon.com/dp/B0041OSCBU",
                "itemInfo": {
                    "title": {"displayValue": "Test Search Product 1"},
                    "byLineInfo": {"brand": {"displayValue": "Brand A"}},
                },
                "offers": {
                    "listings": [
                        {
                            "price": {
                                "amount": 29.99,
                                "currency": "USD",
                                "displayAmount": "$29.99",
                            }
                        }
                    ]
                },
            },
            {
                "asin": "B0011ZK6PC",
                "detailPageUrl": "https://www.amazon.com/dp/B0011ZK6PC",
                "itemInfo": {
                    "title": {"displayValue": "Test Search Product 2"},
                },
            },
        ],
        "totalResultCount": 42,
        "totalPages": 5,
        "searchUrl": "https://www.amazon.com/s?k=test&tag=test-tag-20",
    }
}

MOCK_GET_VARIATIONS_CREATORS_RESPONSE = {
    "variationsResult": {
        "items": [
            {
                "asin": "B0041OSCBU_V1",
                "detailPageUrl": "https://www.amazon.com/dp/B0041OSCBU_V1",
                "itemInfo": {
                    "title": {"displayValue": "Product Black 16GB"},
                    "color": {"displayValue": "Black"},
                    "size": {"displayValue": "16GB"},
                },
            },
            {
                "asin": "B0041OSCBU_V2",
                "detailPageUrl": "https://www.amazon.com/dp/B0041OSCBU_V2",
                "itemInfo": {
                    "title": {"displayValue": "Product Denim 32GB"},
                    "color": {"displayValue": "Denim"},
                    "size": {"displayValue": "32GB"},
                },
            },
        ],
        "variationSummary": {
            "pageCount": 1,
            "variationCount": 2,
            "priceRange": {
                "lowestPrice": {"amount": 129.99, "currency": "USD", "displayAmount": "$129.99"},
                "highestPrice": {"amount": 169.99, "currency": "USD", "displayAmount": "$169.99"},
            },
        },
    }
}

MOCK_GET_BROWSE_NODES_CREATORS_RESPONSE = {
    "browseNodesResult": {
        "browseNodes": [
            {
                "id": "17",
                "displayName": "Literature & Fiction",
                "contextFreeName": "Books - Literature & Fiction",
                "isRoot": False,
                "ancestor": {
                    "id": "283155",
                    "displayName": "Books",
                    "contextFreeName": "Books",
                    "ancestor": None,
                },
                "children": [
                    {"id": "10129", "displayName": "Contemporary"},
                    {"id": "10134", "displayName": "Classics"},
                ],
            }
        ]
    }
}

MOCK_PAAPI5_GET_ITEMS_RESPONSE = {
    "ItemsResult": {
        "Items": [
            {
                "ASIN": "B0041OSCBU",
                "DetailPageURL": "https://www.amazon.com/dp/B0041OSCBU",
                "ItemInfo": {
                    "Title": {"DisplayValue": "Kindle Paperwhite (PA-API 5)"},
                    "ByLineInfo": {"Brand": {"DisplayValue": "Amazon"}},
                },
                "Offers": {
                    "Listings": [
                        {
                            "Price": {
                                "Amount": 139.99,
                                "Currency": "USD",
                                "DisplayAmount": "$139.99",
                            }
                        }
                    ]
                },
            }
        ]
    }
}


@pytest.fixture(autouse=True)
def mock_all_oauth_token_endpoints():
    """Automatically mock regional token endpoints."""
    respx.post("https://api.amazon.com/auth/o2/token").respond(
        status_code=200,
        json=MOCK_OAUTH_TOKEN_RESPONSE,
    )
    respx.post("https://api.amazon.co.uk/auth/o2/token").respond(
        status_code=200,
        json=MOCK_OAUTH_TOKEN_RESPONSE,
    )
    respx.post("https://api.amazon.co.jp/auth/o2/token").respond(
        status_code=200,
        json=MOCK_OAUTH_TOKEN_RESPONSE,
    )


@pytest.fixture
def creators_credentials() -> dict[str, str]:
    return {
        "credential_id": "test-credential-id-123",
        "credential_secret": "test-credential-secret-456",
        "marketplace": "US",
    }


@pytest.fixture
def paapi5_credentials() -> dict[str, str]:
    return {
        "access_key": "AKIAIOSFODNN7EXAMPLE",
        "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "associate_tag": "testpartner-20",
        "marketplace": "US",
    }
