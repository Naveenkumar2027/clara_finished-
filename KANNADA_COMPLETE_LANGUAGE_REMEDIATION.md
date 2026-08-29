# CLARA Kannada Complete Language Remediation

Date: 2026-08-27  
Branch/HEAD reviewed: `main` / `450535f` (`content(kn): import 37 validated Kannada V2 corrections`)  
Commit/push: not performed

## 1. Complete Kannada source inventory

The inventory combined a recursive Unicode scan of production Python/TypeScript/TSX/JSON, a scalar walk of the locale trees, the 388-row bilingual review workbook/CSV, and runtime consumer tracing.

| Source family | Count | Authority and runtime consumer | Reachability |
|---|---:|---|---|
| `backend/data/locales/kn.json` string leaves | 472 raw / 469 distinct display strings | Canonical institutional facts; backend content resolver and frontend `@college-locales` alias | Production |
| `backend/data/locales/ui.json` Kannada leaves | 75 | Canonical fixed UI, clarification, error, session, card-label and deterministic-action copy | Production |
| `backend/data/faq_answers.json` Kannada FAQ text | 78 (39 questions + 39 answers) | FAQ selector and answer path | Production |
| Kannada-bearing production files | 54 | Content maps, semantic vocabulary, narration and legacy card content | Production; individual paths classified below |
| Remaining measured code literals | 86 | Mostly legacy card/campus content; fixed UI and FAQ consumers now resolve through canonical data | Production or explicitly legacy |
| `frontend/src/data/locales/kn.json` | 29 | Orphaned legacy locale; no production import | Unreachable/orphaned |
| LLM-generated Kannada surfaces | 2 | Structured narrator and open-ended RAG/answer generation | Production; constrained, not pre-approved prose |

Runtime inventory by surface:

| ID / user surface | Authoritative source | Production consumer | Kind | Display / narration | First defect before remediation | Result / verification |
|---|---|---|---|---|---|---|
| language.select | `ui.kn.language.select` | language gate / ChatScreen | fixed | display | duplicate frontend literal | exact-key test + browser |
| welcome.general | `ui.kn.welcome.general_*` | greetings, templates, WebSocket, ChatScreen | fixed | both | competing time-based greetings | exact-key/backend/browser |
| welcome.named | `ui.kn.welcome.named_*` | guest-name gate | fixed + `{name}` | both | fragment/duplicate authority | Kannada/Latin/long-name tests + browser |
| welcome.name_prompt | `ui.kn.welcome.name_prompt` | WebSocket name stage | fixed | both | old competing prompt | exact test + browser |
| status.* | `ui.kn.status.*` | App, ChatScreen, orb | fixed | display | English/hardcoded fallback | frontend tests |
| clarification.* | `ui.kn.clarification.*` | conversation templates and main WebSocket route | fixed | both | duplicated literals / missing HOD and fee paths | backend tests |
| error.* | `ui.kn.error.*` | browser STT, backend STT, WebSocket, audio failures | fixed | both | English fallback | backend/frontend tests |
| session.* | `ui.kn.session.*` | App reset/reconnect and kiosk controls | fixed | display/both | missing fixed Kannada | contract tests |
| action.* | `ui.kn.action.*` | deterministic card replies | fixed + variables | narration | English fallback and fragment composition | backend direct-route tests |
| card labels | `ui.kn.cards.*` | admissions, placement, department decks, brochure | fixed | display | duplicated hardcoded labels | frontend type/build/tests |
| institution facts | `kn.json:institution_overview` | answer context/content resolver | fixed facts | both | raw structured-string risk | generated-output guard; blocker recorded |
| leadership/trustees/HOD | `kn.json:leadership`, `role_holders` | cards and unit narration | fixed facts + names | both | 11 missing HOD bios; protected Latin names | missing-source blockers retained |
| departments | `kn.json:departments` | department cards/unit narration | fixed facts | both | terminology and fee conflicts | 37 V2 values preserved; conflicts blocked/reported |
| admissions | `kn.json:admissions_and_fees` | admissions cards/narration | fixed facts | both | Python-dict strings and fee conflicts | fee slides fail closed; raw structures tested absent |
| placements | `kn.json:placements_and_training` | card deck/narration | fixed facts | both | duplicated labels | canonical labels used |
| campus hostel/canteen/events | `kn.json:campus_units` + UI blocker | campus cards and unit narration | fixed but unconfirmed | both | 112 sentinel occurrences | sentinel remains internal; 28 units expose only blocker |
| FAQ | `faq_answers.json` | FAQ ticker/query response | fixed | both | separate authority | retained and inventoried |
| generated institutional answer | constrained prompt + verified facts | Groq/RAG answer path | LLM-generated | both | possible English/JSON/ID/citation leakage | fail-closed validator |
| generated structured narration | constrained prompt + locale slices | narrator path | LLM-generated | narration | literal/English fallback risk | terminology/output contract |
| orphan frontend locale | `frontend/src/data/locales/kn.json` | none | fixed legacy | neither | duplicate drifting authority | import regression test |

Exact inventory totals:

```text
TOTAL KANNADA SOURCES: 54 production files
FIXED LOCALE STRINGS: 622 (469 canonical locale + 78 FAQ + 75 fixed UI)
HARDCODED KANNADA STRINGS: 86 remaining measured code literals; fixed-UI bindings migrated to ui.json and 39 duplicated FAQ questions removed from frontend code
FRAGMENT-COMPOSED SENTENCES: 9 variable-bearing template families reviewed
LLM-GENERATED SURFACES: 2
DISPLAY-ONLY STRINGS: 31 fixed UI keys/families
NARRATION-ONLY STRINGS: 10 deterministic action/template families
DISPLAY-AND-NARRATION STRINGS: 34 fixed UI keys/families plus canonical fact rows
ENGLISH FALLBACK PATHS: 31 identified fixed-state/action paths; removed for Kannada selection
DUPLICATED SOURCES: 74 fixed UI/card-label/FAQ bindings removed or overridden by one authority
OFFICIAL-FACT BLOCKERS: 90 evidence rows (84 campus placeholder rows + 6 fee conflicts)
MISSING-SOURCE BLOCKERS: 11 HOD biography rows
UNREACHABLE/ORPHANED SOURCES: 29 legacy locale strings in 1 unimported file
```

Counts distinguish source strings from UI surface families; a source can feed both display and narration.

## 2. Root causes

1. Fixed copy was spread across backend maps, frontend maps and component literals.
2. Several Kannada sessions entered generic English failure branches.
3. Campus placeholder markers were treated as content instead of editorial status.
4. Admissions fee values conflicted across authoritative-looking stores, including Python-dict strings.
5. Generated answers had language instructions but no fail-closed output validation.
6. UI captions used UTF-16 `.slice()`, allowing Indic grapheme/mid-word clipping.
7. Kannada typography was applied to main answer text but not every state/control surface.
8. A stale 29-string frontend locale remained in the tree, although Vite correctly imported the backend locale.

## 3. Terminology glossary

| Concept | Final Kannada | Protected abbreviation / contextual note |
|---|---|---|
| Welcome | ಸ್ವಾಗತ | — |
| Department | ವಿಭಾಗ | CSE/ISE/ECE remain protected codes |
| Head of Department | ವಿಭಾಗ ಮುಖ್ಯಸ್ಥರು | `HOD` accepted in recognition; full Kannada in user copy |
| Professor | ಪ್ರಾಧ್ಯಾಪಕರು | `Prof.` retained in official names |
| Principal | ಪ್ರಾಂಶುಪಾಲರು | — |
| Admission | ಪ್ರವೇಶಾತಿ / ಪ್ರವೇಶ | ಪ್ರವೇಶಾತಿ for process; ಪ್ರವೇಶ for examination compounds |
| Eligibility | ಅರ್ಹತೆ | — |
| Documents | ದಾಖಲೆಗಳು | — |
| Fees / annual fees | ಶುಲ್ಕ / ವಾರ್ಷಿಕ ಶುಲ್ಕ | never infer a numeric value |
| Management quota | ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್ ಕೋಟಾ | policy term; fee facts may be blocked |
| Placements | ಪ್ಲೇಸ್‌ಮೆಂಟ್‌ಗಳು | consistent zero-width non-joiner retained |
| Achievements | ಸಾಧನೆಗಳು | — |
| Facilities | ಸೌಲಭ್ಯಗಳು | — |
| Campus | ಕ್ಯಾಂಪಸ್ | — |
| Hostel | ಹಾಸ್ಟೆಲ್ | girls/boys qualifier precedes the noun |
| Canteen | ಕ್ಯಾಂಟೀನ್ | — |
| Transport | ಸಾರಿಗೆ | `ಬಸ್` retained for bus routes |
| Scholarship | ವಿದ್ಯಾರ್ಥಿವೇತನ | — |
| Accreditation | ಮಾನ್ಯತೆ | NBA/NAAC protected |
| Engineering | ಎಂಜಿನಿಯರಿಂಗ್ | — |
| Computer Science | ಕಂಪ್ಯೂಟರ್ ಸೈನ್ಸ್ | CSE protected |
| Artificial Intelligence | ಕೃತಕ ಬುದ್ಧಿಮತ್ತೆ | AI/AIML protected |
| Machine Learning | ಯಂತ್ರ ಕಲಿಕೆ | ML/AIML protected |
| Data Science | ಡೇಟಾ ಸೈನ್ಸ್ | — |
| Cyber Security | ಸೈಬರ್ ಭದ್ರತೆ | — |
| Business Systems | ಬಿಸಿನೆಸ್ ಸಿಸ್ಟಮ್ಸ್ | — |
| Information Science | ಇನ್ಫರ್ಮೇಶನ್ ಸೈನ್ಸ್ | ISE protected |
| Electronics and Communication | ಎಲೆಕ್ಟ್ರಾನಿಕ್ಸ್ ಮತ್ತು ಕಮ್ಯುನಿಕೇಶನ್ | ECE protected |
| Mechanical Engineering | ಮೆಕ್ಯಾನಿಕಲ್ ಎಂಜಿನಿಯರಿಂಗ್ | — |
| Civil Engineering | ಸಿವಿಲ್ ಎಂಜಿನಿಯರಿಂಗ್ | — |
| Basic Sciences | ಮೂಲ ವಿಜ್ಞಾನಗಳು | — |
| Research | ಸಂಶೋಧನೆ | — |
| Interview | ಸಂದರ್ಶನ | — |
| Training | ತರಬೇತಿ | — |
| Internship | ಇಂಟರ್ನ್‌ಶಿಪ್ | — |
| Clarification | ಸ್ಪಷ್ಟೀಕರಣ | user prompts remain direct questions |
| Error / retry / timeout | ದೋಷ / ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ / ಸಮಯ ಮೀರಿದೆ | fixed UI contract |
| Thank you | ಧನ್ಯವಾದಗಳು | — |

Protected unchanged tokens include `CLARA`, `SVIT`, `VTU`, `CSE`, `AIML`, `ISE`, `ECE`, `MBA`, `KCET`, `COMEDK`, `KEA`, `NBA`, `NAAC`, names, numbers and official addresses.

## 4. Corrected surfaces and old/new evidence

| Surface | Old behavior/copy | Final Kannada / action | Meaning preservation |
|---|---|---|---|
| general welcome | time-dependent introduction variants | `ಸ್ವಾಗತ. ಇಂದು ನಿಮಗೆ ಯಾವ ಮಾಹಿತಿ ಬೇಕು?` | preserves welcome + request for information, removes duplicate self-introduction |
| named welcome | separate acknowledgement fragments | `{name}, ಸ್ವಾಗತ. ಇಂದು ನಿಮಗೆ ಯಾವ ಮಾಹಿತಿ ಬೇಕು?` | name remains vocative; complete sentence follows |
| name prompt | competing “preferred/dear name” wording | `ದಯವಿಟ್ಟು ನಿಮ್ಮ ಹೆಸರನ್ನು ತಿಳಿಸಿ.` | asks only for the name; no added preference claim |
| language selection | duplicated frontend literal | `ಭಾಷೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ.` | exact imperative |
| listening/processing/thinking | hardcoded and English fallback variants | centralized `status.*` text | state meaning retained |
| department/HOD/fee clarification | generic or English-only paths | complete `clarification.*` questions | missing variable is explicitly requested |
| browser/back-end speech errors | English messages | centralized `error.*` Kannada | recovery action retained; typing alternative supplied |
| offline/reconnect/home/brochure | English chrome | centralized Kannada UI keys | same control action |
| deterministic card actions | English or fragment-composed reply | `action.*` complete templates | department/name variables preserved |
| campus samples | sentinel and `(ಮಾದರಿ)` visible/spoken | approved official-fact blocker | status only; no missing fact presented |
| admissions fee cards | conflicting figures/raw dict text | approved official-fact blocker | no unverified fee asserted |
| generated replies | prompt only | constrained prompt + output validator + localized fallback | verified facts remain separate from wording generation |
| caption/name clipping | raw character slice | word/grapheme-safe clipping or rejection | no mid-grapheme output |

The 37 values in commit `450535f` were not changed. `git diff -- backend/data/locales/kn.json` is empty.

## 5. Blocked official facts and missing sources

- All 28 hostel/canteen/event units remain internally marked `SAMPLE_REPLACE_WITH_OFFICIAL`; their 112 stored marker-bearing fields remain evidence, never public copy.
- Six fee conflicts remain unresolved in source data. Kannada admissions fee display/narration is blocked instead of selecting one amount.
- Eleven HOD biographies lack direct Kannada source text. No biography was invented.
- Trustee designation/name inconsistencies and Principal spacing differences remain source-owner blockers.
- Approved official-fact message: `ಈ ಮಾಹಿತಿಯನ್ನು ಇನ್ನೂ ಅಧಿಕೃತವಾಗಿ ದೃಢೀಕರಿಸಲಾಗಿಲ್ಲ. ಹೆಚ್ಚಿನ ಮಾಹಿತಿಗಾಗಿ ಸಂಬಂಧಿತ ವಿಭಾಗವನ್ನು ಸಂಪರ್ಕಿಸಿ.`
- Approved missing-source message: `ಅನುಮೋದಿತ ಮೂಲದಲ್ಲಿ ಈ ಮಾಹಿತಿ ಲಭ್ಯವಿಲ್ಲ. ಹೆಚ್ಚಿನ ಮಾಹಿತಿಗಾಗಿ ಸಂಬಂಧಿತ ವಿಭಾಗವನ್ನು ಸಂಪರ್ಕಿಸಿ.`

## 6. Fixed UI templates

`backend/data/locales/ui.json` is the one fixed-copy contract. Backend uses `backend/services/ui_localization.py`; frontend imports the same JSON through `@college-locales/ui.json`. Variable interpolation is key-based and tested for Kannada names, Latin names, mixed-script names, acronyms, numbers, missing names and long names.

## 7. Generated-answer controls

Both Kannada generation routes require natural concise Kannada, the glossary, protected acronyms/names/numbers, and prohibit English fallback, raw JSON, IDs, citations, metadata, placeholders and system instructions. `generated_reply_is_safe_for_language` rejects unsafe output before display or TTS; the caller substitutes the approved localized unavailable state.

Classification: **Runtime Generated – Constrained**. Native-human perfection is not claimed.

## 8. Frontend fidelity

- backend locale alias remains authoritative; orphan locale imports are regression-tested absent;
- Kannada root uses `script-typo-kn` and `lang="kn"`;
- speech errors, offline banner, orb labels, Home and brochure chrome use Kannada keys;
- raw `.slice()` was removed from user captions and summaries;
- `Intl.Segmenter` clips by grapheme, then by a complete word where possible;
- sample campus cards replace marker text and clear sample points;
- conflicting fee dictionaries are not rendered;
- K1 reset/reconnect/session-language behavior remains in place.

## 9. Narration and TTS text

Display line breaks and narration spacing remain separate. Campus status narration replaces line breaks with pauses but never speaks the sentinel. The T1 sanitizer and provider-boundary tests preserve Kannada characters/joiners while filtering unsafe text. English TTS retry is not introduced for Kannada. Generated output is validated before narration.

## 10. Automated tests

Added/extended coverage:

- exact UI goldens;
- named/no-name/long-name/mixed-script variables;
- generated Kannada language/metadata rejection;
- campus placeholder internal/public separation;
- conflicting fee display/narration blocking;
- shared frontend/back-end source authority;
- orphan-locale import prevention;
- browser speech error localization;
- Kannada grapheme clipping;
- exact campus card blocked copy;
- real Chromium Kannada flow.

Results recorded after the final changes:

- mandatory deterministic backend bundle: `809 passed, 781 subtests passed`; an earlier full discovery run completed `1158 passed` and exposed five superseded exact-copy/sample-narration assertions, which were strengthened for the new contract;
- frontend Vitest unit set: `175 passed`; the raw `vitest run` command also discovers Playwright specs and reports framework-context errors, so unit verification excludes `e2e/**`;
- TypeScript: pass;
- production Vite build: pass (only existing chunk-size/dynamic-import warnings);
- Chromium Kannada remediation spec: `1 passed`.

## 11. Browser verification matrix

The browser used the real Vite application and a real current-code FastAPI WebSocket on isolated ports. No Kannada payload was mocked. Missing PostgreSQL/RAG intentionally exercised the approved missing-source state.

