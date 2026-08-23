"""Amazon Marketplaces metadata and configuration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from amazon.exceptions import AmazonConfigurationError


class OAuthRegion(str, Enum):
    """Regional OAuth 2.0 endpoints for Login with Amazon (LwA)."""

    NA = "https://api.amazon.com/auth/o2/token"
    EU = "https://api.amazon.co.uk/auth/o2/token"
    FE = "https://api.amazon.co.jp/auth/o2/token"


@dataclass(frozen=True)
class MarketplaceInfo:
    """Metadata describing an Amazon marketplace."""

    country_code: str
    country_name: str
    domain: str
    paapi_host: str
    aws_region: str
    oauth_region: OAuthRegion
    currency: str

    @property
    def token_url(self) -> str:
        """Return the regional OAuth 2.0 token URL."""
        return self.oauth_region.value


class Marketplace(str, Enum):
    """Supported Amazon Marketplaces."""

    US = "US"
    CA = "CA"
    MX = "MX"
    BR = "BR"
    UK = "UK"
    DE = "DE"
    FR = "FR"
    IT = "IT"
    ES = "ES"
    NL = "NL"
    PL = "PL"
    SE = "SE"
    TR = "TR"
    BE = "BE"
    EG = "EG"
    SA = "SA"
    AE = "AE"
    IN = "IN"
    JP = "JP"
    AU = "AU"
    SG = "SG"


MARKETPLACES: dict[Marketplace, MarketplaceInfo] = {
    # North America
    Marketplace.US: MarketplaceInfo(
        country_code="US",
        country_name="United States",
        domain="www.amazon.com",
        paapi_host="webservices.amazon.com",
        aws_region="us-east-1",
        oauth_region=OAuthRegion.NA,
        currency="USD",
    ),
    Marketplace.CA: MarketplaceInfo(
        country_code="CA",
        country_name="Canada",
        domain="www.amazon.ca",
        paapi_host="webservices.amazon.ca",
        aws_region="us-east-1",
        oauth_region=OAuthRegion.NA,
        currency="CAD",
    ),
    Marketplace.MX: MarketplaceInfo(
        country_code="MX",
        country_name="Mexico",
        domain="www.amazon.com.mx",
        paapi_host="webservices.amazon.com.mx",
        aws_region="us-east-1",
        oauth_region=OAuthRegion.NA,
        currency="MXN",
    ),
    Marketplace.BR: MarketplaceInfo(
        country_code="BR",
        country_name="Brazil",
        domain="www.amazon.com.br",
        paapi_host="webservices.amazon.com.br",
        aws_region="us-east-1",
        oauth_region=OAuthRegion.NA,
        currency="BRL",
    ),
    # Europe & Middle East
    Marketplace.UK: MarketplaceInfo(
        country_code="UK",
        country_name="United Kingdom",
        domain="www.amazon.co.uk",
        paapi_host="webservices.amazon.co.uk",
        aws_region="eu-west-1",
        oauth_region=OAuthRegion.EU,
        currency="GBP",
    ),
    Marketplace.DE: MarketplaceInfo(
        country_code="DE",
        country_name="Germany",
        domain="www.amazon.de",
        paapi_host="webservices.amazon.de",
        aws_region="eu-west-1",
        oauth_region=OAuthRegion.EU,
        currency="EUR",
    ),
    Marketplace.FR: MarketplaceInfo(
        country_code="FR",
        country_name="France",
        domain="www.amazon.fr",
        paapi_host="webservices.amazon.fr",
        aws_region="eu-west-1",
        oauth_region=OAuthRegion.EU,
        currency="EUR",
    ),
    Marketplace.IT: MarketplaceInfo(
        country_code="IT",
        country_name="Italy",
        domain="www.amazon.it",
        paapi_host="webservices.amazon.it",
        aws_region="eu-west-1",
        oauth_region=OAuthRegion.EU,
        currency="EUR",
    ),
    Marketplace.ES: MarketplaceInfo(
        country_code="ES",
        country_name="Spain",
        domain="www.amazon.es",
        paapi_host="webservices.amazon.es",
        aws_region="eu-west-1",
        oauth_region=OAuthRegion.EU,
        currency="EUR",
    ),
    Marketplace.NL: MarketplaceInfo(
        country_code="NL",
        country_name="Netherlands",
        domain="www.amazon.nl",
        paapi_host="webservices.amazon.nl",
        aws_region="eu-west-1",
        oauth_region=OAuthRegion.EU,
        currency="EUR",
    ),
    Marketplace.PL: MarketplaceInfo(
        country_code="PL",
        country_name="Poland",
        domain="www.amazon.pl",
        paapi_host="webservices.amazon.pl",
        aws_region="eu-west-1",
        oauth_region=OAuthRegion.EU,
        currency="PLN",
    ),
    Marketplace.SE: MarketplaceInfo(
        country_code="SE",
        country_name="Sweden",
        domain="www.amazon.se",
        paapi_host="webservices.amazon.se",
        aws_region="eu-west-1",
        oauth_region=OAuthRegion.EU,
        currency="SEK",
    ),
    Marketplace.TR: MarketplaceInfo(
        country_code="TR",
        country_name="Turkey",
        domain="www.amazon.com.tr",
        paapi_host="webservices.amazon.com.tr",
        aws_region="eu-west-1",
        oauth_region=OAuthRegion.EU,
        currency="TRY",
    ),
    Marketplace.BE: MarketplaceInfo(
        country_code="BE",
        country_name="Belgium",
        domain="www.amazon.com.be",
        paapi_host="webservices.amazon.com.be",
        aws_region="eu-west-1",
        oauth_region=OAuthRegion.EU,
        currency="EUR",
    ),
    Marketplace.EG: MarketplaceInfo(
        country_code="EG",
        country_name="Egypt",
        domain="www.amazon.eg",
        paapi_host="webservices.amazon.eg",
        aws_region="eu-west-1",
        oauth_region=OAuthRegion.EU,
        currency="EGP",
    ),
    Marketplace.SA: MarketplaceInfo(
        country_code="SA",
        country_name="Saudi Arabia",
        domain="www.amazon.sa",
        paapi_host="webservices.amazon.sa",
        aws_region="eu-west-1",
        oauth_region=OAuthRegion.EU,
        currency="SAR",
    ),
    Marketplace.AE: MarketplaceInfo(
        country_code="AE",
        country_name="United Arab Emirates",
        domain="www.amazon.ae",
        paapi_host="webservices.amazon.ae",
        aws_region="eu-west-1",
        oauth_region=OAuthRegion.EU,
        currency="AED",
    ),
    Marketplace.IN: MarketplaceInfo(
        country_code="IN",
        country_name="India",
        domain="www.amazon.in",
        paapi_host="webservices.amazon.in",
        aws_region="eu-west-1",
        oauth_region=OAuthRegion.EU,
        currency="INR",
    ),
    # Far East
    Marketplace.JP: MarketplaceInfo(
        country_code="JP",
        country_name="Japan",
        domain="www.amazon.co.jp",
        paapi_host="webservices.amazon.co.jp",
        aws_region="us-west-2",
        oauth_region=OAuthRegion.FE,
        currency="JPY",
    ),
    Marketplace.AU: MarketplaceInfo(
        country_code="AU",
        country_name="Australia",
        domain="www.amazon.com.au",
        paapi_host="webservices.amazon.com.au",
        aws_region="us-west-2",
        oauth_region=OAuthRegion.FE,
        currency="AUD",
    ),
    Marketplace.SG: MarketplaceInfo(
        country_code="SG",
        country_name="Singapore",
        domain="www.amazon.sg",
        paapi_host="webservices.amazon.sg",
        aws_region="us-west-2",
        oauth_region=OAuthRegion.FE,
        currency="SGD",
    ),
}

# Alias mapping for domain names and country codes (case-insensitive)
_MARKETPLACE_ALIASES: dict[str, Marketplace] = {}
for _mp, _info in MARKETPLACES.items():
    _MARKETPLACE_ALIASES[_mp.value.lower()] = _mp
    _MARKETPLACE_ALIASES[_info.country_code.lower()] = _mp
    _MARKETPLACE_ALIASES[_info.domain.lower()] = _mp
    _MARKETPLACE_ALIASES[_info.paapi_host.lower()] = _mp
    # Also support "gb" for UK
    if _mp == Marketplace.UK:
        _MARKETPLACE_ALIASES["gb"] = Marketplace.UK


def resolve_marketplace(marketplace: str | Marketplace | None) -> MarketplaceInfo:
    """Resolve a marketplace string, domain, or Marketplace enum to MarketplaceInfo.

    Args:
        marketplace: A country code (e.g. 'US', 'uk'), domain ('www.amazon.com'),
                     or Marketplace enum instance.

    Returns:
        MarketplaceInfo dataclass with domain, hosts, and region info.

    Raises:
        AmazonConfigurationError: If the marketplace cannot be identified.
    """
    if marketplace is None:
        raise AmazonConfigurationError(
            "Marketplace must be provided. Supported values include: "
            + ", ".join(sorted(m.value for m in Marketplace))
        )

    if isinstance(marketplace, Marketplace):
        return MARKETPLACES[marketplace]

    key = str(marketplace).strip().lower()
    if key in _MARKETPLACE_ALIASES:
        return MARKETPLACES[_MARKETPLACE_ALIASES[key]]

    raise AmazonConfigurationError(
        f"Unknown marketplace: '{marketplace}'. Supported marketplace codes: "
        + ", ".join(sorted(m.value for m in Marketplace))
    )
