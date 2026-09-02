"""Hostel, canteen, and event ContentUnits (M5.10 Phase 2C).

Category is organizational only. The selectable object is the unitId.
Does not invent official institutional facts — locale records are SAMPLE.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.services.content.semantic_composition import SemanticItem
from backend.services.content.unicode_text import casefold_keep_scripts, latin_token_boundaries_ok

SAMPLE_STATUS = "SAMPLE_REPLACE_WITH_OFFICIAL"

HOSTEL_GIRLS = "hostel.girls"
HOSTEL_BOYS = "hostel.boys"
CANTEEN_ENTITY = "canteen"
EVENTS_PREFIX = "events."

HOSTEL_TOPICS: tuple[str, ...] = (
    "overview",
    "rooms",
    "timings",
    "food",
    "safety",
    "activities",
    "fees",
)
CANTEEN_TOPICS: tuple[str, ...] = (
    "overview",
    "food_quality",
    "hygiene",
    "variety",
    "pricing",
    "timings",
    "safety",
)
EVENT_IDS: tuple[str, ...] = (
    "sanchalana",
    "techvidya",
    "sirikannada_utsava",
    "freshers_fest",
    "sports_meet",
    "project_expo",
    "alumni_meet",
)

HOSTEL_UNIT_IDS: tuple[str, ...] = tuple(
    f"{entity}.{topic}" for entity in (HOSTEL_GIRLS, HOSTEL_BOYS) for topic in HOSTEL_TOPICS
)
CANTEEN_UNIT_IDS: tuple[str, ...] = tuple(f"canteen.{topic}" for topic in CANTEEN_TOPICS)
EVENT_UNIT_IDS: tuple[str, ...] = tuple(f"events.{eid}" for eid in EVENT_IDS)
CAMPUS_UNIT_IDS: tuple[str, ...] = HOSTEL_UNIT_IDS + CANTEEN_UNIT_IDS + EVENT_UNIT_IDS

HOSTEL_ENTITIES = frozenset({HOSTEL_GIRLS, HOSTEL_BOYS})
CAMPUS_ENTITIES = HOSTEL_ENTITIES | {CANTEEN_ENTITY} | frozenset(EVENT_UNIT_IDS)


def is_campus_entity(entity: str) -> bool:
    return (entity or "").strip().lower() in CAMPUS_ENTITIES


def is_campus_unit_id(unit_id: str) -> bool:
    return (unit_id or "").strip().lower() in set(CAMPUS_UNIT_IDS)


def unit_id_for_campus_item(entity: str, topic: str) -> str | None:
    ent = (entity or "").strip().lower()
    top = (topic or "").strip().lower() or "overview"
    if ent in HOSTEL_ENTITIES:
        if top not in HOSTEL_TOPICS:
            return None
        return f"{ent}.{top}"
    if ent == CANTEEN_ENTITY:
        if top == "food":
            top = "food_quality"
        if top == "fees":
            top = "pricing"
        if top not in CANTEEN_TOPICS:
            return None
        return f"canteen.{top}"
    if ent in EVENT_UNIT_IDS or ent.startswith(EVENTS_PREFIX):
        if ent in EVENT_UNIT_IDS:
            return ent
    return None


# Longer cues first. Gendered hostel phrases beat bare "hostel".
_GIRLS_CUES: tuple[str, ...] = (
    "girls hostel",
    "girl's hostel",
    "girls' hostel",
    "ladies hostel",
    "women's hostel",
    "womens hostel",
    "woman hostel",
    "girls hostal",
    "ಹುಡುಗಿಯರ ಹಾಸ್ಟೆಲ್",
    "ಹುಡುಗಿಯರ ವಸತಿ",
    "ಮಹಿಳಾ ಹಾಸ್ಟೆಲ್",
    "ಗರ್ಲ್ಸ್ ಹಾಸ್ಟೆಲ್",
    "लड़कियों के हॉस्टल",
    "लड़कियों का हॉस्टल",
    "महिला हॉस्टल",
    "गर्ल्स हॉस्टल",
    "பெண்கள் விடுதி",
    "பெண்கள் ஹாஸ்டல்",
    "బాలికల హాస్టల్",
    "ఆడపిల్లల హాస్టల్",
    "గర్ల్స్ హాస్టల్",
    "പെൺകുട്ടികളുടെ ഹോസ്റ്റൽ",
    "ഗേൾസ് ഹോസ്റ്റൽ",
)
_BOYS_CUES: tuple[str, ...] = (
    "boys hostel",
    "boy's hostel",
    "boys' hostel",
    "mens hostel",
    "men's hostel",
    "gents hostel",
    "boys hostal",
    "ಹುಡುಗರ ಹಾಸ್ಟೆಲ್",
    "ಹುಡುಗರ ವಸತಿ",
    "ಬಾಯ್ಸ್ ಹಾಸ್ಟೆಲ್",
    "लड़कों के हॉस्टल",
    "लड़कों का हॉस्टल",
    "बॉयज हॉस्टल",
    "ஆண்கள் விடுதி",
    "ஆண்கள் ஹாஸ்டல்",
    "బాలుర హాస్టల్",
    "బాయ్స్ హాస్టల్",
    "ആൺകുട്ടികളുടെ ഹോസ്റ്റൽ",
    "ബോയ്സ് ഹോസ്റ്റൽ",
)
_CANTEEN_CUES: tuple[str, ...] = (
    "college canteen",
    "canteen",
    "cafeteria",
    "ಕ್ಯಾಂಟೀನ್",
    "ಕ್ಯಾಂಟಿನ್",
    "कैंटीन",
    "केन्टीन",
    "கேண்டீன்",
    "కాంటీన్",
    "കാന്റീൻ",
)
_EVENT_CUES: tuple[tuple[str, str], ...] = (
    ("events.sanchalana", "sanchalana"),
    ("events.sanchalana", "sanchaalana"),
    ("events.sanchalana", "ಸಂಚಲನ"),
    ("events.sanchalana", "संचलना"),
    ("events.sanchalana", "சஞ்சலனா"),
    ("events.sanchalana", "సంచలన"),
    ("events.sanchalana", "സഞ്ചലന"),
    ("events.techvidya", "techvidya"),
    ("events.techvidya", "techvidyaയെ"),
    ("events.techvidya", "tech vidya"),
    ("events.techvidya", "tech-vidya"),
    ("events.techvidya", "ಟೆಕ್ ವಿದ್ಯಾ"),
    ("events.techvidya", "ಟೆಕ್‌ವಿದ್ಯಾ"),
    ("events.techvidya", "टेक विद्या"),
    ("events.techvidya", "டெக் வித்யா"),
    ("events.techvidya", "టెక్ విద్యా"),
    ("events.techvidya", "ടെക് വിദ്യ"),
    ("events.sirikannada_utsava", "sirikannada utsava"),
    ("events.sirikannada_utsava", "siri kannada utsava"),
    ("events.sirikannada_utsava", "siri kannada"),
    ("events.sirikannada_utsava", "sirikannada"),
    ("events.sirikannada_utsava", "ಸಿರಿಕನ್ನಡ ಉತ್ಸವ"),
    ("events.sirikannada_utsava", "ಸಿರಿಕನ್ನಡ"),
    ("events.sirikannada_utsava", "सिरीकन्नड़"),
    ("events.sirikannada_utsava", "சிரிகன்னட"),
    ("events.sirikannada_utsava", "సిరికన్నడ"),
    ("events.sirikannada_utsava", "സിരികന്നഡ"),
    ("events.freshers_fest", "freshers fest"),
    ("events.freshers_fest", "fresher's fest"),
    ("events.freshers_fest", "freshers"),
    ("events.freshers_fest", "ಫ್ರೆಷರ್ಸ್"),
    ("events.freshers_fest", "फ्रेशर्स"),
    ("events.freshers_fest", "ஃப்ரெஷர்ஸ்"),
    ("events.freshers_fest", "ఫ్రెషర్స్"),
    ("events.freshers_fest", "ഫ്രെഷേഴ്സ്"),
    ("events.sports_meet", "sports meet"),
    ("events.sports_meet", "sports day"),
    ("events.sports_meet", "ಕ್ರೀಡಾ ಕೂಟ"),
    ("events.sports_meet", "खेल मेला"),
    ("events.sports_meet", "விளையாட்டு சந்திப்பு"),
    ("events.sports_meet", "క్రీడా కూటం"),
    ("events.sports_meet", "കായിക മീറ്റ്"),
    ("events.project_expo", "project expo"),
    ("events.project_expo", "project exhibition"),
    ("events.project_expo", "ಪ್ರಾಜೆಕ್ಟ್ ಎಕ್ಸ್‌ಪೋ"),
    ("events.project_expo", "प्रोजेक्ट एक्सपो"),
    ("events.project_expo", "பிராஜெக்ட் எக்ஸ்போ"),
    ("events.project_expo", "ప్రాజెక్ట్ ఎక్స్‌పో"),
    ("events.project_expo", "പ്രോജക്ട് എക്സ്പോ"),
    ("events.alumni_meet", "alumni meet"),
    ("events.alumni_meet", "alumni day"),
    ("events.alumni_meet", "ಹಳೆಯ ವಿದ್ಯಾರ್ಥಿ"),
    ("events.alumni_meet", "पूर्व छात्र"),
    ("events.alumni_meet", "முன்னாள் மாணவர்"),
    ("events.alumni_meet", "పూర్వ విద్యార్థి"),
    ("events.alumni_meet", "പൂർവ വിദ്യാർഥി"),
)

# Canonical campus topics. "fees" is reused with hostel; canteen maps later.
_TOPIC_CUES: tuple[tuple[str, str], ...] = (
    ("rooms", "comfortable rooms"),
    ("rooms", "hostel rooms"),
    ("rooms", "rooms"),
    ("rooms", "room"),
    ("rooms", "ಕೊಠಡಿ"),
    ("rooms", "कमरे"),
    ("rooms", "அறைகள்"),
    ("rooms", "గదులు"),
    ("rooms", "മുറികൾ"),
    ("timings", "entry and exit"),
    ("timings", "entry time"),
    ("timings", "exit time"),
    ("timings", "in-time"),
    ("timings", "out-time"),
    ("timings", "timings"),
    ("timings", "timing"),
    ("timings", "ಸಮಯ"),
    ("timings", "समय"),
    ("timings", "நேரம்"),
    ("timings", "సమయం"),
    ("timings", "സമയം"),
    ("food_quality", "food quality"),
    ("food", "hostel food"),
    ("food", "hostel mess"),
    ("food", "mess food"),
    ("food", "food"),
    ("food", "ಆಹಾರ"),
    ("food", "खाना"),
    ("food", "உணவு"),
    ("food", "ఆహారం"),
    ("food", "ഭക്ഷണം"),
    ("safety", "anti-ragging"),
    ("safety", "anti ragging"),
    ("safety", "no ragging"),
    ("safety", "ragging"),
    ("safety", "food safety"),
    ("safety", "safety"),
    ("safety", "security"),
    ("safety", "ಭದ್ರತೆ"),
    ("safety", "सुरक्षा"),
    ("safety", "பாதுகாப்பு"),
    ("safety", "భద్రత"),
    ("safety", "സുരക്ഷ"),
    ("activities", "hostel activities"),
    ("activities", "activities"),
    ("activities", "ಚಟುವಟಿಕೆ"),
    ("activities", "गतिविधि"),
    ("activities", "செயல்பாடு"),
    ("activities", "కార్యకలాప"),
    ("activities", "പ്രവർത്തന"),
    ("fees", "hostel fees"),
    ("fees", "hostel charges"),
    ("fees", "fees"),
    ("fees", "fee"),
    ("fees", "ಶುಲ್ಕ"),
    ("fees", "फीस"),
    ("fees", "கட்டணம்"),
    ("fees", "ఫీజు"),
    ("fees", "ഫീസ്"),
    ("hygiene", "hygiene"),
    ("hygiene", "cleanliness"),
    ("hygiene", "clean"),
    ("hygiene", "ನೈರ್ಮಲ್ಯ"),
    ("hygiene", "ಸ್ವಚ್ಛತೆ"),
    ("hygiene", "स्वच्छता"),
    ("hygiene", "சுகாதாரம்"),
    ("hygiene", "పరిశుభ్రత"),
    ("hygiene", "ശുചിത്വം"),
    ("variety", "variety"),
    ("variety", "menu"),
    ("variety", "ವೈವಿಧ್ಯ"),
    ("variety", "विविधता"),
    ("variety", "வகை"),
    ("variety", "వైవిధ్యం"),
    ("variety", "വൈവിധ്യം"),
    ("pricing", "pricing"),
    ("pricing", "affordable"),
    ("pricing", "price"),
    ("pricing", "ಬೆಲೆ"),
    ("pricing", "कीमत"),
    ("pricing", "விலை"),
    ("pricing", "ధర"),
    ("pricing", "വില"),
    ("overview", "facilities"),
    ("overview", "amenities"),
)


@dataclass(frozen=True)
class CampusSpan:
    entity: str
    start: int
    end: int
    family: str


@dataclass(frozen=True)
class CampusTopicSpan:
    topic: str
    start: int
    end: int


def _boundaries_ok(hay: str, start: int, end: int) -> bool:
    return latin_token_boundaries_ok(hay, start, end)


def _consume(hay: str, occupied: list[bool], cues: tuple[str, ...], entity: str, family: str) -> list[CampusSpan]:
    spans: list[CampusSpan] = []
    variants = sorted((casefold_keep_scripts(c) for c in cues if c), key=len, reverse=True)
    for variant in variants:
        if not variant:
            continue
        probe = 0
        while True:
            idx = hay.find(variant, probe)
            if idx < 0:
                break
            end = idx + len(variant)
            if end <= len(occupied) and not any(occupied[idx:end]) and _boundaries_ok(hay, idx, end):
                for i in range(idx, end):
                    occupied[i] = True
                spans.append(CampusSpan(entity=entity, start=idx, end=end, family=family))
                probe = end
            else:
                probe = idx + 1
    return spans


def detect_campus_entity_spans(raw_text: str) -> tuple[CampusSpan, ...]:
    if not raw_text or not isinstance(raw_text, str):
        return ()
    hay = casefold_keep_scripts(raw_text)
    if not hay:
        return ()
    occupied = [False] * len(hay)
    spans: list[CampusSpan] = []
    for unit_id, cue in sorted(_EVENT_CUES, key=lambda p: len(p[1]), reverse=True):
        spans.extend(_consume(hay, occupied, (cue,), unit_id, "event"))
    spans.extend(_consume(hay, occupied, _GIRLS_CUES, HOSTEL_GIRLS, "hostel"))
    spans.extend(_consume(hay, occupied, _BOYS_CUES, HOSTEL_BOYS, "hostel"))
    spans.extend(_consume(hay, occupied, _CANTEEN_CUES, CANTEEN_ENTITY, "canteen"))
    spans.sort(key=lambda s: s.start)
    seen: set[str] = set()
    out: list[CampusSpan] = []
    for span in spans:
        if span.entity in seen:
            continue
        seen.add(span.entity)
        out.append(span)
    return tuple(out)


def detect_campus_topic_spans(raw_text: str) -> tuple[CampusTopicSpan, ...]:
    if not raw_text or not isinstance(raw_text, str):
        return ()
    hay = casefold_keep_scripts(raw_text)
    if not hay:
        return ()
    occupied = [False] * len(hay)
    spans: list[CampusTopicSpan] = []
    variants = sorted(_TOPIC_CUES, key=lambda p: len(p[1]), reverse=True)
    for canonical, cue in variants:
        folded = casefold_keep_scripts(cue)
        if not folded:
            continue
        probe = 0
        while True:
            idx = hay.find(folded, probe)
            if idx < 0:
                break
            end = idx + len(folded)
            if end <= len(occupied) and not any(occupied[idx:end]) and _boundaries_ok(hay, idx, end):
                for i in range(idx, end):
                    occupied[i] = True
                spans.append(CampusTopicSpan(topic=canonical, start=idx, end=end))
                probe = end
            else:
                probe = idx + 1
    spans.sort(key=lambda s: s.start)
    return tuple(spans)


def _distance(a_start: int, a_end: int, b_start: int, b_end: int) -> int:
    if a_end <= b_start:
        return b_start - a_end
    if b_end <= a_start:
        return a_start - b_end
    return 0


def _normalize_topic_for_family(topic: str, family: str) -> str:
    if family == "canteen":
        if topic == "food":
            return "food_quality"
        if topic == "fees":
            return "pricing"
    return topic


def _topic_allowed(topic: str, family: str) -> bool:
    if family == "hostel":
        return topic in HOSTEL_TOPICS
    if family == "canteen":
        return topic in CANTEEN_TOPICS
    return False


def pair_campus_items(
    *,
    entity_spans: tuple[CampusSpan, ...],
    topic_spans: tuple[CampusTopicSpan, ...],
) -> tuple[SemanticItem, ...]:
    """Bind campus topics to campus entities. Events never take a sibling topic."""
    if not entity_spans:
        return ()

    events = tuple(s for s in entity_spans if s.family == "event")
    bindable = tuple(s for s in entity_spans if s.family != "event")
    items: list[SemanticItem] = []

    if bindable:
        usable: list[CampusTopicSpan] = []
        for ts in topic_spans:
            # A topic is kept if it is valid for at least one bindable family after mapping.
            if any(_topic_allowed(_normalize_topic_for_family(ts.topic, s.family), s.family) for s in bindable):
                usable.append(ts)
        distinct: list[str] = []
        for ts in usable:
            if ts.topic not in distinct:
                distinct.append(ts.topic)

        if not distinct:
            items.extend(SemanticItem(entity=s.entity, topic="overview") for s in bindable)
        elif len(distinct) == 1:
            raw_topic = distinct[0]
            for ent in bindable:
                mapped = _normalize_topic_for_family(raw_topic, ent.family)
                if _topic_allowed(mapped, ent.family):
                    items.append(SemanticItem(entity=ent.entity, topic=mapped))
                else:
                    items.append(SemanticItem(entity=ent.entity, topic="overview"))
        elif len(bindable) == 1:
            ent = bindable[0]
            for raw_topic in distinct:
                mapped = _normalize_topic_for_family(raw_topic, ent.family)
                if _topic_allowed(mapped, ent.family):
                    items.append(SemanticItem(entity=ent.entity, topic=mapped))
        elif len(distinct) == len(bindable):
            bound = _bind_campus_proximity(bindable, tuple(usable), distinct)
            if bound:
                items.extend(bound)
            else:
                items.extend(SemanticItem(entity=s.entity, topic="overview") for s in bindable)
        else:
            # Unequal N: bind each topic to the nearest compatible entity; leftover entities overview.
            claimed: set[str] = set()
            for ts in usable:
                choice = None
                for ent in bindable:
                    mapped = _normalize_topic_for_family(ts.topic, ent.family)
                    if not _topic_allowed(mapped, ent.family):
                        continue
                    dist = _distance(ts.start, ts.end, ent.start, ent.end)
                    cand = (dist, ent.start, ent.entity)
                    if choice is None or cand < choice:
                        choice = cand
                if choice is None:
                    continue
                _, _, entity = choice
                family = next(s.family for s in bindable if s.entity == entity)
                mapped = _normalize_topic_for_family(ts.topic, family)
                key = (entity, mapped)
                if key in claimed:
                    continue
                claimed.add(key)
                items.append(SemanticItem(entity=entity, topic=mapped))
            for ent in bindable:
                if not any(i.entity == ent.entity for i in items):
                    items.append(SemanticItem(entity=ent.entity, topic="overview"))

    items.extend(SemanticItem(entity=s.entity, topic="overview") for s in events)
    start_of = {s.entity: s.start for s in entity_spans}
    items.sort(key=lambda it: start_of.get(it.entity, 0))
    out: list[SemanticItem] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        key = (item.entity, item.topic)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return tuple(out)


def _bind_campus_proximity(
    entities: tuple[CampusSpan, ...],
    topics: tuple[CampusTopicSpan, ...],
    distinct: list[str],
) -> tuple[SemanticItem, ...] | None:
    best: dict[tuple[str, int], int] = {}
    for topic in distinct:
        for e_index, ent in enumerate(entities):
            mapped = _normalize_topic_for_family(topic, ent.family)
            if not _topic_allowed(mapped, ent.family):
                continue
            distances = [
                _distance(ts.start, ts.end, ent.start, ent.end)
                for ts in topics
                if ts.topic == topic
            ]
            if distances:
                best[(topic, e_index)] = min(distances)
    unbound_topics = list(enumerate(distinct))
    unbound_entities = list(range(len(entities)))
    bound: list[tuple[int, int]] = []
    while unbound_topics and unbound_entities:
        choice = None
        for t_pos, (t_index, topic) in enumerate(unbound_topics):
            for e_index in unbound_entities:
                dist = best.get((topic, e_index))
                if dist is None:
                    continue
                candidate = (dist, t_index, e_index, t_pos)
                if choice is None or candidate < choice:
                    choice = candidate
        if choice is None:
            return None
        _, t_index, e_index, t_pos = choice
        bound.append((e_index, t_index))
        unbound_topics.pop(t_pos)
        unbound_entities.remove(e_index)
    bound.sort(key=lambda p: entities[p[0]].start)
    items: list[SemanticItem] = []
    for e_index, t_index in bound:
        ent = entities[e_index]
        mapped = _normalize_topic_for_family(distinct[t_index], ent.family)
        if not _topic_allowed(mapped, ent.family):
            mapped = "overview"
        items.append(SemanticItem(entity=ent.entity, topic=mapped))
    return tuple(items)


def campus_items_from_text(raw_text: str) -> tuple[SemanticItem, ...]:
    entities = detect_campus_entity_spans(raw_text)
    if not entities:
        return ()
    topics = detect_campus_topic_spans(raw_text)
    return pair_campus_items(entity_spans=entities, topic_spans=topics)


_BARE_HOSTEL_CUES: tuple[str, ...] = (
    "hostel",
    "hostal",
    "ಹಾಸ್ಟೆಲ್",
    "ವಸತಿ ನಿಲಯ",
)


def is_bare_hostel_request(raw_text: str) -> bool:
    """True when the user mentioned a hostel but not girls vs boys."""
    if detect_campus_entity_spans(raw_text):
        return False
    hay = casefold_keep_scripts(raw_text or "")
    if not hay:
        return False
    return any(casefold_keep_scripts(cue) in hay for cue in _BARE_HOSTEL_CUES if cue)