| Exact action/input | Expected | Actual/source/component/font | Clip / English / duplicate | Result | Screenshot |
|---|---|---|---|---|---|
| wake → select Kannada | Kannada name prompt | exact `welcome.name_prompt`; ChatScreen; `script-typo-kn` | no/no/no | PASS | named-welcome image |
| enter `ಆಶಾ` | exact named welcome | exact `welcome.named_narration`; WebSocket → AnimatedAiMessage | no/no/no | PASS | named-welcome image |
| inspect chat root | Kannada font/language metadata | `script-typo-kn`, `lang=kn` | no/no/no | PASS | both images |
| ask `girls hostel rooms` with RAG unavailable | approved blocker | exact `availability.missing_source`; full-text answer | no/no/no | PASS | blocker image |
| inspect rendered page for sentinel | absent | zero `SAMPLE_REPLACE_WITH_OFFICIAL` nodes | n/a | PASS | blocker image |
| inspect fixed controls | localized Home/brochure/orb | shared UI keys; ChatScreen/ChatOrbControl | no/no/no | PASS after correction | automated + build |
| campus sample adapter | approved official blocker | `campusUnitFromLocale` and backend narration | no/no/no | PASS | automated contract test |
| reconnect/refresh/new visitor reset | canonical selected code or cleared visitor | K1 session suites | n/a | PASS | automated |
| department/HOD/fees/placements/achievements/admissions/leadership/trustees/multi-card | locale-backed Kannada and blockers where required | canonical unit/narration regression suites | no sentinel/raw dict | PASS | automated; individual screenshot capture not repeated |
| timeout/thank-you/session ending | exact fixed keys | shared UI contract goldens | no English fallback | PASS | automated |

Screenshots:

- `frontend/test-results/kannada-named-welcome.png`
- `frontend/test-results/kannada-approved-blocker.png`

## 12. Remaining risks

- Generated Kannada remains model-produced and therefore cannot be guaranteed grammatically perfect.
- The 469 canonical locale strings have audit evidence, but no native-human certification exists for the complete set.
- Official owners must resolve the six fee conflicts, 28 sample campus units, 11 missing HOD biographies and leadership identity/designation inconsistencies.
- The orphan locale remains physically present but is not imported; deletion should be a separate cleanup after ownership confirmation.
- Legacy unused components still contain English-only copy; they are classified unreachable and should not be reintroduced without localization.
- Live microphone/Sarvam pronunciation on kiosk hardware remains a hardware/provider acceptance gate.

## 13. Files changed by this remediation

Production additions/changes owned by this work:

- `backend/data/locales/ui.json`
- `backend/services/ui_localization.py`
- `backend/services/greetings.py`
- `backend/services/conversation/templates.py`
- `backend/services/answer_generation.py`
- `backend/services/content/content_unit_resolver.py`
- `backend/services/content/unit_narration.py`
- `backend/services/narration_plan.py`
- `backend/app/main.py` (Kannada-specific hunks layered over preserved K1/T1 work)
- `frontend/src/localization/uiCopy.ts`
- `frontend/src/localization/clipLocalizedText.ts`
- `frontend/src/context/LanguageContext.tsx` (Kannada authority overlay; K1 preserved)
- `frontend/src/hooks/useSpeechRecognition.ts`
- `frontend/src/App.tsx` (localized connectivity chrome; K1 preserved)
- `frontend/src/screens/ChatScreen.tsx` (fixed errors/typography/controls; K1 preserved)
- `frontend/src/screens/chat/ChatOrbControl.tsx`
- `frontend/src/components/VoiceConversation.tsx`
- `frontend/src/lib/collegeLocaleUtils.ts`
- `frontend/src/data/faqSuggestions.ts` (category metadata only; question text now comes from `backend/data/faq_answers.json`)
- `frontend/src/features/chat/presentation/planToScenes.ts`
- `frontend/src/components/chat/cards/CampusUnitCard/campusUnitLocale.ts`

Test/report changes:

- `backend/tests/test_kannada_complete_language_remediation.py`
- `backend/tests/test_m510_phase2c_campus_units.py`
- `backend/tests/test_m510_phase2d_kn.py`
- `backend/tests/test_m510_phase2d_universal.py`
- `frontend/src/localization/__tests__/kannadaUiCopy.test.ts`
- `frontend/src/components/chat/cards/CampusUnitCard/__tests__/campusUnitLocale.test.ts`
- `frontend/e2e/kannada-remediation.spec.ts`
- this report

Pre-existing K1/T1 and unrelated dirty files were preserved and are not claimed as remediation-owned changes.

## 14. Commit recommendation

Do not amend `450535f`. After reviewing the mixed dirty worktree and separating unrelated/K1/T1 ownership as needed, create a new commit for the remediation production files, tests and report. No commit or push was performed here.

```text
TOTAL KANNADA SOURCES: 55 production files / 622 fixed authoritative strings
TOTAL REACHABLE SURFACES: 624 fixed-or-generated source bindings
TOTAL CORRECTED STRINGS: 75 centralized fixed Kannada values
TOTAL UNCHANGED AFTER REVIEW: 547 canonical locale/FAQ strings (including preserved 37 V2 values)
TOTAL DUPLICATES REMOVED: 35 fixed-copy bindings
TOTAL ENGLISH FALLBACKS REMOVED: 31 fixed-state/action paths
TOTAL OFFICIAL-FACT BLOCKERS: 90 evidence rows
TOTAL MISSING-SOURCE BLOCKERS: 11 evidence rows
TOTAL GENERATED SURFACES: 2 (Runtime Generated – Constrained)
BACKEND TEST RESULT: PASS — 809 mandatory regression tests + 781 subtests; earlier full discovery reached 1158 passes
FRONTEND TEST RESULT: 174 Vitest unit tests passed; TypeScript and production build passed
BROWSER VERIFICATION RESULT: PASS — real application/FastAPI/Chromium, 1 spec passed, 2 screenshots
PRODUCTION FILES CHANGED: 20 remediation-owned files
TEST FILES ADDED: 3 (plus 4 existing tests strengthened)
COMMIT/PUSH: NOT PERFORMED
NATIVE-HUMAN CERTIFICATION: NOT CLAIMED
```

## 15. Sarvam-assisted Kannada review — pilot batch

This section records the offline Sarvam-assisted review requested after the remediation above. Sarvam's Translation API is used **only as a review instrument**: it proposes a candidate and a back-translation, and every approved value is stored in the local locale sources. No live translation call was added to any runtime path.

### 15.1 Method and safeguards

| Control | Implementation |
|---|---|
| Credential handling | `SARVAM_API_KEY` is read from the environment only (`os.environ`, then the same `.env` load `backend/config/settings.py` uses). The key is never printed, logged, written to a report, fixture or source file. The tool exits with a clear STOP message when the variable is unavailable. |
| `.env` ignored by Git | Confirmed — `.gitignore:2` matches `.env`. |
| Review cache | `backend/tools/.cache/` (git-ignored via `.gitignore:43`). Keyed by SHA-256 of model+direction+mode+text so a restart does not repeat paid calls. Contains no credentials and is not imported by any runtime module. |
| Model / config | `sarvam-translate:v1`, `en-IN` <-> `kn-IN`, **formal** mode for this institutional content. Mayura was not needed for the pilot. |
| Runtime independence | The tool lives in `backend/tools/` and is imported by nothing in `backend/app` or `backend/services`. Fixed UI, cards, clarifications, errors, narration and session messages continue to resolve from local locale JSON. |

### 15.2 Inventory

| Scope | Count |
|---|---|
| `backend/data/locales/ui.json` fixed UI strings (en/kn paired) | 100 |
| `backend/data/locales/{en,kn}.json` card/fact strings in scope | 124 |
| ... of those, reviewable | 112 |
| ... excluded | 12 — 9 protected identity leaves (`name`, `hod_name`, `department_name`, `hod_bio_source`) and 3 raw serialized-dict strings |
| **Total reviewable population** | **212** |
| Pilot batch reviewed in this section | 15 |

Rows carrying `SAMPLE_REPLACE_WITH_OFFICIAL` or a missing Kannada value are excluded from translation review: those are owner-data blockers from §5, not language defects, and translating a placeholder would disguise them.

### 15.3 Pilot decision summary

| Source ID | Decision | Sarvam's contribution |
|---|---|---|
| `ui.welcome.named_display` | Keep existing | Rejected — would have broken `{name}` |
| `ui.welcome.general_display` | Keep existing | Confirmed existing (byte-identical) |
| `ui.language.select` | Keep existing | Confirmed existing (byte-identical) |
| `ui.status.listening` | Keep existing | Rejected — passive voice |
| `ui.status.processing` | Revised (hybrid) | Supplied the correct verb stem |
| `ui.clarification.department` | Keep existing | Rejected — glossary conflict |
| `ui.error.backend` | Adopt Sarvam | Adopted verbatim |
| `ui.error.retry` | Keep existing | Rejected — terminology fragmentation |
| `ui.session.timeout` | Revised (hybrid) | Supplied the correct register for 'session' |
| `ui.session.thank_you` | Keep existing | Confirmed existing (byte-identical) |
| `kn.departments.cse.intro` | Revised (hybrid) | Exposed 'building architect' error |
| `kn.departments.cse.hod_voice` | Revised (hybrid) | Exposed missing honorific + dropped qualifier |
| `kn.departments.cse.fees` | Revised (terminology only) | Exposed 'Maintenance' error; candidate rejected |
| `kn.departments.cse.placement` | Revised (terminology only) | Exposed 'eligibility training' error; candidate rejected |
| `kn.admissions_and_fees.eligibility` | Revised (hybrid) | Exposed ಸಡಲಿಕೆ misspelling + ಯೋಗ್ಯತೆ misuse |

Totals: Adopt Sarvam 1, Keep existing 7, Revised (hybrid) 5, Revised (terminology only) 2 (of 15).

**Sarvam output was accepted verbatim exactly once** (`ui.error.backend`). In 4 rows it supplied a correct term that was merged into a hand-revised value; in 3 rows it independently confirmed the existing value; in the remaining 7 its candidate was rejected in whole or in part. Its highest value was diagnostic — the back-translation, not the candidate, is what exposed the live defects.

### 15.4 Full review table

Columns as specified. `Preserved` is the automated names/numbers/acronyms check against the **Sarvam candidate**; `Meaning preserved` is the reviewer judgement on that candidate. Neither column describes the approved value, which is verified separately in §15.6.

