"""Security tests: Bounded error memory footprint and response truncation."""

from __future__ import annotations

import httpx

from amazon.clients.base import MAX_ERROR_BODY_LENGTH, map_http_error
from amazon.exceptions import AmazonServerError


def test_map_http_error_truncates_huge_payload() -> None:
    # 50,000 characters payload (e.g. huge HTML crash dump)
    huge_text = "<html>" + ("A" * 50000) + "</html>"
    resp = httpx.Response(500, text=huge_text)

    err = map_http_error(resp)
    assert isinstance(err, AmazonServerError)
    assert len(err.response_body) <= MAX_ERROR_BODY_LENGTH + 50
    assert "... [truncated]" in err.response_body
    assert "... [truncated]" in err.message
