import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app import main as app_main


class HealthEndpointTests(unittest.TestCase):
    def test_health_reports_process_liveness(self) -> None:
        with TestClient(app_main.app) as client:
            response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy"})

    def test_ready_reports_dependency_status_without_secrets(self) -> None:
        with patch.object(app_main, "GROQ_API_KEY", "set"), patch.object(
            app_main, "SARVAM_API_KEY", "set"
        ), patch.object(app_main, "PRODUCTION_STRICT_READY", False), patch.object(
            app_main, "RAG_MIN_DOCUMENTS", 500
        ), patch.object(app_main, "get_rag_document_count", return_value=7):
            with TestClient(app_main.app) as client:
                response = client.get("/ready")

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["service"], "CLARA")
        self.assertEqual(payload["checks"]["rag_documents"], 7)
        self.assertTrue(payload["checks"]["rag_ready"])
        self.assertTrue(payload["checks"]["groq_configured"])
        self.assertTrue(payload["checks"]["sarvam_configured"])
        self.assertFalse(payload["checks"]["production_strict_ready"])
        self.assertNotIn("set", str(payload))

    def test_ready_degrades_when_rag_is_empty(self) -> None:
        with patch.object(app_main, "GROQ_API_KEY", "set"), patch.object(
            app_main, "SARVAM_API_KEY", "set"
        ), patch.object(app_main, "PRODUCTION_STRICT_READY", False), patch.object(
            app_main, "RAG_MIN_DOCUMENTS", 500
        ), patch.object(app_main, "get_rag_document_count", return_value=0):
            with TestClient(app_main.app) as client:
                response = client.get("/ready")

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "degraded")
        self.assertFalse(payload["checks"]["rag_ready"])

    def test_ready_strict_mode_requires_minimum_rag_docs(self) -> None:
        with patch.object(app_main, "GROQ_API_KEY", "set"), patch.object(
            app_main, "SARVAM_API_KEY", "set"
        ), patch.object(app_main, "PRODUCTION_STRICT_READY", True), patch.object(
            app_main, "RAG_MIN_DOCUMENTS", 500
        ), patch.object(app_main, "WS_AUTH_REQUIRED", True), patch.object(
            app_main, "WS_ALLOWED_ORIGINS", ["https://kiosk.example"]
        ), patch.object(app_main, "get_rag_document_count", return_value=499):
            with TestClient(app_main.app) as client:
                response = client.get("/ready")

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "degraded")
        self.assertEqual(payload["checks"]["rag_documents"], 499)
        self.assertFalse(payload["checks"]["rag_ready"])

    def test_ready_strict_mode_requires_ws_auth_and_locked_origins(self) -> None:
        with patch.object(app_main, "GROQ_API_KEY", "set"), patch.object(
            app_main, "SARVAM_API_KEY", "set"
        ), patch.object(app_main, "PRODUCTION_STRICT_READY", True), patch.object(
            app_main, "REQUIRE_WS_AUTH_IN_PRODUCTION", True
        ), patch.object(app_main, "RAG_MIN_DOCUMENTS", 500), patch.object(
            app_main, "WS_AUTH_REQUIRED", False
        ), patch.object(app_main, "WS_ALLOWED_ORIGINS", ["*"]), patch.object(
            app_main, "get_rag_document_count", return_value=500
        ):
            with TestClient(app_main.app) as client:
                response = client.get("/ready")

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "degraded")
        self.assertFalse(payload["checks"]["ws_auth_required"])
        self.assertFalse(payload["checks"]["ws_allowed_origins_locked"])

    def test_ready_strict_mode_ready_when_all_required_checks_pass(self) -> None:
        with patch.object(app_main, "GROQ_API_KEY", "set"), patch.object(
            app_main, "SARVAM_API_KEY", "set"
        ), patch.object(app_main, "PRODUCTION_STRICT_READY", True), patch.object(
            app_main, "REQUIRE_WS_AUTH_IN_PRODUCTION", True
        ), patch.object(app_main, "RAG_MIN_DOCUMENTS", 500), patch.object(
            app_main, "WS_AUTH_REQUIRED", True
        ), patch.object(
            app_main, "WS_TOKEN_SIGNING_SECRET", "signing-secret"
        ), patch.object(app_main, "WS_ALLOWED_ORIGINS", ["https://kiosk.example"]), patch.object(
            app_main, "get_rag_document_count", return_value=500
        ):
            with TestClient(app_main.app) as client:
                response = client.get("/ready")

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "ready")
        self.assertTrue(payload["checks"]["production_strict_ready"])


if __name__ == "__main__":
    unittest.main()