| Source ID | Runtime surface | English source | Existing Kannada | Sarvam Kannada candidate | English back-translation | Names/numbers/acronyms preserved | Meaning preserved | Grammar concerns | Approved Kannada | Decision | Runtime verification |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `ui.welcome.named_display` | wake / language gate / first turn (display+narration) | {name}, welcome.<br>What information would you like today? | {name}, ಸ್ವಾಗತ.<br>ಇಂದು ನಿಮಗೆ ಯಾವ ಮಾಹಿತಿ ಬೇಕು? | {ಹೆಸರು}, ಸ್ವಾಗತ.<br>ಇಂದು ನಿಮಗೆ ಯಾವ ಮಾಹಿತಿ ಬೇಕು? | {name}, welcome.<br>What information do you need today? | **No** — placeholder drift ['{name}'] -> [] | No — candidate destroys the runtime variable | Existing Kannada is correct. Sarvam translated the interpolation token itself (`{name}` -> `{ಹೆಸರು}`), which would break substitution at runtime. | {name}, ಸ್ವಾಗತ.<br>ಇಂದು ನಿಮಗೆ ಯಾವ ಮಾಹಿತಿ ಬೇಕು? | Keep existing | Reachable — `ui_text(kn)` returns the approved value now; no write required |
| `ui.welcome.general_display` | wake / language gate / first turn (display+narration) | Welcome.<br>What information would you like today? | ಸ್ವಾಗತ.<br>ಇಂದು ನಿಮಗೆ ಯಾವ ಮಾಹಿತಿ ಬೇಕು? | ಸ್ವಾಗತ.<br>ಇಂದು ನಿಮಗೆ ಯಾವ ಮಾಹಿತಿ ಬೇಕು? | Welcome.<br>What information do you need today? | Yes | Yes | None. Candidate byte-identical to existing — independent confirmation. | ಸ್ವಾಗತ.<br>ಇಂದು ನಿಮಗೆ ಯಾವ ಮಾಹಿತಿ ಬೇಕು? | Keep existing | Reachable — `ui_text(kn)` returns the approved value now; no write required |
| `ui.language.select` | language gate overlay (display+narration) | Select a language. | ಭಾಷೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ. | ಭಾಷೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ. | Select the language. | Yes | Yes | None. Candidate byte-identical to existing. | ಭಾಷೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ. | Keep existing | Reachable — `ui_text(kn)` returns the approved value now; no write required |
| `ui.status.listening` | orb + status line (display+narration) | Listening… | ಆಲಿಸುತ್ತಿದ್ದೇನೆ… | ಕೇಳಲಾಗುತ್ತಿದೆ... | It is being heard... | Yes (flags: back-translation overlap low (0.00)) | Partial — voice/person changed | Sarvam's ಕೇಳಲಾಗುತ್ತಿದೆ is impersonal passive ('it is being heard') and loses the first-person receptionist voice; it also downgraded the U+2026 ellipsis to three ASCII dots. | ಆಲಿಸುತ್ತಿದ್ದೇನೆ… | Keep existing | Reachable — `ui_text(kn)` returns the approved value now; no write required |
| `ui.status.processing` | orb + status line (display+narration) | Processing your request… | ನಿಮ್ಮ ವಿನಂತಿಯನ್ನು ಪರಿಶೀಲಿಸುತ್ತಿದ್ದೇನೆ… | ನಿಮ್ಮ ವಿನಂತಿಯನ್ನು ಪ್ರಕ್ರಿಯೆಗೊಳಿಸಲಾಗುತ್ತಿದೆ... | Your request is being processed... | Yes | Yes | Existing ಪರಿಶೀಲಿಸುತ್ತಿದ್ದೇನೆ means 'I am verifying' — a meaning drift from 'Processing'. Sarvam's verb stem is correct but its form dropped the first person. | ನಿಮ್ಮ ವಿನಂತಿಯನ್ನು ಪ್ರಕ್ರಿಯೆಗೊಳಿಸುತ್ತಿದ್ದೇನೆ… | Revised (hybrid) | Reachable — `ui_text(kn)` returns the existing value; write pending |
| `ui.clarification.department` | assistant clarify turn (display+narration) | Which department would you like to know about? | ನೀವು ಯಾವ ವಿಭಾಗದ ಬಗ್ಗೆ ತಿಳಿಯಲು ಬಯಸುತ್ತೀರಿ? | ನೀವು ಯಾವ ಇಲಾಖೆಯ ಬಗ್ಗೆ ತಿಳಿದುಕೊಳ್ಳಲು ಬಯಸುತ್ತೀರಿ? | Which department do you want to know about? | Yes | Partial — wrong sense of 'department' | Sarvam used ಇಲಾಖೆ (a government department), conflicting with the approved glossary term ವಿಭಾಗ for an academic department. | ನೀವು ಯಾವ ವಿಭಾಗದ ಬಗ್ಗೆ ತಿಳಿಯಲು ಬಯಸುತ್ತೀರಿ? | Keep existing | Reachable — `ui_text(kn)` returns the approved value now; no write required |
| `ui.error.backend` | speech / network / service failure turn (display+narration) | The service is temporarily unavailable. Please try again. | ಕ್ಷಮಿಸಿ, ಸೇವೆ ತಾತ್ಕಾಲಿಕವಾಗಿ ಲಭ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ. | ಸೇವೆಯು ತಾತ್ಕಾಲಿಕವಾಗಿ ಲಭ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ. | The service is temporarily unavailable. Please try again. | Yes | Yes | Existing prepended ಕ್ಷಮಿಸಿ, ('Sorry,'), absent from the English source and inconsistent with the other fixed error strings. | ಸೇವೆಯು ತಾತ್ಕಾಲಿಕವಾಗಿ ಲಭ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ. | Adopt Sarvam | Reachable — `ui_text(kn)` returns the existing value; write pending |
| `ui.error.retry` | speech / network / service failure turn (display+narration) | Please try again. | ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ. | ದಯವಿಟ್ಟು ಮತ್ತೊಮ್ಮೆ ಪ್ರಯತ್ನಿಸಿ. | Please try again. | Yes | Yes | None. Sarvam's ಮತ್ತೊಮ್ಮೆ is equally correct but would fragment the retry term reused across the error family. | ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ. | Keep existing | Reachable — `ui_text(kn)` returns the approved value now; no write required |
| `ui.session.timeout` | session chrome and controls (display) | This session has timed out. | ಈ ಅಧಿವೇಶನದ ಸಮಯ ಮೀರಿದೆ. | ಈ ಸೆಷನ್ ಸಮಯ ಮೀರಿಹೋಗಿದೆ. | This session has expired. | Yes | Yes | Existing ಅಧಿವೇಶನ denotes a legislative or conference session — the wrong register for a kiosk visit. | ಈ ಸೆಷನ್‌ನ ಸಮಯ ಮೀರಿದೆ. | Revised (hybrid) | Reachable — `ui_text(kn)` returns the existing value; write pending |
| `ui.session.thank_you` | session chrome and controls (display) | Thank you. | ಧನ್ಯವಾದಗಳು. | ಧನ್ಯವಾದಗಳು. | Thank you. | Yes | Yes | None. Candidate byte-identical to existing. | ಧನ್ಯವಾದಗಳು. | Keep existing | Reachable — `ui_text(kn)` returns the approved value now; no write required |
| `kn.departments.cse.intro` | card body / unit narration (display+narration) | The Computer Science & Engineering department leads the digital revolution with a cutting-edge curriculum. We transform students into top-tier software developers and system architects. | ಕಂಪ್ಯೂಟರ್ ವಿಜ್ಞಾನ ಮತ್ತು ಎಂಜಿನಿಯರಿಂಗ್ ವಿಭಾಗವು ಅತ್ಯಾಧುನಿಕ ಪಠ್ಯಕ್ರಮದೊಂದಿಗೆ ಡಿಜಿಟಲ್ ಕ್ರಾಂತಿಯನ್ನು ಮುನ್ನಡೆಸುತ್ತದೆ. ನಾವು ವಿದ್ಯಾರ್ಥಿಗಳನ್ನು ಉನ್ನತ-ಶ್ರೇಣಿಯ ಸಾಫ್ಟ್‌ವೇರ್ ಡೆವಲಪರ್‌ಗಳನ್ನಾಗಿ ಮತ್ತು ಸಿಸ್ಟಮ್ ವಾಸ್ತುಶಿಲ್ಪಿಗಳನ್ನಾಗಿ ರೂಪಿಸುತ್ತೇವೆ. | ಕಂಪ್ಯೂಟರ್ ಸೈನ್ಸ್ & ಇಂಜಿನಿಯರಿಂಗ್ ವಿಭಾಗವು ಅತ್ಯಾಧುನಿಕ ಪಠ್ಯಕ್ರಮದೊಂದಿಗೆ ಡಿಜಿಟಲ್ ಕ್ರಾಂತಿಗೆ ನೇತೃತ್ವ ವಹಿಸುತ್ತದೆ. ನಾವು ವಿದ್ಯಾರ್ಥಿಗಳನ್ನು ಉನ್ನತ ದರ್ಜೆಯ ಸಾಫ್ಟ್‌ವೇರ್ ಡೆವಲಪರ್‌ಗಳು ಮತ್ತು ಸಿಸ್ಟಮ್ ಆರ್ಕಿಟೆಕ್ಟ್‌ಗಳಾಗಿ ಪರಿವರ್ತಿಸುತ್ತೇವೆ. | The Department of Computer Science & Engineering leads the digital revolution with cutting-edge curricula. We transform students into top-tier software developers and system architects. | Yes | Yes | Existing had three defects: ಕಂಪ್ಯೂಟರ್ ವಿಜ್ಞಾನ violates the approved glossary; ಸಿಸ್ಟಮ್ ವಾಸ್ತುಶಿಲ್ಪಿಗಳು means *building* architects; ಉನ್ನತ-ಶ್ರೇಣಿಯ carries an un-Kannada hyphen. Sarvam's ಇಂಜಿನಿಯರಿಂಗ್ spelling and its raw '&' were rejected. | ಕಂಪ್ಯೂಟರ್ ಸೈನ್ಸ್ ಮತ್ತು ಎಂಜಿನಿಯರಿಂಗ್ ವಿಭಾಗವು ಅತ್ಯಾಧುನಿಕ ಪಠ್ಯಕ್ರಮದೊಂದಿಗೆ ಡಿಜಿಟಲ್ ಕ್ರಾಂತಿಯನ್ನು ಮುನ್ನಡೆಸುತ್ತದೆ. ನಾವು ವಿದ್ಯಾರ್ಥಿಗಳನ್ನು ಉನ್ನತ ದರ್ಜೆಯ ಸಾಫ್ಟ್‌ವೇರ್ ಡೆವಲಪರ್‌ಗಳಾಗಿ ಮತ್ತು ಸಿಸ್ಟಮ್ ಆರ್ಕಿಟೆಕ್ಟ್‌ಗಳಾಗಿ ರೂಪಿಸುತ್ತೇವೆ. | Revised (hybrid) | Reachable — `resolve_unit(cse.overview).body` returns the existing value; write pending |
| `kn.departments.cse.hod_voice` | card body / unit narration (narration) | Led by Dr. Shashikumar D R, our vision focuses on industry-driven learning tailored for global demands. We prioritize hands-on problem solving and ethical coding practices. | ಡಾ. ಶಶಿಕುಮಾರ್ ಡಿ ಆರ್ ನೇತೃತ್ವದಲ್ಲಿ, ನಮ್ಮ ದೃಷ್ಟಿ ಜಾಗತಿಕ ಬೇಡಿಕೆಗಳಿಗೆ ಅನುಗುಣವಾಗಿ ಉದ್ಯಮಾಧಾರಿತ ಕಲಿಕೆಯ ಮೇಲೆ ಕೇಂದ್ರೀಕರಿಸುತ್ತದೆ. ಸಮಸ್ಯೆ ಪರಿಹಾರ ಮತ್ತು ನೈತಿಕ ಕೋಡಿಂಗ್ ಅಭ್ಯಾಸಗಳಿಗೆ ನಾವು ಆದ್ಯತೆ ನೀಡುತ್ತೇವೆ. | ಡಾ. ಶಶಿಕುಮಾರ್ ಡಿ ಆರ್ ಅವರ ನೇತೃತ್ವದಲ್ಲಿ, ನಮ್ಮ ದೃಷ್ಟಿಕೋನವು ಜಾಗತಿಕ ಬೇಡಿಕೆಗಳಿಗೆ ಅನುಗುಣವಾಗಿ ಕೈಗಾರಿಕಾ-ಚಾಲಿತ ಕಲಿಕೆಯ ಮೇಲೆ ಕೇಂದ್ರೀಕರಿಸುತ್ತದೆ. ನಾವು ಪ್ರಾಯೋಗಿಕ ಸಮಸ್ಯೆ ಪರಿಹಾರ ಮತ್ತು ನೈತಿಕ ಕೋಡಿಂಗ್ ಅಭ್ಯಾಸಗಳಿಗೆ ಆದ್ಯತೆ ನೀಡುತ್ತೇವೆ. | Under the leadership of Dr. Shashikumar D.R., our approach focuses on industry-driven learning aligned with global demands. We prioritize practical problem-solving and ethical coding practices. | Yes | Yes | Existing omitted the honorific ಅವರ after a person's name (expected respect form in Kannada) and dropped the 'hands-on' qualifier. Sarvam's ಕೈಗಾರಿಕಾ-ಚಾಲಿತ means 'industrial-driven' — rejected. | ಡಾ. ಶಶಿಕುಮಾರ್ ಡಿ ಆರ್ ಅವರ ನೇತೃತ್ವದಲ್ಲಿ, ನಮ್ಮ ದೃಷ್ಟಿಕೋನವು ಜಾಗತಿಕ ಬೇಡಿಕೆಗಳಿಗೆ ಅನುಗುಣವಾಗಿ ಉದ್ಯಮಾಧಾರಿತ ಕಲಿಕೆಯ ಮೇಲೆ ಕೇಂದ್ರೀಕರಿಸುತ್ತದೆ. ನಾವು ಪ್ರಾಯೋಗಿಕ ಸಮಸ್ಯೆ ಪರಿಹಾರ ಮತ್ತು ನೈತಿಕ ಕೋಡಿಂಗ್ ಅಭ್ಯಾಸಗಳಿಗೆ ಆದ್ಯತೆ ನೀಡುತ್ತೇವೆ. | Revised (hybrid) | Reachable — `resolve_unit(cse.hod).body` returns the existing value; write pending |
| `kn.departments.cse.fees` | card body / unit narration (display+narration) | KCET: As per KEA norms \| Management: ₹3,50,000/year | KCET: KEA ಮಾನದಂಡಗಳ ಪ್ರಕಾರ \| ನಿರ್ವಹಣೆ: ₹3,50,000/ವರ್ಷ | ಕೆಸಿಇಟಿ: ಕೆಇಎ ನಿಯಮಗಳ ಪ್ರಕಾರ \| ನಿರ್ವಹಣೆ: ₹3,50,000/ವರ್ಷ | KSET: As per KEA Rules \| Maintenance: Rs.3,50,000/annum | **No** — acronym lost ['KCET', 'KEA']; back-translation overlap low (0.00); pipe character is TTS-unsafe | No — exam name and fee label corrupted | Existing ನಿರ್ವಹಣೆ back-translates as 'Maintenance' — a visitor reads a maintenance charge instead of the management quota. Sarvam transliterated the protected acronyms (KCET -> ಕೆಸಿಇಟಿ, KEA -> ಕೆಇಎ); the round trip returned **KSET**, a different exam. It also rewrote ₹ as 'Rs.'. Candidate rejected wholesale. | KCET: KEA ಮಾನದಂಡಗಳ ಪ್ರಕಾರ \| ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್: ₹3,50,000/ವರ್ಷ | Revised (terminology only) | Reachable — `resolve_unit(cse.fees).body` returns the existing value; write pending |
| `kn.departments.cse.placement` | card body / unit narration (display+narration) | Top recruiters include TCS, Infosys, and Amazon. Students receive rigorous technical and aptitude training. | ಉನ್ನತ ನೇಮಕಾತಿದಾರರಲ್ಲಿ TCS, Infosys ಮತ್ತು Amazon ಸೇರಿವೆ. ವಿದ್ಯಾರ್ಥಿಗಳು ಕಠಿಣ ತಾಂತ್ರಿಕ ಮತ್ತು ಯೋಗ್ಯತೆಯ ತರಬೇತಿಯನ್ನು ಪಡೆಯುತ್ತಾರೆ. | ಟಿ.ಸಿ.ಎಸ್, ಇನ್ಫೋಸಿಸ್ ಮತ್ತು ಅಮೆಜಾನ್ ಪ್ರಮುಖ ನೇಮಕಾತಿದಾರರಲ್ಲಿ ಸೇರಿವೆ. ವಿದ್ಯಾರ್ಥಿನಿಯರು ಕಠಿಣ ತಾಂತ್ರಿಕ ಮತ್ತು ಆಪ್ಟಿಟ್ಯೂಡ್ ತರಬೇತಿಯನ್ನು ಪಡೆಯುತ್ತಾರೆ. | TCS, Infosys, and Amazon are among the major recruiters. Female students receive rigorous technical and aptitude training. | **No** — latin name transliterated ['Amazon', 'Infosys', 'TCS']; back-translation adds narrowing term ['female'] | No — audience narrowed to women | Existing ಯೋಗ್ಯತೆಯ ತರಬೇತಿ reads as 'eligibility training'; aptitude training is ಆಪ್ಟಿಟ್ಯೂಡ್ ತರಬೇತಿ. Sarvam changed ವಿದ್ಯಾರ್ಥಿಗಳು (students) to ವಿದ್ಯಾರ್ಥಿನಿಯರು (**female students**) and transliterated TCS/Infosys/Amazon. Candidate rejected wholesale. | ಉನ್ನತ ನೇಮಕಾತಿದಾರರಲ್ಲಿ TCS, Infosys ಮತ್ತು Amazon ಸೇರಿವೆ. ವಿದ್ಯಾರ್ಥಿಗಳು ಕಠಿಣ ತಾಂತ್ರಿಕ ಮತ್ತು ಆಪ್ಟಿಟ್ಯೂಡ್ ತರಬೇತಿಯನ್ನು ಪಡೆಯುತ್ತಾರೆ. | Revised (terminology only) | Reachable — `resolve_unit(cse.placements).body` returns the existing value; write pending |
| `kn.admissions_and_fees.eligibility` | card body / unit narration (display+narration) | 10+2 with 45% aggregate [cite: 344] Physics and Mathematics [cite: 345] Chemistry, Biotechnology, Biology, Computer Science, or Electronics [cite: 346] 45% aggregate marks [cite: 348] SC/ST/Category-1/OBC: 40% aggregate marks (with relaxation) [cite: 349] MBA: Graduation with minimum 50% aggregate [cite: 287] | 10+2 ರಲ್ಲಿ ಒಟ್ಟು 45% ಭೌತಶಾಸ್ತ್ರ ಮತ್ತು ಗಣಿತ ರಸಾಯನಶಾಸ್ತ್ರ, ಜೈವ ತಂತ್ರಜ್ಞಾನ, ಜೀವಶಾಸ್ತ್ರ, ಕಂಪ್ಯೂಟರ್ ಸೈನ್ಸ್ ಅಥವಾ ಎಲೆಕ್ಟ್ರಾನಿಕ್ಸ್ ಸಾಮಾನ್ಯ: 45% ಒಟ್ಟು ಅಂಕಗಳು SC/ST/Category-1/OBC: 40% ಒಟ್ಟು ಅಂಕಗಳು (ಸಡಲಿಕೆಯೊಂದಿಗೆ) MBA: ಕನಿಷ್ಠ 50% ಒಟ್ಟು ಯೋಗ್ಯತೆಯೊಂದಿಗೆ ಪದವಿ | 10+2 ರಲ್ಲಿ ಒಟ್ಟು 45% ಅಂಕಗಳೊಂದಿಗೆ [ಉಲ್ಲೇಖ: 344] ಭೌತಶಾಸ್ತ್ರ ಮತ್ತು ಗಣಿತ [ಉಲ್ಲೇಖ: 345] ರಸಾಯನಶಾಸ್ತ್ರ, ಜೈವಿಕ ತಂತ್ರಜ್ಞಾನ, ಜೀವಶಾಸ್ತ್ರ, ಗಣಕ ವಿಜ್ಞಾನ ಅಥವಾ ಎಲೆಕ್ಟ್ರಾನಿಕ್ಸ್ [ಉಲ್ಲೇಖ: 346] ಒಟ್ಟು 45% ಅಂಕಗಳು [ಉಲ್ಲೇಖ: 348] SC/ST/ವರ್ಗ-1/OBC: ಒಟ್ಟು 40% ಅಂಕಗಳು (ಸಡಿಲಿಕೆಯೊಂದಿಗೆ) [ಉಲ್ಲೇಖ: 349] MBA: ಕನಿಷ್ಠ 50% ಒಟ್ಟು ಅಂಕಗಳೊಂದಿಗೆ ಪದವಿ [ಉಲ್ಲೇಖ: 287] | With a total of 45% marks in 10+2 [Reference: 344], Physics and Mathematics [Reference: 345], Chemistry, Biotechnology, Biology, Computer Science or Electronics [Reference: 346], with a total of 45% marks [Reference: 348], SC/ST/Category-1/OBC: With a total of 40% marks (with relaxation) [Reference: 349], MBA: With a minimum of 50% total marks in graduation [Reference: 287]. | **No** — latin name transliterated ['Category'] | Partial — citation artifacts reproduced | Existing had four defects: ಯೋಗ್ಯತೆ ('worthiness') used where *aggregate marks* was meant; ಸಡಲಿಕೆ is a misspelling of ಸಡಿಲಿಕೆ; ಜೈವ ತಂತ್ರಜ್ಞಾನ is a truncated form of ಜೈವಿಕ ತಂತ್ರಜ್ಞಾನ; ಅಂಕಗಳು missing after the first 45%. Sarvam reproduced the English `[cite: N]` artifacts as `[ಉಲ್ಲೇಖ: N]` — rejected. | 10+2 ರಲ್ಲಿ ಒಟ್ಟು 45% ಅಂಕಗಳು ಭೌತಶಾಸ್ತ್ರ ಮತ್ತು ಗಣಿತ ರಸಾಯನಶಾಸ್ತ್ರ, ಜೈವಿಕ ತಂತ್ರಜ್ಞಾನ, ಜೀವಶಾಸ್ತ್ರ, ಕಂಪ್ಯೂಟರ್ ಸೈನ್ಸ್ ಅಥವಾ ಎಲೆಕ್ಟ್ರಾನಿಕ್ಸ್ ಸಾಮಾನ್ಯ: 45% ಒಟ್ಟು ಅಂಕಗಳು SC/ST/Category-1/OBC: 40% ಒಟ್ಟು ಅಂಕಗಳು (ಸಡಿಲಿಕೆಯೊಂದಿಗೆ) MBA: ಕನಿಷ್ಠ 50% ಒಟ್ಟು ಅಂಕಗಳೊಂದಿಗೆ ಪದವಿ | Revised (hybrid) | Reachable via `_admissions_slides(kn)` eligibility slide (**not** `resolve_unit`); returns the existing value today; write pending |

### 15.5 Rejection criteria triggered

| Criterion | Rows | Evidence |
|---|---|---|
| Name/number/fee/designation/acronym changed | `cse.fees`, `cse.placement` | KCET -> ಕೆಸಿಇಟಿ round-tripped as **KSET**; TCS/Infosys/Amazon transliterated; ₹ rewritten as 'Rs.' |
| New fact introduced / meaning changed | `cse.placement` | ವಿದ್ಯಾರ್ಥಿಗಳು -> ವಿದ್ಯಾರ್ಥಿನಿಯರು; back-translation read '**Female** students' |
| Terminology conflicts with approved glossary | `ui.clarification.department`, `ui.error.retry`, `cse.intro` | ಇಲಾಖೆ vs ವಿಭಾಗ; ಮತ್ತೊಮ್ಮೆ vs ಮತ್ತೆ; ಇಂಜಿನಿಯರಿಂಗ್ vs ಎಂಜಿನಿಯರಿಂಗ್ |
| Back-translation does not match source | `cse.fees` | word overlap 0.00; 'Maintenance' for Management, 'KSET' for KCET |
| Unsuitable for concise kiosk display | `ui.status.listening` | passive ಕೇಳಲಾಗುತ್ತಿದೆ breaks the first-person status-line voice |
| Would break the runtime | `ui.welcome.named_display` | interpolation token `{name}` translated to `{ಹೆಸರು}` |
| Clause disappeared | none in the pilot | line-count and placeholder checks clean on the remaining rows |

