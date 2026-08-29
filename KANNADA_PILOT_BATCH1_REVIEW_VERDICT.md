# Kannada Pilot Batch 1 — Independent Read-Only Review Verdict

**Date:** 2026-08-29
**Reviewer:** Claude (independent read-only)
**Scope:** The five applied Kannada corrections in pilot batch 1, and only those.
**Gate status:** **APPROVE all five** (the gate may lift for these five rows only).

This verdict does **not** authorize the three pending writes, Batch 2, or any of
the four deferred workstreams.

---

## 1. Gate

The gate is the question: *Are the five applied Kannada corrections safe and
meaning-preserving?* All five pass. The three pending values
(`ui.status.processing`, `ui.session.timeout`,
`kn.admissions_and_fees.eligibility`) remain blocked and are not adjudicated
here.

## 2. Evidence collected (read-only, no commits, no pushes)

1. `git diff --stat backend/data/locales/` → `kn.json` 8/8, `ui.json` 2/2.
   Five string changes total, exactly matching the five applied corrections.
2. `git diff backend/data/locales/kn.json backend/data/locales/ui.json`
   read end-to-end. No collateral edits to other CSE fields
   (`name`, `achievements` untouched) or to other `ui.error.*` siblings.
3. Runtime re-read via `ui_text("kn", "error.backend")` and
   `load_locale_data_for_lang_key("kn")["departments"]["cse"]` — all five
   runtime values are byte-identical to the `approved` field in
   `backend/tools/kannada_review_decisions.json`.
4. Runtime chain verified by direct read:
   - `ui_text` at `backend/services/ui_localization.py:30-50`.
   - Section→unit-suffix mapping at
     `backend/services/content/content_unit_registry.py:35-41`
     (`intro→overview`, `hod_voice→hod`, `fees→fees`, `placement→placements`).
   - Narration prepends at `backend/services/content/unit_narration.py:91`
     (`ಶುಲ್ಕ`) and `:105` (`ಉದ್ಯೋಗಾವಕಾಶಗಳು`); HOD name template at `:74`
     confirms the guest name is dropped on `.hod` units and the visitor's
     spoken output is the body verbatim.
5. `python -m pytest backend/tests/test_kannada_safe_pilot_batch1_exact_strings.py`
   → **8 passed in 0.25s** (5 exact-string + 3 protected-token).
6. `python -m pytest backend/tests/test_kannada_corrected_locale_integration.py`
   → **3 passed in 0.42s** (no regression in the existing corrected-locale
   integration test).
