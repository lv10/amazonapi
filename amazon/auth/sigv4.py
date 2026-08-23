"""AWS Signature Version 4 (SigV4) Signer for Amazon PA-API 5.0."""

from __future__ import annotations

import datetime
import hashlib
import hmac


def _hmac_sha256(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _get_signature_key(key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
    k_date = _hmac_sha256(("AWS4" + key).encode("utf-8"), date_stamp)
    k_region = _hmac_sha256(k_date, region_name)
    k_service = _hmac_sha256(k_region, service_name)
    return _hmac_sha256(k_service, "aws4_request")


class SigV4Signer:
    """AWS Signature Version 4 Signer for PA-API 5.0 requests."""

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        aws_region: str,
        service: str = "ProductAdvertisingAPI",
    ) -> None:
        """Initialize SigV4Signer.

        Args:
            access_key: AWS Access Key ID.
            secret_key: AWS Secret Access Key.
            aws_region: AWS Region (e.g. us-east-1, eu-west-1, us-west-2).
            service: AWS service name (default: ProductAdvertisingAPI).
        """
        self.access_key = access_key.strip()
        self.secret_key = secret_key.strip()
        self.aws_region = aws_region.strip()
        self.service = service.strip()

    def sign(
        self,
        host: str,
        path: str,
        target: str,
        payload: str,
        timestamp: datetime.datetime | None = None,
    ) -> dict[str, str]:
        """Sign a PA-API 5.0 request and return the complete headers.

        Args:
            host: Endpoint hostname (e.g. webservices.amazon.com).
            path: Canonical URI path (e.g. /paapi5/searchitems).
            target: Amz target header (e.g. com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems).
            payload: JSON request body string.
            timestamp: Optional UTC datetime object (defaults to current UTC time).

        Returns:
            Dictionary of request headers including Authorization and x-amz-date.
        """
        if timestamp is None:
            timestamp = datetime.datetime.now(datetime.timezone.utc)

        amz_date = timestamp.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = timestamp.strftime("%Y%m%d")

        canonical_uri = path
        canonical_querystring = ""

        # Lowercase header map for canonical calculation
        headers_to_sign = {
            "content-encoding": "amz-1.0",
            "content-type": "application/json; charset=utf-8",
            "host": host.lower(),
            "x-amz-date": amz_date,
            "x-amz-target": target,
        }

        # Build canonical headers
        sorted_header_keys = sorted(headers_to_sign.keys())
        canonical_headers = "".join(f"{k}:{headers_to_sign[k]}\n" for k in sorted_header_keys)
        signed_headers = ";".join(sorted_header_keys)

        payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        canonical_request = (
            f"POST\n"
            f"{canonical_uri}\n"
            f"{canonical_querystring}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{payload_hash}"
        )

        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{date_stamp}/{self.aws_region}/{self.service}/aws4_request"
        string_to_sign = (
            f"{algorithm}\n"
            f"{amz_date}\n"
            f"{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        )

        signing_key = _get_signature_key(
            self.secret_key, date_stamp, self.aws_region, self.service
        )
        signature = hmac.new(
            signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        authorization_header = (
            f"{algorithm} "
            f"Credential={self.access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )

        return {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Encoding": "amz-1.0",
            "Host": host,
            "X-Amz-Date": amz_date,
            "X-Amz-Target": target,
            "Authorization": authorization_header,
        }