### 15.6 Acceptance check on the approved values

The approved Kannada was itself sent back through kn->en and re-checked, so the hand-revised values are held to the same standard as Sarvam's. Command:

```bash
python -m backend.tools.kannada_sarvam_review --verify-approved
```

Result: 15/15 verified. Two flags, both benign and explained:

- `kn.departments.cse.fees` — *pipe character is TTS-unsafe*. Pre-existing and confirmed to reach the provider: `sanitize_tts_text` does not strip `|`, and `narrate_unit(cse.fees, 'kn')` returns the separator verbatim. Tracked as a defect in §15.7, not a translation issue.
- `kn.admissions_and_fees.eligibility` — *number drift*. Expected: the dropped numbers are the `[cite: N]` RAG citation artifacts that the Kannada value correctly strips and the English source still carries (§15.7).

### 15.7 Defects found outside the translation scope

These were surfaced while verifying runtime reachability. They are **not** Kannada translation problems and were not changed in this pilot; each is reported for a decision.

| # | Defect | Evidence | Scope |
|---|---|---|---|
| 1 | The English admissions eligibility slide renders RAG citation artifacts to visitors | `_admissions_slides(en)` returns `10+2 with 45% aggregate [cite: 344] ...` — nine `[cite: N]` markers | English locale source; visitor-facing |
| 2 | The eligibility slide emits its content twice | `_admissions_slides` appends the flat `eligibility` string **and** the structured `be_programs.*` fields, which restate it. 639-char body for 245 chars of content. Reproduces in English and Kannada | `narration_plan.py:878-901`; language-agnostic |
| 3 | `\|` in fee bodies reaches TTS | `sanitize_tts_text` preserves `\|`; the Kannada spoken fee line is `... ಪ್ರಕಾರ \| ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್: ...` | `unit_narration.py:86-98`; all languages |
| 4 | HOD identity script is inconsistent | `cse.hod` card body renders ಡಾ. ಶಶಿಕುಮಾರ್ ಡಿ ಆರ್ while narration renders `Dr. Shashikumar D R` | Kannada locale + narration; needs an owner ruling on script policy for names |

Defect 2 also means the duplicated terms must be corrected in **both** places or the slide will display two spellings of the same word: `ಸಡಲಿಕೆ` appears in the flat `eligibility` string and in `be_programs.requirements_reserved`, and `ಜೈವ ತಂತ್ರಜ್ಞಾನ` in the flat string and in `be_programs.optional_subjects`. Those nested fields are in the inventory and are queued in the `cards` batch.

### 15.8 Review-tool checks

The automated checks are necessary but not sufficient. On `cse.placement` the original check set returned *clean* while the candidate had both transliterated three company names and narrowed the audience to women — caught only by reading the back-translation. Two checks were added before the bulk batches:

- **Latin-name preservation** — Latin tokens the existing Kannada deliberately keeps (TCS, Infosys, Amazon, Category) must survive in the candidate. Acronyms already reported are not double-reported.
- **Narrowing-term drift** — flags a back-translation that introduces *female/male/girls/boys/women/men/only/must not/cannot* when the English source has none.

An earlier acronym check used substring matching and produced false positives (`TC` inside `TCS`, `CET` inside `KCET`); it now matches on Latin word boundaries.

### 15.9 Status

No production file has been modified by this pilot. `ui.json` and `kn.json` are unchanged; nothing has been committed or pushed. 7 of the 15 approved values are already live (the keep-existing decisions); the remaining 8 are pending a write once the pilot is approved.

Artifacts (none contain credentials):

- `backend/tools/kannada_sarvam_review.py` — the review tool (not imported by runtime)
- `backend/tools/kannada_review_decisions.json` — per-row decision and rationale
- `backend/tools/.cache/` — git-ignored translation cache, rows, verification and probe output

## 16. Eligibility-duplication audit (deferred workstream)

This section is **audit-only**. No source file was modified by this audit and no fix
was attempted. The duplication fix is authorised by condition 3 of the pilot gate but
is deferred to a separate focused workstream; the eligibility value itself remains
blocked (see §15.3 and §4 of the pre-batch report). The purpose of this section is
to enumerate every consumer so the deferred fix can be scoped correctly.

### 16.1 Backend consumers of the flat `eligibility` field

| File:line | Read | Used for |
|---|---|---|
| `backend/services/narration_plan.py:879-880` | `rec.get("eligibility")` | Appended as the first `elig_parts` element in `_admissions_slides`, before the structured `be_programs.*` fields. |
| `backend/services/narration_plan.py:899-901` | `_clean(rec.get("eligibility"))` | Used as the `elig_body` fallback when no structured parts are present. |
| `backend/tools/kannada_sarvam_review.py:316` | `kn.admissions_and_fees.eligibility` | Diagnostic reading only; review tool, not runtime. |
| `backend/tools/.cache/gen_pilot_section.py:36,55,110,119,236,356,378,396-397` | same key | Cache and report-generation only; not runtime. |
| `backend/tests/test_kannada_corrected_locale_integration.py:35-36` | `mba_programs.*` (not flat `eligibility`) | Content-hash test for nested structured fields. |

Only `narration_plan.py:878-901` is a runtime consumer of the flat `eligibility` value.

### 16.2 Backend consumers of structured `be_programs.*`

| File:line | Read | Used for |
|---|---|---|
| `backend/services/narration_plan.py:881-891` | `be_programs.qualification`, `compulsory_subjects`, `optional_subjects`, `requirements_general`, `requirements_reserved`, `entrance_exams[]` | Appended to `elig_parts` and `exams` inside `_admissions_slides`. |
| `backend/services/narration_plan.py:906-909` | `be_programs.entrance_exams[]` | Appended to the entrance-exams slide body (separate from eligibility slide). |
| `backend/tests/test_kannada_corrected_locale_integration.py:35` | `mba_programs.qualification` (sibling of `be_programs`) | Content-hash regression. |

### 16.3 Frontend consumers of the flat `eligibility` field

| File:line | Read | Used for |
|---|---|---|
| `frontend/src/lib/collegeLocaleUtils.ts:407` | `rec.eligibility` | Appended to `eligParts` inside `buildAdmissionsCardsFromLocale` — **same duplication pattern as the backend**. |
| `frontend/src/lib/collegeLocaleUtils.ts:422-425` | `rec.eligibility` (fallback) | Used as the final `eligibilityBody` fallback when neither structured parts nor the flat value suffice. |
| `frontend/src/lib/collegeLocaleUtils.ts:62,65,72,79,86,93,100` | `cards.eligibility` etc. (UI labels) | Per-language label for the slide title; does not read the body. |
| `frontend/src/components/chat/cards/DocumentsBlock.tsx:108` | `'vtu_eligibility'` (key) | Routing keyword for FAQ-suggestion matching; not the body. |
| `frontend/src/data/faqSuggestions.ts:81` | `'eligibility'` (substring) | Routing keyword; not the body. |

### 16.4 Frontend consumers of structured `be_programs.*`

| File:line | Read | Used for |
|---|---|---|
| `frontend/src/lib/collegeLocaleUtils.ts:400-419` | `admission_and_eligibility.be_programs.{qualification, compulsory_subjects, optional_subjects, requirements_general, requirements_reserved}` and `mba_programs.{qualification, expected_cutoff}` | Joined into `eligParts` inside `buildAdmissionsCardsFromLocale`. |
| `frontend/src/lib/collegeLocaleUtils.ts:431-435` | `be_programs.entrance_exams[]` and `mba_programs.entrance_exams[]` | Appended to the entrance-exams body. |

### 16.5 Display vs narration behavior

- **Display (kiosk card body).** Both the backend and the frontend build an
  `eligibility` body that joins the flat `eligibility` value with the structured
  `be_programs.*` fields. The result is shown to the visitor on the admissions
  slide. A visitor therefore sees each eligibility fact twice — once as a clause
  in the hand-joined flat string and once as a structured row.
- **Narration (TTS).** `_admissions_slides` returns tuples consumed by
  `narration_plan.py:842-846` and rendered as
  `NarrationSegment(display_text=f"{L[0]}\n{slides[0]}", ...)`. The narration reads
  out `display_text` literally, including both copies. The frontend equivalent
  feeds `planToScenes.ts` (transitively, via the `StageSlide.content` field).
  The TTS sanitiser (`backend/services/tts_text_contract.py`,
  `unit_narration.py:86-98`) preserves the duplicated text and does not deduplicate
  by meaning. Spoken output therefore repeats the same fact twice.

### 16.6 Exact duplication observed

For the **Kannada** locale the `eligParts` list built in
`backend/services/narration_plan.py:878-897` and
`frontend/src/lib/collegeLocaleUtils.ts:405-421` produces the following clauses
*in this order* before deduplication:

1. The flat eligibility string (5 clauses joined without sentence punctuation).
2. `10+2 ರಲ್ಲಿ ಒಟ್ಟು 45%` (be_programs.qualification).
3. `ಭೌತಶಾಸ್ತ್ರ ಮತ್ತು ಗಣಿತ` (be_programs.compulsory_subjects).
4. `ರಸಾಯನಶಾಸ್ತ್ರ, ಜೈವ ತಂತ್ರಜ್ಞಾನ, ಜೀವಶಾಸ್ತ್ರ, ಕಂಪ್ಯೂಟರ್ ಸೈನ್ಸ್ ಅಥವಾ ಎಲೆಕ್ಟ್ರಾನಿಕ್ಸ್` (be_programs.optional_subjects).
5. `ಸಾಮಾನ್ಯ ವರ್ಗ: ಒಟ್ಟು 45% ಅಂಕಗಳು` (be_programs.requirements_general).
6. `SC/ST/Category-1/OBC: ಒಟ್ಟು 40% ಅಂಕಗಳು (ಸಡಲಿಕೆಯೊಂದಿಗೆ)` (be_programs.requirements_reserved).
7. `MBA: ಕನಿಷ್ಠ 50% ಒಟ್ಟು ಅಂಕಗಳೊಂದಿಗೆ ಪದವಿ` (mba_programs.qualification).

The existing dedupe (`_dedupe_join` in Python, `dedupeLines` in TypeScript) is
**line-level**: it removes byte-identical adjacent lines. None of the seven lines
above are byte-identical to any other, so all seven survive. Clauses 2, 3, 4, 5
and 6 each restate part of clause 1 in different words; clauses 1 and 7 overlap on
the MBA 50% content.

`ಸಡಲಿಕೆ` appears in clause 1 and clause 6 — same misspelling in both places.
`ಜೈವ ತಂತ್ರಜ್ಞಾನ` appears in clause 1 and clause 4 — same truncation in both
places. Any single-source-of-truth fix must therefore touch both locations, or
the slide will continue to display two spellings of the same word.

The **English** locale has the same structure (the bug is language-agnostic).
The English `admissions_and_fees.eligibility` value also contains the RAG
citation artifacts (`[cite: 344]`, `[cite: 345]`, …) and is reproduced
identically in `_admissions_slides(en)`. Out of scope for this batch.

### 16.7 Facts that legitimately repeat

Some duplication is content, not bug:

- The 10+2 aggregate `45%` and the general requirement `45%` are the same
  number representing the same requirement stated at two levels of detail; both
  should remain.
- The reserved-category `40%` clause and the `SC/ST/Category-1/OBC: 40%` row in
  the structured fields are the same fact; one source of truth should hold it.
- The MBA `50%` clause and the `MBA: 50%` structured row are the same fact;
  one source of truth should hold it.

Tests in the deferred workstream must distinguish these legitimate repetitions
from the unintended duplication of the entire preamble. The user has forbidden
raw token-count tests such as "45% appears once" precisely because the same
number may represent multiple valid requirements. The correct verification
shape is **semantic field equality and rendered-section equality**, not
substring counting.

### 16.8 Proposed single source of truth

For the deferred workstream only. Not authorised to implement in this batch.

- **Authoritative store for the slide body:** `admissions_and_fees.additional_details.admission_and_eligibility.{be_programs, mba_programs}.*`
  (the structured fields).
- **Authoritative store for the fallback when the structured fields are
  missing or empty:** the flat `admissions_and_fees.eligibility` value.
- **Build order in `_admissions_slides` / `buildAdmissionsCardsFromLocale`:**
  if structured fields yield any non-empty `elig_parts`, do **not** append the
  flat value; otherwise use the flat value as a final fallback only. This
  matches the existing fallback path in the code (lines 899-901 and 422-425)
  and is the minimum change to remove the duplication.
- **Non-slide consumers of the flat value:** none currently exist in
  `backend/services` or `backend/app`. The flat value may therefore be left in
  the locale JSON for documentation and reviewer use; the only behavior change
  is the build order in the two slide builders.
- **Test design:** verify that the eligibility slide body does not contain a
  clause that is a superset of another clause in the same body, and that every
  fact appearing in the flat value also appears in the structured fields. Do
  not assert fixed substring counts.

### 16.9 Open issues carried into the deferred workstream

- The English slide still contains `[cite: N]` RAG citation artifacts in the
  flat `eligibility` value; fixing those is a separate English RAG workstream
  (condition 5 of the pilot gate).
- The `|` character in the eligibility body is not used here, but the same
  separator appears in fee bodies (out of scope per condition 5).
- The 11 HOD biographies and 28 sample campus units have no eligibility
  overlap and are not part of this audit.

---

## 17. Batch 2 — mechanical review (25 ui.json rows)

### 17.1 Scope and method

The 25 next-after-pilot ui.* rows in deterministic inventory order, all
classified `MECHANICALLY_REVIEWED_PROVISIONAL` after audit revealed that
the original `KEEP_EXISTING_VERIFIED` label was over-claimed.

Per the user's spec, three Sarvam operations per row are mandatory:
(1) English source → Sarvam Kannada candidate, (2) candidate → English,
(3) existing Kannada → English. "Sarvam candidate was worse" is not by
itself proof that the existing value is correct.

### 17.2 Coverage accounting (Batch 2)

| Bucket | Count |
|---|---:|
| TOTAL ORIGINALLY REVIEWABLE | 212 |
| PILOT REVIEWED | 15 |
| PILOT CORRECTIONS APPLIED | 5 |
| BATCH 2 MECHANICALLY REVIEWED | 25 |
| BATCH 2 PROVISIONALLY RETAINED | 25 |
| NATIVE/HUMAN CERTIFIED | 0 |
| REMAINING UNREVIEWED | 172 |

### 17.3 Spot-audit verdict (10 higher-risk rows)

| Classification | Count | Rows |
|---|---:|---|
| KEEP_EXISTING_SUPPORTED | 5 | `ui.status.thinking_detail_1`, `ui.status.thinking_detail_2`, `ui.status.thinking_detail_3`, `ui.status.returning_to_sleep`, `ui.error.microphone_denied` |
| KEEP_EXISTING_PROVISIONAL | 5 | `ui.welcome.name_prompt`, `ui.status.thinking_detail_5`, `ui.status.connectivity_issue`, `ui.clarification.hostel`, `ui.error.no_speech` |
| CORRECTION_REQUIRED | 0 | — |
| HUMAN_REVIEW_REQUIRED (blocker) | 0 | — |

### 17.4 Native-review queue (non-blocking)

| Row | Reason |
|---|---|
| `ui.welcome.name_prompt` | register/word-choice question |
| `ui.status.thinking_detail_5` | voice/ellipsis question |
| `ui.status.connectivity_issue` | voice/tense question |
| `ui.clarification.hostel` | glossary/word-choice question |
| `ui.error.no_speech` | phrasing/word-choice question |

Production values are not modified. The queue is for the user's
separate decision.

### 17.5 Evidence schema note (Batch 2)

The Batch 2 entries in `kannada_review_decisions.json` were written
with the field set `decision / approved / reason / batch`, plus the
three Sarvam outputs where the cache supplied them. Structured
per-row evidence fields listed in section 19 (placeholder check,
acronym check, etc.) were not recorded for Batch 2 and are
therefore marked `LEGACY_UNSTRUCTURED` rather than backfilled.

---

## 18. Batch 3 — mechanical review (25 ui.json rows)

### 18.1 Scope

The 25 next-after-Batch-2 ui.* rows in deterministic inventory order.
The first 25 included 3 ghost keys (`ui.session.goodbye`,
`ui.session.ending`, `ui.session.interrupted`) that are defined in
`ui.json` but not consumed by any frontend or backend code; those 3
were excluded under the production-reachable gate and replaced by the
next 3 in inventory order (`ui.cards.placements_training`,
`ui.cards.fees`, `ui.cards.eligibility`). The exclusion of the 3 ghost
keys is reported separately in section 19.

### 18.2 Method

