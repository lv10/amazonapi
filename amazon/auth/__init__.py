"""Authentication modules for Amazon APIs (OAuth 2.0 and AWS SigV4)."""

from amazon.auth.oauth import OAuthToken, OAuthTokenManager
from amazon.auth.sigv4 import SigV4Signer

__all__ = ["OAuthToken", "OAuthTokenManager", "SigV4Signer"]
