"""Unit tests for Marketplace configuration and resolution."""

from __future__ import annotations

import pytest

from amazon.exceptions import AmazonConfigurationError
from amazon.marketplaces import (
    MARKETPLACES,
    Marketplace,
    OAuthRegion,
    resolve_marketplace,
)


def test_all_marketplaces_have_required_metadata() -> None:
    for _mp, info in MARKETPLACES.items():
        assert info.country_code
        assert info.country_name
        assert info.domain.startswith("www.amazon.")
        assert info.paapi_host.startswith("webservices.amazon.")
        assert info.aws_region
        assert info.currency
        assert info.token_url in [r.value for r in OAuthRegion]


def test_resolve_marketplace_by_enum() -> None:
    info = resolve_marketplace(Marketplace.US)
    assert info.country_code == "US"
    assert info.domain == "www.amazon.com"
    assert info.currency == "USD"
    assert info.token_url == "https://api.amazon.com/auth/o2/token"


def test_resolve_marketplace_by_string_case_insensitive() -> None:
    assert resolve_marketplace("us").country_code == "US"
    assert resolve_marketplace("US").country_code == "US"
    assert resolve_marketplace("Uk").country_code == "UK"
    assert resolve_marketplace("gb").country_code == "UK"
    assert resolve_marketplace("de").country_code == "DE"
    assert resolve_marketplace("jp").country_code == "JP"
    assert resolve_marketplace("ca").country_code == "CA"


def test_resolve_marketplace_by_domain() -> None:
    assert resolve_marketplace("www.amazon.com").country_code == "US"
    assert resolve_marketplace("www.amazon.co.uk").country_code == "UK"
    assert resolve_marketplace("www.amazon.co.jp").country_code == "JP"
    assert resolve_marketplace("www.amazon.de").country_code == "DE"


def test_resolve_marketplace_unknown_raises() -> None:
    with pytest.raises(AmazonConfigurationError) as exc_info:
        resolve_marketplace("mars")
    assert "Unknown marketplace: 'mars'" in str(exc_info.value)


def test_resolve_marketplace_none_raises() -> None:
    with pytest.raises(AmazonConfigurationError) as exc_info:
        resolve_marketplace(None)
    assert "Marketplace must be provided" in str(exc_info.value)