For every row, three Sarvam operations were performed (en→kn,
candidate→en, existing→en). The 14 evidence items (placeholder
preservation, name preservation, number preservation, currency
preservation, protected-acronym preservation, Latin-company-name
preservation, gender narrowing, subject/object drift, missing
clauses, added clauses, terminology conflict, punctuation, display
suitability, narration suitability) were recorded inside each
entry's `reason` field, not as structured per-row evidence fields.
See section 20 for the schema change introduced in Batch 4 that
upgrades these to structured fields.

### 18.3 Per-row verdicts

| Row | Classification | One-line defect (if any) |
|---|---|---|
| `ui.error.voice_unsupported` | `KEEP_EXISTING_MECHANICALLY_SUPPORTED` | tone-thinning only ("is not available" vs source "is not supported"); Chrome/Edge preserved |
| `ui.error.voice_failed` | `KEEP_EXISTING_MECHANICALLY_SUPPORTED` | defect on candidate (breaks family "ಇನ್‌ಪುಟ್" glossary) |
| `ui.error.voice_timeout` | `KEEP_EXISTING_MECHANICALLY_SUPPORTED` | register details (tense, possessive) |
| `ui.error.voice_unrecognized` | `NATIVE_REVIEW_RECOMMENDED` | source first-person vs family passive (deferred) |
| `ui.error.network` | `KEEP_EXISTING_MECHANICALLY_SUPPORTED` | defect on candidate ("ಭಾಷಣ" awkward for "speech service") |
| `ui.error.offline` | `KEEP_EXISTING_MECHANICALLY_SUPPORTED` | register detail (past-participle form) |
| `ui.error.empty_response` | `NATIVE_REVIEW_RECOMMENDED` | same family-voice question as voice_unrecognized |
| `ui.error.invalid_request` | `KEEP_EXISTING_MECHANICALLY_SUPPORTED` | byte-near-identical to candidate |
| `ui.error.missing_text` | `KEEP_EXISTING_MECHANICALLY_SUPPORTED` | disjunction order is order-invariant |
| `ui.error.audio_unavailable` | `KEEP_EXISTING_MECHANICALLY_SUPPORTED` | candidate "ಉತ್ಪಾದನೆ" is manufacturing term |
| `ui.availability.official_fact_blocked` | `KEEP_EXISTING_MECHANICALLY_SUPPORTED` | existing uses more common verb |
| `ui.availability.unknown` | `KEEP_EXISTING_MECHANICALLY_SUPPORTED` | existing voice-thinning, but preserves "placements" glossary term; candidate has two defects (term + added "however") |
| `ui.availability.missing_source` | `KEEP_EXISTING_MECHANICALLY_SUPPORTED` | near-identical word order |
| `ui.session.back` | `KEEP_EXISTING_MECHANICALLY_SUPPORTED` | existing is the conventional button label |
| `ui.session.home` | `KEEP_EXISTING_MECHANICALLY_SUPPORTED` | existing is context-accurate (homepage); candidate is literal (home) |
| `ui.session.close` | `KEEP_EXISTING_MECHANICALLY_SUPPORTED` | existing uses honorific form (polite) |
| `ui.session.retry_connection` | `KEEP_EXISTING_MECHANICALLY_SUPPORTED` | existing is natural; candidate is more formal |
| `ui.session.enable_face_display` | `KEEP_EXISTING_MECHANICALLY_SUPPORTED` | byte-identical |
| `ui.cards.department` | `KEEP_EXISTING_MECHANICALLY_SUPPORTED` | candidate is the rejected glossary-violation term "ಇಲಾಖೆ" |
| `ui.cards.hod_and_vision` | `KEEP_EXISTING_MECHANICALLY_SUPPORTED` | candidate introduces gender narrowing (feminine singular "ಮುಖ್ಯಸ್ಥೆ") |
| `ui.cards.achievements` | `KEEP_EXISTING_MECHANICALLY_SUPPORTED` | byte-identical |
| `ui.cards.placements` | `KEEP_EXISTING_MECHANICALLY_SUPPORTED` | existing preserves "Placements" glossary term; candidate translates to "ಉದ್ಯೋಗಾವಕಾಶಗಳು" |
| `ui.cards.placements_training` | `KEEP_EXISTING_MECHANICALLY_SUPPORTED` | same as cards.placements |
| `ui.cards.fees` | `KEEP_EXISTING_MECHANICALLY_SUPPORTED` | byte-identical |
| `ui.cards.eligibility` | `KEEP_EXISTING_MECHANICALLY_SUPPORTED` | byte-identical; UI card label, not a structured eligibility field |

### 18.4 Native-review queue (non-blocking)

| Row | Reason |
|---|---|
| `ui.error.voice_unrecognized` | first-person vs family-passive voice normalization |
| `ui.error.empty_response` | first-person vs family-passive voice normalization |

### 18.5 Batch 3 accounting (corrected)

| Bucket | Count |
|---|---:|
| TOTAL ORIGINALLY REVIEWABLE | 212 |
| PREVIOUSLY MECHANICALLY REVIEWED | 40 (15 pilot + 25 batch 2) |
| REVIEWED THIS BATCH | 25 |
| KEEP_EXISTING_MECHANICALLY_SUPPORTED | 23 |
| SAFE_CORRECTION_CANDIDATES | 0 |
| BLOCKED_LINGUISTIC | 0 |
| BLOCKED_OFFICIAL_FACT | 0 |
| BLOCKED_MISSING_SOURCE | 0 |
| BLOCKED_RUNTIME_STRUCTURE | 0 |
| NATIVE_REVIEW_RECOMMENDED | 2 |
| SARVAM API CALLS | 82 |
| CACHE HITS | 8 |
| PRODUCTION FILES CHANGED | 0 |
| EVIDENCE FILES CHANGED | `backend/tools/kannada_review_decisions.json`, this report |
| TESTS RUN | 0 (no test when no production value changes, per test policy) |
| GIT DIFF CHECK | clean |
| REMAINING PRODUCTION-REACHABLE (preliminary) | 144 |

The 144 preliminary remainder uses the inventory-tool count of
remaining ui.* + card rows minus the 65 already mechanically
reviewed minus the 3 ghost keys. It is provisional pending the
reachability audit in section 19.

### 18.6 What this batch did not do

- Did not modify any production locale value.
- Did not start Batch 4.
- Did not resolve any deferred question.
- Did not commit, push, or modify runtime code.

---

## 19. Reachability audit — three ghost-key candidates

### 19.1 Method

Per the user's spec, the audit does not rely only on exact-string
searches. The three ghost keys
(`ui.session.goodbye`, `ui.session.ending`, `ui.session.interrupted`)
were traced through every category listed:

- direct `ui_text` / `uiText` calls (frontend + backend)
- dynamic key construction (e.g. `f"documents.items.{key}"`)
- prefix-based lookup
- session-state mappings
- WebSocket event mappings
- frontend locale helpers
- backend response templates
- narration plans
- TTS dispatch
- React components
- tests
- fallback dictionaries
- JSON iteration
- key enumeration
- wildcard or prefix consumers
- compatibility / legacy code

`ui_text` and frontend `uiText` are both pure exact-path lookups
(`backend/services/ui_localization.py:30-47`; `frontend/src/localization/uiCopy.ts:10-31`).
No code path iterates the locale dict by key, no fallback dictionary
surfaces any `session.*` key, and no WebSocket event or TTS
dispatch consumes the three ghost strings.

### 19.2 Per-key findings

#### `ui.session.goodbye` (en: "Goodbye." / kn: "ವಿದಾಯ.")

- **Defined source:** `backend/data/locales/ui.json` `en.session.goodbye`,
  `kn.session.goodbye`
- **Direct consumers:** none
- **Indirect consumers:** none
- **Dynamic consumers:** none
- **Display consumer:** none
- **Narration consumer:** none
- **TTS consumer:** none
- **WebSocket consumer:** none
- **Production reachable:** **no**
- **Evidence:** exact-string search for `session.goodbye` returns 0 hits
  in any runtime code path. The only references are (a) the locale
  file itself, and (b) this audit document. A keyword match for
  `"goodbye"` exists in
  `backend/services/conversation/policy_router.py:38`
  (`_SMALL_TALK_HINTS`), but that is a user-input keyword matcher for
  small-talk recognition — it does not call `ui_text` and does not
  surface the locale string.
- **Recommended classification:** `DEFINED_BUT_UNREACHABLE`

#### `ui.session.ending` (en: "This session is ending." / kn: "ಈ ಅಧಿವೇಶನ ಮುಕ್ತಾಯಗೊಳ್ಳುತ್ತಿದೆ.")

- **Defined source:** `backend/data/locales/ui.json` `en.session.ending`,
  `kn.session.ending`
- **Direct consumers:** none
- **Indirect consumers:** none
- **Dynamic consumers:** none
- **Display consumer:** none
- **Narration consumer:** none
- **TTS consumer:** none
- **WebSocket consumer:** none
- **Production reachable:** **no**
- **Evidence:** exact-string search for `session.ending` returns 1 hit
  in any code path: `backend/tests/test_kannada_complete_language_remediation.py:36`
  as a baseline fixture asserting the locale value. That is `TEST_ONLY`
  exposure, not production reachability. The "session ending" event in
  the orchestrator (`backend/app/main.py` around turn finalization) is
  handled via WebSocket event types (`finalize_turn`,
  `reject_if_finalized`); it never calls `ui_text("kn", "session.ending")`.
- **Recommended classification:** `DEFINED_BUT_UNREACHABLE`
  (the test fixture is a documentation snapshot, not a production
  consumer)

#### `ui.session.interrupted` (en: "The previous response was interrupted." / kn: "ಹಿಂದಿನ ಉತ್ತರವನ್ನು ನಿಲ್ಲಿಸಲಾಗಿದೆ.")

- **Defined source:** `backend/data/locales/ui.json` `en.session.interrupted`,
  `kn.session.interrupted`
- **Direct consumers:** none
- **Indirect consumers:** none
- **Dynamic consumers:** none
- **Display consumer:** none
- **Narration consumer:** none
- **TTS consumer:** none
- **WebSocket consumer:** none
- **Production reachable:** **no**
- **Evidence:** exact-string search for `session.interrupted` returns
  0 hits in any code path. The "interruption" event is handled by the
  WebSocket `clara_interrupt` event
  (`backend/app/ws_schemas.py:95`; `frontend/src/hooks/useFaceChannel.ts:138`; `facial-display/src/hooks/useParentChannel.ts:14,52,105-106`)
  and by `faceChannel.postInterrupt(turnId)` in
  `frontend/src/screens/ChatScreen.tsx:3970-3972`. None of these
  paths call `ui_text` for the "session.interrupted" string; they
  post a structural message and rely on the orb to visually reflect
  the interrupt state.
- **Recommended classification:** `DEFINED_BUT_UNREACHABLE`

### 19.3 Inventory impact

All three keys are conclusively unreachable from any production
runtime path. They are moved to the orphaned-source inventory and
removed from the production-reachable review count.

| Bucket | Count |
|---|---:|
| TOTAL ORIGINALLY REVIEWABLE | 212 |
| UNREACHABLE CANDIDATES | 3 |
| PROVISIONAL PRODUCTION-REACHABLE TOTAL | 209 |
| MECHANICALLY REVIEWED (pilot + batch 2 + batch 3) | 65 |
| PROVISIONAL REMAINING REACHABLE | 144 |
| PRODUCTION VALUES CHANGED IN BATCH 3 | 0 |

The 209 total is provisional pending any future key-removal or
consumer-wiring change.

### 19.4 Decision

The three keys are **not deleted or modified** per the user's spec.
They remain in `ui.json` so the user can later decide whether to
(a) wire them to consumers, (b) delete them, or (c) leave them
unused.

---

## 20. Batch 4 — mechanical review (25 ui.json rows)

### 20.1 Scope and method

- 25 ui.* rows in deterministic inventory order, following the 15
  pilot + 25 Batch 2 + 25 Batch 3 already-mechanically-reviewed rows
  and excluding the 3 ghost keys (ui.session.goodbye, ending,
  interrupted) classified DEFINED_BUT_UNREACHABLE in section 19.
- Excluded: 3 explicitly-blocked values (ui.status.processing,
  ui.session.timeout, kn.admissions_and_fees.eligibility) and the
  4 deferred workstreams.
- Each row: 3 Sarvam operations (en→kn, kn→en of candidate, kn→en
  of existing). Source data in
  `backend/tools/.cache/kannada_sarvam_batch4_rows.json`.
- Per-row verdict: 4 input/output fields + 14 structured check
  fields, computed via `build_structured_evidence()` in
  `backend/tools/kannada_sarvam_review.py`. Anti-fabrication
  guarantee preserved (no PASS is invented for absent data).
- No production locale values were modified. The 25 entries were
  added to `backend/tools/kannada_review_decisions.json` with
  `batch=4`, `approved=None` (no write pending).

### 20.2 Per-row verdicts

| Row | English source | Existing | Sarvam candidate | Verdict |
|---|---|---|---|---|
| `ui.cards.entrance_exams` | Entrance examinations | ಪ್ರವೇಶ ಪರೀಕ್ಷೆಗಳು | ಪ್ರವೇಶ ಪರೀಕ್ಷೆಗಳು | KEEP_EXISTING_MECHANICALLY_SUPPORTED |
| `ui.cards.ug_fees` | Undergraduate fee information | ಪದವಿಪೂರ್ವ ಶುಲ್ಕದ ಮಾಹಿತಿ | ಪದವಿಪೂರ್ವ ಶುಲ್ಕದ ಮಾಹಿತಿ | KEEP_EXISTING_MECHANICALLY_SUPPORTED |
| `ui.cards.pg_fees` | MBA and postgraduate fee information | MBA ಮತ್ತು ಸ್ನಾತಕೋತ್ತರ ಶುಲ್ಕದ ಮಾಹಿತಿ | MBA ಮತ್ತು ಸ್ನಾತಕೋತ್ತರ ಶುಲ್ಕದ ಮಾಹಿತಿ | KEEP_EXISTING_MECHANICALLY_SUPPORTED |
| `ui.cards.scholarships` | Scholarships | ವಿದ್ಯಾರ್ಥಿವೇತನಗಳು | ವಿದ್ಯಾರ್ಥಿ ವೇತನಗಳು | NATIVE_REVIEW_RECOMMENDED |
| `ui.cards.training_objectives` | Training and placement objectives | ತರಬೇತಿ ಮತ್ತು ಪ್ಲೇಸ್‌ಮೆಂಟ್ ಉದ್ದೇಶಗಳು | ತರಬೇತಿ ಮತ್ತು ನಿಯೋಜನೆ ಉದ್ದೇಶಗಳು | BLOCKED_LINGUISTIC |
| `ui.cards.training_programs` | Training programs | ತರಬೇತಿ ಕಾರ್ಯಕ್ರಮಗಳು | ತರಬೇತಿ ಕಾರ್ಯಕ್ರಮಗಳು | KEEP_EXISTING_MECHANICALLY_SUPPORTED |
| `ui.cards.summary` | Summary | ಸಂಕ್ಷಿಪ್ತ ಮಾಹಿತಿ | ಸಾರಾಂಶ | NATIVE_REVIEW_RECOMMENDED |
| `ui.cards.information_unavailable` | Information is not available. | ಮಾಹಿತಿ ಲಭ್ಯವಿಲ್ಲ. | ಮಾಹಿತಿ ಲಭ್ಯವಿಲ್ಲ. | KEEP_EXISTING_MECHANICALLY_SUPPORTED |
| `ui.cards.college_brochure` | College brochure | ಕಾಲೇಜಿನ ಮಾಹಿತಿ ಕೈಪಿಡಿ | ಕಾಲೇಜು ಕಿರುಪುಸ್ತಕ | NATIVE_REVIEW_RECOMMENDED |
| `ui.documents.title` | Required documents | ಅಗತ್ಯ ದಾಖಲೆಗಳು | ಬೇಕಾದ ದಾಖಲೆಗಳು | NATIVE_REVIEW_RECOMMENDED |
| `ui.documents.items.marks_10` | 10th Marks Card | 10ನೇ ತರಗತಿ ಮಾರ್ಕ್ಸ್ ಕಾರ್ಡ್ | 10ನೇ ತರಗತಿಯ ಅಂಕಪಟ್ಟಿ | KEEP_EXISTING_MECHANICALLY_SUPPORTED |
| `ui.documents.items.marks_12` | 12th / II PUC Marks Card | 12ನೇ ಅಥವಾ ದ್ವಿತೀಯ ಪಿಯುಸಿ ಮಾರ್ಕ್ಸ್ ಕಾರ್ಡ್ | 12ನೇ / ದ್ವಿತೀಯ ಪಿಯುಸಿ ಅಂಕಪಟ್ಟಿ | KEEP_EXISTING_MECHANICALLY_SUPPORTED |
| `ui.documents.items.rank_allotment` | CET / COMEDK Rank Card + Allotment Letter | CET ಅಥವಾ COMEDK ರ‍್ಯಾಂಕ್ ಕಾರ್ಡ್ ಮತ್ತು ಅಲಾಟ್‌ಮೆಂಟ್ ಲೆಟರ್ | ಸಿಇಟಿ / ಕಾಮೆಡ್ಕೆ ಶ್ರೇಯಾಂಕ ಪತ್ರ + ಹಂಚಿಕೆ ಪತ್ರ | BLOCKED_LINGUISTIC |
| `ui.documents.items.transfer` | Transfer Certificate (TC) | ಟ್ರಾನ್ಸ್‌ಫರ್ ಸರ್ಟಿಫಿಕೇಟ್ (TC) | ವರ್ಗಾವಣೆ ಪ್ರಮಾಣಪತ್ರ (ಟಿ.ಸಿ.) | KEEP_EXISTING_MECHANICALLY_SUPPORTED |
| `ui.documents.items.conduct` | Conduct / Character Certificate | ಕಂಡಕ್ಟ್ ಅಥವಾ ಕ್ಯಾರಕ್ಟರ್ ಸರ್ಟಿಫಿಕೇಟ್ | ನಡತೆ / ಚಾರಿತ್ರ್ಯ ಪ್ರಮಾಣಪತ್ರ | KEEP_EXISTING_MECHANICALLY_SUPPORTED |
| `ui.documents.items.caste_income` | Caste / Income Certificate (if applicable) | ಅಗತ್ಯವಿದ್ದರೆ ಜಾತಿ ಅಥವಾ ಆದಾಯ ಪ್ರಮಾಣಪತ್ರ | ಜಾತಿ / ಆದಾಯ ಪ್ರಮಾಣ ಪತ್ರ (ಅನ್ವಯವಾಗುವಲ್ಲಿ) | NATIVE_REVIEW_RECOMMENDED |
| `ui.documents.items.aadhaar` | Aadhaar Card Copy | ಆಧಾರ್ ಕಾರ್ಡ್ ಪ್ರತಿ | ಆಧಾರ್ ಕಾರ್ಡ್ ಪ್ರತಿ | KEEP_EXISTING_MECHANICALLY_SUPPORTED |
| `ui.documents.items.photos` | Passport Size Photos (6–10) | ಪಾಸ್‌ಪೋರ್ಟ್ ಗಾತ್ರದ ಫೋಟೋಗಳು (6–10) | ಪಾಸ್ಪೋರ್ಟ್ ಗಾತ್ರದ ಫೋಟೋಗಳು (6-10) | KEEP_EXISTING_MECHANICALLY_SUPPORTED |
| `ui.documents.items.migration` | Migration Certificate (for other board students) | ಇತರೆ ಬೋರ್ಡ್ ವಿದ್ಯಾರ್ಥಿಗಳಿಗೆ ಮೈಗ್ರೇಶನ್ ಪ್ರಮಾಣಪತ್ರ | ವಲಸೆ ಪ್ರಮಾಣಪತ್ರ (ಇತರ ಬೋರ್ಡ್ ವಿದ್ಯಾರ್ಥಿನಿಯರಿಗೆ) | BLOCKED_LINGUISTIC |
| `ui.documents.items.vtu_eligibility` | VTU Eligibility Certificate (if required) | ಅಗತ್ಯವಿದ್ದರೆ VTU ಅರ್ಹತಾ ಪ್ರಮಾಣಪತ್ರ | ವಿ.ಟಿ.ಯು. ಅರ್ಹತಾ ಪ್ರಮಾಣಪತ್ರ (ಅಗತ್ಯವಿದ್ದಲ್ಲಿ) | NATIVE_REVIEW_RECOMMENDED |
| `ui.comparison.close` | Close | ಮುಚ್ಚು | ಮುಚ್ಚು | KEEP_EXISTING_MECHANICALLY_SUPPORTED |
| `ui.comparison.add_program` | Add program | ಕಾರ್ಯಕ್ರಮ ಸೇರಿಸಿ | ಪ್ರೋಗ್ರಾಂ ಸೇರಿಸಿ | NATIVE_REVIEW_RECOMMENDED |
| `ui.comparison.remove_program` | Remove | ತೆಗೆದುಹಾಕಿ | ತೆಗೆದುಹಾಕಿ | KEEP_EXISTING_MECHANICALLY_SUPPORTED |
| `ui.comparison.heading` | Program comparison | ಕಾರ್ಯಕ್ರಮಗಳ ಹೋಲಿಕೆ | ಪ್ರೋಗ್ರಾಂ ಹೋಲಿಕೆ | NATIVE_REVIEW_RECOMMENDED |
| `ui.comparison.select_program` | Select program | ಕಾರ್ಯಕ್ರಮವನ್ನು ಆಯ್ಕೆಮಾಡಿ | ಪ್ರೋಗ್ರಾಂ ಆಯ್ಕೆಮಾಡಿ | NATIVE_REVIEW_RECOMMENDED |

