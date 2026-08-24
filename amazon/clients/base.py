"""Base client definitions, error mapping, and constants."""

from __future__ import annotations

import datetime
import email.utils
import logging
import random

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

MAX_ERROR_BODY_LENGTH = 4096

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


def parse_retry_after(response: httpx.Response, default: float) -> float:
    """Parse HTTP Retry-After header if present, returning delay in seconds.

    Supports integer seconds and HTTP-date formats.
    """
    retry_header = response.headers.get("retry-after") or response.headers.get("Retry-After")
    if not retry_header:
        return default

    retry_header = retry_header.strip()
    try:
        # Try integer seconds
        seconds = float(retry_header)
        return max(0.0, seconds)
    except ValueError:
        pass

    try:
        # Try HTTP-date format (RFC 7231)
        target_date = email.utils.parsedate_to_datetime(retry_header)
        now = datetime.datetime.now(datetime.timezone.utc)
        delta = (target_date - now).total_seconds()
        return max(0.0, delta)
    except Exception:
        return default


def calculate_backoff(retry_count: int, base_delay: float, max_delay: float = 60.0) -> float:
    """Calculate exponential backoff with full jitter to avoid thundering herds.

    Args:
        retry_count: Attempt number (1-based index).
        base_delay: Initial base delay in seconds.
        max_delay: Maximum delay cap in seconds.

    Returns:
        Random jittered delay in seconds between 0 and min(max_delay, base_delay * 2^(retry_count-1)).
    """
    delay_ceiling = min(max_delay, base_delay * (2 ** max(0, retry_count - 1)))
    return random.uniform(0.0, delay_ceiling)


def map_http_error(response: httpx.Response) -> AmazonAPIError:
    """Map HTTP response to specific AmazonAPIError subclass with bounded memory footprint."""
    status = response.status_code
    error_code = None
    raw_text = response.text
    truncated_text = (
        raw_text[:MAX_ERROR_BODY_LENGTH] + "... [truncated]"
        if len(raw_text) > MAX_ERROR_BODY_LENGTH
        else raw_text
    )
    message = truncated_text

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
            response_body=truncated_text,
            headers=headers_dict,
        )
    elif status in (401, 403) or error_code in ("InvalidClientTokenId", "MissingClientTokenId", "AccessDeniedException"):
        return AmazonAuthenticationError(
            message=f"Authentication failed: {message}",
            status_code=status,
            error_code=error_code or "Unauthorized",
            response_body=truncated_text,
            headers=headers_dict,
        )
    elif status == 400 or error_code in ("AWS.MissingParameters", "AWS.InvalidParameterValue", "InvalidParameterValue"):
        return AmazonBadRequestError(
            message=f"Bad request: {message}",
            status_code=status,
            error_code=error_code or "BadRequest",
            response_body=truncated_text,
            headers=headers_dict,
        )
    elif status == 404 or error_code in ("ResourceNotFound", "NoExactMatches"):
        return AmazonNotFoundError(
            message=f"Resource not found: {message}",
            status_code=status,
            error_code=error_code or "NotFound",
            response_body=truncated_text,
            headers=headers_dict,
        )
    elif status >= 500 or error_code == "InternalError":
        return AmazonServerError(
            message=f"Amazon server error (HTTP {status}): {message}",
            status_code=status,
            error_code=error_code or "InternalError",
            response_body=truncated_text,
            headers=headers_dict,
        )
    else:
        return AmazonAPIError(
            message=f"API request failed with status {status}: {message}",
            status_code=status,
            error_code=error_code,
            response_body=truncated_text,
            headers=headers_dict,
        )
