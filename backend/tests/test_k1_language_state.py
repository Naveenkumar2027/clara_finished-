"""K1 regression suite: authoritative canonical language-selection state.

Covers the visitor-session lifecycle contract:
- strict application-code validation (en/kn/hi/ta/te/ml only),
- explicit selection overriding auto-detection,
- WebSocket language binding / restore on reconnect,
- deterministic reset so a new visitor never inherits a language,
- spoken pre-selection wake greeting followed by language selection.
"""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.security import ws_auth
from backend.services.session_language import (
    normalize_application_language,
    set_session_language,
    should_run_auto_detect,
)

AUTH_PATCH = dict(
    WS_ALLOWED_ORIGINS=["http://localhost:5176"],
    WS_AUTH_REQUIRED=True,
    WS_AUTH_TOKEN="test-token",
    WS_TOKEN_SIGNING_SECRET="",
)


def _auth_context():
    """Context manager stack mirroring existing WS integration tests."""
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        with patch.object(ws_auth, "WS_ALLOWED_ORIGINS", AUTH_PATCH["WS_ALLOWED_ORIGINS"]), \
                patch.object(ws_auth, "WS_AUTH_REQUIRED", AUTH_PATCH["WS_AUTH_REQUIRED"]), \
                patch.object(ws_auth, "WS_AUTH_TOKEN", AUTH_PATCH["WS_AUTH_TOKEN"]), \
                patch.object(ws_auth, "WS_TOKEN_SIGNING_SECRET", AUTH_PATCH["WS_TOKEN_SIGNING_SECRET"]):
            yield

    return _ctx()


class TestApplicationLanguageValidation(unittest.TestCase):
    def test_all_six_canonical_codes_accepted(self) -> None:
        for code in ("en", "kn", "hi", "ta", "te", "ml"):
            self.assertEqual(normalize_application_language(code), code)

    def test_provider_locale_is_not_application_state(self) -> None:
        self.assertIsNone(normalize_application_language("kn-IN"))
        self.assertIsNone(normalize_application_language("en-IN"))

    def test_display_names_are_not_application_codes(self) -> None:
        self.assertIsNone(normalize_application_language("Kannada"))
        self.assertIsNone(normalize_application_language("ಕನ್ನಡ"))

    def test_non_string_and_empty_fail_closed(self) -> None:
        self.assertIsNone(normalize_application_language(None))
        self.assertIsNone(normalize_application_language(""))
        self.assertIsNone(normalize_application_language(7))

    def test_set_session_language_rejects_invalid_without_en_coercion(self) -> None:
        session = {"language_code_key": None}
        self.assertFalse(set_session_language(session, "kn-IN", is_auto=False))
        self.assertIsNone(session.get("language_code_key"))
        self.assertFalse(set_session_language(session, "Kannada", is_auto=False))
        self.assertIsNone(session.get("language_code_key"))

    def test_explicit_selection_blocks_auto_detection(self) -> None:
        session = {}
        set_session_language(session, "kn", is_auto=False)
        self.assertEqual(session["language_code_key"], "kn")
        self.assertFalse(session["is_language_auto"])
        self.assertFalse(should_run_auto_detect(session))

    def test_detection_cannot_override_explicit_kn(self) -> None:
        session = {}
        set_session_language(session, "kn", is_auto=False)
        # The production pipeline consults should_run_auto_detect before any
        # detection write (main.py); with an explicit pick it never fires, so
        # detected input can never replace the explicit selection.
        self.assertFalse(should_run_auto_detect(session))
        self.assertEqual(session["language_code_key"], "kn")