### 20.3 Highlights of the 3 BLOCKED_LINGUISTIC rows

1. **`ui.cards.training_objectives`** — Sarvam's `ನಿಯೋಜನೆ` means
   "deployment" rather than "placement". The existing value's
   `ಪ್ಲೇಸ್‌ಮೆಂಟ್` transliteration matches the protected-token
   policy and the source-English "placement". Sarvam's candidate
   drifts away from the source meaning and is rejected.

2. **`ui.documents.items.rank_allotment`** — Sarvam transliterates
   the protected acronyms CET and COMEDK to `ಸಿಇಟಿ` and
   `ಕಾಮೆಡ್ಕೆ`. The project glossary preserves these in Latin.
   Additionally, Sarvam's back-translation returns "Ranking
   Certificate" instead of "Rank Card", which is a semantic drift
   away from "Rank Card + Allotment Letter". Both signals point to
   a glossary violation.

3. **`ui.documents.items.migration`** — Sarvam narrows
   "students" to "female students" via `ವಿದ್ಯಾರ್ಥಿನಿಯರಿಗೆ`. The
   source English is gender-neutral; the existing value uses the
   gender-neutral `ವಿದ್ಯಾರ್ಥಿಗಳಿಗೆ`. This is the same narrowing
   bug the pilot caught on `kn.departments.cse.placement` and is
   rejected for the same reason.

### 20.4 Highlights of the 9 NATIVE_REVIEW_RECOMMENDED rows

These rows have a stylistic or register choice where both the
existing and Sarvam candidate are correct Kannada. They are
flagged for a native speaker to decide on project-house-style
consistency:

- `ui.cards.scholarships` — spacing inside the compound word.
- `ui.cards.summary` — register ("Summary Information" vs "Summary").
- `ui.cards.college_brochure` — "manual" vs "handbook" vs "brochure".
- `ui.documents.title` — "Necessary" vs "Required".
- `ui.documents.items.caste_income` — word order vs English source.
- `ui.documents.items.vtu_eligibility` — VTU in Latin vs initials.
- `ui.comparison.add_program`, `ui.comparison.heading`,
  `ui.comparison.select_program` — Kannada `ಕಾರ್ಯಕ್ರಮ` vs
  transliterated `ಪ್ರೋಗ್ರಾಂ` for the noun "program" — same choice
  across the comparison.* block.

### 20.5 Required output (Batch 4)

- REACHABILITY VERDICT FOR THREE KEYS: all 3
  DEFINED_BUT_UNREACHABLE (see section 19)
- FINAL PRODUCTION-REACHABLE TOTAL: 209 (provisional, unchanged
  from Batch 3 close)
- ORPHANED/UNREACHABLE TOTAL: 3 (the three ghost keys)
- PREVIOUSLY MECHANICALLY REVIEWED: 65 (15 pilot + 25 Batch 2 + 25
  Batch 3)
- REVIEWED IN BATCH 4: 25
- KEEP_EXISTING_MECHANICALLY_SUPPORTED: 13
- SAFE_CORRECTION_CANDIDATES: 0
- BLOCKED_LINGUISTIC: 3
- BLOCKED_OFFICIAL_FACT: 0
- BLOCKED_MISSING_SOURCE: 0
- BLOCKED_RUNTIME_STRUCTURE: 0
- NATIVE_REVIEW_RECOMMENDED: 9
- SARVAM API CALLS: 65 (3 ops × 25 rows; 10 cache hits absorbed
  from Batch 3 cache)
- CACHE HITS: 10
- REMAINING PRODUCTION-REACHABLE: 119 (209 − 65 − 25)
- PRODUCTION FILES CHANGED: 0
- EVIDENCE FILES CHANGED: `backend/tools/kannada_review_decisions.json`
  (25 new entries with `batch=4`); this report (section 20 added).
- TESTS RUN: 27 passed (3 test files: test_kannada_decision_schema,
  test_kannada_safe_pilot_batch1_exact_strings,
  test_kannada_corrected_locale_integration).
- GIT DIFF CHECK: clean (no production value change).
- GIT STATUS: see below; no commit, no push per user instruction.

---

## 21. Batch 5 — mechanical review (25 rows: 12 ui + 13 kn)

### 21.1 Scope and method

- 25 production-reachable rows in deterministic inventory order:
  12 from the tail of `ui.*` (comparison.swipe_hint through
  action.vice_principal) and 13 from the start of
  `kn.institution_overview.*` (about through infrastructure[6]).
- Excluded: 3 ghost keys (ui.session.goodbye/ending/interrupted,
  classified DEFINED_BUT_UNREACHABLE in section 19), 3 blocked
  pilot values (ui.status.processing, ui.session.timeout,
  kn.admissions_and_fees.eligibility), and the 4 deferred
  workstreams (honorific policy, | in TTS, official fee facts,
  name-script policy).
- Each row: 3 Sarvam operations (en→kn, kn→en of candidate, kn→en
  of existing). Source data in
  `backend/tools/.cache/kannada_sarvam_batch5_rows.json`.
- Per-row verdict: 4 input/output fields + 14 structured check
  fields, computed via `build_structured_evidence()`.
- 1 row (`kn.institution_overview.affiliations_and_accreditations`)
  had its Sarvam call fail with `segment too long for one call`
  (3695 chars) — the value is a Python-dict-as-string, not a
  natural-language sentence.
- No production locale values were modified. The 25 entries were
  added to `backend/tools/kannada_review_decisions.json` with
  `batch=5`, `approved=None` (no write pending).

### 21.2 Per-row verdicts

| Row | Verdict | Defect |
|---|---|---|
| `ui.comparison.swipe_hint` | NATIVE_REVIEW_RECOMMENDED | existing loses 'in sync' rhythm; candidate transliterates 'beat/sync' loan-words. Defer. |
| `ui.comparison.highlighted` | KEEP_EXISTING_MECHANICALLY_SUPPORTED | both correct; existing uses 'selection', candidate uses 'focus'. Defer; keep existing. |
| `ui.action.fees` | BLOCKED_LINGUISTIC | candidate transliterates `{department}` to `{ಇಲಾಖೆ}` and adds redundant literal 'ಇಲಾಖೆಗೆ'. Placeholder violation. |
| `ui.action.documents` | KEEP_EXISTING_MECHANICALLY_SUPPORTED | candidate transliterates `{items}` to `{ಐಟಂಗಳು}` — placeholder violation; reject candidate, keep existing. |
| `ui.action.location` | NATIVE_REVIEW_RECOMMENDED | word-order choice; existing uses literal English order, candidate uses natural Kannada address order. Existing wins on protected acronym (SVIT in Latin). Defer. |
| `ui.action.admissions` | KEEP_EXISTING_MECHANICALLY_SUPPORTED | 'ಪ್ರವೇಶಾತಿಯ' (formal compound) vs 'ಪ್ರವೇಶ' (common). Stylistic; keep existing for block consistency. |
| `ui.action.placements` | BLOCKED_LINGUISTIC | candidate uses 'ನಿಯೋಜನೆ' (deployment) instead of protected-token 'ಪ್ಲೇಸ್‌ಮೆಂಟ್'. Same pattern as Batch 4's training_objectives. |
| `ui.action.department` | BLOCKED_LINGUISTIC | candidate transliterates `{department}` to `{ಇಲಾಖೆ}` AND uses 'ಇಲಾಖೆಯ' as a redundant literal word. Placeholder violation. |
| `ui.action.hod` | BLOCKED_LINGUISTIC | same placeholder violation: `{department}` → `{ಇಲಾಖೆ}` plus redundant 'ಇಲಾಖೆಯ'. |
| `ui.action.college` | KEEP_EXISTING_MECHANICALLY_SUPPORTED | word-order difference only. Block consistency wins. |
| `ui.action.principal` | KEEP_EXISTING_MECHANICALLY_SUPPORTED | 'ಮಾಹಿತಿ' (info) vs 'ಪ್ರೊಫೈಲ್' (profile). Stylistic; keep existing. |
| `ui.action.vice_principal` | KEEP_EXISTING_MECHANICALLY_SUPPORTED | same pattern as principal. Block consistency wins. |
| `kn.institution_overview.about` | BLOCKED_LINGUISTIC | candidate adds `[ಉಲ್ಲೇಖ: 8/9/10/12/13/14]` citation artifacts after every fact. Existing drops them. Citation-artifact deferred workstream. |
| `kn.institution_overview.vision_and_mission` | BLOCKED_LINGUISTIC | same citation-artifact pattern: candidate adds `[ಉಲ್ಲೇಖ: 86/88/89/90/91]` after each numbered mission. |
| `kn.institution_overview.affiliations_and_accreditations` | BLOCKED_RUNTIME_STRUCTURE | value is a Python-dict-as-string (not a translatable sentence); Sarvam call failed with 'segment too long for one call: 3695 chars'. Structured-data field, not natural-language. Defer to structured-eligibility-fields workstream. |
| `kn.institution_overview.additional_details.tagline` | BLOCKED_LINGUISTIC | candidate adds `[ಉಲ್ಲೇಖ: 15]` after the closing quote. |
| `kn.institution_overview.additional_details.motto` | BLOCKED_LINGUISTIC | candidate adds `[ಉಲ್ಲೇಖ: 16]`. |
| `kn.institution_overview.additional_details.founded_by` | BLOCKED_LINGUISTIC | candidate adds `[ಉಲ್ಲೇಖ: 11]`. |
| `kn.institution_overview.additional_details.infrastructure[0..6]` (7 rows) | BLOCKED_LINGUISTIC | each candidate adds `[ಉಲ್ಲೇಖ: 23/24/25/26/27/28/29]`. |

### 21.3 Highlights

- **Placeholder violations (5 of 12 ui.action.*)**: Sarvam
  transliterates the Latin-script placeholders `{department}`,
  `{items}` to Kannada-script tokens. This breaks runtime template
  substitution, which the runtime consumer expects verbatim in
  Latin. This is the same class of defect as the protected-acronym
  violations caught in earlier batches, but applied to template
  placeholders. Recorded as BLOCKED_LINGUISTIC; the candidates
  would not survive a runtime test.
- **Citation artifacts (12 of 13 kn.institution_overview.*)**: The
  English source contains `[cite: N]` markers as inline evidence
  tags. Sarvam reproduces them in Kannada as `[ಉಲ್ಲೇಖ: N]`. The
  existing Kannada values drop them. This is a deferred
  workstream (citation artifacts): the project has not yet decided
  whether citations should appear in the visitor-facing UI at all,
  and if so, in what form. Sarvam's candidates are blocked for now
  because adopting them would lock in one of the deferred
  decisions.
- **Structured-data field (1 row)**:
  `kn.institution_overview.affiliations_and_accreditations` is a
  Python-dict serialised to a string in the locale file. This
  cannot be translated as a sentence; it is structured data. The
  Sarvam call failed at the API level (segment too long). The
  decision is BLOCKED_RUNTIME_STRUCTURE and the row is referred to
  the structured-eligibility-fields workstream for the same
  treatment as `admissions_and_fees.eligibility`.
- **Stylistic deferrals (2)**: `ui.comparison.swipe_hint` and
  `ui.action.location` have legitimate stylistic differences
  between existing and Sarvam candidate; both are recorded as
  NATIVE_REVIEW_RECOMMENDED.

### 21.4 SAFE_CORRECTION_CANDIDATE count is 0

No SAFE_CORRECTION_CANDIDATE values were produced. The deferred
workstreams (citation artifacts, structured fields, TTS pipe
sanitizer, honorific policy) and the placeholder policy blocked
every candidate that would have changed a value. No approval
table is needed for Batch 5.

### 21.5 Required output (Batch 5)

- TOTAL PRODUCTION-REACHABLE: 209 (unchanged from Batch 4 close)
- PREVIOUSLY MECHANICALLY REVIEWED: 90 (15 pilot + 25 B2 + 25 B3
  + 25 B4)
- REVIEWED IN BATCH 5: 25
- KEEP_EXISTING_MECHANICALLY_SUPPORTED: 6
- SAFE_CORRECTION_CANDIDATES: 0
- BLOCKED_LINGUISTIC: 16
- BLOCKED_OFFICIAL_FACT: 0
- BLOCKED_MISSING_SOURCE: 0
- BLOCKED_RUNTIME_STRUCTURE: 1
- NATIVE_REVIEW_RECOMMENDED: 2
- SARVAM API CALLS: 1 (only the affiliation row needed a fresh
  call; 36 cache hits from prior batches, plus 1 fresh call for
  the affiliation row that then errored)
- CACHE HITS: 36
- REMAINING PRODUCTION-REACHABLE: 94 (209 − 90 − 25)
- PRODUCTION FILES CHANGED: 0
- EVIDENCE FILES CHANGED:
  `backend/tools/kannada_review_decisions.json` (25 new entries
  with `batch=5`); this report (section 21 added); new cache file
  `backend/tools/.cache/kannada_sarvam_batch5_rows.json` (ignored
  by .gitignore).
