import base64
import hashlib
import hmac
import json
import time
import unittest
from unittest.mock import patch

from backend.security import ws_auth


class _FakeWebSocket:
    def __init__(self, headers: dict[str, str] | None = None, query_params: dict[str, str] | None = None) -> None:
        self.headers = headers or {}
        self.query_params = query_params or {}


class TestWsAuth(unittest.TestCase):
    def test_rejects_missing_token_when_required(self) -> None:
        ws = _FakeWebSocket(headers={"origin": "http://localhost:5176"})
        with patch.object(ws_auth, "WS_ALLOWED_ORIGINS", ["http://localhost:5176"]), patch.object(
            ws_auth, "WS_AUTH_REQUIRED", True
        ), patch.object(ws_auth, "WS_AUTH_TOKEN", "abc123"), patch.object(ws_auth, "WS_TOKEN_SIGNING_SECRET", ""):
            ok, reason = ws_auth.validate_websocket_handshake(ws)
        self.assertFalse(ok)
        self.assertEqual(reason, "unauthorized")

    def test_accepts_shared_token_query_param(self) -> None:
        ws = _FakeWebSocket(
            headers={"origin": "http://localhost:5176"},
            query_params={"token": "abc123"},
        )
        with patch.object(ws_auth, "WS_ALLOWED_ORIGINS", ["http://localhost:5176"]), patch.object(
            ws_auth, "WS_AUTH_REQUIRED", True
        ), patch.object(ws_auth, "WS_AUTH_TOKEN", "abc123"), patch.object(ws_auth, "WS_TOKEN_SIGNING_SECRET", ""):
            ok, reason = ws_auth.validate_websocket_handshake(ws)
        self.assertTrue(ok)
        self.assertEqual(reason, "ok")

    def test_rejects_invalid_origin(self) -> None:
        ws = _FakeWebSocket(headers={"origin": "https://evil.example"}, query_params={"token": "abc123"})
        with patch.object(ws_auth, "WS_ALLOWED_ORIGINS", ["http://localhost:5176"]), patch.object(
            ws_auth, "WS_AUTH_REQUIRED", True
        ), patch.object(ws_auth, "WS_AUTH_TOKEN", "abc123"), patch.object(ws_auth, "WS_TOKEN_SIGNING_SECRET", ""):
            ok, reason = ws_auth.validate_websocket_handshake(ws)
        self.assertFalse(ok)
        self.assertEqual(reason, "forbidden_origin")

    def test_accepts_valid_signed_token(self) -> None:
        secret = "signing-secret"
        with patch.object(ws_auth, "WS_TOKEN_SIGNING_SECRET", secret):
            token, _ = ws_auth.create_hmac_signed_token()
        ws = _FakeWebSocket(headers={"origin": "http://localhost:5176"}, query_params={"token": token})
        with patch.object(ws_auth, "WS_ALLOWED_ORIGINS", ["http://localhost:5176"]), patch.object(
            ws_auth, "WS_AUTH_REQUIRED", True
        ), patch.object(ws_auth, "WS_AUTH_TOKEN", ""), patch.object(ws_auth, "WS_TOKEN_SIGNING_SECRET", secret):
            ok, reason = ws_auth.validate_websocket_handshake(ws)
        self.assertTrue(ok)
        self.assertEqual(reason, "ok")

    def _signed_token(self, payload: dict[str, int], secret: str = "signing-secret") -> str:
        encoded = base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        ).decode("ascii").rstrip("=")
        signature = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        return f"{encoded}.{signature}"

    def test_rejects_expired_signed_token(self) -> None:
        now = int(time.time())
        token = self._signed_token({"iat": now - 91, "exp": now - 1})
        with patch.object(ws_auth, "WS_TOKEN_SIGNING_SECRET", "signing-secret"):
            self.assertFalse(ws_auth._verify_hmac_signed_token(token))

    def test_rejects_modified_payload(self) -> None:
        now = int(time.time())
        token = self._signed_token({"iat": now, "exp": now + 60})
        payload, signature = token.split(".")
        tampered = ("A" if payload[0] != "A" else "B") + payload[1:]
        with patch.object(ws_auth, "WS_TOKEN_SIGNING_SECRET", "signing-secret"):
            self.assertFalse(ws_auth._verify_hmac_signed_token(f"{tampered}.{signature}"))

    def test_rejects_modified_signature(self) -> None:
        now = int(time.time())
        token = self._signed_token({"iat": now, "exp": now + 60})
        payload, signature = token.split(".")
        tampered = ("0" if signature[0] != "0" else "1") + signature[1:]
        with patch.object(ws_auth, "WS_TOKEN_SIGNING_SECRET", "signing-secret"):
            self.assertFalse(ws_auth._verify_hmac_signed_token(f"{payload}.{tampered}"))

    def test_strict_production_policy_rejects_static_token(self) -> None:
        ws = _FakeWebSocket(
            headers={"origin": "http://localhost:5176"}, query_params={"token": "permanent"}
        )
        with patch.object(ws_auth, "WS_ALLOWED_ORIGINS", ["http://localhost:5176"]), patch.object(
            ws_auth, "WS_AUTH_REQUIRED", True
        ), patch.object(ws_auth, "WS_AUTH_TOKEN", "permanent"), patch.object(
            ws_auth, "WS_STATIC_TOKEN_ALLOWED", False
        ), patch.object(ws_auth, "WS_TOKEN_SIGNING_SECRET", "signing-secret"):
            ok, reason = ws_auth.validate_websocket_handshake(ws)
        self.assertFalse(ok)
        self.assertEqual(reason, "unauthorized")


if __name__ == "__main__":
    unittest.main()
