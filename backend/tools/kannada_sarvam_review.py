"""Offline Kannada review helper backed by the Sarvam Translation API.

Content-preparation tooling only. Nothing here is imported by the runtime
application: the approved Kannada is stored in `backend/data/locales/*.json`
and served without any translation call.

Usage:
    python -m backend.tools.kannada_sarvam_review --list
    python -m backend.tools.kannada_sarvam_review --batch pilot
    python -m backend.tools.kannada_sarvam_review --batch ui --limit 20
    python -m backend.tools.kannada_sarvam_review --batch all --report

The API key is read only from the environment (`SARVAM_API_KEY`). It is never
printed, logged, cached or written to any artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Iterable

import httpx

BASE_DIR = Path(__file__).resolve().parents[2]
LOCALES = BASE_DIR / "backend" / "data" / "locales"
CACHE_DIR = Path(__file__).resolve().parent / ".cache"
CACHE_FILE = CACHE_DIR / "kannada_sarvam_review_cache.json"
OUT_DIR = Path(__file__).resolve().parent / ".cache"
ROWS_FILE = OUT_DIR / "kannada_sarvam_review_rows.json"

SARVAM_TRANSLATE_URL = "https://api.sarvam.ai/translate"
TRANSLATE_MODEL = "sarvam-translate:v1"
EN = "en-IN"
KN = "kn-IN"
MAX_INPUT_CHARS = 1900

# Tokens that must survive translation byte-for-byte.
PROTECTED_TOKENS = (
    "CLARA", "SVIT", "VTU", "CSE", "AIML", "ISE", "ECE", "MBA", "KCET",
    "COMEDK", "KEA", "NBA", "NAAC", "AICTE", "CET", "TC", "PUC", "HOD",
    "Chrome", "Edge", "AI", "ML", "IoT", "Aadhaar",
)


# --------------------------------------------------------------------------
# credentials
# --------------------------------------------------------------------------
def read_api_key() -> str:
    """Return the Sarvam key from the environment, or exit with a clear stop."""
    key = os.environ.get("SARVAM_API_KEY", "").strip()
    if not key:
        # The repo defines its environment in the git-ignored .env, exactly as
        # backend/config/settings.py does. Still an environment read.
        try:
            from dotenv import load_dotenv

            load_dotenv(BASE_DIR / ".env")
        except Exception:
            pass
        key = os.environ.get("SARVAM_API_KEY", "").strip()
    if not key or key.startswith("your_"):
        sys.stderr.write(
            "STOP: SARVAM_API_KEY is not available in the environment.\n"
            "Set it in the environment (or the git-ignored .env) before running "
            "the Kannada review tool. No review can proceed without it.\n"
        )
        raise SystemExit(2)
    return key


# --------------------------------------------------------------------------
# cache (no credentials, never a runtime dependency)
# --------------------------------------------------------------------------
def load_cache() -> dict[str, Any]:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_cache(cache: dict[str, Any]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True),
        encoding="utf-8",
    )


def cache_key(text: str, src: str, tgt: str, mode: str) -> str:
    raw = f"{TRANSLATE_MODEL}|{src}|{tgt}|{mode}|{text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Sarvam translate
# --------------------------------------------------------------------------
class Translator:
    def __init__(self, key: str, *, delay: float = 0.6, dry_run: bool = False) -> None:
        self._key = key
        self._delay = delay
        self._dry_run = dry_run
        self._cache = load_cache()
        self._calls = 0
        self._hits = 0
        self._client = httpx.Client(timeout=45.0)

    @property
    def stats(self) -> dict[str, int]:
        return {"api_calls": self._calls, "cache_hits": self._hits}

    def close(self) -> None:
        save_cache(self._cache)
        self._client.close()

    def translate(self, text: str, src: str, tgt: str, mode: str = "formal") -> str:
        """Translate one segment, splitting on newlines to keep display layout."""
        parts = text.split("\n")
        out = [self._one(p, src, tgt, mode) if p.strip() else p for p in parts]
        return "\n".join(out)

    def _one(self, text: str, src: str, tgt: str, mode: str) -> str:
        if len(text) > MAX_INPUT_CHARS:
            raise ValueError(f"segment too long for one call: {len(text)} chars")
        ck = cache_key(text, src, tgt, mode)
        if ck in self._cache:
            self._hits += 1
            return self._cache[ck]
        if self._dry_run:
            return ""
        payload = {
            "input": text,
            "source_language_code": src,
            "target_language_code": tgt,
            "model": TRANSLATE_MODEL,
            "mode": mode,
        }
        headers = {
            "api-subscription-key": self._key,
            "Content-Type": "application/json",
        }
        last_err: Exception | None = None
        for attempt in range(4):
            try:
                resp = self._client.post(
                    SARVAM_TRANSLATE_URL, json=payload, headers=headers
                )
                if resp.status_code == 429:
                    time.sleep(2.0 * (attempt + 1))
                    continue
                resp.raise_for_status()
                body = resp.json()
                got = (body.get("translated_text") or "").strip()
                if not got:
                    raise ValueError("empty translated_text in response")
                self._cache[ck] = got
                self._calls += 1
                if self._calls % 15 == 0:
                    save_cache(self._cache)
                time.sleep(self._delay)
                return got
            except Exception as exc:  # noqa: BLE001 - reported, never swallowed
                last_err = exc
                time.sleep(1.2 * (attempt + 1))
        raise RuntimeError(f"Sarvam translate failed after retries: {last_err}")


# --------------------------------------------------------------------------
# inventory
# --------------------------------------------------------------------------
def _walk(node: Any, prefix: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(node, str):
        yield prefix, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from _walk(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, f"{prefix}[{i}]")


SURFACE_MAP = {
    "welcome": "wake / language gate / first turn",
    "language": "language gate overlay",
    "status": "orb + status line",
    "clarification": "assistant clarify turn",
    "error": "speech / network / service failure turn",
    "availability": "blocked-fact and unknown-answer turn",
    "session": "session chrome and controls",
    "cards": "card labels",
    "documents": "admissions documents card",
    "comparison": "department comparison surface",
    "action": "deterministic card narration",
}

DISPLAY_ONLY = {"cards", "documents", "comparison", "session"}
NARRATION_ONLY = {"action"}


def ui_rows() -> list[dict[str, Any]]:
    data = json.loads((LOCALES / "ui.json").read_text(encoding="utf-8"))
    en_map = dict(_walk(data["en"]))
    kn_map = dict(_walk(data["kn"]))
    rows: list[dict[str, Any]] = []
    for path, en_text in en_map.items():
        family = path.split(".")[0]
        kind = "display"
        if family in NARRATION_ONLY:
            kind = "narration"
        elif family not in DISPLAY_ONLY:
            kind = "display+narration"
        rows.append(
            {
                "id": f"ui.{path}",
                "file": "backend/data/locales/ui.json",
                "json_path": path,
                "surface": SURFACE_MAP.get(family, family),
                "kind": kind,
                "english": en_text,
                "existing_kn": kn_map.get(path, ""),
            }
        )
    return rows


CARD_PREFIXES = (
    "departments.cse.",
    "departments.cse_aiml.",
    "departments.cse_ds.",
    "departments.cyber_security.",
    "departments.business_systems.",
    "departments.ise.",
    "departments.ece.",
    "departments.mechanical.",
    "departments.civil.",
    "departments.mba.",
    "departments.basic_sciences.",
    "admissions_and_fees.",
    "placements_and_training.",
    "institution_overview.",
    "leadership.",
)

# Values that are structured data or protected identity, not reviewable prose.
SKIP_LEAF = re.compile(r"\.(name|hod_name|department_name|hod_bio_source)$")


def _is_reviewable(path: str, en_text: str, kn_text: str) -> tuple[bool, str]:
    if not kn_text:
        return False, "missing Kannada source"
    if "SAMPLE_REPLACE_WITH_OFFICIAL" in en_text or "SAMPLE_REPLACE_WITH_OFFICIAL" in kn_text:
        return False, "blocked: official fact placeholder"
    if en_text.strip().startswith("{") and "':" in en_text:
        return False, "blocked: raw python-dict string"
    if SKIP_LEAF.search(path):
        return False, "do not translate: protected identity"
    if len(en_text) < 3:
        return False, "too short to review"
    if len(en_text) > MAX_INPUT_CHARS:
        return False, "too long for a single call"
    return True, ""


def card_rows() -> list[dict[str, Any]]:
    en = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
    kn = json.loads((LOCALES / "kn.json").read_text(encoding="utf-8"))
    en_map = dict(_walk(en))
    kn_map = dict(_walk(kn))
    rows: list[dict[str, Any]] = []
    for path, en_text in en_map.items():
        if not path.startswith(CARD_PREFIXES):
            continue
        kn_text = kn_map.get(path, "")
        ok, why = _is_reviewable(path, en_text, kn_text)
        kind = "narration" if "tts" in path or "voice" in path else "display+narration"
        rows.append(
            {
                "id": f"kn.{path}",
                "file": "backend/data/locales/kn.json",
                "json_path": path,
                "surface": "card body / unit narration",
                "kind": kind,
                "english": en_text,
                "existing_kn": kn_text,
                "reviewable": ok,
                "not_reviewable_reason": why,
            }
        )
    return rows


PILOT_IDS = [
    "ui.welcome.named_display",
    "ui.welcome.general_display",
    "ui.language.select",
    "ui.status.listening",
    "ui.status.processing",
    "ui.clarification.department",
    "ui.error.backend",
    "ui.error.retry",
    "ui.session.timeout",
    "ui.session.thank_you",
    "kn.departments.cse.intro",
    "kn.departments.cse.hod_voice",
    "kn.departments.cse.fees",
    "kn.departments.cse.placement",
    "kn.admissions_and_fees.eligibility",
]


def build_inventory() -> list[dict[str, Any]]:
    rows = ui_rows()
    for r in rows:
        r.setdefault("reviewable", True)
        r.setdefault("not_reviewable_reason", "")
    rows.extend(card_rows())
    return rows


def select_batch(rows: list[dict[str, Any]], batch: str) -> list[dict[str, Any]]:
    by_id = {r["id"]: r for r in rows}
    if batch == "pilot":
        picked = []
        for pid in PILOT_IDS:
            if pid in by_id:
                picked.append(by_id[pid])
            else:
                sys.stderr.write(f"WARNING: pilot id not found in inventory: {pid}\n")
        return picked
    if batch == "ui":
        return [r for r in rows if r["id"].startswith("ui.")]
    if batch == "cards":
        return [r for r in rows if r["id"].startswith("kn.") and r["reviewable"]]
    if batch == "all":
        return [r for r in rows if r["reviewable"]]
    raise SystemExit(f"unknown batch: {batch}")


# --------------------------------------------------------------------------
# preservation checks
# --------------------------------------------------------------------------
NUM_RE = re.compile(r"\d[\d,._/–-]*\d|\d")
PLACEHOLDER_RE = re.compile(r"\{[a-z_]+\}")


def _numbers(text: str) -> list[str]:
    return sorted(n.strip(".,") for n in NUM_RE.findall(text))


def _acronyms(text: str) -> list[str]:
    # Word-boundary match: a bare "in" of "TC" also hits "TCS"/"Category".
    return sorted(
        {
            t
            for t in PROTECTED_TOKENS
            if re.search(rf"(?<![A-Za-z]){re.escape(t)}(?![A-Za-z])", text)
        }
    )


def _placeholders(text: str) -> list[str]:
    return sorted(PLACEHOLDER_RE.findall(text))


# Latin runs of 2+ chars. In an existing Kannada value these are exactly the
# tokens a human decided must stay in Latin script (TCS, Infosys, Dr, VTU).
LATIN_RUN_RE = re.compile(r"[A-Za-z][A-Za-z&.']*[A-Za-z]")


def _latin_tokens(text: str) -> list[str]:
    # Placeholder bodies are not names; placeholder drift is checked separately.
    text = PLACEHOLDER_RE.sub(" ", text)
    return sorted({m.group(0).strip(".") for m in LATIN_RUN_RE.finditer(text)})


# Terms a back-translation must not invent: they narrow the audience or add a
# fact. Sarvam silently rewrote "Students" as "Female students" on cse.placement.
NARROWING_TERMS = (
    "female",
    "male",
    "girls",
    "boys",
    "women",
    "men",
    "only",
    "must not",
    "cannot",
)


def _narrowing_drift(english: str, back: str) -> list[str]:
    el, bl = english.lower(), back.lower()

    def present(term: str, text: str) -> bool:
        return re.search(rf"(?<![a-z]){re.escape(term)}(?![a-z])", text) is not None

    return [t for t in NARROWING_TERMS if present(t, bl) and not present(t, el)]


def _norm_words(text: str) -> set[str]:
    text = unicodedata.normalize("NFKC", text.lower())
    return {w for w in re.split(r"[^a-z0-9]+", text) if len(w) > 3}


def check_row(row: dict[str, Any]) -> dict[str, Any]:
    """Compare candidate + back-translation against the English source."""
    en = row["english"]
    cand = row.get("sarvam_kn", "")
    back = row.get("back_en", "")
    issues: list[str] = []

    en_ph, cand_ph = _placeholders(en), _placeholders(cand)
    if en_ph != cand_ph:
        issues.append(f"placeholder drift {en_ph} -> {cand_ph}")

    en_num, cand_num = _numbers(en), _numbers(cand)
    if en_num != cand_num:
        issues.append(f"number drift {en_num} -> {cand_num}")

    en_ac, cand_ac = _acronyms(en), _acronyms(cand)
    missing_ac = [a for a in en_ac if a not in cand_ac]
    if missing_ac:
        issues.append(f"acronym lost {missing_ac}")

    # Names the existing Kannada deliberately keeps in Latin must survive.
    keep_latin = _latin_tokens(row.get("existing_kn", ""))
    if keep_latin and cand:
        cand_latin = {t.lower() for t in _latin_tokens(cand)}
        dropped = [
            t
            for t in keep_latin
            if t.lower() not in cand_latin and t not in missing_ac
        ]
        if dropped:
            issues.append(f"latin name transliterated {dropped}")

    en_lines = len([p for p in en.split("\n") if p.strip()])
    cand_lines = len([p for p in cand.split("\n") if p.strip()])
    if en_lines != cand_lines:
        issues.append(f"line-count drift {en_lines} -> {cand_lines}")

    if back:
        bw, ew = _norm_words(back), _norm_words(en)
        if ew:
            overlap = len(bw & ew) / len(ew)
            row["back_overlap"] = round(overlap, 2)
            if overlap < 0.45:
                issues.append(f"back-translation overlap low ({overlap:.2f})")
        back_num = _numbers(back)
        if en_num != back_num:
            issues.append(f"back-translation number drift {en_num} -> {back_num}")
        narrowing = _narrowing_drift(en, back)
        if narrowing:
            issues.append(f"back-translation adds narrowing term {narrowing}")

    if "|" in cand:
        issues.append("pipe character is TTS-unsafe")
    if re.search(r"[ಀ-೿]", en):
        issues.append("english source already contains Kannada")

    row["preserved"] = not any(
        i.startswith(
            (
                "placeholder",
                "number",
                "acronym",
                "latin name",
                "back-translation number",
                "back-translation adds",
            )
        )
        for i in issues
    )
    row["issues"] = issues
    row["identical_to_existing"] = cand.strip() == row["existing_kn"].strip()
    return row


# --------------------------------------------------------------------------
# structured decision evidence
# --------------------------------------------------------------------------
# Allowed classification values for a review decision.
ALLOWED_CLASSIFICATIONS = (
    "KEEP_EXISTING_MECHANICALLY_SUPPORTED",
    "SAFE_CORRECTION_CANDIDATE",
    "BLOCKED_LINGUISTIC",
    "BLOCKED_OFFICIAL_FACT",
    "BLOCKED_MISSING_SOURCE",
    "BLOCKED_RUNTIME_STRUCTURE",
    "NATIVE_REVIEW_RECOMMENDED",
)

# Marker for prior entries that predate the structured schema.
LEGACY_UNSTRUCTURED = "LEGACY_UNSTRUCTURED"

# Regex for currency tokens (₹, Rs, INR, $).
_CURRENCY_RE = re.compile(r"(₹|\bRs\.?\b|\bINR\b|\bUSD\b|\$)")

# Capitalized-name heuristic: 1-4 capitalised words that look like a person's
# name in English source text. Not exhaustive; supplements the protected
# tokens list.
_NAME_RUN_RE = re.compile(
    r"\b(?:Dr|Mr|Mrs|Ms|Prof|Smt|Shri)\.?\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3}"
)


def _check_field_pass(detail: str = "") -> dict[str, str]:
    return {"status": "PASS", "detail": detail}


def _check_field_fail(detail: str) -> dict[str, str]:
    return {"status": "FAIL", "detail": detail}


def _check_field_na(reason: str) -> dict[str, str]:
    return {"status": "N/A", "detail": reason}


def _clause_diff(en: str, cand: str) -> tuple[list[str], list[str]]:
    """Approximate clause-level diff between English and candidate.

    Returns (missing, added) where each list contains normalized clause
    fragments. Heuristic; not a parser. Best-effort for short UI strings.
    """
    en_clauses = [c.strip() for c in re.split(r"[.;\n]", en) if c.strip()]
    cand_clauses = [c.strip() for c in re.split(r"[.;\n]", cand) if c.strip()]

    def norm(s: str) -> str:
        return re.sub(r"\s+", " ", s.lower())

    cand_set = {norm(c) for c in cand_clauses}
    en_set = {norm(e) for e in en_clauses}
    missing = [e for e, n in zip(en_clauses, en_set) if n not in cand_set]
    added = [c for c, n in zip(cand_clauses, cand_set) if n not in en_set]
    return missing, added


def build_structured_evidence(
    row: dict[str, Any],
    classification: str,
    reason: str,
    *,
    back_en_of_candidate: str | None = None,
    back_en_of_existing: str | None = None,
) -> dict[str, Any]:
    """Produce a decision entry with structured per-row evidence.

    The returned dict has the four top-level fields requested by the
    spec (existing_back_translation, candidate_back_translation,
    classification, reason) plus 14 explicit check fields. Booleans are
    not used directly; each check field is a dict with `status` in
    {PASS, FAIL, N/A} and a short `detail` string, or a list of
    strings for clause-level facts.

    Required row keys: `english`, `existing_kn`, `sarvam_kn`.
    """
    if classification not in ALLOWED_CLASSIFICATIONS:
        raise ValueError(
            f"invalid classification {classification!r}; "
            f"allowed: {ALLOWED_CLASSIFICATIONS}"
        )
    en: str = row.get("english", "")
    existing: str = row.get("existing_kn", "")
    cand: str = row.get("sarvam_kn", "") or ""

    # placeholder_check: set of placeholders in EN vs candidate.
    en_ph = set(_placeholders(en))
    cand_ph = set(_placeholders(cand))
    if not en_ph and not cand_ph:
        placeholder_check = _check_field_na("no placeholders in source")
    elif en_ph == cand_ph:
        placeholder_check = _check_field_pass(
            f"placeholders preserved: {sorted(en_ph)}"
        )
    else:
        placeholder_check = _check_field_fail(
            f"placeholders en={sorted(en_ph)} cand={sorted(cand_ph)}"
        )

    # name_check: detected name runs in EN vs candidate.
    en_names = sorted(set(_NAME_RUN_RE.findall(en)))
    if not en_names:
        name_check = _check_field_na("no detected name runs in source")
    else:
        # Check that each detected name's content words appear in the candidate
        # (Kannada transliteration or partial Latin retention).
        cand_lower = cand.lower()
        lost: list[str] = []
        for nm in en_names:
            # Compare by tail word(s); honorifics are removed in Kannada.
            tail = nm.split()[-1].lower()
            if tail and tail not in cand_lower:
                lost.append(nm)
        if not lost:
            name_check = _check_field_pass(f"names preserved: {en_names}")
        else:
            name_check = _check_field_fail(f"names lost: {lost}")

    # number_check: numeric tokens in EN vs candidate.
    en_num = _numbers(en)
    cand_num = _numbers(cand) if cand else []
    if not en_num:
        number_check = _check_field_na("no numbers in source")
    elif en_num == cand_num:
        number_check = _check_field_pass(f"numbers preserved: {en_num}")
    else:
        number_check = _check_field_fail(
            f"numbers en={en_num} cand={cand_num}"
        )

    # currency_check: explicit currency symbols in EN vs candidate.
    en_cur = sorted(set(_CURRENCY_RE.findall(en)))
    cand_cur = sorted(set(_CURRENCY_RE.findall(cand)))
    if not en_cur:
        currency_check = _check_field_na("no currency in source")
    elif en_cur == cand_cur:
        currency_check = _check_field_pass(f"currency preserved: {en_cur}")
    else:
        currency_check = _check_field_fail(
            f"currency en={en_cur} cand={cand_cur}"
        )

    # acronym_check: protected acronyms in EN vs candidate.
    en_ac = _acronyms(en)
    cand_ac = _acronyms(cand) if cand else []
    if not en_ac:
        acronym_check = _check_field_na("no protected acronyms in source")
    elif set(en_ac).issubset(set(cand_ac)):
        acronym_check = _check_field_pass(f"acronyms preserved: {en_ac}")
    else:
        missing_ac = [a for a in en_ac if a not in cand_ac]
        acronym_check = _check_field_fail(f"acronyms lost: {missing_ac}")

    # latin_name_check: Latin-script tokens deliberately kept in existing KN
    # that must survive in the candidate.
    keep_latin = _latin_tokens(existing)
    if not keep_latin or not cand:
        latin_name_check = _check_field_na("no Latin tokens to preserve")
    else:
        cand_latin = {t.lower() for t in _latin_tokens(cand)}
        dropped = [
            t for t in keep_latin
            if t.lower() not in cand_latin and t not in en_ac
        ]
        if not dropped:
            latin_name_check = _check_field_pass(
                f"Latin tokens preserved: {keep_latin}"
            )
        else:
            latin_name_check = _check_field_fail(
                f"Latin tokens transliterated: {dropped}"
            )

    # gender_narrowing: back-translation adds a narrowing term.
    narrowing_existing: list[str] = []
    if back_en_of_existing:
        narrowing_existing = _narrowing_drift(en, back_en_of_existing)
    narrowing_cand: list[str] = []
    if back_en_of_candidate:
        narrowing_cand = _narrowing_drift(en, back_en_of_candidate)
    if not narrowing_existing and not narrowing_cand:
        gender_narrowing = _check_field_na("no narrowing terms detected")
    elif narrowing_existing or narrowing_cand:
        gender_narrowing = _check_field_fail(
            f"narrowing terms existing={narrowing_existing} "
            f"candidate={narrowing_cand}"
        )
    else:
        gender_narrowing = _check_field_pass("no narrowing terms")

    # subject_object_drift: heuristic check based on first-person pronouns in EN.
    # If the EN uses "I/we/my" and the back-translation drops it, flag drift.
    first_person_en = bool(re.search(r"\b(I|we|my|our)\b", en))
    if not first_person_en or not back_en_of_existing or not back_en_of_candidate:
        subject_object_drift = _check_field_na(
            "no first-person pronouns in source or no back-translation available"
        )
    else:
        ex_fp = bool(
            re.search(r"\b(I|we|my|our)\b", back_en_of_existing, re.IGNORECASE)
        )
        ca_fp = bool(
            re.search(r"\b(I|we|my|our)\b", back_en_of_candidate, re.IGNORECASE)
        )
        if ex_fp == ca_fp:
            subject_object_drift = _check_field_pass(
                f"first-person consistent existing={ex_fp} candidate={ca_fp}"
            )
        else:
            subject_object_drift = _check_field_fail(
                f"first-person drift existing={ex_fp} candidate={ca_fp}"
            )

    # missing_clauses / added_clauses: clause-level diff between EN and candidate.
    if not cand:
        missing_clauses: list[str] = []
        added_clauses: list[str] = []
    else:
        missing_clauses, added_clauses = _clause_diff(en, cand)

    # terminology_conflicts: explicit protected-glossary conflicts. Currently
    # the only automated check is "ಇಲಾಖೆ" in a context that should use
    # ವಿಭಾಗ (academic department). Other conflicts are recorded manually
    # via `note`.
    terminology_conflicts: list[str] = []
    if "ಇಲಾಖೆ" in cand:
        terminology_conflicts.append(
            "ಇಲಾಖೆ in candidate (rejected glossary term for academic department)"
        )
    # Translate "Placements" should remain as the protected glossary term
    # rather than a generic synonym.
    if "placements" in en.lower() and "ಉದ್ಯೋಗಾವಕಾಶ" in cand:
        terminology_conflicts.append(
            "candidate translates 'placements' to a non-glossary synonym"
        )

    # punctuation_assessment: short structured note. No automated scoring
    # beyond flagging the literal pipe character which is TTS-unsafe.
    if "|" in cand:
        punctuation_assessment = _check_field_fail(
            "literal '|' in candidate (TTS-unsafe; deferred workstream)"
        )
    elif cand and cand.rstrip()[-1:] not in {".", "।", "?"}:
        punctuation_assessment = _check_field_pass("candidate ends without .?!।")
    else:
        punctuation_assessment = _check_field_pass("punctuation within tolerance")

    # display_assessment / narration_assessment: short structured notes.
    # No automated scoring; both default to PASS unless caller overrides via
    # `note`. Callers can amend the entry post-hoc.
    display_assessment = _check_field_pass("display suitability not flagged")
    narration_assessment = _check_field_pass("narration suitability not flagged")

    return {
        # 4 input/output fields
        "existing_back_translation": back_en_of_existing or "",
        "candidate_back_translation": back_en_of_candidate or "",
        "classification": classification,
        "reason": reason,
        # 14 check fields
        "placeholder_check": placeholder_check,
        "name_check": name_check,
        "number_check": number_check,
        "currency_check": currency_check,
        "acronym_check": acronym_check,
        "latin_name_check": latin_name_check,
        "gender_narrowing": gender_narrowing,
        "subject_object_drift": subject_object_drift,
        "missing_clauses": missing_clauses,
        "added_clauses": added_clauses,
        "terminology_conflicts": terminology_conflicts,
        "punctuation_assessment": punctuation_assessment,
        "display_assessment": display_assessment,
        "narration_assessment": narration_assessment,
    }


def backfill_legacy_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Mark absent structured fields on a pre-schema decision entry.

    Preserves existing fields; only adds markers for fields that are
    absent. Fields that ARE present in the legacy entry are left
    untouched. This is non-destructive: it does not infer PASS for
    absent checks.
    """
    schema_fields = (
        "placeholder_check",
        "name_check",
        "number_check",
        "currency_check",
        "acronym_check",
        "latin_name_check",
        "gender_narrowing",
        "subject_object_drift",
        "missing_clauses",
        "added_clauses",
        "terminology_conflicts",
        "punctuation_assessment",
        "display_assessment",
        "narration_assessment",
        "existing_back_translation",
        "candidate_back_translation",
        "classification",
        "reason",
    )
    out = dict(entry)
    for f in schema_fields:
        if f not in out:
            out[f] = LEGACY_UNSTRUCTURED
    return out


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------
def run_batch(batch: str, limit: int | None, delay: float) -> list[dict[str, Any]]:
    rows = select_batch(build_inventory(), batch)
    if limit:
        rows = rows[:limit]
    tr = Translator(read_api_key(), delay=delay)
    done: list[dict[str, Any]] = []
    try:
        for i, row in enumerate(rows, 1):
            try:
                row["sarvam_kn"] = tr.translate(row["english"], EN, KN, "formal")
                row["back_en"] = tr.translate(row["sarvam_kn"], KN, EN, "formal")
                check_row(row)
            except Exception as exc:  # noqa: BLE001
                row["error"] = str(exc)
                row["issues"] = [f"api error: {exc}"]
                row["preserved"] = False
            done.append(row)
            sys.stderr.write(f"[{i}/{len(rows)}] {row['id']}\n")
    finally:
        tr.close()
        sys.stderr.write(f"stats: {tr.stats}\n")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    existing: dict[str, Any] = {}
    if ROWS_FILE.exists():
        try:
            existing = {r["id"]: r for r in json.loads(ROWS_FILE.read_text(encoding="utf-8"))}
        except Exception:
            existing = {}
    for r in done:
        existing[r["id"]] = r
    ROWS_FILE.write_text(
        json.dumps(list(existing.values()), ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    return done


def verify_approved(delay: float) -> list[dict[str, Any]]:
    """Back-translate every approved Kannada value and diff against English.

    This is the acceptance check on our own decisions, not on Sarvam's raw
    candidate: a revision we hand-authored must still round-trip to the source.
    """
    decisions_file = Path(__file__).resolve().parent / "kannada_review_decisions.json"
    decisions = json.loads(decisions_file.read_text(encoding="utf-8"))["decisions"]
    inv = {r["id"]: r for r in build_inventory()}
    tr = Translator(read_api_key(), delay=delay)
    out: list[dict[str, Any]] = []
    try:
        for rid, dec in decisions.items():
            row = inv.get(rid)
            if row is None:
                sys.stderr.write(f"WARNING: unknown id in decisions: {rid}\n")
                continue
            approved = dec["approved"]
            try:
                back = tr.translate(approved, KN, EN, "formal")
            except Exception as exc:  # noqa: BLE001
                back = ""
                sys.stderr.write(f"{rid}: back-translation failed: {exc}\n")
            probe = {
                "id": rid,
                "english": row["english"],
                "existing_kn": row["existing_kn"],
                "sarvam_kn": approved,  # reuse the checker on the approved value
                "back_en": back,
                "decision": dec["decision"],
            }
            check_row(probe)
            probe["approved_kn"] = approved
            probe["changed"] = approved.strip() != row["existing_kn"].strip()
            out.append(probe)
            sys.stderr.write(f"verified {rid}\n")
    finally:
        tr.close()
        sys.stderr.write(f"stats: {tr.stats}\n")
    (OUT_DIR / "kannada_approved_verification.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--batch", choices=["pilot", "ui", "cards", "all"])
    ap.add_argument("--limit", type=int)
    ap.add_argument("--delay", type=float, default=0.6)
    ap.add_argument("--list", action="store_true", help="print inventory counts only")
    ap.add_argument(
        "--verify-approved",
        action="store_true",
        help="back-translate the approved Kannada in kannada_review_decisions.json",
    )
    args = ap.parse_args()

    if args.verify_approved:
        rows = verify_approved(args.delay)
        bad = [r for r in rows if r.get("issues")]
        print(f"\nverified {len(rows)} approved values; {len(bad)} with issues")
        for r in bad:
            print(f"  {r['id']}: {'; '.join(r['issues'])}")
        return

    if args.list or not args.batch:
        rows = build_inventory()
        ui = [r for r in rows if r["id"].startswith("ui.")]
        cards = [r for r in rows if r["id"].startswith("kn.")]
        blocked = [r for r in cards if not r["reviewable"]]
        print(f"ui.json rows            : {len(ui)}")
        print(f"locale card rows        : {len(cards)}")
        print(f"  reviewable            : {len(cards) - len(blocked)}")
        print(f"  not reviewable        : {len(blocked)}")
        reasons: dict[str, int] = {}
        for r in blocked:
            reasons[r["not_reviewable_reason"]] = reasons.get(r["not_reviewable_reason"], 0) + 1
        for k, v in sorted(reasons.items(), key=lambda kv: -kv[1]):
            print(f"    {k}: {v}")
        print(f"TOTAL reviewable        : {len(ui) + len(cards) - len(blocked)}")
        return

    done = run_batch(args.batch, args.limit, args.delay)
    flagged = [r for r in done if r.get("issues")]
    print(f"\nreviewed {len(done)} rows; {len(flagged)} flagged")
    for r in flagged:
        print(f"  {r['id']}: {'; '.join(r['issues'])}")


if __name__ == "__main__":
    main()