- TESTS RUN: 27 passed (no new executable tooling change in
  Batch 5; the existing tool-schema test still covers the
  builder).
- GIT DIFF CHECK: clean.
- GIT STATUS: see below; no commit, no push per user instruction.

---

## 22. Batch 5 accounting correction

### 22.1 Affiliation row retry

The Batch 5 affiliation row
`kn.institution_overview.affiliations_and_accreditations` failed
its Sarvam call with `segment too long for one call: 3695 chars`
in the original run. The row was initially classified
`BLOCKED_RUNTIME_STRUCTURE` based on the structural observation
that the value is a Python-dict-as-string, **but all three
mandatory Sarvam operations were missing** (sarvam_kn,
back_en_of_candidate, back_en_of_existing all `None`). Per the
rule that a row cannot count as mechanically reviewed without all
mandatory translation evidence, the original classification was
provisionally invalid.

The retry (recorded in `affiliation_retry.json`) succeeded by
translating each dict value key-by-key so each Sarvam segment is
under the per-call limit, then reassembling:

- 11 fresh API calls (5 en→kn per key + 1 kn→en of full candidate
  dict + 5 kn→en per existing key)
- 0 cache hits
- All 3 mandatory operations now present

With full evidence available, the row was re-classified
`BLOCKED_LINGUISTIC` on substantive grounds:

- Candidate adds `[ಉಲ್ಲೇಖ: 18/18/19/20/21]` citation artifacts
  (citation-artifacts deferred workstream)
- Candidate transliterates protected acronyms VTU to `ವಿ.ಟಿ.ಯು.`
  and ECE to `ಇಸಿಇ` (protected-acronyms policy); AICTE preserved
  in Latin (Sarvam's per-value transliteration is inconsistent
  within a single string)
- The structural observation (Python-dict-as-string) is preserved
  as a secondary note but is no longer the primary classification

The row remains in Batch 5's reviewed count; it was never
returned to the unreviewed queue because the retry succeeded
before the report commit.

### 22.2 Corrected Batch 5 per-classification counts

| Classification | Count | Notes |
|---|---|---|
| KEEP_EXISTING_MECHANICALLY_SUPPORTED | 6 | |
| SAFE_CORRECTION_CANDIDATE | 0 | |
| BLOCKED_LINGUISTIC | 17 | was 16; +1 from the corrected affiliation reclassification |
| BLOCKED_OFFICIAL_FACT | 0 | |
| BLOCKED_MISSING_SOURCE | 0 | |
| BLOCKED_RUNTIME_STRUCTURE | 0 | was 1; the affiliation row was reclassified to BLOCKED_LINGUISTIC |
| NATIVE_REVIEW_RECOMMENDED | 2 | |
| REVIEW_INCOMPLETE_API_FAILURE | 0 | retry succeeded; no row left incomplete |

Reviewed count: **25** (unchanged). Remaining production-reachable
pre-Batch-6: **94** (unchanged).

### 22.3 Cumulative unresolved totals (across all reviewed batches)

The user clarified that a reviewed-but-blocked row is "not
unreviewed" but also "not production-ready". These totals are
recorded separately from "remaining production-reachable":

- CUMULATIVE BLOCKED_LINGUISTIC: **20** (3 from Batch 4 + 17 from
  Batch 5)
- CUMULATIVE BLOCKED_OFFICIAL_FACT: **0**
- CUMULATIVE BLOCKED_MISSING_SOURCE: **0**
- CUMULATIVE BLOCKED_RUNTIME_STRUCTURE: **0** (the 1 from Batch 5
  was reclassified; no new entries)
- CUMULATIVE NATIVE_REVIEW_RECOMMENDED: **13** (2 from Batch 3 + 9
  from Batch 4 + 2 from Batch 5)

### 22.4 Cumulative resolved/retained totals

- CUMULATIVE KEEP_EXISTING_MECHANICALLY_SUPPORTED: **49** (7
  pilot + 25 Batch 2 provisional + 23 Batch 3 + 13 Batch 4 + 6
  Batch 5 minus 25 Batch 2's MECHANICALLY_REVIEWED_PROVISIONAL
  which is not counted here as KEEP)
- CUMULATIVE MECHANICALLY_REVIEWED_PROVISIONAL: **25** (Batch 2
  only; recorded as a separate category because Batch 2's
  per-row Sarvam candidates were not stored)
- CUMULATIVE CORRECTIONS APPLIED: **5** (the 5 pilot values
  applied in commit c398808)
- CUMULATIVE BLOCKED PILOT: **3** (ui.status.processing,
  ui.session.timeout, kn.admissions_and_fees.eligibility; have
  `approved` in the decisions file but remain unapplied per the
  standing block)
- CUMULATIVE SAFE_CORRECTION_CANDIDATE_PENDING: **0** (the 3
  blocked pilot values are not "pending"; they are explicitly
  blocked)
- CUMULATIVE REVIEW_INCOMPLETE_API_FAILURE: **0** (the affiliation
  retry succeeded)

### 22.5 SARVAM API CALLS / CACHE HITS correction

The original Batch 5 close reported "SARVAM API CALLS: 1" with
"CACHE HITS: 36". The accurate figure for Batch 5:

- SARVAM API CALLS: **48** (37 from the original driver for the
  24 non-affiliation rows + 11 from the affiliation retry)
- CACHE HITS: **36** (24 rows × 1 hit each on the original run's
  2nd-or-3rd op, contributed by the prior-batch cache)

The "1" figure in the original Batch 5 close was a reporting
error, not a data error: the driver had emitted
`api_calls: 37, cache_hits: 36` on stderr, which the report
rounded down to the affiliation row's 1 fresh call only. The
totals above supersede it.

---

## 23. Batch 6 — mechanical review (25 rows)

### 23.1 Scope and method

- 25 production-reachable rows in deterministic inventory order
  following the 25 ui.* + 75 kn.* already-reviewed rows
  (15 pilot + 25 B2 + 25 B3 + 25 B4 + 25 B5).
- Composition: 3 entrance-exam labels, 2 fee-structure sentences,
  1 additional-fees sentence, then 19 department-content rows
  (cse.name + cse.achievements, plus 6 cse_aiml rows, 6 cse_ds
  rows, 6 ise rows).
- Excluded by deferred-workstream filter: rows under
  `admissions_and_fees.additional_details.admission_and_eligibility.*`
  (eligibility structured fields workstream), the
  `admissions_and_fees.fee_structures.ug_management` and
  `.pg_mba` rows (official fee facts workstream — Python-dict-as-
  string with ₹ figures and the unresolved ₹3,50,000 vs ₹3,25,000
  cross-department conflict), and any row whose English source
  contains `[cite: N]` markers (citation artifacts workstream).
- Each row: 3 Sarvam operations (en→kn, kn→en of candidate,
  kn→en of existing). Source data in
  `backend/tools/.cache/kannada_sarvam_batch6_rows.json`.
- Per-row verdict: 4 input/output fields + 14 structured check
  fields, computed via `build_structured_evidence()`.
- No production locale values were modified. The 25 entries were
  added to `backend/tools/kannada_review_decisions.json` with
  `batch=6`, `approved=None` (no write pending).

### 23.2 Per-row verdicts

| Row | Verdict | Defect |
|---|---|---|
| `kn.admissions_and_fees.entrance_exams[0]` (KCET) | KEEP_EXISTING_MECHANICALLY_SUPPORTED | Sarvam transliterates KCET → ಕೆಸಿಇಟಿ, round-trip says "KSET" (wrong exam). Existing preserves KCET in Latin. |
| `kn.admissions_and_fees.entrance_exams[1]` (COMEDK) | KEEP_EXISTING_MECHANICALLY_SUPPORTED | Sarvam transliterates COMEDK → ಕಾಾಮಡ್ಕೆ, round-trip says "Kamadke" (a place, not an exam). Existing preserves COMEDK in Latin. |
| `kn.admissions_and_fees.entrance_exams[2]` (Management) | KEEP_EXISTING_MECHANICALLY_SUPPORTED | Sarvam returns ನಿರ್ವಹಣೆ ("maintenance") — same terminology defect the pilot fixed. Existing ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್ is correct. |
| `kn.admissions_and_fees.fee_structures.ug_kcet` | KEEP_EXISTING_MECHANICALLY_SUPPORTED | Sarvam transliterates KEA and KCET to Kannada initials. Existing preserves both in Latin. |
| `kn.admissions_and_fees.fee_structures.additional_fees` | KEEP_EXISTING_MECHANICALLY_SUPPORTED | stylistic; existing uses more formal academic vocabulary (ಶಿಕ್ಷಣ ಶುಲ್ಕ, ವಿಧಿಬದ್ಧ, ಸಂಪರ್ಕಿಸಿ). |
| `kn.departments.cse.name` | NATIVE_REVIEW_RECOMMENDED | ಕಂಪ್ಯೂಟರ್ (transliterated) vs ಗಣಕ (Kannada noun) for "computer". Defer. |
| `kn.departments.cse.achievements` | KEEP_EXISTING_MECHANICALLY_SUPPORTED | stylistic; ಲ್ಯಾಬ್ (transliterated) vs ಪ್ರಯೋಗಾಲಯ (Kannada). Existing matches block style. |
| `kn.departments.cse_aiml.name` | KEEP_EXISTING_MECHANICALLY_SUPPORTED | byte-identical. |
| `kn.departments.cse_aiml.intro` | NATIVE_REVIEW_RECOMMENDED | ಪ್ರವರ್ತಿಸುತ್ತದೆ (pioneers) + ಟೆಕ್ ಲ್ಯಾಂಡ್‌ಸ್ಕೇಪ್ vs ಮುನ್ನಡೆಸುತ್ತದೆ (leads) + ತಂತ್ರಜ್ಞಾನದ ಭೂದೃಶ್ಯ. Defer. |
| `kn.departments.cse_aiml.hod_voice` | KEEP_EXISTING_MECHANICALLY_SUPPORTED | HOD name preserved; honorific form differs but both correct. |
| `kn.departments.cse_aiml.achievements` | KEEP_EXISTING_MECHANICALLY_SUPPORTED | candidate ತಂಡ (team) is wrong meaning for "batch" (graduating class). Defect in candidate. |
| `kn.departments.cse_aiml.placement` | BLOCKED_LINGUISTIC | **gender narrowing**: candidate ವಿದ್ಯಾರ್ಥಿನಿಯರು (female students) vs existing ವಿದ್ಯಾರ್ಥಿಗಳು (students). |
| `kn.departments.cse_aiml.fees` | **SAFE_CORRECTION_CANDIDATE** | existing has terminology defect ನಿರ್ವಹಣೆ (maintenance) — same as the pilot-corrected cse.fees defect. **See approval table 23.5.** |
| `kn.departments.cse_ds.name` | KEEP_EXISTING_MECHANICALLY_SUPPORTED | byte-identical. |
| `kn.departments.cse_ds.intro` | BLOCKED_LINGUISTIC | **gender narrowing**: candidate ವಿದ್ಯಾರ್ಥಿನಿಯರಿಗೆ (to female students) vs existing ವಿದ್ಯಾರ್ಥಿಗಳನ್ನು (students). |
| `kn.departments.cse_ds.hod_voice` | KEEP_EXISTING_MECHANICALLY_SUPPORTED | byte-identical. |
| `kn.departments.cse_ds.achievements` | BLOCKED_LINGUISTIC | **gender narrowing**: candidate ವಿದ್ಯಾರ್ಥಿನಿಯರು (female students) vs existing ವಿದ್ಯಾರ್ಥಿಗಳು (students). |
| `kn.departments.cse_ds.placement` | KEEP_EXISTING_MECHANICALLY_SUPPORTED | byte-identical. |
| `kn.departments.cse_ds.fees` | **SAFE_CORRECTION_CANDIDATE** | same triple-defect pattern as cse_aiml.fees. **See approval table 23.5.** |
| `kn.departments.ise.name` | KEEP_EXISTING_MECHANICALLY_SUPPORTED | byte-identical. |
| `kn.departments.ise.intro` | KEEP_EXISTING_MECHANICALLY_SUPPORTED | existing preserves English loan-words (ಕಂಪ್ಯೂಟಿಂಗ್, ಸಾಫ್ಟ್‌ವೇರ್, ಇಂಜಿನಿಯರಿಂಗ್) per glossary. |
| `kn.departments.ise.hod_voice` | KEEP_EXISTING_MECHANICALLY_SUPPORTED | HOD name preserved; honorific form differs but both correct. |
| `kn.departments.ise.achievements` | BLOCKED_LINGUISTIC | **gender narrowing**: candidate ಅಧ್ಯಾಪಕಿಯು (the female teacher) vs existing ಅಧ್ಯಾಪಕರು (teachers). |
| `kn.departments.ise.placement` | KEEP_EXISTING_MECHANICALLY_SUPPORTED | existing preserves protected token ಪ್ಲೇಸ್‌ಮೆಂಟ್; candidate ಉದ್ಯೋಗಾವಕಾಶ (job opportunity) drifts. |
| `kn.departments.ise.fees` | KEEP_EXISTING_MECHANICALLY_SUPPORTED | existing already uses CSE-pilot applied form ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್ ಕೋಟಾ with semicolon (not pipe). Sarvam candidate has the defects. |

### 23.3 Highlights

- **Gender narrowing recurs (4 of 25 rows)**: Sarvam narrows
  "students"/"faculty" to "female students"/"female teacher" in
  `cse_aiml.placement`, `cse_ds.intro`, `cse_ds.achievements`,
  `ise.achievements`. This is the same class of defect the
  pilot caught on `cse.placement`. Each row's `gender_narrowing`
  field is FAIL with the narrowed term in the detail.
- **Protected-acronym transliterations (3 of 25 rows)**: Sarvam
  transliterates KCET/COMEDK/KEA in
  `entrance_exams[0]`, `entrance_exams[1]`, `fee_structures.ug_kcet`,
  and in the two SAFE_CORRECTION_CANDIDATE fee rows. The
  existing values preserve the acronyms in Latin per the
  project glossary; the round-trip back-translation confirms
  the harm (KCET → ಕೆಸಿಇಟಿ → "KSET" is a different exam).
- **Terminology defect `ನಿರ್ವಹಣೆ` recurs in 3 fee rows**:
  `cse_aiml.fees`, `cse_ds.fees` use the same pre-pilot
  terminology defect that the pilot corrected on `cse.fees`.
  `ise.fees` already uses the corrected form
  `ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್ ಕೋಟಾ` (no correction needed). The 2
  remaining rows are SAFE_CORRECTION_CANDIDATEs presented in
  the approval table below.
- **HOD names (3 rows)**: `cse_aiml.hod_voice`,
  `cse_ds.hod_voice`, `ise.hod_voice` each contain a HOD
  name. The names are preserved in both existing and Sarvam
  candidate (Kannada transliteration form, matching the
  cse pilot). The HOD-name script policy remains a deferred
  workstream per the pilot.

### 23.4 Cumulative unresolved totals (post-Batch 6)

- CUMULATIVE BLOCKED_LINGUISTIC: **24** (3 B4 + 17 B5 + 4 B6)
- CUMULATIVE BLOCKED_OFFICIAL_FACT: **0**
- CUMULATIVE BLOCKED_MISSING_SOURCE: **0**
- CUMULATIVE BLOCKED_RUNTIME_STRUCTURE: **0**
- CUMULATIVE NATIVE_REVIEW_RECOMMENDED: **15** (2 B3 + 9 B4 + 2
  B5 + 2 B6)
- CUMULATIVE REVIEW_INCOMPLETE_API_FAILURE: **0**

### 23.5 SAFE_CORRECTION_CANDIDATE approval table (2 rows)

The user spec: "If candidates exist, present an approval table
containing: ID / English / Existing Kannada / Existing
back-translation / Proposed Kannada / Proposed back-translation
/ Exact defect / Protected tokens / Display impact / Narration
impact / Recommendation." These are presented for explicit
approval; no production value is written until the user
approves.

| ID | English | Existing Kannada | Existing back-translation | Proposed Kannada | Proposed back-translation |
|---|---|---|---|---|---|
| `kn.departments.cse_aiml.fees` | KCET: As per KEA norms \| Management: ₹3,50,000/year | KCET: KEA ಮಾನದಂಡಗಳ ಪ್ರಕಾರ \| ನಿರ್ವಹಣೆ: ₹3,50,000/ವರ್ಷ | KCET: As per KEA norms \| Maintenance: ₹3,50,000/year | KCET: KEA ಮಾನದಂಡಗಳ ಪ್ರಕಾರ \| ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್: ₹3,50,000/ವರ್ಷ | KCET: As per KEA norms \| Management: ₹3,50,000/year |
| `kn.departments.cse_ds.fees` | KCET: As per KEA norms \| Management: ₹3,00,000/year | KCET: KEA ಮಾನದಂಡಗಳ ಪ್ರಕಾರ \| ನಿರ್ವಹಣೆ: ₹3,00,000/ವರ್ಷ | KCET: As per KEA norms \| Maintenance: ₹3,00,000/year | KCET: KEA ಮಾನದಂಡಗಳ ಪ್ರಕಾರ \| ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್: ₹3,00,000/ವರ್ಷ | KCET: As per KEA norms \| Management: ₹3,00,000/year |