class TestWebSocketLanguageLifecycle(unittest.TestCase):
    URL = "/ws/clara?token=test-token"
    ORIGIN = {"origin": "http://localhost:5176"}

    def _open(self):
        client = TestClient(app)
        ws = client.websocket_connect(self.URL, headers=self.ORIGIN).__enter__()
        return client, ws

    @staticmethod
    def _send(ws, payload: dict) -> None:
        import json

        ws.send_text(json.dumps(payload))

    def test_valid_canonical_code_selected_over_websocket(self) -> None:
        with _auth_context():
            with TestClient(app).websocket_connect(self.URL, headers=self.ORIGIN) as ws:
                ws.receive_json()  # initial state 0
                with patch("backend.app.main.tts_to_base64_cached", return_value=(None, {})):
                    self._send(ws, {"action": "wake", "visitor_session_id": "visitor-A"})
                    ws.receive_json()  # wake ack state 5
                    self._send(
                        ws,
                        {
                            "action": "language_selected",
                            "language": "Kannada",
                            "language_code_key": "kn",
                            "visitor_session_id": "visitor-A",
                        },
                    )
                    ack = ws.receive_json()
                self.assertEqual(ack.get("state"), 5)
                self.assertIn(
                    "name_prompt",
                    [m.get("id") for m in ack["payload"].get("messages", [])],
                )

            # Reconnect path: a fresh socket + same visitor id restores kn
            # deterministically, with no welcome replay.
            with TestClient(app).websocket_connect(self.URL, headers=self.ORIGIN) as ws2:
                ws2.receive_json()
                self._send(ws2, {"action": "wake", "visitor_session_id": "visitor-A"})
                ws2.receive_json()
                self._send(
                    ws2,
                    {
                        "action": "restore_language",
                        "language_code_key": "kn",
                        "visitor_session_id": "visitor-A",
                        "ui_state": 5,
                    },
                )
                restored = ws2.receive_json()
                self.assertTrue(restored["payload"].get("restored"))
                self.assertEqual(restored["payload"].get("language_code_key"), "kn")
                self.assertNotIn("audioBase64", restored["payload"])

    def test_invalid_codes_are_never_activated(self) -> None:
        for bad in ("kn-IN", "Kannada", "ಕನ್ನಡ"):
            with _auth_context():
                with TestClient(app).websocket_connect(self.URL, headers=self.ORIGIN) as ws:
                    ws.receive_json()
                    self._send(ws, {"action": "wake", "visitor_session_id": "visitor-B"})
                    ws.receive_json()
                    with patch(
                        "backend.app.main.tts_to_base64_cached", return_value=(None, {})
                    ):
                        self._send(
                            ws,
                            {
                                "action": "language_selected",
                                "language_code_key": bad,
                                "visitor_session_id": "visitor-B",
                            },
                        )
                        ack = ws.receive_json()
                    self.assertEqual(ack.get("state"), 5)
                    # Rejected selection: no messages / no activated language.
                    self.assertNotIn("messages", ack.get("payload") or {})
                    # Session language is still unset: conversation_started
                    # takes the pre-selection branch, proving the invalid value
                    # never became the active session language. TTS is mocked
                    # unavailable here because this test checks language state.
                    with patch(
                        "backend.app.main.tts_to_base64_cached", return_value=(None, {})
                    ):
                        self._send(ws, {"action": "conversation_started"})
                        gate = ws.receive_json()
                    gate_payload = gate.get("payload") or {}
                    self.assertNotEqual(gate_payload.get("type"), "welcome_resumed")
                    self.assertIs(gate_payload.get("isSpeaking"), False)

    def test_reset_clears_language_and_blocks_stale_restore(self) -> None:
        with _auth_context():
            with TestClient(app).websocket_connect(self.URL, headers=self.ORIGIN) as ws:
                ws.receive_json()
                with patch(
                    "backend.app.main.tts_to_base64_cached", return_value=(None, {})
                ):
                    self._send(ws, {"action": "wake", "visitor_session_id": "visitor-C"})
                    ws.receive_json()
                    self._send(
                        ws,
                        {
                            "action": "language_selected",
                            "language_code_key": "kn",
                            "visitor_session_id": "visitor-C",
                        },
                    )
                    ws.receive_json()

                    self._send(ws, {"action": "reset_session", "type": "RESET_SESSION"})
                    ws.receive_json()  # state 0 ack

                    # A late/stale restore from the ended visitor must fail.
                    self._send(
                        ws,
                        {
                            "action": "restore_language",
                            "language_code_key": "kn",
                            "visitor_session_id": "visitor-C",
                            "ui_state": 5,
                        },
                    )
                    restored = ws.receive_json()
                    self.assertFalse(restored["payload"].get("restored"))

                    # A genuinely new visitor can reselect Kannada afterwards.
                    self._send(ws, {"action": "wake", "visitor_session_id": "visitor-D"})
                    ws.receive_json()
                    self._send(
                        ws,
                        {
                            "action": "language_selected",
                            "language_code_key": "kn",
                            "visitor_session_id": "visitor-D",
                        },
                    )
                    ack = ws.receive_json()
                    self.assertIsNotNone(ack.get("payload"))

    def test_pre_selection_welcome_speaks_then_allows_language_selection(self) -> None:
        with _auth_context():
            with TestClient(app).websocket_connect(self.URL, headers=self.ORIGIN) as ws:
                ws.receive_json()
                self._send(ws, {"action": "wake"})
                ws.receive_json()
                fake_audio = "d2FrZS1ncmVldGluZw=="
                with patch(
                    "backend.app.main.tts_to_base64_cached",
                    return_value=(fake_audio, {"cache_hit": False}),
                ) as tts_mock, patch(
                    "backend.app.main.get_wakeup_language_gate_display_text",
                    return_value="Good afternoon. I am CLARA, your campus assistant.",
                ):
                    self._send(ws, {"action": "conversation_started"})
                    greeting = ws.receive_json()
                payload = greeting.get("payload") or {}
                self.assertEqual(greeting.get("state"), 5)
                self.assertTrue(payload.get("messages"))
                self.assertIs(payload.get("isSpeaking"), True)
                self.assertEqual(payload.get("turn_id"), "greeting_opening")
                self.assertEqual(payload.get("audioBase64"), fake_audio)
                self.assertEqual(
                    payload["messages"][0]["text"],
                    "Good afternoon. I am CLARA, your campus assistant.",
                )
                self.assertEqual(payload.get("languageGateNudgeAudioBase64"), fake_audio)
                self.assertIs(payload.get("audioUnavailable"), False)
                self.assertEqual(tts_mock.call_count, 2)
                self.assertEqual(tts_mock.call_args_list[0].kwargs["utterance_kind"], "greeting_opening")
                self.assertEqual(tts_mock.call_args_list[1].kwargs["utterance_kind"], "language_gate_nudge")
                self.assertEqual(tts_mock.call_args.args[1], "en-IN")

    def test_resumed_visitor_does_not_replay_welcome(self) -> None:
        with _auth_context():
            with TestClient(app).websocket_connect(self.URL, headers=self.ORIGIN) as ws:
                ws.receive_json()
                with patch(
                    "backend.app.main.tts_to_base64_cached", return_value=(None, {})
                ):
                    self._send(ws, {"action": "wake", "visitor_session_id": "visitor-E"})
                    ws.receive_json()
                    self._send(
                        ws,
                        {
                            "action": "language_selected",
                            "language_code_key": "kn",
                            "visitor_session_id": "visitor-E",
                        },
                    )
                    ws.receive_json()
                    self._send(ws, {"action": "conversation_started", "resumed": True})
                    resumed = ws.receive_json()
                payload = resumed.get("payload") or {}
                self.assertEqual(payload.get("type"), "welcome_resumed")
                self.assertIs(payload.get("isSpeaking"), False)
                self.assertNotIn("audioBase64", payload)


if __name__ == "__main__":
    unittest.main()
