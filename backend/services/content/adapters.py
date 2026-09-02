"""Feature adapters — map current content owners into CanonicalContent (no wording changes)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from backend.services.answer_generation import (
    BUS_ROUTES_SPOKEN_PROMPT_BY_LANGUAGE,
    COURSE_MENU_OPTIONS,
    COURSE_MENU_SPOKEN_PROMPT_BY_LANGUAGE,
    department_label_to_json_key,
    load_locale_data_for_lang_key,
    locale_file_id_for_lang_key,
)
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
    SURFACE_HOD,
    SURFACE_PLACEMENTS,
    SURFACE_PRINCIPAL,
    SURFACE_TRUSTEES,
    SURFACE_VICE_PRINCIPAL,
    CanonicalContent,
    ContentSection,
    ContentType,
    ResolveRequest,
    utc_now_iso,
)
from backend.services.content.validators import compute_content_hash
from backend.services.faq_answers import get_faq_answer_for_question
from backend.services.narration_plan import (
    DOCUMENT_ITEMS,
    DOCUMENT_TITLES,
    _DEPT_DISPLAY,
    _FEES_AMOUNT_BY_KEY,
    _FEES_LABELS,
    _effective_lang,
    _format_inr,
    _init_executive_profiles,
    _load_static_cards,
)

# Bind after init
from backend.services import narration_plan as _narration_plan_mod

_COMPARISON_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "department_comparison.json"
)


def _lang_display(language: str, language_code: str) -> tuple[str, str]:
    code = (language_code or "en").lower().strip() or "en"
    name = (language or "English").strip() or "English"
    return name, code


def _finalize(
    *,
    content_id: str,
    content_type: str,
    surface: str,
    language: str,
    language_code: str,
    title: str,
    subtitle: str,
    summary: str,
    sections: list[ContentSection],
    metadata: dict[str, Any],
    keywords: list[str],
    presentation_mode: str,
    canonical_source: str,
    version: str = "m4.0-foundation",
) -> CanonicalContent:
    secs = tuple(sections)
    h = compute_content_hash(
        title=title,
        subtitle=subtitle,
        summary=summary,
        sections=secs,
        language_code=language_code,
        surface=surface,
        canonical_source=canonical_source,
    )
    return CanonicalContent(
        content_id=content_id,
        content_type=content_type,
        surface=surface,
        language=language,
        language_code=language_code,
        title=title,
        subtitle=subtitle,
        summary=summary,
        sections=secs,
        metadata=dict(metadata),
        keywords=tuple(keywords),
        presentation_mode=presentation_mode,
        canonical_source=canonical_source,
        version=version,
        hash=h,
        created_at=utc_now_iso(),
    )


def _resolve_dept_key(department: str | None) -> str | None:
    if not department:
        return None
    return department_label_to_json_key(department) or (
        department.strip().lower().replace(" ", "_") if department.strip() else None
    )


def adapt_department(req: ResolveRequest) -> CanonicalContent | None:
    language, code = _lang_display(req.language, req.language_code)
    data = load_locale_data_for_lang_key(code)
    deps = data.get("departments")
    if not isinstance(deps, dict):
        return None
    jkey = _resolve_dept_key(req.department)
    if not jkey or not isinstance(deps.get(jkey), dict):
        # All-departments summary when no dept — preserve overview capability
        sections = []
        for i, (k, rec) in enumerate(deps.items()):
            if not isinstance(rec, dict):
                continue
            name = str(rec.get("name") or k)
            intro = str(rec.get("intro") or "")
            sections.append(ContentSection(id=f"dept_{k}", title=name, body=intro))
        if not sections:
            return None
        title = "Departments"
        summary = sections[0].body or title
        return _finalize(
            content_id=f"department:all:{code}",
            content_type=ContentType.DEPARTMENT.value,
            surface=SURFACE_DEPARTMENT_OVERVIEW,
            language=language,
            language_code=code,
            title=title,
            subtitle="",
            summary=summary,
            sections=sections,
            metadata={"department": None, "mode": "all"},
            keywords=["department"],
            presentation_mode="CARD_PRESENTATION",
            canonical_source="backend/data/locales/*.json#departments",
        )

    rec = deps[jkey]
    name = str(rec.get("name") or jkey)
    intro = str(rec.get("intro") or "")
    hod_voice = str(rec.get("hod_voice") or "")
    achievements = str(rec.get("achievements") or "")
    placement = str(rec.get("placement") or "")
    fees = str(rec.get("fees") or "")
    sections = [
        ContentSection(id="intro", title=name, body=intro),
        ContentSection(id="hod_voice", title="HOD & Vision", body=hod_voice),
        ContentSection(id="achievements", title="Achievements", body=achievements),
        ContentSection(id="placement", title="Placements", body=placement),
        ContentSection(id="fees", title="Fees", body=fees),
    ]
    return _finalize(
        content_id=f"department:{jkey}:{code}",
        content_type=ContentType.DEPARTMENT.value,
        surface=SURFACE_DEPARTMENT_OVERVIEW,
        language=language,
        language_code=code,
        title=name,
        subtitle="",
        summary=intro or name,
        sections=sections,
        metadata={"department": jkey, "mode": "single"},
        keywords=["department", jkey],
        presentation_mode="CARD_PRESENTATION",
        canonical_source="backend/data/locales/*.json#departments",
    )


def adapt_fees(req: ResolveRequest) -> CanonicalContent | None:
    language, code = _lang_display(req.language, req.language_code)
    locale_id = locale_file_id_for_lang_key(code)
    lk = _effective_lang(locale_id)
    labels = _FEES_LABELS.get(lk) or _FEES_LABELS["en"]
    display = _DEPT_DISPLAY.get(lk) or _DEPT_DISPLAY["en"]
    jkey = _resolve_dept_key(req.department) or ""
    sections: list[ContentSection] = []
    for k in (
        "cse",
        "ise",
        "cse_aiml",
        "cse_ds",
        "cse_cysec",
        "cse_bs",
        "ece",
        "civil",
        "mechanical",
    ):
        amt = _FEES_AMOUNT_BY_KEY.get(k)
        row_name = display.get(k, k)
        amount_str = _format_inr(amt) if amt else labels["officeContact"]
        body = f"{labels['managementQuotaFee']}: {amount_str}"
        sections.append(ContentSection(id=f"fee_{k}", title=row_name, body=body))
    title = labels["title"]
    summary = labels["description"]
    subtitle = ""
    if jkey:
        subtitle = f"{labels['selectedDepartment']}: {display.get(jkey, jkey)}"
    return _finalize(
        content_id=f"fees:{jkey or 'all'}:{code}",
        content_type=ContentType.FEES.value,
        surface=SURFACE_DEPARTMENT_FEES,
        language=language,
        language_code=code,
        title=title,
        subtitle=subtitle,
        summary=summary,
        sections=sections,
        metadata={
            "department": jkey or None,
            "amounts": dict(_FEES_AMOUNT_BY_KEY),
            "office_contact": labels["officeContact"],
        },
        keywords=["fees"],
        presentation_mode="CARD_PRESENTATION",
        canonical_source="backend/services/narration_plan.py#_FEES_AMOUNT_BY_KEY",
    )


def adapt_documents(req: ResolveRequest) -> CanonicalContent | None:
    language, code = _lang_display(req.language, req.language_code)
    locale_id = locale_file_id_for_lang_key(code)
    lk = _effective_lang(locale_id)
    title = DOCUMENT_TITLES.get(lk, DOCUMENT_TITLES["en"])
    items = DOCUMENT_ITEMS.get(lk) or DOCUMENT_ITEMS["en"]
    sections = [
        ContentSection(id=f"doc_{i}", title=str(i + 1), body=str(item))
        for i, item in enumerate(items)
    ]
    summary = items[0] if items else title
    return _finalize(
        content_id=f"documents:{code}",
        content_type=ContentType.DOCUMENTS.value,
        surface=SURFACE_DOCUMENTS,
        language=language,
        language_code=code,
        title=title,
        subtitle="",
        summary=summary,
        sections=sections,
        metadata={"item_count": len(items)},
        keywords=["documents"],
        presentation_mode="CARD_PRESENTATION",
        canonical_source="backend/services/narration_plan.py#DOCUMENT_ITEMS",
    )


def adapt_principal(req: ResolveRequest) -> CanonicalContent | None:
    _init_executive_profiles()
    language, code = _lang_display(req.language, req.language_code)
    locale_id = locale_file_id_for_lang_key(code)
    lk = _effective_lang(locale_id)
    pack = _narration_plan_mod.EXEC_PRINCIPAL or {}
    p = pack.get(lk) or pack.get("en") or {}
    if not p:
        return None
    title = str(p.get("name") or "Principal")
    summary = str(p.get("bio") or "")
    sections = [
        ContentSection(id="label", title="Label", body=str(p.get("label") or "")),
        ContentSection(id="name", title="Name", body=str(p.get("name") or "")),
        ContentSection(id="title", title="Title", body=str(p.get("title") or "")),
        ContentSection(id="bio", title="Bio", body=summary),
    ]
    return _finalize(
        content_id=f"principal:{code}",
        content_type=ContentType.PRINCIPAL.value,
        surface=SURFACE_PRINCIPAL,
        language=language,
        language_code=code,
        title=title,
        subtitle=str(p.get("title") or ""),
        summary=summary or title,
        sections=sections,
        metadata={},
        keywords=["principal"],
        presentation_mode="CARD_PRESENTATION",
        canonical_source="backend/services/narration_plan.py#EXEC_PRINCIPAL",
    )


def adapt_vice_principal(req: ResolveRequest) -> CanonicalContent | None:
    _init_executive_profiles()
    language, code = _lang_display(req.language, req.language_code)
    locale_id = locale_file_id_for_lang_key(code)
    lk = _effective_lang(locale_id)
    pack = _narration_plan_mod.EXEC_VICE or {}
    p = pack.get(lk) or pack.get("en") or {}
    if not p:
        return None
    title = str(p.get("name") or "Vice Principal")
    summary = str(p.get("bio") or "")
    sections = [
        ContentSection(id="label", title="Label", body=str(p.get("label") or "")),
        ContentSection(id="name", title="Name", body=str(p.get("name") or "")),
        ContentSection(id="title", title="Title", body=str(p.get("title") or "")),
        ContentSection(id="bio", title="Bio", body=summary),
    ]
    return _finalize(
        content_id=f"vice_principal:{code}",
        content_type=ContentType.VICE_PRINCIPAL.value,
        surface=SURFACE_VICE_PRINCIPAL,
        language=language,
        language_code=code,
        title=title,
        subtitle=str(p.get("title") or ""),
        summary=summary or title,
        sections=sections,
        metadata={},
        keywords=["vice_principal"],
        presentation_mode="CARD_PRESENTATION",
        canonical_source="backend/services/narration_plan.py#EXEC_VICE",
    )


def adapt_hod(req: ResolveRequest) -> CanonicalContent | None:
    language, code = _lang_display(req.language, req.language_code)
    data = load_locale_data_for_lang_key(code)
    deps = data.get("departments")
    if not isinstance(deps, dict):
        return None
    jkey = _resolve_dept_key(req.department)
    if not jkey or not isinstance(deps.get(jkey), dict):
        # Pick-prompt style: list dept names
        sections = []
        for k, rec in deps.items():
            if isinstance(rec, dict):
                sections.append(
                    ContentSection(
                        id=f"hod_{k}",
                        title=str(rec.get("name") or k),
                        body=str(rec.get("hod_voice") or ""),
                    )
                )
        if not sections:
            return None
        return _finalize(
            content_id=f"hod:pick:{code}",
            content_type=ContentType.HOD.value,
            surface=SURFACE_HOD,
            language=language,
            language_code=code,
            title="Head of Department",
            subtitle="",
            summary="Select a department to view HOD details.",
            sections=sections,
            metadata={"mode": "pick"},
            keywords=["hod"],
            presentation_mode="CARD_PRESENTATION",
            canonical_source="backend/data/locales/*.json#departments.*.hod_voice",
        )
    rec = deps[jkey]
    name = str(rec.get("name") or jkey)
    hod_voice = str(rec.get("hod_voice") or "")
    return _finalize(
        content_id=f"hod:{jkey}:{code}",
        content_type=ContentType.HOD.value,
        surface=SURFACE_HOD,
        language=language,
        language_code=code,
        title=name,
        subtitle="HOD",
        summary=hod_voice or name,
        sections=[
            ContentSection(id="department", title="Department", body=name),
            ContentSection(id="hod_voice", title="Lead & Vision", body=hod_voice),
        ],
        metadata={"department": jkey},
        keywords=["hod", jkey],
        presentation_mode="CARD_PRESENTATION",
        canonical_source="backend/data/locales/*.json#departments.*.hod_voice",
    )


def adapt_placements(req: ResolveRequest) -> CanonicalContent | None:
    language, code = _lang_display(req.language, req.language_code)
    data = load_locale_data_for_lang_key(code)
    pt = data.get("placements_and_training")
    if not isinstance(pt, dict):
        return None
    obj = str(pt.get("objectives") or "")
    train = str(pt.get("training_programs") or "")
    sections = [
        ContentSection(id="objectives", title="Objectives", body=obj),
        ContentSection(id="training", title="Training programs", body=train),
    ]
    summary = obj or train or "Placements"
    return _finalize(
        content_id=f"placements:{code}",
        content_type=ContentType.PLACEMENTS.value,
        surface=SURFACE_PLACEMENTS,
        language=language,
        language_code=code,
        title="Placements & Training",
        subtitle="",
        summary=summary,
        sections=sections,
        metadata={},
        keywords=["placements"],
        presentation_mode="CARD_PRESENTATION",
        canonical_source="backend/data/locales/*.json#placements_and_training",
    )


def adapt_admissions(req: ResolveRequest) -> CanonicalContent | None:
    language, code = _lang_display(req.language, req.language_code)
    data = load_locale_data_for_lang_key(code)
    adm = data.get("admissions_and_fees")
    if not isinstance(adm, dict):
        return None
    elig = str(adm.get("eligibility") or "")
    exams = adm.get("entrance_exams")
    exam_body = ""
    if isinstance(exams, list):
        exam_body = "\n".join(str(x) for x in exams)
    elif exams:
        exam_body = str(exams)
    sections = [
        ContentSection(id="eligibility", title="Eligibility", body=elig),
        ContentSection(id="entrance_exams", title="Entrance exams", body=exam_body),
    ]
    return _finalize(
        content_id=f"admissions:{code}",
        content_type=ContentType.ADMISSIONS.value,
        surface=SURFACE_ADMISSIONS,
        language=language,
        language_code=code,
        title="Admissions",
        subtitle="",
        summary=elig or "Admissions",
        sections=sections,
        metadata={},
        keywords=["admissions"],
        presentation_mode="CARD_PRESENTATION",
        canonical_source="backend/data/locales/*.json#admissions_and_fees",
    )


def _static_pack(code: str, key: str) -> list[dict[str, Any]]:
    raw = _load_static_cards()
    lk = _effective_lang(locale_file_id_for_lang_key(code))
    pack = raw.get(lk) or raw.get("en") if isinstance(raw, dict) else None
    if not isinstance(pack, dict):
        return []
    cards = pack.get(key)
    return cards if isinstance(cards, list) else []


def adapt_trustees(req: ResolveRequest) -> CanonicalContent | None:
    language, code = _lang_display(req.language, req.language_code)
    data = load_locale_data_for_lang_key(code)
    holders = data.get("role_holders") if isinstance(data, dict) else None
    trustees = holders.get("trustees") if isinstance(holders, dict) else None
    if not isinstance(trustees, list) or not trustees:
        return None
    sections = []
    for i, item in enumerate(trustees):
        if not isinstance(item, dict):
            continue
        title = str(item.get("display_name") or item.get("name") or f"Trustee {i+1}").strip()
        body = str(item.get("tts_summary") or item.get("description") or "").strip()
        designation = str(item.get("designation") or "").strip()
        if designation and body and designation not in body:
            body = f"{designation}. {body}"
        elif designation and not body:
            body = designation
        sections.append(ContentSection(id=str(item.get("id") or f"trustee_{i}"), title=title, body=body))
    if not sections:
        return None
    ui = holders.get("ui") if isinstance(holders.get("ui"), dict) else {}
    heading = str(ui.get("board_label") or "Trustees")
    return _finalize(
        content_id=f"trustees:{code}",
        content_type=ContentType.TRUSTEES.value,
        surface=SURFACE_TRUSTEES,
        language=language,
        language_code=code,
        title=heading,
        subtitle="",
        summary=sections[0].body if sections else heading,
        sections=sections,
        metadata={"slide_count": len(sections), "trustee_ids": [s.id for s in sections]},
        keywords=["trustees"],
        presentation_mode="CARD_PRESENTATION",
        canonical_source="backend/data/locales/*.json#role_holders.trustees",
    )


def adapt_college(req: ResolveRequest) -> CanonicalContent | None:
    language, code = _lang_display(req.language, req.language_code)
    cards = _static_pack(code, "college")
    if not cards:
        return None
    sections = []
    for i, c in enumerate(cards):
        if not isinstance(c, dict):
            continue
        sections.append(
            ContentSection(
                id=f"college_{i}",
                title=str(c.get("title") or f"Slide {i+1}"),
                body=str(c.get("content") or ""),
            )
        )
    summary = sections[0].body if sections else "College"
    return _finalize(
        content_id=f"college:{code}",
        content_type=ContentType.COLLEGE.value,
        surface=SURFACE_COLLEGE,
        language=language,
        language_code=code,
        title="College Overview",
        subtitle="",
        summary=summary,
        sections=sections,
        metadata={"slide_count": len(sections)},
        keywords=["college"],
        presentation_mode="CARD_PRESENTATION",
        canonical_source="backend/data/narration/static_cards.json#college",
    )


def adapt_comparison(req: ResolveRequest) -> CanonicalContent | None:
    language, code = _lang_display(req.language, req.language_code)
    try:
        data = json.loads(_COMPARISON_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    deps = data.get("departments") if isinstance(data, dict) else None
    if not isinstance(deps, dict):
        return None
    ids = list(req.comparison_department_ids) or list(data.get("department_order") or [])[:3]
    ids = [x for x in ids if isinstance(x, str) and x in deps]
    if not ids:
        ids = list(deps.keys())[:2]
    sections: list[ContentSection] = []
    for did in ids:
        row = deps.get(did)
        if not isinstance(row, dict):
            continue
        names = row.get("display_names") if isinstance(row.get("display_names"), dict) else {}
        name = str(names.get(code) or names.get("en") or did)
        cells = row.get("cells") if isinstance(row.get("cells"), dict) else {}
        learn = cells.get("student_learning_4y") if isinstance(cells.get("student_learning_4y"), dict) else {}
        body = str(learn.get(code) or learn.get("en") or "")
        sections.append(ContentSection(id=f"cmp_{did}", title=name, body=body))
    if not sections:
        return None
    return _finalize(
        content_id=f"comparison:{'-'.join(ids)}:{code}",
        content_type=ContentType.COMPARISON.value,
        surface=SURFACE_COMPARISON,
        language=language,
        language_code=code,
        title="Department Comparison",
        subtitle="",
        summary=sections[0].body or sections[0].title,
        sections=sections,
        metadata={"department_ids": ids},
        keywords=["comparison"],
        presentation_mode="CARD_PRESENTATION",
        canonical_source="backend/data/department_comparison.json",
    )


def adapt_bus(req: ResolveRequest) -> CanonicalContent | None:
    language, code = _lang_display(req.language, req.language_code)
    prompt = BUS_ROUTES_SPOKEN_PROMPT_BY_LANGUAGE.get(
        language, BUS_ROUTES_SPOKEN_PROMPT_BY_LANGUAGE["English"]
    )
    return _finalize(
        content_id=f"bus:{code}",
        content_type=ContentType.BUS.value,
        surface=SURFACE_BUS,
        language=language,
        language_code=code,
        title="Bus Routes",
        subtitle="",
        summary=prompt,
        sections=[ContentSection(id="prompt", title="Spoken prompt", body=prompt)],
        metadata={
            "routes_ui": "frontend/src/data/collegeBusRoutes.json",
            "note": "Spoken prompt only; route table is FE-owned.",
        },
        keywords=["bus"],
        presentation_mode="CARD_PRESENTATION",
        canonical_source="backend/services/answer_generation.py#BUS_ROUTES_SPOKEN_PROMPT_BY_LANGUAGE",
    )


def adapt_course_menu(req: ResolveRequest) -> CanonicalContent | None:
    language, code = _lang_display(req.language, req.language_code)
    prompt = COURSE_MENU_SPOKEN_PROMPT_BY_LANGUAGE.get(
        language, COURSE_MENU_SPOKEN_PROMPT_BY_LANGUAGE["English"]
    )
    sections = [
        ContentSection(id=f"opt_{i}", title=opt, body=opt)
        for i, opt in enumerate(COURSE_MENU_OPTIONS)
    ]
    return _finalize(
        content_id=f"course_menu:{code}",
        content_type=ContentType.COURSE_MENU.value,
        surface=SURFACE_COURSE_MENU,
        language=language,
        language_code=code,
        title="Course Menu",
        subtitle="",
        summary=prompt,
        sections=sections,
        metadata={"spoken_prompt": prompt, "options": list(COURSE_MENU_OPTIONS)},
        keywords=["courses", "menu"],
        presentation_mode="CARD_PRESENTATION",
        canonical_source="backend/services/answer_generation.py#COURSE_MENU_OPTIONS+PROMPT",
    )


def adapt_faq(req: ResolveRequest) -> CanonicalContent | None:
    language, code = _lang_display(req.language, req.language_code)
    q = (req.faq_question or "").strip()
    if not q:
        return None
    answer = get_faq_answer_for_question(q, language)
    if not answer:
        return None
    return _finalize(
        content_id=f"faq:{hash(q) & 0xFFFFFFFF:x}:{code}",
        content_type=ContentType.FAQ.value,
        surface=SURFACE_FAQ,
        language=language,
        language_code=code,
        title=q,
        subtitle="",
        summary=answer,
        sections=[
            ContentSection(id="question", title="Question", body=q),
            ContentSection(id="answer", title="Answer", body=answer),
        ],
        metadata={},
        keywords=["faq"],
        presentation_mode="DIRECT_FAQ",
        canonical_source="backend/data/faq_answers.json",
    )


def adapt_campus_unit(req: ResolveRequest) -> CanonicalContent | None:
    """Campus units resolve per unitId via ContentUnitResolver, never as a mega-card."""
    return None


def adapt_faculty(req: ResolveRequest) -> CanonicalContent | None:
    """Faculty resolves per department unit via ContentUnitResolver."""
    return None


ADAPTERS: dict[str, Callable[[ResolveRequest], CanonicalContent | None]] = {
    "department": adapt_department,
    "fees": adapt_fees,
    "documents": adapt_documents,
    "principal": adapt_principal,
    "vice_principal": adapt_vice_principal,
    "hod": adapt_hod,
    "placements": adapt_placements,
    "admissions": adapt_admissions,
    "trustees": adapt_trustees,
    "college": adapt_college,
    "comparison": adapt_comparison,
    "bus": adapt_bus,
    "course_menu": adapt_course_menu,
    "faq": adapt_faq,
    "campus_unit": adapt_campus_unit,
    "faculty": adapt_faculty,
}


def get_adapter(adapter_key: str) -> Callable[[ResolveRequest], CanonicalContent | None] | None:
    return ADAPTERS.get(adapter_key)
