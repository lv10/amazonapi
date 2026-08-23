"""Item, Offer, and Search Result Models for Amazon APIs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from amazon.models.common import APIErrorDetail, BaseResponse, ImageGroup, PaginationInfo, Price


@dataclass
class OfferListing:
    """Represents a specific buying offer listing."""

    id: str | None = None
    price: Price | None = None
    saving_basis: Price | None = None
    availability_type: str | None = None
    availability_message: str | None = None
    condition: str | None = None
    is_prime: bool = False
    merchant_name: str | None = None
    merchant_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OfferListing:
        price_data = data.get("Price") or data.get("price")
        saving_data = data.get("SavingBasis") or data.get("savingBasis")
        avail_data = data.get("Availability") or data.get("availability") or {}
        cond_data = data.get("Condition") or data.get("condition") or {}
        delivery_info = data.get("DeliveryInfo") or data.get("deliveryInfo") or {}
        merchant_info = data.get("MerchantInfo") or data.get("merchantInfo") or {}

        return cls(
            id=data.get("Id") or data.get("id"),
            price=Price.from_dict(price_data),
            saving_basis=Price.from_dict(saving_data),
            availability_type=avail_data.get("Type") or avail_data.get("type"),
            availability_message=avail_data.get("Message") or avail_data.get("message"),
            condition=cond_data.get("Value") or cond_data.get("value"),
            is_prime=bool(delivery_info.get("IsPrimeEligible") or delivery_info.get("isPrimeEligible")),
            merchant_name=merchant_info.get("Name") or merchant_info.get("name"),
            merchant_id=merchant_info.get("Id") or merchant_info.get("id"),
            raw=data,
        )


@dataclass
class Offers:
    """Container for item offers and pricing summaries."""

    listings: list[OfferListing] = field(default_factory=list)
    primary_price: Price | None = None
    lowest_price: Price | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Offers | None:
        if not data:
            return None

        listings_data = (
            data.get("Listings")
            or data.get("listings")
            or []
        )
        listings = [OfferListing.from_dict(item) for item in listings_data]

        # Summaries
        summaries = data.get("Summaries") or data.get("summaries") or []
        lowest = None
        if summaries and isinstance(summaries, list) and len(summaries) > 0:
            lowest_data = summaries[0].get("LowestPrice") or summaries[0].get("lowestPrice")
            lowest = Price.from_dict(lowest_data)

        primary_price = listings[0].price if listings else lowest

        return cls(
            listings=listings,
            primary_price=primary_price,
            lowest_price=lowest,
            raw=data,
        )


@dataclass
class ItemInfo:
    """Core product information and metadata."""

    title: str | None = None
    brand: str | None = None
    manufacturer: str | None = None
    features: list[str] = field(default_factory=list)
    color: str | None = None
    size: str | None = None
    product_group: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ItemInfo | None:
        if not data:
            return None

        title_data = data.get("Title") or data.get("title") or {}
        title = title_data.get("DisplayValue") or title_data.get("displayValue") if isinstance(title_data, dict) else str(title_data) if title_data else None

        byline_data = data.get("ByLineInfo") or data.get("byLineInfo") or {}
        brand_data = byline_data.get("Brand") or byline_data.get("brand") or {}
        brand = brand_data.get("DisplayValue") or brand_data.get("displayValue") if isinstance(brand_data, dict) else None

        mfg_data = byline_data.get("Manufacturer") or byline_data.get("manufacturer") or {}
        mfg = mfg_data.get("DisplayValue") or mfg_data.get("displayValue") if isinstance(mfg_data, dict) else None

        features_data = data.get("Features") or data.get("features") or {}
        features_list = features_data.get("DisplayValues") or features_data.get("displayValues") or []

        class_data = data.get("Classifications") or data.get("classifications") or {}
        pg_data = class_data.get("ProductGroup") or class_data.get("productGroup") or {}
        product_group = pg_data.get("DisplayValue") or pg_data.get("displayValue") if isinstance(pg_data, dict) else None

        color_data = data.get("Color") or data.get("color") or {}
        color = color_data.get("DisplayValue") or color_data.get("displayValue") if isinstance(color_data, dict) else None

        size_data = data.get("Size") or data.get("size") or {}
        size = size_data.get("DisplayValue") or size_data.get("displayValue") if isinstance(size_data, dict) else None

        return cls(
            title=title,
            brand=brand,
            manufacturer=mfg,
            features=features_list,
            color=color,
            size=size,
            product_group=product_group,
            raw=data,
        )


@dataclass
class Item:
    """Represents an Amazon product item."""

    asin: str
    detail_page_url: str | None = None
    item_info: ItemInfo | None = None
    images: ImageGroup | None = None
    offers: Offers | None = None
    parent_asin: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def title(self) -> str | None:
        """Convenience property for product title."""
        return self.item_info.title if self.item_info else None

    @property
    def price(self) -> Price | None:
        """Convenience property for primary price."""
        if self.offers:
            return self.offers.primary_price or self.offers.lowest_price
        return None

    @property
    def image_url(self) -> str | None:
        """Convenience property for large or medium image URL."""
        if self.images:
            if self.images.large:
                return self.images.large.url
            if self.images.medium:
                return self.images.medium.url
            if self.images.small:
                return self.images.small.url
        return None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Item:
        asin = data.get("ASIN") or data.get("asin") or ""
        url = data.get("DetailPageURL") or data.get("detailPageUrl") or data.get("url")
        parent_asin = data.get("ParentASIN") or data.get("parentAsin")

        info_data = data.get("ItemInfo") or data.get("itemInfo")
        item_info = ItemInfo.from_dict(info_data)

        images_data = data.get("Images") or data.get("images") or {}
        primary_images = images_data.get("Primary") or images_data.get("primary")
        images = ImageGroup.from_dict(primary_images)

        offers_data = data.get("Offers") or data.get("offers") or data.get("OffersV2") or data.get("offersV2")
        offers = Offers.from_dict(offers_data)

        return cls(
            asin=asin,
            detail_page_url=url,
            item_info=item_info,
            images=images,
            offers=offers,
            parent_asin=parent_asin,
            raw=data,
        )


@dataclass
class GetItemsResult(BaseResponse):
    """Response wrapper for get_items operation."""

    items: list[Item] = field(default_factory=list)

    @property
    def item(self) -> Item | None:
        """Return the first item or None if no items were returned."""
        return self.items[0] if self.items else None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GetItemsResult:
        items_result = data.get("ItemsResult") or data.get("itemsResult") or data
        raw_items = items_result.get("Items") or items_result.get("items") or []
        items = [Item.from_dict(item) for item in raw_items]

        errors_raw = data.get("Errors") or data.get("errors") or []
        errors = [APIErrorDetail.from_dict(e) for e in errors_raw]

        return cls(raw=data, errors=errors, items=items)


@dataclass
class SearchResult(BaseResponse):
    """Response wrapper for search_items operation."""

    items: list[Item] = field(default_factory=list)
    pagination: PaginationInfo | None = None

    @property
    def item(self) -> Item | None:
        """Return the first item or None if empty."""
        return self.items[0] if self.items else None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SearchResult:
        search_result = data.get("SearchResult") or data.get("searchResult") or data
        raw_items = search_result.get("Items") or search_result.get("items") or []
        items = [Item.from_dict(item) for item in raw_items]

        search_url = (
            search_result.get("SearchURL")
            or search_result.get("searchUrl")
            or data.get("SearchURL")
            or data.get("searchUrl")
        )
        total_results = (
            search_result.get("TotalResultCount")
            or search_result.get("totalResultCount")
            or search_result.get("TotalResults")
        )
        total_pages = search_result.get("TotalPages") or search_result.get("totalPages")

        pagination = PaginationInfo(
            total_result_count=total_results,
            total_pages=total_pages,
            search_url=search_url,
            raw=search_result,
        )

        errors_raw = data.get("Errors") or data.get("errors") or []
        errors = [APIErrorDetail.from_dict(e) for e in errors_raw]

        return cls(raw=data, errors=errors, items=items, pagination=pagination)


@dataclass
class VariationSummary:
    """Summary of variation dimensions and pricing."""

    page_count: int | None = None
    variation_count: int | None = None
    lowest_price: Price | None = None
    highest_price: Price | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> VariationSummary | None:
        if not data:
            return None
        price_range = data.get("PriceRange") or data.get("priceRange") or {}
        lowest = Price.from_dict(price_range.get("LowestPrice") or price_range.get("lowestPrice"))
        highest = Price.from_dict(price_range.get("HighestPrice") or price_range.get("highestPrice"))

        return cls(
            page_count=data.get("PageCount") or data.get("pageCount"),
            variation_count=data.get("VariationCount") or data.get("variationCount"),
            lowest_price=lowest,
            highest_price=highest,
            raw=data,
        )


@dataclass
class GetVariationsResult(BaseResponse):
    """Response wrapper for get_variations operation."""

    items: list[Item] = field(default_factory=list)
    variation_summary: VariationSummary | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GetVariationsResult:
        var_result = data.get("VariationsResult") or data.get("variationsResult") or data
        raw_items = var_result.get("Items") or var_result.get("items") or []
        items = [Item.from_dict(item) for item in raw_items]

        summary_data = var_result.get("VariationSummary") or var_result.get("variationSummary")
        summary = VariationSummary.from_dict(summary_data)

        errors_raw = data.get("Errors") or data.get("errors") or []
        errors = [APIErrorDetail.from_dict(e) for e in errors_raw]

        return cls(raw=data, errors=errors, items=items, variation_summary=summary)
