# Kannada runtime data-flow diagnosis — 2026-08-29

## Outcome

The reported Kannada is not introduced by a frontend override, stale browser cache, stale container, language-code mismatch, or fallback. The active source itself contains the reported sentence:

- English: `backend/data/locales/ui.json` → `en.welcome.name_prompt` = `Please tell me your preferred name.`
- Kannada: `backend/data/locales/ui.json` → `kn.welcome.name_prompt` = `ದಯವಿಟ್ಟು ನಿಮ್ಮ ಹೆಸರನ್ನು ತಿಳಿಸಿ.`

The first divergence is therefore the authoritative Kannada value at `kn.welcome.name_prompt`. The proposed replacement `ದಯವಿಟ್ಟು ನಿಮ್ಮನ್ನು ಯಾವ ಹೆಸರಿನಿಂದ ಕರೆಯಬೇಕೆಂದು ತಿಳಿಸಿ.` was not written because it remains `READY_FOR_NATIVE_REVIEW` and has not received Kannada-language approval.

## Running environment

| Item | Observed runtime |
|---|---|
| Frontend | Local Vite development server, Node PID 39536, `vite --host=0.0.0.0 --port 5176 --strictPort` |
| Backend | Local Python PID 40468, `python -m backend.main`, WebSocket/API on port 6969 |
| Browser | Chrome connected to localhost ports 5176 and 6969 |
| Frontend URL used for repeatable probe | `http://localhost:5176/?e2e=1`; the query only makes the language picker deterministic in headless mode |
| Docker | Not serving this application. The only compose service declared is PostgreSQL, and the Docker Desktop API was unavailable during diagnosis. |
| Git | Branch `main`, commit `2272d285b076de592b13a3f7ddeeadb626cdb77e` |

## Exact runtime path

1. `backend/data/locales/ui.json` → JSON path `kn.welcome.name_prompt`.
2. `backend/services/ui_localization.py` → `load_ui_locales()` reads that file; `ui_text()` resolves the path.
3. `backend/services/greetings.py` → `_NAME_PROMPTS_BY_LANGUAGE["Kannada"]` is initialized from `ui_text("kn", "welcome.name_prompt")`; `get_name_prompt()` returns it.
4. `backend/app/main.py` handles client action `language_selected`, calls `get_name_prompt(language)`, and creates message id `name_prompt`.
5. The same `name_prompt_text` is passed to `tts_to_base64_cached(..., utterance_kind="language_selected_name_prompt")`.
6. The backend sends a WebSocket state payload containing `messages[0].text`, `audioBase64`, and `turn_id: "name_after_language_pick"`.
7. `frontend/src/screens/ChatScreen.tsx` assigns `payload.messages` to `displayMessages`.
8. `frontend/src/components/chat/AnimatedAiMessage.tsx` renders the message text verbatim.

No translation or substitution occurs after the backend lookup.

## Browser/network evidence

The fresh-browser probe sent:

```json
{"action":"language_selected","language":"Kannada","language_code_key":"kn"}
```

It received and rendered one exact occurrence of `ದಯವಿಟ್ಟು ನಿಮ್ಮ ಹೆಸರನ್ನು ತಿಳಿಸಿ.` and zero occurrences of the unapproved candidate. The received payload included TTS audio generated from the same backend variable. The saved evidence redacts 99,344 base64 characters of audio.

- Vite served `/@vite/client` and `/src/main.tsx`.
- Vite directly requested the shared locale through `/@fs/.../backend/data/locales/ui.json?import` with `Cache-Control: no-cache`.
- `localStorage` was empty.
- `sessionStorage` contained only visitor id, canonical language `kn`, and the welcome-complete flag; it contained no localized text.
- No service worker was registered.
- A reload did not replay onboarding because the visitor session recorded welcome completion. A new browser context rendered the source value again. This is session behavior, not cached Kannada.

Evidence: `reviews/kannada-name-prompt-runtime-evidence.json` and `reviews/kannada-name-prompt-runtime-before-fix.png`.

## Kannada source inventory

| Source family | Authoritative? | Runtime reachable? | Can override this name prompt? | Finding |
|---|---:|---:|---:|---|
| `backend/data/locales/ui.json` | Yes, shared fixed UI/session copy | Yes, backend and frontend | **Yes** | Actual owner and first divergence |
| `backend/data/locales/kn.json` | Yes, institutional/content locale | Yes | No | Does not own `welcome.name_prompt` |
| `backend/data/faq_answers.json` | Yes for FAQ responses | Yes | No | Separate answer source |
| Backend content/narration JSON and localized content services | Yes for their respective cards/answers | Yes | No | Separate surfaces |
| `frontend/src/context/LanguageContext.tsx` | Mixed legacy/fixed frontend labels | Yes | No for this prompt | It does not receive or replace message id `name_prompt` |
| Frontend card/campus locale helpers | Surface-specific | Yes when their cards/routes are reached | No | Separate consumers |
| `frontend/src/data/locales/kn.json` | No; legacy copy | No production import found | No | Stale-source risk exists as repository clutter, but it is not active |
| `frontend/dist` | Build artifact | Not in the observed Vite runtime | Only if a separate static server deploys it | The pre-diagnosis bundle was older than the source. A clean build embeds the same current source value, proving the build does not create the mismatch. |
| Tests, E2E fixtures, tools, reports, caches | No | No | No | Excluded from runtime ownership |

The scan found Kannada-bearing files across several runtime surface families, but only `ui.json` owns the investigated prompt.

## Language normalization

The live selection sends canonical `kn`, and both backend and frontend use `kn` correctly. `kn-IN`, `Kannada`, and the native label are intentionally rejected by the session-state normalizers under existing tests; changing that contract would not address this incident because no key mismatch occurred. The display-name mapping in `get_name_prompt()` receives `Kannada` after canonical session normalization and resolves the Kannada entry.

## Stale-source risk

- Browser cache: low for the observed runtime. Vite serves source modules with `no-cache`, and no service worker/localized storage exists.
- Docker/container cache: none for the observed runtime because the app is not running in Docker.
- Static deployment: real but not causal here. A separately served `frontend/dist` can remain stale until rebuilt and redeployed; content-hashed bundle names prevent an updated HTML document from reusing the old chunk.
- Backend process cache: `load_ui_locales()` is process-cached and greeting dictionaries are initialized on import, so a future approved edit requires a backend restart. No edit was made in this diagnosis.
- Legacy frontend locale: repository clutter only; no active import path was found.

## Verification

- Backend focused tests: 35 passed.
- Frontend localization/session tests: 20 passed across 3 files.
- Production frontend build: passed (Vite 6.4.3, 2,273 modules).
- Clean bundle inspection: contains the current source sentence and does not contain the unapproved candidate.
- Real browser/WebSocket flow: reproduced the current source exactly in a fresh browser context.

## Fix status

No production fix was applied. The runtime is already consistent with its authoritative source; correcting the semantic omission requires changing `kn.welcome.name_prompt`, and the only supplied candidate is explicitly awaiting native Kannada approval. Once that row is approved or corrected, the minimum implementation is one source edit in `backend/data/locales/ui.json`, followed by backend restart, clean frontend build/redeploy if static deployment is used, and the same browser/WebSocket verification.
