"""Amazon Product Advertising API 5.0 (PA-API 5.0) Clients with SigV4."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, cast

import httpx

from amazon.auth.sigv4 import SigV4Signer
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

    @property
    def client(self) -> httpx.Client:
        """Get or initialize the underlying httpx.Client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def __enter__(self) -> AmazonPAAPI5:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client session."""
        if self._client and not self._client.is_closed:
            self._client.close()

    def _execute_request(
        self,
        operation: str,
        payload: dict[str, Any],
        marketplace: str | Marketplace | None = None,
    ) -> dict[str, Any]:
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
        """Retrieve detailed product information for up to 10 ASINs via PA-API 5.0."""
        if isinstance(item_ids, str):
            item_ids = [item_ids]

        if not item_ids:
            raise AmazonBadRequestError("item_ids list cannot be empty")

        if len(item_ids) > 10:
            raise AmazonBadRequestError("A maximum of 10 item_ids can be requested per call")

        payload: dict[str, Any] = {
            "ItemIds": item_ids,
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
        if not asin:
            raise AmazonBadRequestError("asin cannot be empty")

        payload: dict[str, Any] = {
            "ASIN": asin,
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
        if isinstance(browse_node_ids, (str, int)):
            browse_node_ids = [browse_node_ids]

        node_ids_str = [str(n) for n in browse_node_ids]
        if not node_ids_str:
            raise AmazonBadRequestError("browse_node_ids list cannot be empty")

        if len(node_ids_str) > 10:
            raise AmazonBadRequestError("A maximum of 10 browse_node_ids can be requested per call")

        payload: dict[str, Any] = {
            "BrowseNodeIds": node_ids_str,
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

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or initialize the underlying httpx.AsyncClient."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def __aenter__(self) -> AsyncAmazonPAAPI5:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client session."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _execute_request(
        self,
        operation: str,
        payload: dict[str, Any],
        marketplace: str | Marketplace | None = None,
    ) -> dict[str, Any]:
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
            "ItemIds": item_ids,
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
        if not asin:
            raise AmazonBadRequestError("asin cannot be empty")

        payload: dict[str, Any] = {
            "ASIN": asin,
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
        if isinstance(browse_node_ids, (str, int)):
            browse_node_ids = [browse_node_ids]

        node_ids_str = [str(n) for n in browse_node_ids]
        if not node_ids_str:
            raise AmazonBadRequestError("browse_node_ids list cannot be empty")

        if len(node_ids_str) > 10:
            raise AmazonBadRequestError("A maximum of 10 browse_node_ids can be requested per call")

        payload: dict[str, Any] = {
            "BrowseNodeIds": node_ids_str,
            "Resources": resources if resources is not None else DEFAULT_BROWSE_NODE_RESOURCES,
        }

        data = await self._execute_request("GetBrowseNodes", payload, marketplace=marketplace)
        return data if raw else BrowseNodesResult.from_dict(data)
