"""Unified AmazonAPI and AsyncAmazonAPI facades for seamless sync/async usage."""

from __future__ import annotations

from typing import Any

from amazon.clients.creators import AmazonCreatorsAPI, AsyncAmazonCreatorsAPI
from amazon.clients.paapi5 import AmazonPAAPI5, AsyncAmazonPAAPI5
from amazon.exceptions import AmazonConfigurationError
from amazon.marketplaces import Marketplace
from amazon.models.browse_nodes import BrowseNodesResult
from amazon.models.items import GetItemsResult, GetVariationsResult, SearchResult


class AmazonAPI:
    """Unified Synchronous Amazon API Client.

    Supports both modern Amazon Creators API (OAuth 2.0) and PA-API 5.0 (AWS SigV4).
    """

    def __init__(
        self,
        credential_id: str | None = None,
        credential_secret: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        associate_tag: str | None = None,
        aws_access_key: str | None = None,  # Legacy alias
        marketplace: str | Marketplace = Marketplace.US,
        host: str | None = None,  # Legacy alias
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        """Initialize AmazonAPI client.

        Args:
            credential_id: Creators API Credential ID (OAuth 2.0).
            credential_secret: Creators API Credential Secret (OAuth 2.0).
            access_key: AWS Access Key ID (PA-API 5.0).
            secret_key: AWS Secret Key.
            associate_tag: Amazon Associate Tracking ID.
            aws_access_key: Legacy alias for access_key.
            marketplace: Amazon Marketplace code or domain (default: 'US').
            host: Legacy host alias (e.g. 'us', 'de', 'ecs.amazonaws.com').
            timeout: HTTP request timeout in seconds.
            max_retries: Maximum number of request retries.
        """
        # Resolve legacy parameter aliases
        target_marketplace = host if host is not None else marketplace
        effective_access_key = access_key or aws_access_key

        if credential_id and credential_secret:
            self._backend: AmazonCreatorsAPI | AmazonPAAPI5 = AmazonCreatorsAPI(
                credential_id=credential_id,
                credential_secret=credential_secret,
                marketplace=target_marketplace,
                timeout=timeout,
                max_retries=max_retries,
            )
            self._is_creators = True
        elif effective_access_key and secret_key and associate_tag:
            self._backend = AmazonPAAPI5(
                access_key=effective_access_key,
                secret_key=secret_key,
                associate_tag=associate_tag,
                marketplace=target_marketplace,
                timeout=timeout,
                max_retries=max_retries,
            )
            self._is_creators = False
        else:
            raise AmazonConfigurationError(
                "Must provide either Creators API credentials (credential_id, credential_secret) "
                "or PA-API credentials (access_key, secret_key, associate_tag)."
            )

    def __enter__(self) -> AmazonAPI:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close underlying HTTP client."""
        self._backend.close()

    def get_items(
        self,
        item_ids: str | list[str],
        resources: list[str] | None = None,
        marketplace: str | Marketplace | None = None,
        raw: bool = False,
    ) -> GetItemsResult | dict[str, Any]:
        """Retrieve item details for up to 10 ASINs."""
        return self._backend.get_items(
            item_ids=item_ids,
            resources=resources,
            marketplace=marketplace,
            raw=raw,
        )

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
        """Search products in Amazon catalog."""
        return self._backend.search_items(
            keywords=keywords,
            actor=actor,
            artist=artist,
            author=author,
            brand=brand,
            browse_node_id=browse_node_id,
            title=title,
            search_index=search_index,
            item_count=item_count,
            item_page=item_page,
            min_price=min_price,
            max_price=max_price,
            min_reviews_rating=min_reviews_rating,
            min_saving_percent=min_saving_percent,
            sort_by=sort_by,
            resources=resources,
            marketplace=marketplace,
            raw=raw,
        )

    def get_variations(
        self,
        asin: str,
        variation_count: int = 10,
        variation_page: int = 1,
        resources: list[str] | None = None,
        marketplace: str | Marketplace | None = None,
        raw: bool = False,
    ) -> GetVariationsResult | dict[str, Any]:
        """Retrieve variation items for a parent ASIN."""
        return self._backend.get_variations(
            asin=asin,
            variation_count=variation_count,
            variation_page=variation_page,
            resources=resources,
            marketplace=marketplace,
            raw=raw,
        )

    def get_browse_nodes(
        self,
        browse_node_ids: str | int | list[str | int],
        resources: list[str] | None = None,
        marketplace: str | Marketplace | None = None,
        raw: bool = False,
    ) -> BrowseNodesResult | dict[str, Any]:
        """Retrieve category browse node information."""
        return self._backend.get_browse_nodes(
            browse_node_ids=browse_node_ids,
            resources=resources,
            marketplace=marketplace,
            raw=raw,
        )

    # Legacy Backward Compatibility Helpers
    def item_lookup(self, host: str | None = None, ItemId: str | None = None, **kwargs: Any) -> Any:
        """Legacy alias for get_items."""
        item_id = ItemId or kwargs.get("item_id") or kwargs.get("ItemId")
        if not item_id:
            raise AmazonConfigurationError("ItemId must be specified for item_lookup")
        return self.get_items(item_ids=str(item_id), marketplace=host)

    def item_search(self, host: str | None = None, **kwargs: Any) -> Any:
        """Legacy alias for search_items."""
        keywords = kwargs.get("Keywords") or kwargs.get("keywords")
        search_index = kwargs.get("SearchIndex") or kwargs.get("search_index") or "All"
        return self.search_items(keywords=keywords, search_index=search_index, marketplace=host)

    def node_browse_lookup(self, host: str | None = None, browse_node_id: str | int | None = None, **kwargs: Any) -> Any:
        """Legacy alias for get_browse_nodes."""
        node_id = browse_node_id or kwargs.get("BrowseNodeId") or kwargs.get("browse_node_id")
        if not node_id:
            raise AmazonConfigurationError("browse_node_id must be specified")
        return self.get_browse_nodes(browse_node_ids=node_id, marketplace=host)


class AsyncAmazonAPI:
    """Unified Asynchronous Amazon API Client.

    Supports both modern Amazon Creators API (OAuth 2.0) and PA-API 5.0 (AWS SigV4).
    """

    def __init__(
        self,
        credential_id: str | None = None,
        credential_secret: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        associate_tag: str | None = None,
        aws_access_key: str | None = None,
        marketplace: str | Marketplace = Marketplace.US,
        host: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        """Initialize AsyncAmazonAPI client."""
        target_marketplace = host if host is not None else marketplace
        effective_access_key = access_key or aws_access_key

        if credential_id and credential_secret:
            self._backend: AsyncAmazonCreatorsAPI | AsyncAmazonPAAPI5 = AsyncAmazonCreatorsAPI(
                credential_id=credential_id,
                credential_secret=credential_secret,
                marketplace=target_marketplace,
                timeout=timeout,
                max_retries=max_retries,
            )
            self._is_creators = True
        elif effective_access_key and secret_key and associate_tag:
            self._backend = AsyncAmazonPAAPI5(
                access_key=effective_access_key,
                secret_key=secret_key,
                associate_tag=associate_tag,
                marketplace=target_marketplace,
                timeout=timeout,
                max_retries=max_retries,
            )
            self._is_creators = False
        else:
            raise AmazonConfigurationError(
                "Must provide either Creators API credentials (credential_id, credential_secret) "
                "or PA-API credentials (access_key, secret_key, associate_tag)."
            )

    async def __aenter__(self) -> AsyncAmazonAPI:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close underlying HTTP client."""
        await self._backend.close()

    async def get_items(
        self,
        item_ids: str | list[str],
        resources: list[str] | None = None,
        marketplace: str | Marketplace | None = None,
        raw: bool = False,
    ) -> GetItemsResult | dict[str, Any]:
        """Retrieve item details for up to 10 ASINs asynchronously."""
        return await self._backend.get_items(
            item_ids=item_ids,
            resources=resources,
            marketplace=marketplace,
            raw=raw,
        )

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
        return await self._backend.search_items(
            keywords=keywords,
            actor=actor,
            artist=artist,
            author=author,
            brand=brand,
            browse_node_id=browse_node_id,
            title=title,
            search_index=search_index,
            item_count=item_count,
            item_page=item_page,
            min_price=min_price,
            max_price=max_price,
            min_reviews_rating=min_reviews_rating,
            min_saving_percent=min_saving_percent,
            sort_by=sort_by,
            resources=resources,
            marketplace=marketplace,
            raw=raw,
        )

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
        return await self._backend.get_variations(
            asin=asin,
            variation_count=variation_count,
            variation_page=variation_page,
            resources=resources,
            marketplace=marketplace,
            raw=raw,
        )

    async def get_browse_nodes(
        self,
        browse_node_ids: str | int | list[str | int],
        resources: list[str] | None = None,
        marketplace: str | Marketplace | None = None,
        raw: bool = False,
    ) -> BrowseNodesResult | dict[str, Any]:
        """Retrieve category browse node information asynchronously."""
        return await self._backend.get_browse_nodes(
            browse_node_ids=browse_node_ids,
            resources=resources,
            marketplace=marketplace,
            raw=raw,
        )
