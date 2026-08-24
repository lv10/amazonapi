"""Security tests: Concurrency and race condition safety in OAuth token manager."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest
import respx

from amazon.auth.oauth import OAuthTokenManager
from tests.conftest import MOCK_OAUTH_TOKEN_RESPONSE


@respx.mock
def test_oauth_token_manager_thread_safety() -> None:
    token_route = respx.post("https://api.amazon.com/auth/o2/token").respond(
        status_code=200,
        json=MOCK_OAUTH_TOKEN_RESPONSE,
    )

    manager = OAuthTokenManager(
        credential_id="test-id",
        credential_secret="test-secret",
        token_url="https://api.amazon.com/auth/o2/token",
    )

    def fetch_token() -> str:
        return manager.get_token()

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: fetch_token(), range(20)))

    for r in results:
        assert r == "mock-access-token-123456"

    # Only 1 network request should have been made due to caching and synchronization
    assert token_route.call_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_oauth_token_manager_coroutine_safety() -> None:
    token_route = respx.post("https://api.amazon.com/auth/o2/token").respond(
        status_code=200,
        json=MOCK_OAUTH_TOKEN_RESPONSE,
    )

    manager = OAuthTokenManager(
        credential_id="test-id",
        credential_secret="test-secret",
        token_url="https://api.amazon.com/auth/o2/token",
    )

    async def fetch_token() -> str:
        return await manager.get_token_async()

    tasks = [fetch_token() for _ in range(20)]
    results = await asyncio.gather(*tasks)

    for r in results:
        assert r == "mock-access-token-123456"

    assert token_route.call_count == 1
