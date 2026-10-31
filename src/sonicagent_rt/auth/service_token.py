"""Shared-secret authentication for OllaBridge and other private callers.

Microphone routes always require ``SONIC_API_KEY``. Development mode does not
disable that check, and well-known placeholder tokens are rejected everywhere.
"""

from __future__ import annotations

import hashlib
import hmac

from sonicagent_rt.config import Settings
from sonicagent_rt.stt.errors import OriginDenied, Unauthenticated

_INSECURE_API_KEYS = {
    "",
    "change-me",
    "changeme",
    "replace-before-deployment",
    "development-token",
    "dev",
    "test",
    "password",
    "secret",
    "token",
    "your_service_token",
    "your-service-token",
}


def bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise Unauthenticated("authentication is required")
    scheme, separator, value = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not value.strip():
        raise Unauthenticated("authentication is required")
    return value.strip()


def require_api_key(authorization: str | None, settings: Settings) -> str:
    presented = bearer_token(authorization)
    expected = settings.api_key.strip()
    if not _key_is_acceptable(expected, settings) or not _keys_match(presented, expected):
        raise Unauthenticated("authentication is required")
    return expected


def enforce_origin(origin: str | None, settings: Settings) -> None:
    """Allow server-to-server calls that omit Origin. Reject unknown browsers."""
    if origin is None or origin == "":
        return
    if origin in settings.parsed_allowed_origins():
        return
    raise OriginDenied("origin is not allowed")


def _key_is_acceptable(token: str, settings: Settings) -> bool:
    if token.lower() in _INSECURE_API_KEYS:
        return False
    minimum = 24 if settings.requires_strong_api_key() else 16
    return len(token) >= minimum and " " not in token


def _keys_match(presented: str, expected: str) -> bool:
    return hmac.compare_digest(
        hashlib.sha256(presented.encode("utf-8")).digest(),
        hashlib.sha256(expected.encode("utf-8")).digest(),
    )
