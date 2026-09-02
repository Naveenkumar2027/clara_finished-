"""Immutable PresentationBundle — built once after M2 contract (Milestone 3.5)."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Sequence

from backend.services.content.card_registry import department_id_for_unit_id


def _segment_public_dict(seg: Any) -> dict[str, Any]:
    if hasattr(seg, "public_dict") and callable(seg.public_dict):
        return dict(seg.public_dict())
    if isinstance(seg, dict):
        return dict(seg)
    return {
        "displayText": str(getattr(seg, "display_text", "") or ""),
        "ttsText": str(getattr(seg, "tts_text", "") or ""),
        "cardIndex": getattr(seg, "card_index", None),
    }


def _display_text(seg: Any) -> str:
    if isinstance(seg, dict):
        return str(seg.get("displayText") or seg.get("display_text") or "")
    return str(getattr(seg, "display_text", "") or "")


def _tts_text(seg: Any) -> str:
    if isinstance(seg, dict):
        return str(seg.get("ttsText") or seg.get("tts_text") or "")
    return str(getattr(seg, "tts_text", "") or "")


def compute_contract_hash(
    *,
    language_code: str,
    card_surface: str | None,
    display_captions: Sequence[str],
    spoken_summaries: Sequence[str],
    indices: Sequence[int] | None = None,
) -> str:
    payload = {
        "language_code": language_code,
        "card_surface": card_surface,
        "display_captions": list(display_captions),
        "spoken_summaries": list(spoken_summaries),
        "indices": list(indices) if indices is not None else list(range(len(display_captions))),
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


@dataclass(frozen=True)
class PresentationBundle:
    """Immutable presentation object for one CARD_PRESENTATION turn."""

    presentation_id: str
    language: str
    language_code: str
    tts_language: str
    card_surface: str | None
    segments: tuple[dict[str, Any], ...]
    spoken_summaries: tuple[str, ...]
    display_captions: tuple[str, ...]
    contract_hash: str
    created_at: str
    # Milestone 4.1 — backend metadata only (not in narration_plan_payload / WS)
    canonical_surface: str | None = None
    canonical_content_id: str | None = None
    content_hash: str | None = None

    def narration_plan_payload(self, turn_id: str) -> dict[str, Any]:
        """Derive the WS plan plus an explicit canonical ordered card queue."""
        cards: list[dict[str, Any]] = []
        seen_cards: set[tuple[str, str]] = set()
        for segment in self.segments:
            card_id = str(segment.get("canonicalCardId") or "").strip()
            unit_id = str(segment.get("unitId") or "").strip()
            if not card_id:
                continue
            identity = (card_id, unit_id)
            if identity in seen_cards:
                continue
            seen_cards.add(identity)
            cards.append(
                {
                    "cardId": card_id,
                    "departmentId": department_id_for_unit_id(unit_id),
                    "unitId": unit_id or None,
                }
            )
        return {
            "turnId": turn_id,
            "mode": "card_narration",
            "language": self.language_code,
            "cards": cards,
            "activeIndex": 0,
            "segments": list(self.segments),
        }

    def joined_spoken_text(self) -> str:
        return "\n\n".join(s for s in self.spoken_summaries if s).strip()


def build_presentation_bundle(
    *,
    resolution: Any,
    segments: Sequence[Any],
    turn_id: str | None = None,
) -> PresentationBundle:
    """
    Build an immutable bundle from validated narration segments.
    Call only after M2 presentation contract passes.
    """
    public_segs = tuple(_segment_public_dict(s) for s in segments)
    captions = tuple(_display_text(s) for s in segments)
    spoken = tuple(_tts_text(s) for s in segments)
    surface = getattr(resolution, "show_card", None) or getattr(resolution, "card_surface", None)
    lang = str(getattr(resolution, "language", "English") or "English")
    code = str(getattr(resolution, "language_code_key", "en") or "en")
    tts = str(getattr(resolution, "tts_code", "en-IN") or "en-IN")
    indices = []
    for i, s in enumerate(segments):
        if isinstance(s, dict):
            indices.append(int(s.get("cardIndex", s.get("card_index", i)) or i))
        else:
            indices.append(int(getattr(s, "card_index", i) or i))

    contract_hash = compute_contract_hash(
        language_code=code,
        card_surface=surface,
        display_captions=captions,
        spoken_summaries=spoken,
        indices=indices,
    )
    pid = f"{turn_id or 'turn'}:{surface or 'card'}:{uuid.uuid4().hex[:8]}"
    return PresentationBundle(
        presentation_id=pid,
        language=lang,
        language_code=code,
        tts_language=tts,
        card_surface=str(surface) if surface else None,
        segments=public_segs,
        spoken_summaries=spoken,
        display_captions=captions,
        contract_hash=contract_hash,
        created_at=datetime.now(timezone.utc).isoformat(),
        canonical_surface=getattr(resolution, "canonical_surface", None),
        canonical_content_id=getattr(resolution, "canonical_content_id", None),
        content_hash=getattr(resolution, "content_hash", None),
    )