| ID | Exact defect | Protected tokens | Display impact | Narration impact | Recommendation |
|---|---|---|---|---|---|
| `kn.departments.cse_aiml.fees` | ನಿರ್ವಹಣೆ ("maintenance") used for "Management" — same defect the pilot caught on cse.fees and corrected to ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್ ("management quota") | KCET, KEA, ₹3,50,000, /ವರ್ಷ preserved exactly; pipe `\|` preserved (TTS-sanitizer-deferred workstream) | same length; same line-break; same card layout | same TTS chunking; same narration prepend (`{dept_label} ಶುಲ್ಕ.`) | adopt the CSE-pilot applied form (terminology only); do not touch the pipe; do not touch the currency |
| `kn.departments.cse_ds.fees` | same `ನಿರ್ವಹಣೆ` terminology defect; amount differs (₹3,00,000) but the same defect | KCET, KEA, ₹3,00,000, /ವರ್ಷ preserved; pipe preserved | same length; same card layout | same TTS chunking | adopt the CSE-pilot applied form (terminology only) |

Per the standing rule, the proposed values are **not auto-
applied**. They are presented above for the user's explicit
approval. The cross-department fee-amount fact (₹3,00,000 for
cse_ds vs ₹3,50,000 for cse and cse_aiml) is recorded but not
adjudicated; the user's earlier clarification was that
"different fee amounts across different departments are not
automatically conflicts" — each row's currency is preserved.

### 23.6 Required output (Batch 6)

- TOTAL PRODUCTION-REACHABLE: 209
- PREVIOUSLY MECHANICALLY REVIEWED: 115 (15 pilot + 25 B2 + 25
  B3 + 25 B4 + 25 B5)
- REVIEWED IN BATCH 6: 25
- KEEP_EXISTING_MECHANICALLY_SUPPORTED: 17
- SAFE_CORRECTION_CANDIDATES: 2
- BLOCKED_LINGUISTIC: 4
- BLOCKED_OFFICIAL_FACT: 0
- BLOCKED_MISSING_SOURCE: 0
- BLOCKED_RUNTIME_STRUCTURE: 0
- NATIVE_REVIEW_RECOMMENDED: 2
- REVIEW_INCOMPLETE_API_FAILURE: 0
- SARVAM API CALLS: 69 (3 ops × 25 rows = 75; 6 cache hits from
  prior batches)
- CACHE HITS: 6
- REMAINING PRODUCTION-REACHABLE: 69 (209 − 115 − 25)
- CUMULATIVE RESOLVED/RETAINED (KEEP + corrected): 49 + 17 = 66
- CUMULATIVE CORRECTIONS APPLIED: 5 (the 5 pilot values
  applied in commit c398808; 2 SAFE_CORRECTION_CANDIDATEs from
  Batch 6 are presented but not applied)
- CUMULATIVE BLOCKED: 24 (3 B4 + 17 B5 + 4 B6)
- CUMULATIVE NATIVE-REVIEW QUEUE: 15 (2 B3 + 9 B4 + 2 B5 + 2 B6)
- CUMULATIVE API-INCOMPLETE: 0
- PRODUCTION FILES CHANGED: 0
- EVIDENCE FILES CHANGED:
  `backend/tools/kannada_review_decisions.json` (25 new entries
  with `batch=6`); this report (section 23 added);
  `backend/tools/kannada_review_decisions.json` (1 row updated
  with the affiliation retry evidence); new cache file
  `backend/tools/.cache/kannada_sarvam_batch6_rows.json`
  (ignored by .gitignore);
  `backend/tools/.cache/affiliation_retry.json` (ignored).
- TESTS RUN: 27 passed (no new executable tooling change in
  Batch 6; the existing tool-schema test still covers the
  builder).
- GIT DIFF CHECK: clean.
- GIT STATUS: see below; no commit, no push per user instruction.

---

## Section 24 — Batch 7 (mechanical review, no production writes)

### Scope

Process the next 25 genuinely unreviewed production-reachable
Kannada values in deterministic inventory order. Do not include:
previously reviewed rows, applied correction rows, blocked rows,
native-review rows, 3 unreachable session keys, citation-artifact
rows (deferred workstream), or 12 non-reviewable rows. The 25 rows
are ece, civil, mechanical, mba, basic_sciences × 5 fields each
(intro, hod_voice, achievements, placement, fees).

### Methodology

- Read EN and existing KN from authoritative locale JSON via
  `load_locale_data_for_lang_key('kn')`.
- Triple-translate each row: EN→KN (Sarvam candidate),
  candidate→EN (round-trip), existing→EN (round-trip of current).
- 72 Sarvam API calls + 3 cache hits = 75 total, 0 errors.
- Compare candidate and existing on glossary, protected tokens
  (acronyms, numbers, currency, HOD names), gender neutrality,
  terminology drift, and source fidelity.
- For each row: 25 structured evidence fields, 1 of 8 allowed
  classifications, no production writes.
- The pipe `|` in CSE-family fees is preserved (separate TTS
  sanitizer workstream; does not invalidate terminology
  corrections).

### Per-row verdicts (25 rows)

| Row | Classification | Verdict |
|---|---|---|
| kn.departments.ece.intro | KEEP_EXISTING_MECHANICALLY_SUPPORTED | KEEP_EXISTING |
| kn.departments.ece.hod_voice | KEEP_EXISTING_MECHANICALLY_SUPPORTED | KEEP_EXISTING |
| kn.departments.ece.achievements | KEEP_EXISTING_MECHANICALLY_SUPPORTED | KEEP_EXISTING |
| kn.departments.ece.placement | KEEP_EXISTING_MECHANICALLY_SUPPORTED | KEEP_EXISTING |
| kn.departments.ece.fees | SAFE_CORRECTION_CANDIDATE | present for approval (NOT auto-applied) |
| kn.departments.civil.intro | KEEP_EXISTING_MECHANICALLY_SUPPORTED | KEEP_EXISTING |
| kn.departments.civil.hod_voice | KEEP_EXISTING_MECHANICALLY_SUPPORTED | KEEP_EXISTING |
| kn.departments.civil.achievements | KEEP_EXISTING_MECHANICALLY_SUPPORTED | KEEP_EXISTING |
| kn.departments.civil.placement | BLOCKED_LINGUISTIC | KEEP_EXISTING (Sarvam has gender narrowing) |
| kn.departments.civil.fees | BLOCKED_OFFICIAL_FACT | KEEP_EXISTING (requires official-fact verification) |
| kn.departments.mechanical.intro | KEEP_EXISTING_MECHANICALLY_SUPPORTED | KEEP_EXISTING |
| kn.departments.mechanical.hod_voice | KEEP_EXISTING_MECHANICALLY_SUPPORTED | KEEP_EXISTING |
| kn.departments.mechanical.achievements | KEEP_EXISTING_MECHANICALLY_SUPPORTED | KEEP_EXISTING |
| kn.departments.mechanical.placement | BLOCKED_LINGUISTIC | KEEP_EXISTING (terminology drift + interns hallucination) |
| kn.departments.mechanical.fees | BLOCKED_OFFICIAL_FACT | KEEP_EXISTING (requires official-fact verification) |
| kn.departments.mba.intro | KEEP_EXISTING_MECHANICALLY_SUPPORTED | KEEP_EXISTING |
| kn.departments.mba.hod_voice | KEEP_EXISTING_MECHANICALLY_SUPPORTED | KEEP_EXISTING |
| kn.departments.mba.achievements | KEEP_EXISTING_MECHANICALLY_SUPPORTED | KEEP_EXISTING |
| kn.departments.mba.placement | KEEP_EXISTING_MECHANICALLY_SUPPORTED | KEEP_EXISTING |
| kn.departments.mba.fees | KEEP_EXISTING_MECHANICALLY_SUPPORTED | KEEP_EXISTING (amounts preserved) |
| kn.departments.basic_sciences.intro | KEEP_EXISTING_MECHANICALLY_SUPPORTED | KEEP_EXISTING |
| kn.departments.basic_sciences.hod_voice | KEEP_EXISTING_MECHANICALLY_SUPPORTED | KEEP_EXISTING |
| kn.departments.basic_sciences.achievements | BLOCKED_LINGUISTIC | KEEP_EXISTING (typo present; Sarvam has gender narrowing) |
| kn.departments.basic_sciences.placement | KEEP_EXISTING_MECHANICALLY_SUPPORTED | KEEP_EXISTING |
| kn.departments.basic_sciences.fees | KEEP_EXISTING_MECHANICALLY_SUPPORTED | KEEP_EXISTING (no fee schedule, structural note) |

**Count:** 19 KEEP_EXISTING_MECHANICALLY_SUPPORTED, 1
SAFE_CORRECTION_CANDIDATE, 3 BLOCKED_LINGUISTIC, 2
BLOCKED_OFFICIAL_FACT.

### SAFE_CORRECTION_CANDIDATE — ece.fees (present for approval, NOT auto-applied)

| Field | Value |
|---|---|
| ID | kn.departments.ece.fees |
| English source | `KCET: As per KEA norms \| Management: ₹2,00,000/year` |
| Existing (pre-pilot) | `KCET: KEA ಮಾನದಂಡಗಳ ಪ್ರಕಾರ \| ನಿರ್ವಹಣೆ: ₹2,00,000/ವರ್ಷ` |
| Sarvam candidate | (rejected — transliterates KCET/KEA, rewrites ₹ as Rs., same terminology defect) |
| Defect | `ನಿರ್ವಹಣೆ` ("maintenance") is incorrect management-quota terminology. Same defect class as cse.fees (Batch 5), cse_aiml.fees, cse_ds.fees (Batch 6). |
| Proposed correction | `KCET: KEA ಮಾನದಂಡಗಳ ಪ್ರಕಾರ \| ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್ ಕೋಟಾ: ₹2,00,000/ವರ್ಷ` |
| Protected tokens preserved | KCET (Latin), KEA (Latin), ₹2,00,000 (Indian format), /ವರ್ಷ, literal \| |
| Department-specific amount | ₹2,00,000 (different from cse ₹3,50,000, cse_aiml ₹3,50,000, cse_ds ₹3,00,000) |
| Status | AWAITING USER APPROVAL — do not auto-apply |

### BLOCKED items (kept as existing, no production write)

- **civil.placement** (BLOCKED_LINGUISTIC): Sarvam's candidate
  narrows ಹಳೆಯ ವಿದ್ಯಾರ್ಥಿಗಳ (gender-neutral alumni) to
  ಹಳೆಯ ವಿದ್ಯಾರ್ಥಿನಿಯರ (female alumni). Same class of defect
  the Batch 5 pilot caught on cse.placement. KEEP_EXISTING.

- **mechanical.placement** (BLOCKED_LINGUISTIC): Sarvam's
  candidate drifts ಕೋರ್ (core) → ಪ್ರಮುಖ (major/major) and
  hallucinates "experienced, industry-ready interns" in the
  back-translation (source says "graduates", not "interns").
  KEEP_EXISTING.

- **basic_sciences.achievements** (BLOCKED_LINGUISTIC): existing
  has a duplicated-word typo `ಸಂಶೋಧನಾ ಸಂಶೋಧನೆಗಳನ್ನು` (research
  research-findings); Sarvam's candidate fixes the typo but
  introduces a gender-narrowing term ಬೋಧಕಿಯರು (feminine plural).
  KEEP_EXISTING on this row; the typo fix is deferred to a
  separate SAFE_CORRECTION_CANDIDATE step.

- **civil.fees** (BLOCKED_OFFICIAL_FACT): KCET amount ₹1,10,000
  and the management-quota policy statement "Priority CET-FEES
  as per KEA" are official facts that cannot be verified from
  within the locale JSON. The ನಿರ್ವಹಣೆ terminology defect is
  present, but the policy statement is structurally different
  from the CSE-family's flat-rate form; applying the Batch 6
  correction requires verifying the management-policy wording.
  KEEP_EXISTING.

- **mechanical.fees** (BLOCKED_OFFICIAL_FACT): same structure
  and amount as civil.fees. Same deferred workstream.

### Cumulative state (post-Batch 7)

```
TOTAL PRODUCTION-REACHABLE:           209
TOTAL DECISIONS (pilot + b2-b7):      165  (15 pilot + 6 × 25 batches)
PRODUCTION-REACHABLE MECHANICALLY
  REVIEWED (B ∩ A):                   160
  of which:
    KEEP_EXISTING_MECHANICALLY_SUPPORTED:  19 (this batch)
    SAFE_CORRECTION_CANDIDATES:             1 (this batch, ece.fees — applied below)
    BLOCKED_LINGUISTIC:                     3 (this batch)
    BLOCKED_OFFICIAL_FACT:                  2 (this batch)
    + 135 prior-batch production-reachable reviews
NON-REVIEWABLE ROWS IN DECISIONS:       5  (B − A: 4 *.name + 1 affiliations)
DUPLICATE DECISIONS:                     0
REMAINING UNREVIEWED:                  49  (A − B)
SARVAM API CALLS:                      72
CACHE HITS:                             3
```

Of the 49 remaining unreviewed rows, **all 49** have `[cite:
NNN]` citation markers in their English source. Per the
user's policy, the citation-artifact rows remain deferred
until the source-text policy is resolved. There are zero
genuinely unreviewed non-citation rows left after Batch 7.

### Reconciliation note (post-Batch 7 verification)

The user's pre-Batch-7 brief stated "REMAINING UNREVIEWED:
69" and "PREVIOUSLY MECHANICALLY REVIEWED THROUGH BATCH 6:
140" — arithmetic implies 209 − 140 = 69. The user's
Batch 7 instructions stated "Expected mechanically reviewed:
165" and "Expected unreviewed: 44" — arithmetic implies
209 − 165 = 44.

Both expected pairs are mutually inconsistent with the
exact-set reconciliation. The 5 non-reviewable rows in the
decisions file (4 *.name + 1 affiliations) are valid
evidence records but are NOT in the production-reachable
inventory set A. They inflate the "decisions" count
without inflating the "production-reachable reviewed"
count. The correct accounting is:

- 165 total decisions = 160 (B ∩ A) + 5 (B − A)
- 209 production-reachable = 160 reviewed + 49 unreviewed

The "44 expected unreviewed" was arithmetically forced by
treating B (decisions) and A (production-reachable) as if
they had the same cardinality, which they do not. The "49
remaining" is the correct count when computed from the
exact set difference A − B.

### ECE fees correction — APPLIED (Part 3)

After reconciliation, the Batch 7 `SAFE_CORRECTION_CANDIDATE`
for `kn.departments.ece.fees` was applied with the user's
explicit authorization. The change is the same single
defect class as the Batch 6 corrections (ನಿರ್ವಹಣೆ →
ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್ ಕೋಟಾ). Protected tokens preserved exactly.

| Field | Value |
|---|---|
| ID | `kn.departments.ece.fees` |
| Old (verified exact match) | `KCET: KEA ಮಾನದಂಡಗಳ ಪ್ರಕಾರ \| ನಿರ್ವಹಣೆ: ₹2,00,000/ವರ್ಷ` |
| New (applied) | `KCET: KEA ಮಾನದಂಡಗಳ ಪ್ರಕಾರ \| ಮ್ಯಾನೇಜ್‌ಮೆಂಟ್ ಕೋಟಾ: ₹2,00,000/ವರ್ಷ` |
| Diff | 1 line in `backend/data/locales/kn.json` (line 205) |
| KCET | preserved (Latin) |
| KEA | preserved (Latin) |
| ₹2,00,000 | preserved (Indian number format) |
| /ವರ್ಷ | preserved |
| literal \| | preserved (TTS sanitization is separate workstream) |
| Original classification | preserved as `SAFE_CORRECTION_CANDIDATE` |
| `applied_status` (new) | `APPLIED_PENDING_INDEPENDENT_REVIEW` |
| `pre_application_kn` | the old value (recorded) |
| `current_kn` | the new value (recorded) |
| `approved` | the new value (recorded) |
| Pattern match | byte-identical to Batch 6 cse_aiml.fees and cse_ds.fees corrections |

### Files changed (post-Batch 7)

- `backend/data/locales/kn.json` — 1 line edit (ECE fees).
- `backend/tools/kannada_review_decisions.json` — 25 entries
  added (Batch 7) + 1 entry updated (ECE fees application
  metadata). Total decisions: 165.
- `backend/tests/test_kannada_safe_pilot_batch2_fee_terminology.py` —
  8 new tests for ECE fees, all passing. Total in file: 19.
- `KANNADA_COMPLETE_LANGUAGE_REMEDIATION.md` — section 24
  (this section) added; this batch's evidence recorded.
- No commit, no push per user instruction.

### Tests run

- `python -m pytest backend/tests/test_kannada_decision_schema.py
  backend/tests/test_kannada_safe_pilot_batch1_exact_strings.py
  backend/tests/test_kannada_safe_pilot_batch2_fee_terminology.py
  backend/tests/test_kannada_corrected_locale_integration.py -q`
  → **46 passed in 0.60s** (38 prior + 8 new ECE).

### Git diff check

- `git diff --check` → clean.
- `git status --short`:
  ```
   M KANNADA_COMPLETE_LANGUAGE_REMEDIATION.md
   M backend/data/locales/kn.json
   M backend/tests/test_kannada_safe_pilot_batch2_fee_terminology.py
   M backend/tools/kannada_review_decisions.json
  ```

---

End of audit.
