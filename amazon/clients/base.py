"""Base client definitions, error mapping, and constants."""

from __future__ import annotations

import logging

import httpx

from amazon.exceptions import (
    AmazonAPIError,
    AmazonAuthenticationError,
    AmazonBadRequestError,
    AmazonNotFoundError,
    AmazonServerError,
    AmazonThrottlingError,
)

logger = logging.getLogger("amazonapi")

DEFAULT_ITEM_RESOURCES: list[str] = [
    "ItemInfo.Title",
    "ItemInfo.ByLineInfo",
    "ItemInfo.Classifications",
    "ItemInfo.Features",
    "Images.Primary.Small",
    "Images.Primary.Medium",
    "Images.Primary.Large",
    "Offers.Listings.Price",
    "Offers.Listings.SavingBasis",
    "Offers.Listings.Availability.Message",
    "Offers.Listings.Condition",
    "Offers.Listings.DeliveryInfo.IsPrimeEligible",
    "Offers.Listings.MerchantInfo",
    "Offers.Summaries.LowestPrice",
    "ParentASIN",
]

DEFAULT_VARIATION_RESOURCES: list[str] = [
    "ItemInfo.Title",
    "ItemInfo.Color",
    "ItemInfo.Size",
    "Images.Primary.Medium",
    "Offers.Listings.Price",
    "VariationSummary.Price.LowestPrice",
    "VariationSummary.Price.HighestPrice",
    "VariationSummary.VariationDimension",
]

DEFAULT_BROWSE_NODE_RESOURCES: list[str] = [
    "BrowseNodes.Ancestor",
    "BrowseNodes.Children",
]


def map_http_error(response: httpx.Response) -> AmazonAPIError:
    """Map HTTP response to specific AmazonAPIError subclass."""
    status = response.status_code
    error_code = None
    message = response.text

    try:
        data = response.json()
        if isinstance(data, dict):
            errors = data.get("Errors") or data.get("errors")
            if errors and isinstance(errors, list) and len(errors) > 0:
                first_err = errors[0]
                error_code = first_err.get("Code") or first_err.get("code")
                message = first_err.get("Message") or first_err.get("message") or message
            elif "message" in data or "Message" in data:
                message = data.get("message") or data.get("Message") or message
            elif "error" in data:
                message = str(data.get("error"))
    except Exception:
        pass

    headers_dict = dict(response.headers)

    if status == 429 or error_code in ("RequestThrottled", "TooManyRequests"):
        return AmazonThrottlingError(
            message=f"Rate limit exceeded: {message}",
            status_code=status,
            error_code=error_code or "TooManyRequests",
            response_body=response.text,
            headers=headers_dict,
        )
    elif status in (401, 403) or error_code in ("InvalidClientTokenId", "MissingClientTokenId", "AccessDeniedException"):
        return AmazonAuthenticationError(
            message=f"Authentication failed: {message}",
            status_code=status,
            error_code=error_code or "Unauthorized",
            response_body=response.text,
            headers=headers_dict,
        )
    elif status == 400 or error_code in ("AWS.MissingParameters", "AWS.InvalidParameterValue", "InvalidParameterValue"):
        return AmazonBadRequestError(
            message=f"Bad request: {message}",
            status_code=status,
            error_code=error_code or "BadRequest",
            response_body=response.text,
            headers=headers_dict,
        )
    elif status == 404 or error_code in ("ResourceNotFound", "NoExactMatches"):
        return AmazonNotFoundError(
            message=f"Resource not found: {message}",
            status_code=status,
            error_code=error_code or "NotFound",
            response_body=response.text,
            headers=headers_dict,
        )
    elif status >= 500 or error_code == "InternalError":
        return AmazonServerError(
            message=f"Amazon server error (HTTP {status}): {message}",
            status_code=status,
            error_code=error_code or "InternalError",
            response_body=response.text,
            headers=headers_dict,
        )
    else:
        return AmazonAPIError(
            message=f"API request failed with status {status}: {message}",
            status_code=status,
            error_code=error_code,
            response_body=response.text,
            headers=headers_dict,
        )
