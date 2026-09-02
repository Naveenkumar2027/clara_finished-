"""Canonical card identity registry.

Natural-language aliases and localized labels never enter this module. It maps
language-independent semantic topics/ContentUnit IDs to stable card IDs only.
"""

from __future__ import annotations


TOPIC_TO_INTENT_ID: dict[str, str] = {
    "overview": "show_department",
    "hod": "show_hod",
    "faculty": "show_faculty",
    "admissions": "show_admissions",
    "fees": "show_fees",
    "placements": "show_placements",
    "contact": "show_contact",
    "location": "show_location",
    "principal": "show_principal",
    "vice_principal": "show_vice_principal",
    "trustees": "show_trustees",
}

TOPIC_TO_CARD_ID: dict[str, str] = {
    "overview": "department_overview",
    "hod": "hod_profile",
    "faculty": "faculty_list",
    "admissions": "admissions",
    "fees": "fees",
    "placements": "placements",
    "contact": "contact_details",
    "location": "location",
    "principal": "principal_profile",
    "vice_principal": "vice_principal_profile",
    "trustees": "trustees",
}


def intent_id_for_topic(topic: str) -> str:
    key = (topic or "").strip().lower()
    return TOPIC_TO_INTENT_ID.get(key, f"show_{key}" if key else "unknown")


def card_id_for_topic(topic: str) -> str:
    key = (topic or "").strip().lower()
    return TOPIC_TO_CARD_ID.get(key, key)


def card_id_for_unit_id(unit_id: str) -> str | None:
    """Resolve a registered ContentUnit identity to one canonical card ID."""
    uid = (unit_id or "").strip().lower()
    if not uid or "." not in uid:
        return None
    if uid == "fees.overview":
        return "fees"
    if uid in {"documents.overview", "admission.documents_required"}:
        return "admissions"
    if uid == "leadership.principal":
        return "principal_profile"
    if uid == "leadership.vice_principal":
        return "vice_principal_profile"
    if uid == "leadership.trustees":
        return "trustees"
    if uid.startswith("hostel."):
        return "hostel"
    if uid.startswith("canteen."):
        return "canteen"
    if uid.startswith("events."):
        return "event"
    return card_id_for_topic(uid.split(".", 1)[1]) or None


def department_id_for_unit_id(unit_id: str) -> str | None:
    uid = (unit_id or "").strip().lower()
    if not uid or "." not in uid:
        return None
    if uid.startswith("hostel."):
        parts = uid.split(".")
        return ".".join(parts[:2]) if len(parts) >= 2 else None
    if uid.startswith(("leadership.", "college.", "canteen.", "events.", "fees.", "documents.", "admission.")):
        return None
    return uid.split(".", 1)[0]
