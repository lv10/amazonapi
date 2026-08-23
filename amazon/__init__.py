"""AmazonAPIWrapper: Modern Async & Sync Python Client for Amazon APIs."""

from amazon._version import __version__
from amazon.clients import (
    AmazonAPI,
    AmazonCreatorsAPI,
    AmazonPAAPI5,
    AsyncAmazonAPI,
    AsyncAmazonCreatorsAPI,
    AsyncAmazonPAAPI5,
)
from amazon.exceptions import (
    AmazonAPIError,
    AmazonAPIResponseError,
    AmazonAuthenticationError,
    AmazonBadRequestError,
    AmazonConfigurationError,
    AmazonNotFoundError,
    AmazonServerError,
    AmazonThrottlingError,
)
from amazon.marketplaces import Marketplace, resolve_marketplace
from amazon.models import (
    BrowseNode,
    BrowseNodesResult,
    GetItemsResult,
    GetVariationsResult,
    Item,
    ItemInfo,
    OfferListing,
    Offers,
    Price,
    SearchResult,
    VariationSummary,
)

__all__ = [
    "__version__",
    # Clients
    "AmazonAPI",
    "AsyncAmazonAPI",
    "AmazonCreatorsAPI",
    "AsyncAmazonCreatorsAPI",
    "AmazonPAAPI5",
    "AsyncAmazonPAAPI5",
    # Marketplaces
    "Marketplace",
    "resolve_marketplace",
    # Exceptions
    "AmazonAPIError",
    "AmazonAPIResponseError",
    "AmazonConfigurationError",
    "AmazonAuthenticationError",
    "AmazonThrottlingError",
    "AmazonBadRequestError",
    "AmazonNotFoundError",
    "AmazonServerError",
    # Models
    "Item",
    "ItemInfo",
    "Price",
    "Offers",
    "OfferListing",
    "GetItemsResult",
    "SearchResult",
    "GetVariationsResult",
    "VariationSummary",
    "BrowseNode",
    "BrowseNodesResult",
]