7. `python -m backend.tools.kannada_sarvam_review --list` →
   `100 ui.json rows + 124 card rows = 212 reviewable strings total`
   (matches the plan's coverage accounting).

## 3. Per-row verdict

### 3.1 `ui.error.backend` — **APPROVE**

| Field | Value |
|---|---|
| English source | `The service is temporarily unavailable. Please try again.` |
| Pre-pilot | `ಕ್ಷಮಿಸಿ, ಸೇವೆ ತಾತ್ಕಾಲಿಕವಾಗಿ ಲಭ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.` |
| Applied | `ಸೇವೆಯು ತಾತ್ಕಾಲಿಕವಾಗಿ ಲಭ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.` |
| Decision | `adopt_sarvam` |
| Classification | `SAFE_TO_APPLY` |

**Reasoning.** Removed `ಕ್ಷಮಿಸಿ,` ("Sorry,") — a fragment absent from the English
source and inconsistent with the other 15 `ui.error.*` strings, all of which
end the apologetic form and use `ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.` as their tail
(spot-checked: `empty_response`, `invalid_request`, `missing_text`). No
protected tokens, no names, no numbers, no acronyms. `ui_text(kn,
"error.backend")` returns the approved value byte-identically.

### 3.2 `kn.departments.cse.intro` — **APPROVE**

| Field | Value |
|---|---|
| English source | "…Computer Science & Engineering department…system architects…top-tier…" |
| Pre-pilot | `ಕಂಪ್ಯೂಟರ್ ವಿಜ್ಞಾನ` / `ಸಿಸ್ಟಮ್ ವಾಸ್ತುಶಿಲ್ಪಿಗಳನ್ನಾಗಿ` / `ಉನ್ನತ-ಶ್ರೇಣಿಯ` |
| Applied | `ಕಂಪ್ಯೂಟರ್ ಸೈನ್ಸ್` / `ಸಿಸ್ಟಮ್ ಆರ್ಕಿಟೆಕ್ಟ್‌ಗಳಾಗಿ` / `ಉನ್ನತ ದರ್ಜೆಯ` |
| Decision | `revised` (hybrid) |
| Classification | `SAFE_TO_APPLY` |

**Reasoning.** Three independent glossary fixes:
1. `ಕಂಪ್ಯೂಟರ್ ವಿಜ್ಞಾನ` → `ಕಂಪ್ಯೂಟರ್ ಸೈನ್ಸ್` (glossary compliance for "Computer
   Science").
2. `ಸಿಸ್ಟಮ್ ವಾಸ್ತುಶಿಲ್ಪಿಗಳನ್ನಾಗಿ` ("building architects") →
   `ಸಿಸ್ಟಮ್ ಆರ್ಕಿಟೆಕ್ಟ್‌ಗಳಾಗಿ` (software system architects, glossary term).
3. `ಉನ್ನತ-ಶ್ರೇಣಿಯ` (Latin-hyphenated, un-Kannada) → `ಉನ್ನತ ದರ್ಜೆಯ` (glossary
   for "top-tier").

Sarvam's `ಇಂಜಿನಿಯರಿಂಗ್` and raw `&` were correctly rejected in favour of
glossary `ಎಂಜಿನಿಯರಿಂಗ್` and the in-script `ಮತ್ತು`. No protected tokens
affected — no numbers, currency, official names, or acronyms. The "CSE"
abbreviation is not used in this string; the full department name is spelled
out. Runtime chain
`load_locale_data_for_lang_key("kn")["departments"]["cse"]["intro"]`
→ `resolve_unit("cse.overview", ...).body` is reachable per the registry
mapping at `content_unit_registry.py:35-41`.

### 3.3 `kn.departments.cse.hod_voice` — **APPROVE**

| Field | Value |
|---|---|
| English source | "Led by Dr. Shashikumar D R…industry-driven learning…hands-on problem solving…" |
| Pre-pilot | `…ಶಶಿಕುಮಾರ್ ಡಿ ಆರ್ ನೇತೃತ್ವದಲ್ಲಿ…ಸಮಸ್ಯೆ ಪರಿಹಾರ…` |
| Applied | `…ಶಶಿಕುಮಾರ್ ಡಿ ಆರ್ ಅವರ ನೇತೃತ್ವದಲ್ಲಿ…ಪ್ರಾಯೋಗಿಕ ಸಮಸ್ಯೆ ಪರಿಹಾರ…` |
| Decision | `revised` (hybrid) |
| Classification | `SAFE_TO_APPLY` |

**Reasoning.** Two independent fixes:
1. Added honorific `ಅವರ` after the HOD's named person — grammatically
   respectful in Kannada. The HOD name `ಡಾ. ಶಶಿಕುಮಾರ್ ಡಿ ಆರ್` is byte-identical
   to the pre-pilot form; the honorific is a respect marker, not a name
   change. Per the user's clarification 3, a consistency policy across all
   HOD names is a separate deferred workstream and is **not** part of this
   review. Per clarification 6, the `ಡಿ ಆರ್` is fully Kannada transliteration
   of `D R`; the applied change did not touch the name.
2. Restored the dropped "hands-on" qualifier: `ಪ್ರಾಯೋಗಿಕ` added before
   `ಸಮಸ್ಯೆ ಪರಿಹಾರ`.

Sarvam's `ಕೈಗಾರಿಕಾ-ಚಾಲಿತ` ("industrial-driven") was correctly rejected in
favour of the glossary `ಉದ್ಯಮಾಧಾರಿತ`. Protected-token test
`test_cse_hod_voice_preserves_hod_name_token` asserts the HOD name is intact
and `ಅವರ` is present — both confirmed. Runtime chain
`load_locale_data_for_lang_key("kn")["departments"]["cse"]["hod_voice"]`
→ `resolve_unit("cse.hod", ...).body` is reachable; the visitor's spoken
output is the body verbatim per `unit_narration.py:74`.

### 3.4 `kn.departments.cse.fees` — **APPROVE**

| Field | Value |
|---|---|
| English source | `KCET: As per KEA norms \| Management: ₹3,50,000/year` |
| Pre-pilot | `KCET: KEA ಮಾನದಂಡಗಳ ಪ್ರಕಾರ \| ನಿರ್ವಹಣೆ: ₹3,50,000/ವರ್ಷ` |
| Applied | `KCET: KEA ಮಾನದಂಡಗಳ ಪ್ರಕಾರ \| ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್: ₹3,50,000/ವರ್ಷ` |
| Decision | `revised_terminology_only` |
| Classification | `SAFE_TO_APPLY` |

**Reasoning.** Terminology-only change: `ನಿರ್ವಹಣೆ` ("maintenance") →
`ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್` (glossary term for "management quota"). The Kannada
visitor was reading a maintenance charge for the management quota.

Sarvam's candidate was correctly rejected wholesale: it transliterated the
protected acronyms (KCET → `ಕೆಸಿಇಟಿ`, KEA → `ಕೆಇಎ`) and the round-trip
returned `KSET` (a different exam), and it rewrote `₹` as `Rs.`.

**Fee-amount question (per user clarification 5):** The fee amount
`₹3,50,000` was not changed by this correction. The cross-department
`₹3,50,000 vs ₹3,25,000` figure is from a different source and is not
adjudicated here — per the user, an official-fact conflict only exists if
two sources disagree for the **same department**. The terminology change is
independent of the amount question.

**`|` separator (per user clarification 4):** The literal `|` reaching TTS
is a pre-existing global sanitizer defect. It is recorded and remains
scheduled for the separate multilingual TTS workstream. It does not
invalidate the terminology correction, which is verified independently.

Protected-token test `test_cse_fees_preserves_kcet_kea_currency_and_number`
asserts `KCET`, `KEA`, `₹3,50,000`, and `ವರ್ಷ` are all present — all
confirmed. Runtime chain reaches `resolve_unit("cse.fees", ...).body` with
narration prepending `{dept_label} ಶುಲ್ಕ.` per `unit_narration.py:91`.

### 3.5 `kn.departments.cse.placement` — **APPROVE**

| Field | Value |
|---|---|
| English source | "Top recruiters include TCS, Infosys, and Amazon. Students receive rigorous technical and aptitude training." |
| Pre-pilot | `…ಯೋಗ್ಯತೆಯ ತರಬೇತಿ…` |
| Applied | `…ಆಪ್ಟಿಟಿಟ್ಯೂಡ್ ತರಬೇತಿ…` |
| Decision | `revised_terminology_only` |
| Classification | `SAFE_TO_APPLY` |

**Reasoning.** Terminology-only change: `ಯೋಗ್ಯತೆಯ ತರಬೇತಿ` ("eligibility
training") → `ಆಪ್ಟಿಟ್ಯೂಡ್ ತರಬೇತಿ` (glossary term for "aptitude training").
The English source clearly says "aptitude", not "eligibility".

**Highest-signal evidence of an honest review:** Sarvam's candidate was
correctly rejected wholesale because it narrowed `ವಿದ್ಯಾರ್ಥಿಗಳು` (gender-neutral
"students") to `ವಿದ್ಯಾರ್ಥಿನಿಯರು` (**female students**), confirmed by the
back-translation. The reviewer caught the gender narrowing and kept the
neutral term. Sarvam also transliterated `TCS`/`Infosys`/`Amazon`, which
would have corrupted the protected company names. The protected-token test
`test_cse_placement_preserves_latin_company_names` explicitly asserts
`ವಿದ್ಯಾರ್ಥಿಗಳು in placement` and `ವಿದ್ಯಾರ್ಥಿನಿಯರು not in placement` — both
confirmed by the applied value. Runtime chain reaches
`resolve_unit("cse.placements", ...).body` with narration prepending
`{dept_label} ಉದ್ಯೋಗಾವಕಾಶಗಳು.` per `unit_narration.py:105`.

## 4. Verdict summary

| Row | Decision | Classification | Verdict |
|---|---|---|---|
| `ui.error.backend` | adopt_sarvam | SAFE_TO_APPLY | **APPROVE** |
| `kn.departments.cse.intro` | revised (hybrid) | SAFE_TO_APPLY | **APPROVE** |
| `kn.departments.cse.hod_voice` | revised (hybrid) | SAFE_TO_APPLY | **APPROVE** |
| `kn.departments.cse.fees` | revised_terminology_only | SAFE_TO_APPLY | **APPROVE** |
| `kn.departments.cse.placement` | revised_terminology_only | SAFE_TO_APPLY | **APPROVE** |

**The pilot gate may lift for these five rows only.**

## 5. Coverage accounting (current state, post-pilot)

```
TOTAL KANNADA REVIEWABLE:            212  (100 ui.json + 124 card; 12 of the 124 are non-reviewable)
REVIEWED WITH SARVAM (pilot):         15  (the 15 in PILOT_IDS)
  - KEEP_EXISTING_VERIFIED:            0
  - SAFE_TO_APPLY:                     5  (the five applied corrections)
  - KEEP_EXISTING (sarvam-confirmed):  7
  - REVISED, PENDING WRITE:            3  (ui.status.processing, ui.session.timeout,
                                            kn.admissions_and_fees.eligibility)
HUMAN-SOURCE REVIEWED:                0
BLOCKED_LINGUISTIC:                   0
BLOCKED_OFFICIAL_FACT:                0  (per user clarification 5)
BLOCKED_MISSING_SOURCE:               0
BLOCKED_RUNTIME_STRUCTURE:            0
REQUIRES_HUMAN_REVIEW:                0
REMAINING UNREVIEWED:                197
```

## 6. What this review does NOT do

- Does not write the three pending approved values.
- Does not start Batch 2.
- Does not resolve any of the four deferred workstreams:
  - Honorific policy (`ಅವರ` after named HODs)
  - Literal `|` reaching TTS (multilingual TTS workstream)
  - Official fee verification (₹3,50,000 vs ₹3,25,000 cross-department)
  - Name-script policy (Kannada transliteration vs official Latin)
- Does not commit, push, or modify any runtime code or locale JSON.
- Does not claim CLARA's Kannada, TTS, or official facts are fully
  production-verified.
- Does not authorize Batch 2.

## 7. What a human reviewer should still do

Per the user's clarification 1 and the existing screenshots in
`frontend/test-results/` not covering any of the five applied changes, the
backend exact-string test is necessary but **not sufficient**. A real
Kannada kiosk session (or new browser pass) should confirm the displayed
and spoken text match the Applied column. The `|` reaching TTS is expected
and is not a regression introduced by this batch.

## 8. Next step after gate lift (out of scope here)

Lifting the gate for these five rows does not authorize the three pending
writes. The user has not yet authorized Batch 2.
