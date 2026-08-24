# AmazonAPIWrapper

[![PyPI version](https://img.shields.io/pypi/v/AmazonAPIWrapper.svg)](https://pypi.org/project/AmazonAPIWrapper/)
[![Python Versions](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://pypi.org/project/AmazonAPIWrapper/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/lv10/amazonapi/actions/workflows/ci.yml/badge.svg)](https://github.com/lv10/amazonapi/actions/workflows/ci.yml)

A modern, high-performance, asynchronous and synchronous Python client for the Amazon Catalog APIs.

Supports both Amazon's modern **Creators API** (OAuth 2.0) and **Product Advertising API 5.0 (PA-API 5.0)** (AWS SigV4), with complete type hints, automatic OAuth token management, exponential backoff retries, and Python 3.9 through 3.13+ support.

---

## Features

- ⚡ **Async & Sync Support**: Native support for standard synchronous code and asynchronous `asyncio` code powered by `httpx`.
- 🔐 **Dual Protocol Engines**:
  - **Amazon Creators API**: Modern OAuth 2.0 client credentials flow with automatic token caching and proactive refresh.
  - **Amazon PA-API 5.0**: AWS Signature Version 4 (SigV4) request signing for AWS IAM credentials.
- 📦 **Complete Catalog Operations**:
  - `get_items`: Detailed product lookup by ASIN (supports batching up to 10 items).
  - `search_items`: Rich product search with filters (actor, brand, category, price range, review rating, sort order).
  - `get_variations`: Retrieve child variation ASINs, colors, sizes, and price ranges.
  - `get_browse_nodes`: Browse category trees, parent ancestors, and child subcategories.
- 🌍 **Global Marketplace Support**: Native routing across 20+ Amazon global marketplaces (`US`, `UK`, `DE`, `FR`, `JP`, `CA`, `IT`, `ES`, `IN`, `BR`, `MX`, `AU`, `AE`, `SG`, `SA`, `TR`, `NL`, `PL`, `SE`, `EG`, `BE`).
- 🛡️ **Robust Error Handling**: Structured exception hierarchy (`AmazonThrottlingError`, `AmazonAuthenticationError`, `AmazonBadRequestError`, etc.) with built-in retry mechanisms for rate-limited requests.
- 🚀 **Modern Tooling**: Managed with [uv](https://github.com/astral-sh/uv), fully typed (PEP 561), and tested with `pytest`.

---

## Installation

Install using `pip`:

```bash
pip install AmazonAPIWrapper
```

Or using `uv`:

```bash
uv add AmazonAPIWrapper
```

---

## Quickstart

### 1. Amazon Creators API (Recommended)

To use the modern Amazon Creators API, you need your **Credential ID** and **Credential Secret** from Amazon Associates Central (**Tools > Creators API**).

#### Synchronous Example

```python
from amazon import AmazonAPI, Marketplace

# Initialize client
with AmazonAPI(
    credential_id="YOUR_CREDENTIAL_ID",
    credential_secret="YOUR_CREDENTIAL_SECRET",
    marketplace=Marketplace.US,
) as api:
    # Look up products by ASIN
    response = api.get_items(item_ids=["B0041OSCBU"])

    if response.item:
        print(f"Title: {response.item.title}")
        print(f"Price: {response.item.price.display_amount}")
        print(f"Image: {response.item.image_url}")

    # Search products
    search_res = api.search_items(
        keywords="Python Programming",
        search_index="Books",
        item_count=5,
    )
    for item in search_res.items:
        print(f"{item.asin}: {item.title}")
```

#### Asynchronous Example (`asyncio`)

```python
import asyncio
from amazon import AsyncAmazonAPI, Marketplace

async def main():
    async with AsyncAmazonAPI(
        credential_id="YOUR_CREDENTIAL_ID",
        credential_secret="YOUR_CREDENTIAL_SECRET",
        marketplace=Marketplace.US,
    ) as api:
        # Batch lookup
        response = await api.get_items(item_ids=["B0041OSCBU", "B0011ZK6PC"])
        for item in response.items:
            print(f"{item.asin} -> {item.title} ({item.price.display_amount if item.price else 'N/A'})")

asyncio.run(main())
```

---

### 2. PA-API 5.0 (AWS SigV4)

If you have legacy AWS IAM credentials for PA-API 5.0:

```python
from amazon import AmazonPAAPI5, Marketplace

api = AmazonPAAPI5(
    access_key="YOUR_AWS_ACCESS_KEY",
    secret_key="YOUR_AWS_SECRET_KEY",
    associate_tag="yourtag-20",
    marketplace=Marketplace.US,
)

response = api.get_items(item_ids=["B0041OSCBU"])
print(response.item.title)
```

---

## Detailed Operations

### Product Lookup (`get_items`)

Retrieve rich metadata for up to 10 ASINs per call:

```python
response = api.get_items(
    item_ids=["B0041OSCBU", "B08N5WRWNW"],
    resources=[
        "ItemInfo.Title",
        "ItemInfo.ByLineInfo",
        "Images.Primary.Large",
        "Offers.Listings.Price",
        "Offers.Listings.DeliveryInfo.IsPrimeEligible",
    ]
)

for item in response.items:
    print("ASIN:", item.asin)
    print("Title:", item.title)
    print("Brand:", item.item_info.brand if item.item_info else None)
    if item.offers and item.offers.listings:
        listing = item.offers.listings[0]
        print("Price:", listing.price.display_amount if listing.price else None)
        print("Prime Eligible:", listing.is_prime)
```

### Product Search (`search_items`)

Search the Amazon catalog with advanced filters:

```python
search_res = api.search_items(
    keywords="wireless headphones",
    brand="Sony",
    search_index="Electronics",
    min_price=5000,          # in cents (e.g. $50.00)
    max_price=30000,         # in cents (e.g. $300.00)
    min_reviews_rating=4,    # 4 stars and above
    sort_by="Price:LowToHigh",
    item_count=10,
    item_page=1,
)

print(f"Total Results: {search_res.pagination.total_result_count}")
for item in search_res.items:
    print(f"- {item.title}")
```

### Product Variations (`get_variations`)

Get child variations (colors, sizes) for a parent ASIN:

```python
variations = api.get_variations(
    asin="B0041OSCBU",
    variation_count=10,
)

if variations.variation_summary:
    print(f"Price Range: {variations.variation_summary.lowest_price.display_amount} - {variations.variation_summary.highest_price.display_amount}")

for item in variations.items:
    print(f"Child ASIN: {item.asin}, Color: {item.item_info.color}, Size: {item.item_info.size}")
```

### Category Browse Nodes (`get_browse_nodes`)

Inspect category trees and subcategories:

```python
nodes = api.get_browse_nodes(browse_node_ids=["17"])

node = nodes.browse_node
if node:
    print(f"Category: {node.display_name} (ID: {node.id})")
    if node.ancestor:
        print(f"Parent Category: {node.ancestor.display_name}")
    for child in node.children:
        print(f"Subcategory: {child.display_name} (ID: {child.id})")
```

---

## Supported Marketplaces

You can specify marketplaces using the `Marketplace` enum, 2-letter country codes (`'US'`, `'UK'`, `'DE'`, etc.), or domain names (`'www.amazon.com'`):

| Marketplace | Code | Domain | Currency |
| :--- | :--- | :--- | :--- |
| United States | `Marketplace.US` | `www.amazon.com` | USD |
| United Kingdom | `Marketplace.UK` | `www.amazon.co.uk` | GBP |
| Germany | `Marketplace.DE` | `www.amazon.de` | EUR |
| France | `Marketplace.FR` | `www.amazon.fr` | EUR |
| Japan | `Marketplace.JP` | `www.amazon.co.jp` | JPY |
| Canada | `Marketplace.CA` | `www.amazon.ca` | CAD |
| Italy | `Marketplace.IT` | `www.amazon.it` | EUR |
| Spain | `Marketplace.ES` | `www.amazon.es` | EUR |
| India | `Marketplace.IN` | `www.amazon.in` | INR |
| Australia | `Marketplace.AU` | `www.amazon.com.au` | AUD |
| Brazil | `Marketplace.BR` | `www.amazon.com.br` | BRL |
| Mexico | `Marketplace.MX` | `www.amazon.com.mx` | MXN |
| Netherlands | `Marketplace.NL` | `www.amazon.nl` | EUR |
| Poland | `Marketplace.PL` | `www.amazon.pl` | PLN |
| Sweden | `Marketplace.SE` | `www.amazon.se` | SEK |
| Turkey | `Marketplace.TR` | `www.amazon.com.tr` | TRY |
| United Arab Emirates | `Marketplace.AE` | `www.amazon.ae` | AED |
| Saudi Arabia | `Marketplace.SA` | `www.amazon.sa` | SAR |
| Singapore | `Marketplace.SG` | `www.amazon.sg` | SGD |
| Egypt | `Marketplace.EG` | `www.amazon.eg` | EGP |
| Belgium | `Marketplace.BE` | `www.amazon.com.be` | EUR |

---

## Error Handling

AmazonAPIWrapper provides a comprehensive typed exception hierarchy:

```python
from amazon import AmazonAPI
from amazon.exceptions import (
    AmazonAPIError,
    AmazonAuthenticationError,
    AmazonBadRequestError,
    AmazonNotFoundError,
    AmazonThrottlingError,
    AmazonServerError,
)

try:
    with AmazonAPI(credential_id="...", credential_secret="...") as api:
        response = api.get_items(item_ids=["INVALID_ASIN"])
except AmazonThrottlingError as e:
    print(f"Rate limit exceeded (HTTP {e.status_code}): {e.message}")
except AmazonAuthenticationError as e:
    print(f"Invalid credentials (HTTP {e.status_code}): {e.message}")
except AmazonBadRequestError as e:
    print(f"Invalid request parameters: {e.message}")
except AmazonNotFoundError as e:
    print(f"Item not found: {e.message}")
except AmazonServerError as e:
    print(f"Amazon internal error: {e.message}")
except AmazonAPIError as e:
    print(f"General Amazon API error: {e.message}")
```

---

## Migration from v0.0.x to v1.0.0

If you are updating from the legacy Python 2.7 XML wrapper (`0.0.11`):

1. **Python 3.9+ Required**: Update your Python runtime to Python 3.9 or higher.
2. **Credentials**: Switch from legacy XML keys to **Creators API credentials** (or pass `access_key`, `secret_key`, and `associate_tag` for PA-API 5.0).
3. **Methods**:
   - `amz.item_lookup(ItemId=...)` $\rightarrow$ `api.get_items(item_ids=[...])`
   - `amz.item_search(Keywords=...)` $\rightarrow$ `api.search_items(keywords=...)`
   - `amz.node_browse_lookup(browse_node_id=...)` $\rightarrow$ `api.get_browse_nodes(browse_node_ids=[...])`
4. **Response Format**: Instead of parsing BeautifulSoup XML objects, responses are now typed Python objects (`response.item.title`, `response.items`, `response.to_dict()`).

---

## Development & Testing

This project uses [uv](https://github.com/astral-sh/uv) for fast and reliable dependency management.

### Setup

```bash
# Clone the repository
git clone https://github.com/lv10/amazonapi.git
cd amazonapi

# Install dependencies and sync environment
uv sync --all-extras
```

### Running Tests

Run the full offline true unit test suite with coverage:

```bash
uv run pytest
```

### Linting and Type Checking

```bash
# Lint code with Ruff
uv run ruff check .

# Type check with Mypy
uv run mypy amazon
```

### Building Distribution

```bash
uv build
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
