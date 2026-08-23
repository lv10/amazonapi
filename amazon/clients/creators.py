"""Amazon Creators API Synchronous and Asynchronous Clients."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, cast

import httpx

from amazon.auth.oauth import OAuthTokenManager
from amazon.clients.base import (
    DEFAULT_BROWSE_NODE_RESOURCES,
    DEFAULT_ITEM_RESOURCES,
    DEFAULT_VARIATION_RESOURCES,
    map_http_error,
)
from amazon.exceptions import AmazonBadRequestError
from amazon.marketplaces import Marketplace, MarketplaceInfo, resolve_marketplace
from amazon.models.browse_nodes import BrowseNodesResult
from amazon.models.items import GetItemsResult, GetVariationsResult, SearchResult

logger = logging.getLogger("amazonapi")

CREATORS_API_BASE_URL = "https://creatorsapi.amazon/catalog/v1"


class AmazonCreatorsAPI:
    """Synchronous client for Amazon Creators API (OAuth 2.0)."""

    def __init__(
        self,
        credential_id: str,
        credential_secret: str,
        marketplace: str | Marketplace = Marketplace.US,
        timeout: float = 30.0,
        max_retries: int = 2,
        retry_delay: float = 1.0,
    ) -> None:
        """Initialize AmazonCreatorsAPI client.

        Args:
            credential_id: Amazon Associate Creators API Credential ID.
            credential_secret: Amazon Associate Creators API Credential Secret.
            marketplace: Target Amazon marketplace (e.g. 'US', 'UK', Marketplace.US).
            timeout: HTTP request timeout in seconds (default: 30.0).
            max_retries: Maximum number of retries for throttled/transient errors.
            retry_delay: Initial retry delay in seconds.
        """
        self.marketplace_info: MarketplaceInfo = resolve_marketplace(marketplace)
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.token_manager = OAuthTokenManager(
            credential_id=credential_id,
            credential_secret=credential_secret,
            token_url=self.marketplace_info.token_url,
        )
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Get or initialize the underlying httpx.Client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def __enter__(self) -> AmazonCreatorsAPI:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client session."""
        if self._client and not self._client.is_closed:
            self._client.close()

    def _execute_request(self, endpoint: str, payload: dict[str, Any], marketplace: str | Marketplace | None = None) -> dict[str, Any]:
        target_mp = resolve_marketplace(marketplace) if marketplace else self.marketplace_info
        url = f"{CREATORS_API_BASE_URL}/{endpoint.lstrip('/')}"

        retries = 0
        while True:
            token = self.token_manager.get_token(self.client)
            headers = {
                "Authorization": f"Bearer {token}",
                "x-marketplace": target_mp.domain,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            try:
                response = self.client.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    return cast(dict[str, Any], response.json())

                if response.status_code == 401 and retries < self.max_retries:
                    self.token_manager.clear_cache()
                    retries += 1
                    time.sleep(self.retry_delay)
                    continue

                if response.status_code == 429 and retries < self.max_retries:
                    retries += 1
                    time.sleep(self.retry_delay * (2 ** (retries - 1)))
                    continue

                raise map_http_error(response)

            except httpx.RequestError as exc:
                if retries < self.max_retries:
                    retries += 1
                    time.sleep(self.retry_delay * (2 ** (retries - 1)))
                    continue
                raise exc

    def get_items(
        self,
        item_ids: str | list[str],
        resources: list[str] | None = None,
        marketplace: str | Marketplace | None = None,
        raw: bool = False,
    ) -> GetItemsResult | dict[str, Any]:
        """Retrieve detailed product information for up to 10 ASINs.

        Args:
            item_ids: A single ASIN string or list of up to 10 ASINs.
            resources: Optional list of requested resource fields.
            marketplace: Optional marketplace override.
            raw: If True, returns the raw API response dictionary.

        Returns:
            GetItemsResult model or raw dictionary.
        """
        if isinstance(item_ids, str):
            item_ids = [item_ids]

        if not item_ids:
            raise AmazonBadRequestError("item_ids list cannot be empty")

        if len(item_ids) > 10:
            raise AmazonBadRequestError("A maximum of 10 item_ids can be requested per call")

        payload: dict[str, Any] = {
            "itemIds": item_ids,
            "resources": resources if resources is not None else DEFAULT_ITEM_RESOURCES,
        }

        data = self._execute_request("getItems", payload, marketplace=marketplace)
        return data if raw else GetItemsResult.from_dict(data)

    def search_items(
        self,
        keywords: str | None = None,
        actor: str | None = None,
        artist: str | None = None,
        author: str | None = None,
        brand: str | None = None,
        browse_node_id: str | int | None = None,
        title: str | None = None,
        search_index: str = "All",
        item_count: int = 10,
        item_page: int = 1,
        min_price: int | None = None,
        max_price: int | None = None,
        min_reviews_rating: int | None = None,
        min_saving_percent: int | None = None,
        sort_by: str | None = None,
        resources: list[str] | None = None,
        marketplace: str | Marketplace | None = None,
        raw: bool = False,
    ) -> SearchResult | dict[str, Any]:
        """Search products across the Amazon catalog.

        Args:
            keywords: Search query keywords.
            actor: Actor name filter.
            artist: Artist name filter.
            author: Author name filter.
            brand: Brand filter.
            browse_node_id: Category browse node ID.
            title: Title keywords filter.
            search_index: Product category search index (default: 'All').
            item_count: Number of results to return (1-10, default: 10).
            item_page: Page number of results (1-10, default: 1).
            min_price: Minimum price in lowest currency denomination (e.g. cents).
            max_price: Maximum price in lowest currency denomination.
            min_reviews_rating: Minimum review rating (1-5).
            min_saving_percent: Minimum discount percentage (1-100).
            sort_by: Sorting criterion (e.g. 'Featured', 'LowToHigh', 'HighToLow').
            resources: Optional list of requested resource fields.
            marketplace: Optional marketplace override.
            raw: If True, returns the raw API response dictionary.

        Returns:
            SearchResult model or raw dictionary.
        """
        payload: dict[str, Any] = {
            "searchIndex": search_index,
            "itemCount": item_count,
            "itemPage": item_page,
            "resources": resources if resources is not None else DEFAULT_ITEM_RESOURCES,
        }

        if keywords:
            payload["keywords"] = keywords
        if actor:
            payload["actor"] = actor
        if artist:
            payload["artist"] = artist
        if author:
            payload["author"] = author
        if brand:
            payload["brand"] = brand
        if browse_node_id:
            payload["browseNodeId"] = str(browse_node_id)
        if title:
            payload["title"] = title
        if min_price is not None:
            payload["minPrice"] = min_price
        if max_price is not None:
            payload["maxPrice"] = max_price
        if min_reviews_rating is not None:
            payload["minReviewsRating"] = min_reviews_rating
        if min_saving_percent is not None:
            payload["minSavingPercent"] = min_saving_percent
        if sort_by:
            payload["sortBy"] = sort_by

        data = self._execute_request("searchItems", payload, marketplace=marketplace)
        return data if raw else SearchResult.from_dict(data)

    def get_variations(
        self,
        asin: str,
        variation_count: int = 10,
        variation_page: int = 1,
        resources: list[str] | None = None,
        marketplace: str | Marketplace | None = None,
        raw: bool = False,
    ) -> GetVariationsResult | dict[str, Any]:
        """Retrieve variation items for a parent ASIN.

        Args:
            asin: Parent product ASIN.
            variation_count: Number of variations to return (1-10, default: 10).
            variation_page: Page number of variations (1-10, default: 1).
            resources: Optional list of requested resource fields.
            marketplace: Optional marketplace override.
            raw: If True, returns raw API response dictionary.

        Returns:
            GetVariationsResult model or raw dictionary.
        """
        if not asin:
            raise AmazonBadRequestError("asin cannot be empty")

        payload: dict[str, Any] = {
            "asin": asin,
            "variationCount": variation_count,
            "variationPage": variation_page,
            "resources": resources if resources is not None else DEFAULT_VARIATION_RESOURCES,
        }

        data = self._execute_request("getVariations", payload, marketplace=marketplace)
        return data if raw else GetVariationsResult.from_dict(data)

    def get_browse_nodes(
        self,
        browse_node_ids: str | int | list[str | int],
        resources: list[str] | None = None,
        marketplace: str | Marketplace | None = None,
        raw: bool = False,
    ) -> BrowseNodesResult | dict[str, Any]:
        """Retrieve category browse node information for up to 10 IDs.

        Args:
            browse_node_ids: Single ID or list of up to 10 Browse Node IDs.
            resources: Optional list of requested resource fields.
            marketplace: Optional marketplace override.
            raw: If True, returns raw API response dictionary.

        Returns:
            BrowseNodesResult model or raw dictionary.
        """
        if isinstance(browse_node_ids, (str, int)):
            browse_node_ids = [browse_node_ids]

        node_ids_str = [str(n) for n in browse_node_ids]
        if not node_ids_str:
            raise AmazonBadRequestError("browse_node_ids list cannot be empty")

        if len(node_ids_str) > 10:
            raise AmazonBadRequestError("A maximum of 10 browse_node_ids can be requested per call")

        payload: dict[str, Any] = {
            "browseNodeIds": node_ids_str,
            "resources": resources if resources is not None else DEFAULT_BROWSE_NODE_RESOURCES,
        }

        data = self._execute_request("getBrowseNodes", payload, marketplace=marketplace)
        return data if raw else BrowseNodesResult.from_dict(data)


class AsyncAmazonCreatorsAPI:
    """Asynchronous client for Amazon Creators API (OAuth 2.0)."""

    def __init__(
        self,
        credential_id: str,
        credential_secret: str,
        marketplace: str | Marketplace = Marketplace.US,
        timeout: float = 30.0,
        max_retries: int = 2,
        retry_delay: float = 1.0,
    ) -> None:
        """Initialize AsyncAmazonCreatorsAPI client."""
        self.marketplace_info: MarketplaceInfo = resolve_marketplace(marketplace)
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.token_manager = OAuthTokenManager(
            credential_id=credential_id,
            credential_secret=credential_secret,
            token_url=self.marketplace_info.token_url,
        )
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or initialize the underlying httpx.AsyncClient."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def __aenter__(self) -> AsyncAmazonCreatorsAPI:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client session."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _execute_request(
        self, endpoint: str, payload: dict[str, Any], marketplace: str | Marketplace | None = None
    ) -> dict[str, Any]:
        target_mp = resolve_marketplace(marketplace) if marketplace else self.marketplace_info
        url = f"{CREATORS_API_BASE_URL}/{endpoint.lstrip('/')}"

        retries = 0
        while True:
            token = await self.token_manager.get_token_async(self.client)
            headers = {
                "Authorization": f"Bearer {token}",
                "x-marketplace": target_mp.domain,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            try:
                response = await self.client.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    return cast(dict[str, Any], response.json())

                if response.status_code == 401 and retries < self.max_retries:
                    self.token_manager.clear_cache()
                    retries += 1
                    await asyncio.sleep(self.retry_delay)
                    continue

                if response.status_code == 429 and retries < self.max_retries:
                    retries += 1
                    await asyncio.sleep(self.retry_delay * (2 ** (retries - 1)))
                    continue

                raise map_http_error(response)

            except httpx.RequestError as exc:
                if retries < self.max_retries:
                    retries += 1
                    await asyncio.sleep(self.retry_delay * (2 ** (retries - 1)))
                    continue
                raise exc

    async def get_items(
        self,
        item_ids: str | list[str],
        resources: list[str] | None = None,
        marketplace: str | Marketplace | None = None,
        raw: bool = False,
    ) -> GetItemsResult | dict[str, Any]:
        """Retrieve detailed product information for up to 10 ASINs asynchronously."""
        if isinstance(item_ids, str):
            item_ids = [item_ids]

        if not item_ids:
            raise AmazonBadRequestError("item_ids list cannot be empty")

        if len(item_ids) > 10:
            raise AmazonBadRequestError("A maximum of 10 item_ids can be requested per call")

        payload: dict[str, Any] = {
            "itemIds": item_ids,
            "resources": resources if resources is not None else DEFAULT_ITEM_RESOURCES,
        }

        data = await self._execute_request("getItems", payload, marketplace=marketplace)
        return data if raw else GetItemsResult.from_dict(data)

    async def search_items(
        self,
        keywords: str | None = None,
        actor: str | None = None,
        artist: str | None = None,
        author: str | None = None,
        brand: str | None = None,
        browse_node_id: str | int | None = None,
        title: str | None = None,
        search_index: str = "All",
        item_count: int = 10,
        item_page: int = 1,
        min_price: int | None = None,
        max_price: int | None = None,
        min_reviews_rating: int | None = None,
        min_saving_percent: int | None = None,
        sort_by: str | None = None,
        resources: list[str] | None = None,
        marketplace: str | Marketplace | None = None,
        raw: bool = False,
    ) -> SearchResult | dict[str, Any]:
        """Search products across the Amazon catalog asynchronously."""
        payload: dict[str, Any] = {
            "searchIndex": search_index,
            "itemCount": item_count,
            "itemPage": item_page,
            "resources": resources if resources is not None else DEFAULT_ITEM_RESOURCES,
        }

        if keywords:
            payload["keywords"] = keywords
        if actor:
            payload["actor"] = actor
        if artist:
            payload["artist"] = artist
        if author:
            payload["author"] = author
        if brand:
            payload["brand"] = brand
        if browse_node_id:
            payload["browseNodeId"] = str(browse_node_id)
        if title:
            payload["title"] = title
        if min_price is not None:
            payload["minPrice"] = min_price
        if max_price is not None:
            payload["maxPrice"] = max_price
        if min_reviews_rating is not None:
            payload["minReviewsRating"] = min_reviews_rating
        if min_saving_percent is not None:
            payload["minSavingPercent"] = min_saving_percent
        if sort_by:
            payload["sortBy"] = sort_by

        data = await self._execute_request("searchItems", payload, marketplace=marketplace)
        return data if raw else SearchResult.from_dict(data)

    async def get_variations(
        self,
        asin: str,
        variation_count: int = 10,
        variation_page: int = 1,
        resources: list[str] | None = None,
        marketplace: str | Marketplace | None = None,
        raw: bool = False,
    ) -> GetVariationsResult | dict[str, Any]:
        """Retrieve variation items for a parent ASIN asynchronously."""
        if not asin:
            raise AmazonBadRequestError("asin cannot be empty")

        payload: dict[str, Any] = {
            "asin": asin,
            "variationCount": variation_count,
            "variationPage": variation_page,
            "resources": resources if resources is not None else DEFAULT_VARIATION_RESOURCES,
        }

        data = await self._execute_request("getVariations", payload, marketplace=marketplace)
        return data if raw else GetVariationsResult.from_dict(data)

    async def get_browse_nodes(
        self,
        browse_node_ids: str | int | list[str | int],
        resources: list[str] | None = None,
        marketplace: str | Marketplace | None = None,
        raw: bool = False,
    ) -> BrowseNodesResult | dict[str, Any]:
        """Retrieve category browse node information for up to 10 IDs asynchronously."""
        if isinstance(browse_node_ids, (str, int)):
            browse_node_ids = [browse_node_ids]

        node_ids_str = [str(n) for n in browse_node_ids]
        if not node_ids_str:
            raise AmazonBadRequestError("browse_node_ids list cannot be empty")

        if len(node_ids_str) > 10:
            raise AmazonBadRequestError("A maximum of 10 browse_node_ids can be requested per call")

        payload: dict[str, Any] = {
            "browseNodeIds": node_ids_str,
            "resources": resources if resources is not None else DEFAULT_BROWSE_NODE_RESOURCES,
        }

        data = await self._execute_request("getBrowseNodes", payload, marketplace=marketplace)
        return data if raw else BrowseNodesResult.from_dict(data)
