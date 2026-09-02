"""M5.10 backend-only regional pipeline forensic trace.

This is a diagnostic fixture.  It deliberately stops at backend narration segments;
it does not start a server, browser, microphone, WebSocket, LLM, or TTS provider.
"""

from __future__ import annotations

import dataclasses
import json
import unittest
from typing import Any

from backend.core.language_detection import detect_language
from backend.services.answer_generation import normalize_user_input
from backend.services.content.semantic_request_parser import parse_semantic_request
from backend.services.content.semantic_request import SemanticRequest
from backend.services.content.surface_narration_mapper import map_content_units_to_segments
from backend.services.content.unit_selector import resolve_units_for_plan, select_content_units
from backend.services.conversation.response_decision import resolve_response_decision
from backend.services.session_language import resolve_session_language, set_session_language


CASES = (
    ("en", "English exact", "Who is the CSE Data Science HOD, what are the fees, and tell me about TechVidya?", ("cse_ds.hod", "cse_ds.fees", "events.techvidya")),
    ("kn", "Kannada exact", "ಡೇಟಾ ಸೈನ್ಸ್ ವಿಭಾಗದ HOD ಯಾರು ಮತ್ತು ಫೀಸ್ ಎಷ್ಟು ಮತ್ತು TechVidya ಬಗ್ಗೆ ಹೇಳಿ", ("cse_ds.hod", "cse_ds.fees", "events.techvidya")),
    ("kn", "Kannada captured STT 1", "ಡೇಟಾ ಸೈನ್ಸ್ ಸಚಿವರು ಯಾರು", ("cse_ds.hod",)),
    ("kn", "Kannada captured STT 2", "ಡೇಟಾ ಸಂಖ್ಯೆ ಸಚಿವರು ಯಾರು", ("cse_ds.hod",)),
    ("hi", "Hindi equivalent", "डेटा साइंस विभाग के HOD कौन हैं और फीस कितनी है और TechVidya के बारे में बताइए", ("cse_ds.hod", "cse_ds.fees", "events.techvidya")),
    ("ta", "Tamil equivalent", "டேட்டா சயின்ஸ் துறையின் HOD யார், கட்டணம் எவ்வளவு, TechVidya பற்றி சொல்லுங்கள்", ("cse_ds.hod", "cse_ds.fees", "events.techvidya")),
    ("te", "Telugu equivalent", "డేటా సైన్స్ విభాగం HOD ఎవరు, ఫీజు ఎంత, TechVidya గురించి చెప్పండి", ("cse_ds.hod", "cse_ds.fees", "events.techvidya")),
    ("ml", "Malayalam equivalent", "ഡാറ്റാ സയൻസ് വിഭാഗത്തിന്റെ HOD ആര്, ഫീസ് എത്ര, TechVidyaയെ കുറിച്ച് പറയൂ", ("cse_ds.hod", "cse_ds.fees", "events.techvidya")),
    ("kn", "Romanized Kannada equivalent", "Data Science vibhagada HOD yaaru mattu fees eshtu mattu TechVidya bagge heli", ("cse_ds.hod", "cse_ds.fees", "events.techvidya")),
)


