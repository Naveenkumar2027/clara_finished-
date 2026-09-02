"""Minimal WebSocket auth/origin validation for CLARA."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Any

from fastapi import WebSocket

from backend.config.settings import (
    WS_ALLOWED_ORIGINS,
    WS_AUTH_REQUIRED,
    WS_AUTH_TOKEN,
    WS_STATIC_TOKEN_ALLOWED,
    WS_TOKEN_TTL_SECONDS,
    WS_TOKEN_SIGNING_SECRET,
)

logger = logging.getLogger(__name__)

_CLOCK_SKEW_SECONDS = 5


def create_hmac_signed_token(*, now: int | None = None) -> tuple[str, int]:
    """Create the minimal, short-lived credential used only during WS handshake."""
    if not WS_TOKEN_SIGNING_SECRET:
        raise RuntimeError("WS token signing is not configured")
    issued_at = int(time.time()) if now is None else int(now)
    expires_at = issued_at + WS_TOKEN_TTL_SECONDS
    payload = {"iat": issued_at, "exp": expires_at}
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode("ascii").rstrip("=")
    signature = hmac.new(
        WS_TOKEN_SIGNING_SECRET.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256
    ).hexdigest()
    return f"{payload_b64}.{signature}", expires_at


def _extract_bearer_token(auth_header: str | None) -> str | None:
    if not auth_header:
        return None
    prefix = "bearer "
    header = auth_header.strip()
    if not header.lower().startswith(prefix):
        return None
    token = header[len(prefix) :].strip()
    return token or None


def validate_bootstrap_origin(origin: str | None) -> bool:
    """Apply the same exact allow-list policy used by the WebSocket handshake."""
    presented = (origin or "").strip()
    return bool(presented) and (not WS_ALLOWED_ORIGINS or presented in WS_ALLOWED_ORIGINS)


def _verify_hmac_signed_token(token: str) -> bool:
    """
    Signed token format:
      base64url(payload_json).hex_hmac_sha256
    payload_json must contain only integer iat and exp timestamps.
    """
    if not WS_TOKEN_SIGNING_SECRET:
        return False
    try:
        payload_b64, provided_sig = token.split(".", 1)
    except ValueError:
        return False
    if not payload_b64 or not provided_sig:
        return False
    expected_sig = hmac.new(
        WS_TOKEN_SIGNING_SECRET.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(provided_sig, expected_sig):
        return False
    try:
        padded = payload_b64 + "=" * ((4 - len(payload_b64) % 4) % 4)
        payload_bytes = base64.urlsafe_b64decode(padded.encode("utf-8"))
        payload: dict[str, Any] = json.loads(payload_bytes.decode("utf-8"))
        if set(payload) != {"iat", "exp"}:
            return False
        iat = payload.get("iat")
        exp = payload.get("exp")
        if type(iat) is not int or type(exp) is not int:
            return False
    except Exception:
        return False
    now = int(time.time())
    if iat > now + _CLOCK_SKEW_SECONDS or exp <= now or exp <= iat:
        return False
    if (exp - iat) > WS_TOKEN_TTL_SECONDS:
        return False
    return True


def validate_websocket_handshake(websocket: WebSocket) -> tuple[bool, str]:
    """
    Validate origin and token before websocket.accept().
    Returns (True, "ok") on success else (False, safe_error_reason).
    """
    origin = (websocket.headers.get("origin") or "").strip()
    if WS_ALLOWED_ORIGINS and origin not in WS_ALLOWED_ORIGINS:
        return False, "forbidden_origin"

    if not WS_AUTH_REQUIRED:
        return True, "ok"

    header_token = _extract_bearer_token(websocket.headers.get("authorization"))
    query_token = (websocket.query_params.get("token") or "").strip() or None
    presented = header_token or query_token

    if not presented:
        return False, "unauthorized"
    if WS_STATIC_TOKEN_ALLOWED and WS_AUTH_TOKEN and hmac.compare_digest(presented, WS_AUTH_TOKEN):
        return True, "ok"
    if _verify_hmac_signed_token(presented):
        return True, "ok"
    return False, "unauthorized"


def log_ws_auth_configuration_warnings() -> None:
    if not WS_AUTH_REQUIRED:
        logger.warning("WS auth is disabled (WS_AUTH_REQUIRED=false). This is insecure.")
        return
    if not WS_AUTH_TOKEN and not WS_TOKEN_SIGNING_SECRET:
        logger.warning(
            "WS auth is enabled but no WS_AUTH_TOKEN/WS_TOKEN_SIGNING_SECRET configured; all WS handshakes will be rejected."
        )
    if WS_STATIC_TOKEN_ALLOWED and WS_AUTH_TOKEN:
        logger.warning("Permanent WS token compatibility is enabled; disable it in production.")
