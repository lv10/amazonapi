"""Amazon Product Advertising API 5.0 (PA-API 5.0) Clients with SigV4."""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from typing import Any, cast

import httpx

from amazon.auth.sigv4 import SigV4Signer
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

ALLOWED_PAAPI5_OPERATIONS = frozenset({"GetItems", "SearchItems", "GetVariations", "GetBrowseNodes"})


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


class AmazonPAAPI5:
    """Synchronous client for Amazon PA-API 5.0 using AWS SigV4."""

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        associate_tag: str,
        marketplace: str | Marketplace = Marketplace.US,
        partner_type: str = "Associates",
        timeout: float = 30.0,
        max_retries: int = 2,
        retry_delay: float = 1.0,
    ) -> None:
        """Initialize AmazonPAAPI5 client.

        Args:
            access_key: AWS Access Key ID.
            secret_key: AWS Secret Access Key.
            associate_tag: Amazon Associate Tracking Tag.
            marketplace: Target Amazon marketplace (default: US).
            partner_type: Partner type (default: 'Associates').
            timeout: HTTP request timeout in seconds (default: 30.0).
            max_retries: Maximum number of retries for throttled/transient errors.
            retry_delay: Initial retry delay in seconds.
        """
        self.access_key = access_key.strip()
        self.secret_key = secret_key.strip()
        self.associate_tag = associate_tag.strip()
        self.partner_type = partner_type.strip()
        self.marketplace_info: MarketplaceInfo = resolve_marketplace(marketplace)
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.signer = SigV4Signer(
            access_key=self.access_key,
            secret_key=self.secret_key,
            aws_region=self.marketplace_info.aws_region,
        )
        self._client: httpx.Client | None = None
        self._client_lock = threading.Lock()

    def __repr__(self) -> str:
        return (
            f"AmazonPAAPI5(access_key={self.access_key!r}, secret_key='***', "
            f"associate_tag={self.associate_tag!r}, marketplace={self.marketplace_info.country_code!r})"
        )

    @property
    def client(self) -> httpx.Client:
        """Get or initialize the underlying httpx.Client safely."""
        if self._client is None or self._client.is_closed:
            with self._client_lock:
                if self._client is None or self._client.is_closed:
                    self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def __enter__(self) -> AmazonPAAPI5:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client session."""
        with self._client_lock:
            if self._client and not self._client.is_closed:
                self._client.close()

    def _execute_request(
        self,
        operation: str,
        payload: dict[str, Any],
        marketplace: str | Marketplace | None = None,
    ) -> dict[str, Any]:
        if operation not in ALLOWED_PAAPI5_OPERATIONS:
            raise AmazonBadRequestError(f"Invalid PA-API 5.0 operation: {operation}")

        target_mp = resolve_marketplace(marketplace) if marketplace else self.marketplace_info
        host = target_mp.paapi_host
        path = f"/paapi5/{operation.lower()}"
        target = f"com.amazon.paapi5.v1.ProductAdvertisingAPIv1.{operation}"
        url = f"https://{host}{path}"

        payload["PartnerTag"] = self.associate_tag
        payload["PartnerType"] = self.partner_type

        payload_str = json.dumps(payload)

        retries = 0
        while True:
            headers = self.signer.sign(host=host, path=path, target=target, payload=payload_str)
            try:
                response = self.client.post(url, content=payload_str.encode("utf-8"), headers=headers)
                if response.status_code == 200:
                    return cast(dict[str, Any], response.json())

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
        """Retrieve detailed product information for up to 10 ASINs via PA-API 5.0."""
        validated_item_ids = _validate_item_ids(item_ids)

        payload: dict[str, Any] = {
            "ItemIds": validated_item_ids,
            "Resources": resources if resources is not None else DEFAULT_ITEM_RESOURCES,
        }

        data = self._execute_request("GetItems", payload, marketplace=marketplace)
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
        """Search products via PA-API 5.0."""
        _validate_search_params(
            item_count=item_count,
            item_page=item_page,
            min_price=min_price,
            max_price=max_price,
            min_reviews_rating=min_reviews_rating,
            min_saving_percent=min_saving_percent,
        )

        payload: dict[str, Any] = {
            "SearchIndex": search_index,
            "ItemCount": item_count,
            "ItemPage": item_page,
            "Resources": resources if resources is not None else DEFAULT_ITEM_RESOURCES,
        }

        if keywords:
            payload["Keywords"] = keywords
        if actor:
            payload["Actor"] = actor
        if artist:
            payload["Artist"] = artist
        if author:
            payload["Author"] = author
        if brand:
            payload["Brand"] = brand
        if browse_node_id:
            payload["BrowseNodeId"] = str(browse_node_id)
        if title:
            payload["Title"] = title
        if min_price is not None:
            payload["MinPrice"] = min_price
        if max_price is not None:
            payload["MaxPrice"] = max_price
        if min_reviews_rating is not None:
            payload["MinReviewsRating"] = min_reviews_rating
        if min_saving_percent is not None:
            payload["MinSavingPercent"] = min_saving_percent
        if sort_by:
            payload["SortBy"] = sort_by

        data = self._execute_request("SearchItems", payload, marketplace=marketplace)
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
        """Retrieve variation items via PA-API 5.0."""
        validated_asin = _validate_asin(asin)
        _validate_variations_params(variation_count=variation_count, variation_page=variation_page)

        payload: dict[str, Any] = {
            "ASIN": validated_asin,
            "VariationCount": variation_count,
            "VariationPage": variation_page,
            "Resources": resources if resources is not None else DEFAULT_VARIATION_RESOURCES,
        }

        data = self._execute_request("GetVariations", payload, marketplace=marketplace)
        return data if raw else GetVariationsResult.from_dict(data)

    def get_browse_nodes(
        self,
        browse_node_ids: str | int | list[str | int],
        resources: list[str] | None = None,
        marketplace: str | Marketplace | None = None,
        raw: bool = False,
    ) -> BrowseNodesResult | dict[str, Any]:
        """Retrieve category browse node information via PA-API 5.0."""
        validated_node_ids = _validate_browse_node_ids(browse_node_ids)

        payload: dict[str, Any] = {
            "BrowseNodeIds": validated_node_ids,
            "Resources": resources if resources is not None else DEFAULT_BROWSE_NODE_RESOURCES,
        }

        data = self._execute_request("GetBrowseNodes", payload, marketplace=marketplace)
        return data if raw else BrowseNodesResult.from_dict(data)


class AsyncAmazonPAAPI5:
    """Asynchronous client for Amazon PA-API 5.0 using AWS SigV4."""

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        associate_tag: str,
        marketplace: str | Marketplace = Marketplace.US,
        partner_type: str = "Associates",
        timeout: float = 30.0,
        max_retries: int = 2,
        retry_delay: float = 1.0,
    ) -> None:
        """Initialize AsyncAmazonPAAPI5 client."""
        self.access_key = access_key.strip()
        self.secret_key = secret_key.strip()
        self.associate_tag = associate_tag.strip()
        self.partner_type = partner_type.strip()
        self.marketplace_info: MarketplaceInfo = resolve_marketplace(marketplace)
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.signer = SigV4Signer(
            access_key=self.access_key,
            secret_key=self.secret_key,
            aws_region=self.marketplace_info.aws_region,
        )
        self._client: httpx.AsyncClient | None = None
        self._client_lock = threading.Lock()

    def __repr__(self) -> str:
        return (
            f"AsyncAmazonPAAPI5(access_key={self.access_key!r}, secret_key='***', "
            f"associate_tag={self.associate_tag!r}, marketplace={self.marketplace_info.country_code!r})"
        )

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or initialize the underlying httpx.AsyncClient safely."""
        if self._client is None or self._client.is_closed:
            with self._client_lock:
                if self._client is None or self._client.is_closed:
                    self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def __aenter__(self) -> AsyncAmazonPAAPI5:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client session."""
        with self._client_lock:
            if self._client and not self._client.is_closed:
                await self._client.aclose()

    async def _execute_request(
        self,
        operation: str,
        payload: dict[str, Any],
        marketplace: str | Marketplace | None = None,
    ) -> dict[str, Any]:
        if operation not in ALLOWED_PAAPI5_OPERATIONS:
            raise AmazonBadRequestError(f"Invalid PA-API 5.0 operation: {operation}")

        target_mp = resolve_marketplace(marketplace) if marketplace else self.marketplace_info
        host = target_mp.paapi_host
        path = f"/paapi5/{operation.lower()}"
        target = f"com.amazon.paapi5.v1.ProductAdvertisingAPIv1.{operation}"
        url = f"https://{host}{path}"

        payload["PartnerTag"] = self.associate_tag
        payload["PartnerType"] = self.partner_type

        payload_str = json.dumps(payload)

        retries = 0
        while True:
            headers = self.signer.sign(host=host, path=path, target=target, payload=payload_str)
            try:
                response = await self.client.post(url, content=payload_str.encode("utf-8"), headers=headers)
                if response.status_code == 200:
                    return cast(dict[str, Any], response.json())

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
            "ItemIds": validated_item_ids,
            "Resources": resources if resources is not None else DEFAULT_ITEM_RESOURCES,
        }

        data = await self._execute_request("GetItems", payload, marketplace=marketplace)
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
        """Search products asynchronously."""
        _validate_search_params(
            item_count=item_count,
            item_page=item_page,
            min_price=min_price,
            max_price=max_price,
            min_reviews_rating=min_reviews_rating,
            min_saving_percent=min_saving_percent,
        )

        payload: dict[str, Any] = {
            "SearchIndex": search_index,
            "ItemCount": item_count,
            "ItemPage": item_page,
            "Resources": resources if resources is not None else DEFAULT_ITEM_RESOURCES,
        }

        if keywords:
            payload["Keywords"] = keywords
        if actor:
            payload["Actor"] = actor
        if artist:
            payload["Artist"] = artist
        if author:
            payload["Author"] = author
        if brand:
            payload["Brand"] = brand
        if browse_node_id:
            payload["BrowseNodeId"] = str(browse_node_id)
        if title:
            payload["Title"] = title
        if min_price is not None:
            payload["MinPrice"] = min_price
        if max_price is not None:
            payload["MaxPrice"] = max_price
        if min_reviews_rating is not None:
            payload["MinReviewsRating"] = min_reviews_rating
        if min_saving_percent is not None:
            payload["MinSavingPercent"] = min_saving_percent
        if sort_by:
            payload["SortBy"] = sort_by

        data = await self._execute_request("SearchItems", payload, marketplace=marketplace)
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
        """Retrieve variation items asynchronously."""
        validated_asin = _validate_asin(asin)
        _validate_variations_params(variation_count=variation_count, variation_page=variation_page)

        payload: dict[str, Any] = {
            "ASIN": validated_asin,
            "VariationCount": variation_count,
            "VariationPage": variation_page,
            "Resources": resources if resources is not None else DEFAULT_VARIATION_RESOURCES,
        }

        data = await self._execute_request("GetVariations", payload, marketplace=marketplace)
        return data if raw else GetVariationsResult.from_dict(data)

    async def get_browse_nodes(
        self,
        browse_node_ids: str | int | list[str | int],
        resources: list[str] | None = None,
        marketplace: str | Marketplace | None = None,
        raw: bool = False,
    ) -> BrowseNodesResult | dict[str, Any]:
        """Retrieve category browse node information asynchronously."""
        validated_node_ids = _validate_browse_node_ids(browse_node_ids)

        payload: dict[str, Any] = {
            "BrowseNodeIds": validated_node_ids,
            "Resources": resources if resources is not None else DEFAULT_BROWSE_NODE_RESOURCES,
        }

        data = await self._execute_request("GetBrowseNodes", payload, marketplace=marketplace)
        return data if raw else BrowseNodesResult.from_dict(data)
