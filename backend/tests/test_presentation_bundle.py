"""Tests for immutable PresentationBundle (Milestone 3.5)."""

from __future__ import annotations

import unittest
from dataclasses import dataclass

from backend.services.orchestration.presentation_bundle import (
    PresentationBundle,
    build_presentation_bundle,
    compute_contract_hash,
)
from backend.services.orchestration.types import ConversationResolution, PresentationMode


@dataclass
class _Seg:
    display_text: str
    tts_text: str
    card_index: int = 0

    def public_dict(self):
        return {
            "displayText": self.display_text,
            "ttsText": self.tts_text,
            "cardIndex": self.card_index,
        }


class BundleImmutabilityTests(unittest.TestCase):
    def test_frozen_rejects_mutation(self):
        bundle = PresentationBundle(
            presentation_id="id1",
            language="English",
            language_code="en",
            tts_language="en-IN",
            card_surface="college",
            segments=({"displayText": "Hi", "ttsText": "Hi"},),
            spoken_summaries=("Hi",),
            display_captions=("Hi",),
            contract_hash="hash1",
            created_at="2026-01-01T00:00:00+00:00",
        )
        with self.assertRaises(Exception):
            bundle.language = "Hindi"  # type: ignore[misc]
        with self.assertRaises(Exception):
            bundle.segments = ()  # type: ignore[misc]

    def test_hash_stable(self):
        h1 = compute_contract_hash(
            language_code="en",
            card_surface="college",
            display_captions=["a", "b"],
            spoken_summaries=["a", "b"],
            indices=[0, 1],
        )
        h2 = compute_contract_hash(
            language_code="en",
            card_surface="college",
            display_captions=["a", "b"],
            spoken_summaries=["a", "b"],
            indices=[0, 1],
        )
        self.assertEqual(h1, h2)
        h3 = compute_contract_hash(
            language_code="hi",
            card_surface="college",
            display_captions=["a", "b"],
            spoken_summaries=["a", "b"],
            indices=[0, 1],
        )
        self.assertNotEqual(h1, h3)

    def test_build_from_segments(self):
        res = ConversationResolution(
            language="English",
            language_code_key="en",
            tts_code="en-IN",
            show_card="department_overview",
            presentation_mode=PresentationMode.CARD_PRESENTATION.value,
        )
        segs = [
            _Seg("CSE is strong.", "CSE is strong.", 0),
            _Seg("Labs are modern.", "Labs are modern.", 1),
        ]
        bundle = build_presentation_bundle(resolution=res, segments=segs, turn_id="t1")
        self.assertIsInstance(bundle, PresentationBundle)
        self.assertEqual(len(bundle.segments), 2)
        self.assertEqual(bundle.display_captions[0], "CSE is strong.")
        self.assertEqual(bundle.spoken_summaries[1], "Labs are modern.")
        self.assertTrue(bundle.contract_hash)
        self.assertEqual(bundle.card_surface, "department_overview")
        plan = bundle.narration_plan_payload("t1")
        self.assertEqual(plan["mode"], "card_narration")
        self.assertEqual(len(plan["segments"]), 2)

    def test_duplicate_captions_hash_distinct_from_empty(self):
        a = compute_contract_hash(
            language_code="en",
            card_surface="x",
            display_captions=["same", "same"],
            spoken_summaries=["same", "same"],
        )
        b = compute_contract_hash(
            language_code="en",
            card_surface="x",
            display_captions=[],
            spoken_summaries=[],
        )
        self.assertNotEqual(a, b)

    def test_ws_card_queue_is_canonical_ordered_and_deduplicated(self):
        bundle = PresentationBundle(
            presentation_id="id-cards",
            language="Kannada",
            language_code="kn",
            tts_language="kn-IN",
            card_surface="department_overview",
            segments=(
                {"canonicalCardId": "hod_profile", "unitId": "cse_ds.hod"},
                {"canonicalCardId": "hod_profile", "unitId": "cse_ds.hod"},
                {"canonicalCardId": "fees", "unitId": "cse_ds.fees"},
            ),
            spoken_summaries=("a", "b", "c"),
            display_captions=("a", "b", "c"),
            contract_hash="hash-cards",
            created_at="2026-01-01T00:00:00+00:00",
        )
        plan = bundle.narration_plan_payload("turn-cards")
        self.assertEqual(plan["language"], "kn")
        self.assertEqual(plan["activeIndex"], 0)
        self.assertEqual(
            plan["cards"],
            [
                {"cardId": "hod_profile", "departmentId": "cse_ds", "unitId": "cse_ds.hod"},
                {"cardId": "fees", "departmentId": "cse_ds", "unitId": "cse_ds.fees"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
