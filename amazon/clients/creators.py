"""Amazon Creators API Synchronous and Asynchronous Clients."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any, cast

import httpx

from amazon.auth.oauth import OAuthTokenManager
from amazon.clients.base import (
    DEFAULT_BROWSE_NODE_RESOURCES,
    DEFAULT_ITEM_RESOURCES,
    DEFAULT_VARIATION_RESOURCES,
    calculate_backoff,
    map_http_error,
    parse_retry_after,
)
from amazon.exceptions import AmazonBadRequestError
from amazon.marketplaces import Marketplace, MarketplaceInfo, resolve_marketplace
from amazon.models.browse_nodes import BrowseNodesResult
from amazon.models.items import GetItemsResult, GetVariationsResult, SearchResult

logger = logging.getLogger("amazonapi")

CREATORS_API_BASE_URL = "https://creatorsapi.amazon/catalog/v1"
ALLOWED_CREATORS_ENDPOINTS = frozenset({"getItems", "searchItems", "getVariations", "getBrowseNodes"})


def _validate_item_ids(item_ids: str | list[str]) -> list[str]:
    if isinstance(item_ids, str):
        ids = [item_ids]
    elif isinstance(item_ids, (list, tuple)):
        ids = list(item_ids)
    else:
        raise AmazonBadRequestError("item_ids must be a string or list of strings")

    cleaned = [str(i).strip() for i in ids if str(i).strip()]
    if not cleaned:
        raise AmazonBadRequestError("item_ids list cannot be empty")
    if len(cleaned) > 10:
        raise AmazonBadRequestError("A maximum of 10 item_ids can be requested per call")
    return cleaned


def _validate_asin(asin: str) -> str:
    if not asin or not isinstance(asin, str) or not asin.strip():
        raise AmazonBadRequestError("asin cannot be empty")
    return asin.strip()


def _validate_browse_node_ids(browse_node_ids: str | int | list[str | int]) -> list[str]:
    if isinstance(browse_node_ids, (str, int)):
        ids = [browse_node_ids]
    elif isinstance(browse_node_ids, (list, tuple)):
        ids = list(browse_node_ids)
    else:
        raise AmazonBadRequestError("browse_node_ids must be a string, integer, or list")

    cleaned = [str(n).strip() for n in ids if str(n).strip()]
    if not cleaned:
        raise AmazonBadRequestError("browse_node_ids list cannot be empty")
    if len(cleaned) > 10:
        raise AmazonBadRequestError("A maximum of 10 browse_node_ids can be requested per call")
    return cleaned


def _validate_search_params(
    item_count: int,
    item_page: int,
    min_price: int | None = None,
    max_price: int | None = None,
    min_reviews_rating: int | None = None,
    min_saving_percent: int | None = None,
) -> None:
    if not (1 <= item_count <= 10):
        raise AmazonBadRequestError(f"item_count must be between 1 and 10, got {item_count}")
    if not (1 <= item_page <= 10):
        raise AmazonBadRequestError(f"item_page must be between 1 and 10, got {item_page}")
    if min_price is not None and min_price < 0:
        raise AmazonBadRequestError("min_price cannot be negative")
    if max_price is not None and max_price < 0:
        raise AmazonBadRequestError("max_price cannot be negative")
    if min_price is not None and max_price is not None and min_price > max_price:
        raise AmazonBadRequestError(f"min_price ({min_price}) cannot be greater than max_price ({max_price})")
    if min_reviews_rating is not None and not (1 <= min_reviews_rating <= 5):
        raise AmazonBadRequestError(f"min_reviews_rating must be between 1 and 5, got {min_reviews_rating}")
    if min_saving_percent is not None and not (1 <= min_saving_percent <= 100):
        raise AmazonBadRequestError(f"min_saving_percent must be between 1 and 100, got {min_saving_percent}")


def _validate_variations_params(variation_count: int, variation_page: int) -> None:
    if not (1 <= variation_count <= 10):
        raise AmazonBadRequestError(f"variation_count must be between 1 and 10, got {variation_count}")
    if not (1 <= variation_page <= 10):
        raise AmazonBadRequestError(f"variation_page must be between 1 and 10, got {variation_page}")


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
            timeout=timeout,
        )
        self._client: httpx.Client | None = None
        self._client_lock = threading.Lock()

    def __repr__(self) -> str:
        return (
            f"AmazonCreatorsAPI(credential_id={self.token_manager.credential_id!r}, "
            f"credential_secret='***', marketplace={self.marketplace_info.country_code!r})"
        )

    @property
    def client(self) -> httpx.Client:
        """Get or initialize the underlying httpx.Client safely."""
        if self._client is None or self._client.is_closed:
            with self._client_lock:
                if self._client is None or self._client.is_closed:
                    self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def __enter__(self) -> AmazonCreatorsAPI:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client session."""
        with self._client_lock:
            if self._client and not self._client.is_closed:
                self._client.close()

    def _execute_request(self, endpoint: str, payload: dict[str, Any], marketplace: str | Marketplace | None = None) -> dict[str, Any]:
        if endpoint not in ALLOWED_CREATORS_ENDPOINTS:
            raise AmazonBadRequestError(f"Invalid Creators API endpoint: {endpoint}")

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
                    delay = calculate_backoff(retries, self.retry_delay)
                    time.sleep(delay)
                    continue

                if response.status_code in (429, 502, 503, 504) and retries < self.max_retries:
                    retries += 1
                    default_delay = calculate_backoff(retries, self.retry_delay)
                    delay = parse_retry_after(response, default=default_delay)
                    time.sleep(delay)
                    continue

                raise map_http_error(response)

            except httpx.RequestError as exc:
                if retries < self.max_retries:
                    retries += 1
                    delay = calculate_backoff(retries, self.retry_delay)
                    time.sleep(delay)
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
        validated_item_ids = _validate_item_ids(item_ids)

        payload: dict[str, Any] = {
            "itemIds": validated_item_ids,
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
        _validate_search_params(
            item_count=item_count,
            item_page=item_page,
            min_price=min_price,
            max_price=max_price,
            min_reviews_rating=min_reviews_rating,
            min_saving_percent=min_saving_percent,
        )

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
        validated_asin = _validate_asin(asin)
        _validate_variations_params(variation_count=variation_count, variation_page=variation_page)

        payload: dict[str, Any] = {
            "asin": validated_asin,
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
        validated_node_ids = _validate_browse_node_ids(browse_node_ids)

        payload: dict[str, Any] = {
            "browseNodeIds": validated_node_ids,
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
            timeout=timeout,
        )
        self._client: httpx.AsyncClient | None = None
        self._client_lock = threading.Lock()

    def __repr__(self) -> str:
        return (
            f"AsyncAmazonCreatorsAPI(credential_id={self.token_manager.credential_id!r}, "
            f"credential_secret='***', marketplace={self.marketplace_info.country_code!r})"
        )

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or initialize the underlying httpx.AsyncClient safely."""
        if self._client is None or self._client.is_closed:
            with self._client_lock:
                if self._client is None or self._client.is_closed:
                    self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def __aenter__(self) -> AsyncAmazonCreatorsAPI:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client session."""
        with self._client_lock:
            if self._client and not self._client.is_closed:
                await self._client.aclose()

    async def _execute_request(
        self, endpoint: str, payload: dict[str, Any], marketplace: str | Marketplace | None = None
    ) -> dict[str, Any]:
        if endpoint not in ALLOWED_CREATORS_ENDPOINTS:
            raise AmazonBadRequestError(f"Invalid Creators API endpoint: {endpoint}")

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
                    delay = calculate_backoff(retries, self.retry_delay)
                    await asyncio.sleep(delay)
                    continue

                if response.status_code in (429, 502, 503, 504) and retries < self.max_retries:
                    retries += 1
                    default_delay = calculate_backoff(retries, self.retry_delay)
                    delay = parse_retry_after(response, default=default_delay)
                    await asyncio.sleep(delay)
                    continue

                raise map_http_error(response)

            except httpx.RequestError as exc:
                if retries < self.max_retries:
                    retries += 1
                    delay = calculate_backoff(retries, self.retry_delay)
                    await asyncio.sleep(delay)
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
        validated_item_ids = _validate_item_ids(item_ids)

        payload: dict[str, Any] = {
            "itemIds": validated_item_ids,
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
        _validate_search_params(
            item_count=item_count,
            item_page=item_page,
            min_price=min_price,
            max_price=max_price,
            min_reviews_rating=min_reviews_rating,
            min_saving_percent=min_saving_percent,
        )

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
        validated_asin = _validate_asin(asin)
        _validate_variations_params(variation_count=variation_count, variation_page=variation_page)

        payload: dict[str, Any] = {
            "asin": validated_asin,
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
        validated_node_ids = _validate_browse_node_ids(browse_node_ids)

        payload: dict[str, Any] = {
            "browseNodeIds": validated_node_ids,
            "resources": resources if resources is not None else DEFAULT_BROWSE_NODE_RESOURCES,
        }

        data = await self._execute_request("getBrowseNodes", payload, marketplace=marketplace)
        return data if raw else BrowseNodesResult.from_dict(data)
