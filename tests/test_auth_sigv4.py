"""Unit tests for AWS SigV4 request signing."""

from __future__ import annotations

import datetime

from amazon.auth.sigv4 import SigV4Signer


def test_sigv4_signer_headers_generation() -> None:
    signer = SigV4Signer(
        access_key="TESTACCESSKEY",
        secret_key="TESTSECRETKEY",
        aws_region="us-east-1",
    )

    fixed_time = datetime.datetime(2026, 8, 22, 12, 0, 0, tzinfo=datetime.timezone.utc)
    payload = '{"Keywords":"Harry Potter","SearchIndex":"All"}'
    host = "webservices.amazon.com"
    path = "/paapi5/searchitems"
    target = "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems"

    headers = signer.sign(
        host=host,
        path=path,
        target=target,
        payload=payload,
        timestamp=fixed_time,
    )

    assert headers["Host"] == host
    assert headers["X-Amz-Date"] == "20260822T120000Z"
    assert headers["X-Amz-Target"] == target
    assert headers["Content-Type"] == "application/json; charset=utf-8"
    assert headers["Content-Encoding"] == "amz-1.0"
    assert headers["Authorization"].startswith("AWS4-HMAC-SHA256 Credential=TESTACCESSKEY/20260822/us-east-1/ProductAdvertisingAPI/aws4_request")
    assert "SignedHeaders=content-encoding;content-type;host;x-amz-date;x-amz-target" in headers["Authorization"]
    assert "Signature=" in headers["Authorization"]
