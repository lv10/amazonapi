"""OAuth 2.0 Client Credentials Token Manager for Amazon Creators API."""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass

import httpx

from amazon.exceptions import AmazonAuthenticationError


@dataclass
class OAuthToken:
    """OAuth 2.0 Access Token container."""

    access_token: str
    token_type: str
    expires_at: float  # Epoch timestamp in seconds
    scope: str | None = None

    def is_expired(self, buffer_seconds: float = 300.0) -> bool:
        """Check if the token is expired or within the buffer window.

        Args:
            buffer_seconds: Seconds before actual expiration to consider the token expired.
        """
        return time.time() >= (self.expires_at - buffer_seconds)


class OAuthTokenManager:
    """Thread-safe and coroutine-safe manager for OAuth 2.0 access tokens."""

    def __init__(
        self,
        credential_id: str,
        credential_secret: str,
        token_url: str,
        scope: str = "creatorsapi::default",
        buffer_seconds: float = 300.0,
    ) -> None:
        """Initialize OAuthTokenManager.

        Args:
            credential_id: Amazon Associate Creators API Credential ID (client_id).
            credential_secret: Amazon Associate Creators API Credential Secret (client_secret).
            token_url: Regional OAuth 2.0 token endpoint (e.g. https://api.amazon.com/auth/o2/token).
            scope: OAuth scope (default: "creatorsapi::default").
            buffer_seconds: Refresh buffer window in seconds before token expires.
        """
        self.credential_id = credential_id.strip()
        self.credential_secret = credential_secret.strip()
        self.token_url = token_url.strip()
        self.scope = scope.strip()
        self.buffer_seconds = buffer_seconds

        self._cached_token: OAuthToken | None = None
        self._sync_lock = threading.Lock()
        self._async_lock: asyncio.Lock | None = None

    def _get_async_lock(self) -> asyncio.Lock:
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()
        return self._async_lock

    def _build_token_payload(self) -> dict[str, str]:
        return {
            "grant_type": "client_credentials",
            "client_id": self.credential_id,
            "client_secret": self.credential_secret,
            "scope": self.scope,
        }

    def _parse_token_response(self, response: httpx.Response) -> OAuthToken:
        if response.status_code != 200:
            error_details = response.text
            try:
                data = response.json()
                error_msg = data.get("error_description") or data.get("error") or error_details
            except Exception:
                error_msg = error_details

            raise AmazonAuthenticationError(
                message=f"OAuth 2.0 authentication failed (HTTP {response.status_code}): {error_msg}",
                status_code=response.status_code,
                response_body=error_details,
            )

        data = response.json()
        access_token = data.get("access_token")
        if not access_token:
            raise AmazonAuthenticationError(
                message="OAuth response did not contain an access_token",
                status_code=response.status_code,
                response_body=data,
            )

        expires_in = int(data.get("expires_in", 3600))
        token_type = data.get("token_type", "bearer")
        scope = data.get("scope", self.scope)

        return OAuthToken(
            access_token=access_token,
            token_type=token_type,
            expires_at=time.time() + expires_in,
            scope=scope,
        )

    def get_token(self, client: httpx.Client | None = None) -> str:
        """Get a valid access token synchronously, refreshing if needed.

        Args:
            client: Optional httpx.Client instance to use for the HTTP request.

        Returns:
            Bearer access token string.
        """
        with self._sync_lock:
            if self._cached_token and not self._cached_token.is_expired(self.buffer_seconds):
                return self._cached_token.access_token

            payload = self._build_token_payload()
            should_close = False
            if client is None:
                client = httpx.Client(timeout=15.0)
                should_close = True

            try:
                resp = client.post(
                    self.token_url,
                    data=payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                self._cached_token = self._parse_token_response(resp)
                return self._cached_token.access_token
            finally:
                if should_close:
                    client.close()

    async def get_token_async(self, client: httpx.AsyncClient | None = None) -> str:
        """Get a valid access token asynchronously, refreshing if needed.

        Args:
            client: Optional httpx.AsyncClient instance to use for the HTTP request.

        Returns:
            Bearer access token string.
        """
        async with self._get_async_lock():
            if self._cached_token and not self._cached_token.is_expired(self.buffer_seconds):
                return self._cached_token.access_token

            payload = self._build_token_payload()
            should_close = False
            if client is None:
                client = httpx.AsyncClient(timeout=15.0)
                should_close = True

            try:
                resp = await client.post(
                    self.token_url,
                    data=payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                self._cached_token = self._parse_token_response(resp)
                return self._cached_token.access_token
            finally:
                if should_close:
                    await client.aclose()

    def clear_cache(self) -> None:
        """Invalidate the cached access token."""
        with self._sync_lock:
            self._cached_token = None
