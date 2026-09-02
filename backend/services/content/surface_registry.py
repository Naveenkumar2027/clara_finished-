"""SurfaceRegistry — capability contract per canonical surface (Milestone 4.2).

SurfaceSelector picks a surface; this registry supplies owners + capabilities.
Do not hardcode capability flags in consumers.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.services.content.types import (
    SURFACE_ADMISSIONS,
    SURFACE_BUS,
    SURFACE_COLLEGE,
    SURFACE_COMPARISON,
    SURFACE_COURSE_MENU,
    SURFACE_DEPARTMENT_FEES,
    SURFACE_DEPARTMENT_OVERVIEW,
    SURFACE_DOCUMENTS,
    SURFACE_FAQ,
    SURFACE_FACULTY,
    SURFACE_HOD,
    SURFACE_PLACEMENTS,
    SURFACE_PRINCIPAL,
    SURFACE_TRUSTEES,
    SURFACE_VICE_PRINCIPAL,
)


@dataclass(frozen=True)
class SurfaceDescriptor:
    """Surface Capability Contract."""

    surface: str
    content_owner: str
    narration_owner: str  # "canonical" | "legacy"
    presentation_mode: str
    card_surface: str | None
    supports_card: bool
    supports_tts: bool
    supports_menu: bool
    supports_interrupt: bool
    supports_language_translation: bool
    supports_summary_generation: bool  # False for all in M4.2
    supports_scene_navigation: bool


def _card(
    surface: str,
    *,
    narration_owner: str = "legacy",
    presentation_mode: str = "CARD_PRESENTATION",
    supports_menu: bool = False,
    supports_scene_navigation: bool = True,
    card_surface: str | None = None,
) -> SurfaceDescriptor:
    return SurfaceDescriptor(
        surface=surface,
        content_owner=surface,
        narration_owner=narration_owner,
        presentation_mode=presentation_mode,
        card_surface=card_surface if card_surface is not None else surface,
        supports_card=True,
        supports_tts=True,
        supports_menu=supports_menu,
        supports_interrupt=True,
        supports_language_translation=True,
        supports_summary_generation=False,
        supports_scene_navigation=supports_scene_navigation,
    )


_REGISTRY: dict[str, SurfaceDescriptor] = {
    SURFACE_DEPARTMENT_OVERVIEW: _card(
        SURFACE_DEPARTMENT_OVERVIEW,
        narration_owner="canonical",
        supports_menu=True,
        supports_scene_navigation=True,
    ),
    SURFACE_DEPARTMENT_FEES: _card(SURFACE_DEPARTMENT_FEES, supports_scene_navigation=False),
    SURFACE_DOCUMENTS: _card(SURFACE_DOCUMENTS, supports_scene_navigation=False),
    SURFACE_PRINCIPAL: _card(SURFACE_PRINCIPAL, supports_scene_navigation=False),
    SURFACE_VICE_PRINCIPAL: _card(SURFACE_VICE_PRINCIPAL, supports_scene_navigation=False),
    SURFACE_HOD: _card(SURFACE_HOD, supports_menu=True, supports_scene_navigation=False),
    SURFACE_FACULTY: _card(SURFACE_FACULTY, supports_scene_navigation=False),
    SURFACE_PLACEMENTS: _card(SURFACE_PLACEMENTS, supports_scene_navigation=True),
    SURFACE_ADMISSIONS: _card(SURFACE_ADMISSIONS, supports_scene_navigation=True),
    SURFACE_TRUSTEES: _card(SURFACE_TRUSTEES, supports_scene_navigation=True),
    SURFACE_COLLEGE: _card(SURFACE_COLLEGE, supports_scene_navigation=True),
    SURFACE_COMPARISON: _card(SURFACE_COMPARISON, supports_scene_navigation=True),
    SURFACE_BUS: _card(SURFACE_BUS, supports_scene_navigation=False),
    SURFACE_COURSE_MENU: _card(
        SURFACE_COURSE_MENU,
        supports_menu=True,
        supports_scene_navigation=False,
    ),
    SURFACE_FAQ: SurfaceDescriptor(
        surface=SURFACE_FAQ,
        content_owner=SURFACE_FAQ,
        narration_owner="legacy",
        presentation_mode="DIRECT_FAQ",
        card_surface=None,
        supports_card=False,
        supports_tts=True,
        supports_menu=False,
        supports_interrupt=True,
        supports_language_translation=True,
        supports_summary_generation=False,
        supports_scene_navigation=False,
    ),
}


def get_surface(surface: str | None) -> SurfaceDescriptor | None:
    if not surface:
        return None
    return _REGISTRY.get(str(surface).strip())


def all_surfaces() -> list[SurfaceDescriptor]:
    return [_REGISTRY[k] for k in sorted(_REGISTRY.keys())]


def registered_surface_ids() -> frozenset[str]:
    return frozenset(_REGISTRY.keys())
