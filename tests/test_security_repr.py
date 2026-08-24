"""Security tests: Credential protection and string representation masking."""

from __future__ import annotations

import time

from amazon.auth.oauth import OAuthToken, OAuthTokenManager
from amazon.auth.sigv4 import SigV4Signer
from amazon.clients.creators import AmazonCreatorsAPI, AsyncAmazonCreatorsAPI
from amazon.clients.paapi5 import AmazonPAAPI5, AsyncAmazonPAAPI5
from amazon.clients.unified import AmazonAPI, AsyncAmazonAPI


def test_oauth_token_repr_masks_access_token() -> None:
    secret_token = "at-secret-oauth-bearer-token-987654321"
    token = OAuthToken(
        access_token=secret_token,
        token_type="bearer",
        expires_at=time.time() + 3600,
    )
    repr_str = repr(token)
    assert secret_token not in repr_str
    assert "at-s...4321" in repr_str

    short_token = OAuthToken(
        access_token="short",
        token_type="bearer",
        expires_at=time.time() + 3600,
    )
    assert repr(short_token) == "OAuthToken(access_token='***', token_type='bearer', expires_at=" + str(short_token.expires_at) + ", scope=None)"


def test_oauth_token_manager_repr_masks_client_secret() -> None:
    manager = OAuthTokenManager(
        credential_id="my-client-id",
        credential_secret="super-sensitive-secret-key-123",
        token_url="https://api.amazon.com/auth/o2/token",
    )
    repr_str = repr(manager)
    assert "super-sensitive-secret-key-123" not in repr_str
    assert "credential_secret='***'" in repr_str
    assert "my-client-id" in repr_str


def test_sigv4_signer_repr_masks_secret_key() -> None:
    signer = SigV4Signer(
        access_key="AKIA123456789EXAMPLE",
        secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        aws_region="us-east-1",
    )
    repr_str = repr(signer)
    assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" not in repr_str
    assert "secret_key='***'" in repr_str
    assert "AKIA123456789EXAMPLE" in repr_str


def test_creators_clients_repr_masks_credentials() -> None:
    sync_client = AmazonCreatorsAPI(
        credential_id="cred-123",
        credential_secret="secret-abc",
    )
    assert "secret-abc" not in repr(sync_client)
    assert "credential_secret='***'" in repr(sync_client)
    sync_client.close()

    async_client = AsyncAmazonCreatorsAPI(
        credential_id="cred-123",
        credential_secret="secret-abc",
    )
    assert "secret-abc" not in repr(async_client)
    assert "credential_secret='***'" in repr(async_client)


def test_paapi5_clients_repr_masks_credentials() -> None:
    sync_client = AmazonPAAPI5(
        access_key="AKIAEXAMPLE",
        secret_key="secret-aws-key",
        associate_tag="tag-20",
    )
    assert "secret-aws-key" not in repr(sync_client)
    assert "secret_key='***'" in repr(sync_client)
    sync_client.close()

    async_client = AsyncAmazonPAAPI5(
        access_key="AKIAEXAMPLE",
        secret_key="secret-aws-key",
        associate_tag="tag-20",
    )
    assert "secret-aws-key" not in repr(async_client)
    assert "secret_key='***'" in repr(async_client)


def test_unified_clients_repr_masks_credentials() -> None:
    api = AmazonAPI(
        credential_id="cred-123",
        credential_secret="secret-abc",
    )
    assert "secret-abc" not in repr(api)
    assert "credential_secret='***'" in repr(api)
    api.close()

    async_api = AsyncAmazonAPI(
        access_key="AKIAEXAMPLE",
        secret_key="secret-aws-key",
        associate_tag="tag-20",
    )
    assert "secret-aws-key" not in repr(async_api)
    assert "secret_key='***'" in repr(async_api)
