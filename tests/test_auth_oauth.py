"""Unit tests for OAuth 2.0 token manager."""

from __future__ import annotations

import time

import pytest
import respx

from amazon.auth.oauth import OAuthToken, OAuthTokenManager
from amazon.exceptions import AmazonAuthenticationError
from tests.conftest import MOCK_OAUTH_TOKEN_RESPONSE


def test_oauth_token_expiry() -> None:
    token_valid = OAuthToken(
        access_token="valid-token",
        token_type="bearer",
        expires_at=time.time() + 600,
    )
    assert not token_valid.is_expired(buffer_seconds=300)

    token_expiring_soon = OAuthToken(
        access_token="soon-token",
        token_type="bearer",
        expires_at=time.time() + 200,
    )
    assert token_expiring_soon.is_expired(buffer_seconds=300)

    token_expired = OAuthToken(
        access_token="expired-token",
        token_type="bearer",
        expires_at=time.time() - 10,
    )
    assert token_expired.is_expired(buffer_seconds=300)


@respx.mock
def test_oauth_token_sync_get_and_cache() -> None:
    token_route = respx.post("https://api.amazon.com/auth/o2/token").respond(
        status_code=200,
        json=MOCK_OAUTH_TOKEN_RESPONSE,
    )

    manager = OAuthTokenManager(
        credential_id="test-id",
        credential_secret="test-secret",
        token_url="https://api.amazon.com/auth/o2/token",
    )

    # First fetch makes HTTP request
    token1 = manager.get_token()
    assert token1 == "mock-access-token-123456"
    assert token_route.call_count == 1

    # Second fetch returns cached token
    token2 = manager.get_token()
    assert token2 == "mock-access-token-123456"
    assert token_route.call_count == 1  # No additional HTTP request

    # Clear cache and fetch again
    manager.clear_cache()
    token3 = manager.get_token()
    assert token3 == "mock-access-token-123456"
    assert token_route.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_oauth_token_async_get_and_cache() -> None:
    token_route = respx.post("https://api.amazon.com/auth/o2/token").respond(
        status_code=200,
        json=MOCK_OAUTH_TOKEN_RESPONSE,
    )

    manager = OAuthTokenManager(
        credential_id="test-id",
        credential_secret="test-secret",
        token_url="https://api.amazon.com/auth/o2/token",
    )

    token1 = await manager.get_token_async()
    assert token1 == "mock-access-token-123456"
    assert token_route.call_count == 1

    token2 = await manager.get_token_async()
    assert token2 == "mock-access-token-123456"
    assert token_route.call_count == 1


@respx.mock
def test_oauth_token_sync_auth_failure() -> None:
    respx.post("https://api.amazon.com/auth/o2/token").respond(
        status_code=400,
        json={"error": "invalid_client", "error_description": "Client authentication failed"},
    )

    manager = OAuthTokenManager(
        credential_id="bad-id",
        credential_secret="bad-secret",
        token_url="https://api.amazon.com/auth/o2/token",
    )

    with pytest.raises(AmazonAuthenticationError) as exc_info:
        manager.get_token()

    assert exc_info.value.status_code == 400
    assert "Client authentication failed" in str(exc_info.value)


@respx.mock
@pytest.mark.asyncio
async def test_oauth_token_async_missing_access_token() -> None:
    respx.post("https://api.amazon.com/auth/o2/token").respond(
        status_code=200,
        json={"token_type": "bearer"},  # Missing access_token
    )

    manager = OAuthTokenManager(
        credential_id="id",
        credential_secret="secret",
        token_url="https://api.amazon.com/auth/o2/token",
    )

    with pytest.raises(AmazonAuthenticationError) as exc_info:
        await manager.get_token_async()

    assert "OAuth response did not contain an access_token" in str(exc_info.value)
