"""Common models and response wrappers for Amazon API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class APIErrorDetail:
    """Individual error or warning returned by Amazon API."""

    code: str
    message: str
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> APIErrorDetail:
        return cls(
            code=data.get("code") or data.get("Code") or "UnknownError",
            message=data.get("message") or data.get("Message") or "No message provided",
            raw=data,
        )


@dataclass
class Price:
    """Represents a price amount with currency and formatted display string."""

    amount: float | None
    currency: str | None
    display_amount: str | None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Price | None:
        if not data:
            return None
        return cls(
            amount=data.get("Amount") or data.get("amount"),
            currency=data.get("Currency") or data.get("currency"),
            display_amount=data.get("DisplayAmount") or data.get("displayAmount"),
            raw=data,
        )


@dataclass
class Image:
    """Product image details (URL, height, width)."""

    url: str
    height: int | None = None
    width: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Image | None:
        if not data:
            return None
        return cls(
            url=data.get("URL") or data.get("url") or "",
            height=data.get("Height") or data.get("height"),
            width=data.get("Width") or data.get("width"),
            raw=data,
        )


@dataclass
class ImageGroup:
    """Set of product images in different sizes."""

    small: Image | None = None
    medium: Image | None = None
    large: Image | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ImageGroup | None:
        if not data:
            return None
        return cls(
            small=Image.from_dict(data.get("Small") or data.get("small")),
            medium=Image.from_dict(data.get("Medium") or data.get("medium")),
            large=Image.from_dict(data.get("Large") or data.get("large")),
            raw=data,
        )


@dataclass
class PaginationInfo:
    """Pagination metadata for search/variation results."""

    total_result_count: int | None = None
    total_pages: int | None = None
    search_url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> PaginationInfo | None:
        if not data:
            return None
        return cls(
            total_result_count=(
                data.get("TotalResultCount")
                or data.get("totalResultCount")
                or data.get("TotalResults")
                or data.get("totalResults")
            ),
            total_pages=data.get("TotalPages") or data.get("totalPages"),
            search_url=(
                data.get("SearchURL")
                or data.get("searchUrl")
                or data.get("MoreSearchResultsURL")
            ),
            raw=data,
        )


@dataclass
class BaseResponse:
    """Base wrapper for Amazon API responses."""

    raw: dict[str, Any] = field(default_factory=dict)
    errors: list[APIErrorDetail] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Return True if the response contains warnings or errors."""
        return len(self.errors) > 0

    def to_dict(self) -> dict[str, Any]:
        """Return raw response dictionary."""
        return self.raw
