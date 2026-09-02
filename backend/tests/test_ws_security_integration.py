import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend.app import main
from backend.security import ws_auth
from backend.security.rate_limit import BoundedKeyedRateLimiter


def _limiter(capacity: int = 100) -> BoundedKeyedRateLimiter:
    return BoundedKeyedRateLimiter(capacity, capacity)


class TestWsSecurityIntegration(unittest.TestCase):
    def test_bootstrap_issues_usable_short_lived_token(self) -> None:
        secret = "integration-signing-secret"
        with patch.object(main, "WS_TOKEN_SIGNING_SECRET", secret), patch.object(
            ws_auth, "WS_TOKEN_SIGNING_SECRET", secret
        ), patch.object(ws_auth, "WS_ALLOWED_ORIGINS", ["http://localhost:5176"]), patch.object(
            main, "_ip_bootstrap_limiter", _limiter()
        ):
            client = TestClient(main.app)
            response = client.post(
                "/api/ws-token", headers={"origin": "http://localhost:5176"}
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("cache-control"), "no-store")
        body = response.json()
        self.assertEqual(body["expires_in"], main.WS_TOKEN_TTL_SECONDS)
        with patch.object(ws_auth, "WS_TOKEN_SIGNING_SECRET", secret):
            self.assertTrue(ws_auth._verify_hmac_signed_token(body["token"]))

    def test_bootstrap_rejects_wrong_origin(self) -> None:
        with patch.object(main, "WS_TOKEN_SIGNING_SECRET", "secret"), patch.object(
            ws_auth, "WS_ALLOWED_ORIGINS", ["http://localhost:5176"]
        ):
            response = TestClient(main.app).post(
                "/api/ws-token", headers={"origin": "https://evil.example"}
            )
        self.assertEqual(response.status_code, 403)

    def test_expensive_request_over_limit_does_not_invoke_tts(self) -> None:
        tts = AsyncMock(return_value=("audio", False))
        with patch.object(ws_auth, "WS_ALLOWED_ORIGINS", ["http://localhost:5176"]), patch.object(
            ws_auth, "WS_AUTH_REQUIRED", False
        ), patch.object(main, "WS_CONNECTION_EXPENSIVE_BURST", 1), patch.object(
            main, "WS_CONNECTION_EXPENSIVE_RATE", 0.01
        ), patch.object(main, "_ip_connect_limiter", _limiter()), patch.object(
            main, "_ip_message_limiter", _limiter()
        ), patch.object(main, "_ip_expensive_limiter", _limiter()), patch.object(
            main, "tts_to_base64_cached", new=tts
        ):
            with TestClient(main.app).websocket_connect(
                "/ws/clara", headers={"origin": "http://localhost:5176"}
            ) as websocket:
                websocket.receive_json()
                websocket.send_json({"action": "language_gate_prompt"})
                websocket.receive_json()
                websocket.send_json({"action": "language_gate_prompt"})
                rejected = websocket.receive_json()

        self.assertEqual(tts.await_count, 1)
        self.assertEqual(rejected["payload"]["errorCode"], "RATE_LIMITED")
        self.assertTrue(rejected["payload"]["recoverable"])


if __name__ == "__main__":
    unittest.main()
