"""Live Sarvam TTS checks for M5.8. Skips when SARVAM_API_KEY is missing. Never fabricates results."""

from __future__ import annotations

import base64
import os
import time
import unittest

from backend.clients.provider_clients import sarvam_tts_to_base64
from backend.config.settings import SARVAM_API_KEY

LANGS = (
    ("en-IN", "Yes, SVIT has several technical clubs."),
    ("kn-IN", "ಇಲ್ಲಿನ ಅಧ್ಯಾಪಕರು ಬೆಂಬಲ ನೀಡುತ್ತಾರೆ."),
    ("hi-IN", "यहाँ के शिक्षक सहायक और अनुभवी हैं।"),
    ("ta-IN", "இங்கே ஆசிரியர்கள் ஆதரவாக இருக்காங்க."),
    ("te-IN", "ఇక్కడ ఉపాధ్యాయులు సహాయకారులు."),
    ("ml-IN", "ഇവിടുത്തെ അധ്യാപകർ പിന്തുണ നൽകുന്നു."),
)


def _is_riff(b64: str) -> bool:
    try:
        raw = base64.b64decode(b64, validate=False)
    except Exception:
        return False
    return len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WAVE"


_RUN_LIVE_SARVAM = os.getenv("RUN_LIVE_SARVAM_TESTS", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


@unittest.skipUnless(
    bool(SARVAM_API_KEY) and _RUN_LIVE_SARVAM,
    "live Sarvam TTS requires SARVAM_API_KEY and RUN_LIVE_SARVAM_TESTS=1",
)
class TestM58LiveSarvam(unittest.IsolatedAsyncioTestCase):
    async def test_short_phrases_all_six_languages(self) -> None:
        results: list[dict] = []
        for lang, text in LANGS:
            t0 = time.perf_counter()
            audio = await sarvam_tts_to_base64(text, lang)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            ok = bool(audio) and _is_riff(audio or "")
            raw_len = len(base64.b64decode(audio)) if audio else 0
            results.append(
                {
                    "lang": lang,
                    "http_audio": ok,
                    "generation_ms": round(elapsed_ms, 1),
                    "bytes": raw_len,
                    "validation": "RIFF/WAV" if ok else "FAILED",
                }
            )
            self.assertTrue(ok, msg=f"live Sarvam failed for {lang}: {results[-1]}")
        print("M58_LIVE_SARVAM", results)


if __name__ == "__main__":
    unittest.main()