def _plain(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return {k: _plain(v) for k, v in dataclasses.asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(v) for v in value]
    if hasattr(value, "value"):
        return value.value
    return value


class TestM510BackendRegionalForensic(unittest.TestCase):
    def test_emit_backend_trace_records(self) -> None:
        failures: list[str] = []
        for requested_lang, label, raw, expected_ids in CASES:
            detected = detect_language(raw)
            session: dict[str, Any] = {}
            set_session_language(session, requested_lang, is_auto=False)
            session_lang = resolve_session_language(session)

            request = parse_semantic_request(
                raw_text=raw,
                language_code_key=session_lang[0],
            )
            plan = select_content_units(request) if request else None
            units = resolve_units_for_plan(plan) if plan else ()
            segments = map_content_units_to_segments(units, lang_key=session_lang[0]) if units else []
            decision = resolve_response_decision(
                text=raw,
                semantic_request=request,
                ci_intent=None,
                has_department_entity=bool(request and request.entities),
                faq_matched=False,
                local_intent=None,
                validated_proposal=None,
            )

            record = {
                "label": label,
                "raw_transcript": raw,
                "language": {
                    "requested_code_key": requested_lang,
                    "session_code_key": session_lang[0],
                    "session_name": session_lang[1],
                    "tts_code": session_lang[2],
                    "is_language_auto": session.get("is_language_auto"),
                    "detected_from_raw": _plain(detected),
                },
                "normalized_text": normalize_user_input(raw),
                "semantic_request": _plain(request),
                "response_decision": _plain(decision),
                "selected_unit_ids": list(plan.units) if plan else [],
                "expected_unit_ids": list(expected_ids),
                "resolved_units": [
                    {
                        "unit_id": unit.unit_id,
                        "language_code": unit.language_code,
                        "section_id": unit.section_id,
                        "metadata": _plain(unit.metadata),
                        "body": unit.body,
                    }
                    for unit in units
                ],
                "narration_plan": [
                    {
                        "unit_id": segment.unit_id,
                        "card_index": segment.card_index,
                        "display_text": segment.display_text,
                        "tts_text": segment.tts_text,
                    }
                    for segment in segments
                ],
            }
            actual_ids = list(plan.units) if plan else []
            first_failed_stage = self._first_failed_stage(
                request=request,
                plan_ids=actual_ids,
                resolved_ids=[unit.unit_id for unit in units],
                narration_ids=[segment.unit_id for segment in segments],
                expected_ids=list(expected_ids),
            )
            content_ok, content_error = self._content_identity(segments, units, session_lang[0])
            verdict = "PASS" if actual_ids == list(expected_ids) and content_ok else "FAIL"
            record["content_tts_identity"] = {"pass": content_ok, "error": content_error}
            record["first_failed_stage"] = first_failed_stage
            record["final_verdict"] = verdict
            print("M510_BACKEND_TRACE " + json.dumps(record, ensure_ascii=True, sort_keys=True))
            if actual_ids != list(expected_ids):
                failures.append(
                    f"{label}: first failed stage={first_failed_stage}; expected={expected_ids}; actual={actual_ids}"
                )
            if not content_ok:
                failures.append(f"{label}: {content_error}")
        if failures:
            self.fail("\n".join(failures))

    @staticmethod
    def _first_failed_stage(
        *, request: Any, plan_ids: list[str], resolved_ids: list[str], narration_ids: list[str], expected_ids: list[str]
    ) -> str:
        if request is None:
            return "semantic parser"
        expected_items = {
            "cse_ds.hod": ("cse_ds", "hod"),
            "cse_ds.fees": ("cse_ds", "fees"),
            "events.techvidya": ("events.techvidya", "overview"),
        }
        request_items = set(request.unit_items)
        if any(expected_items.get(uid) not in request_items for uid in expected_ids):
            return "semantic parser"
        if plan_ids != expected_ids:
            return "unit selector"
        if resolved_ids != expected_ids:
            return "content resolver"
        if narration_ids != expected_ids:
            return "narration mapper"
        return "none"

    @staticmethod
    def _content_identity(segments: list[Any], units: tuple[Any, ...], lang_key: str) -> tuple[bool, str]:
        if [u.unit_id for u in units] != [s.unit_id for s in segments]:
            return False, "resolved unit IDs and narration unit IDs differ"
        if any(u.language_code != lang_key for u in units):
            return False, "resolved unit language differs from session language"
        for unit, segment in zip(units, segments):
            if unit.unit_id != segment.unit_id:
                return False, f"display/TTS unit mismatch at {unit.unit_id}"
            if unit.unit_id == "cse_ds.fees":
                fee = "₹3,00,000"
                if fee not in unit.body or fee not in segment.display_text or fee not in segment.tts_text:
                    return False, "cse_ds.fees value differs across body/display/TTS"
        return True, ""

    def test_partial_resolution_is_observable(self) -> None:
        request = SemanticRequest(
            language_code="kn",
            topic="hod",
            entities=("cse_ds", "unknown.entity"),
            context="mixed",
            requested_scope="single",
            confidence="MEDIUM",
            source="m510_diagnostic_partial_fixture",
            raw_text="partial resolution fixture",
            items=(("cse_ds", "hod"), ("cse_ds", "fees"), ("unknown.entity", "overview")),
        )
        plan = select_content_units(request)
        self.assertIsNotNone(plan)
        assert plan is not None
        print(
            "M510_PARTIAL_RESOLUTION "
            + json.dumps(
                {
                    "requested_items": list(request.items),
                    "selected_unit_ids": list(plan.units),
                    "unresolved_items": list(plan.unresolved_items),
                    "verdict": "PARTIAL_PRESERVED",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        self.assertEqual(list(plan.units), ["cse_ds.hod", "cse_ds.fees"])
        self.assertEqual(list(plan.unresolved_items), [("unknown.entity", "overview")])


if __name__ == "__main__":
    unittest.main()
