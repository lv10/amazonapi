"""Exceptions for Amazon API Wrapper."""

from __future__ import annotations

from typing import Any


class AmazonAPIError(Exception):
    """Base exception for all Amazon API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_code: str | None = None,
        response_body: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.response_body = response_body
        self.headers = headers or {}

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(message={self.message!r}, "
            f"status_code={self.status_code}, error_code={self.error_code!r})"
        )


class AmazonConfigurationError(AmazonAPIError):
    """Raised when client configuration (credentials, host, marketplace) is invalid or missing."""


class AmazonAuthenticationError(AmazonAPIError):
    """Raised when authentication (OAuth 2.0 or SigV4) fails (HTTP 401/403)."""


class AmazonThrottlingError(AmazonAPIError):
    """Raised when API rate limits or request quotas are exceeded (HTTP 429)."""


class AmazonBadRequestError(AmazonAPIError):
    """Raised when request payload or parameters are invalid (HTTP 400)."""


class AmazonNotFoundError(AmazonAPIError):
    """Raised when the requested resource or endpoint is not found (HTTP 404)."""


class AmazonServerError(AmazonAPIError):
    """Raised when Amazon servers return an internal error (HTTP 5xx)."""


# Backward compatibility alias
AmazonAPIResponseError = AmazonAPIError
